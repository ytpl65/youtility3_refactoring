from asyncio.log import logger
from pprint import pformat
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.generic.base import View
from django.contrib import messages
from django.http import JsonResponse, QueryDict, response as rp, FileResponse, HttpResponseRedirect, HttpResponse
from io import BytesIO
from django.template.loader import render_to_string
from django.templatetags.static import static
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from django.urls import reverse
from apps.onboarding import models as on
from apps.activity  import models as am
from apps.peoples import utils as putils
from apps.core import utils
from apps.activity.forms import QsetBelongingForm
from apps.reports import forms as rp_forms
import logging, subprocess, os
import logging, subprocess, os
from background_tasks.tasks import send_report_on_email, create_report_history
from django.contrib import messages as msg
from django.apps import apps
from django.urls import reverse_lazy
from django.conf import settings
import pandas as pd, xlsxwriter
from apps.reports import utils as rutils
from .models import ScheduleReport, GeneratePDF
from django_weasyprint.views import WeasyTemplateView
from django.db import IntegrityError
from background_tasks.tasks import create_save_report_async
from background_tasks.report_tasks import remove_reportfile
from celery.result import AsyncResult
import time, base64, sys, json, os
from frappeclient import FrappeClient
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from dateutil import parser
import fitz  # PyMuPDF
log = logging.getLogger('__main__')
# Create your views here.

class RetriveSiteReports(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'reports/sitereport_list.html'

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response, requestData= None, request.GET
        if requestData.get('template'):
            return render(request, self.template_path)
        try:
            objs = self.model.objects.get_sitereportlist(request)
            utils.printsql(objs)
            response = rp.JsonResponse({'data':list(objs)}, status = 200, encoder=utils.CustomJsonEncoderWithDistance)
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response


class RetriveIncidentReports(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'reports/incidentreport_list.html'

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response, requestData= None, request.GET
        if requestData.get('template'):
            return render(request, self.template_path)
        try:
            objs, atts = self.model.objects.get_incidentreportlist(request)
            response = rp.JsonResponse({'data':list(objs), 'atts':list(atts)}, status = 200)
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

class MasterReportTemplateList(LoginRequiredMixin, View):
    model         = am.QuestionSet
    template_path = None
    fields        = ['id', 'qsetname', 'enable']
    type          = None

    def get(self, request, *args, **kwargs):
        resp, R, objects = None, request.GET, am.QuestionSet.objects.none()
        filtered = None
        if R.get('template'):
            return render(request, self.template_path)
        try:
            objects = am.QuestionSet.objects.filter(
                type='SITEREPORT'
            ).values('id', 'qsetname', 'enable')
            count = objects.count()
            if count:
                log.info('Site report template objects %s retrieved from db', (count or "No Records!"))
                objects, filtered = utils.get_paginated_results(R, objects, count, self.fields,
                [], self.model)
            filtered = count
            log.info('Results paginated'if count else "")
            resp = rp.JsonResponse(data = {
                'draw':R['draw'], 'recordsTotal':count, 'data' : list(objects), 
                'recordsFiltered': filtered
            }, status = 200)
        except Exception:
            log.critical('something went wrong', exc_info = True)
            return redirect('/dashboard')
        return resp


class MasterReportForm(LoginRequiredMixin, View):
    template_path = None
    form_class    = None
    subform       = QsetBelongingForm
    model         = am.QuestionSet
    initial       = {
        'type'  :None
    }
    viewname = None

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        utils.PD(get = R)
        if R.get('template'):
            # return empty form if no id
            if not R.get('id'):
                log.info("create a %s form requested", self.viewname)
                cxt = {'reporttemp_form': self.form_class(request = request, initial = self.initial),
                       'qsetbng':self.subform()}
                return render(request, self.template_path, context = cxt)

            # return for with instance loaded
            if R.get('id') or kwargs.get('id'):
                import json
                pk = R['id'] or kwargs.get('id')
                obj = self.model.objects.get(id = pk)
                # self.initial.update({
                #     'buincludes': [8,6],
                # })
                form = self.form_class(instance = obj, initial = self.initial, request = request)
                cxt = {'reporttemp_form':form, 'qsetbng':self.subform()}
                return render(request, self.template_path, context = cxt)

        # return reports for list view
        elif R.get('get_reports'):
            resp = self.get_reports(R)
        return resp

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('%s form submitted', self.viewname)
        R, create = QueryDict(request.POST), True
        utils.PD(post = R)
        response = None
        # process already existing data for update
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                request = request, instance = obj, data = request.POST)
            create = False
            log.info("retrieved existing %s template:= '%s'", obj.qsetname, obj.id)

        # process new data for creation
        else:
            form = self.form_class(data = request.POST, request = request, initial = self.initial)
            log.info("new %s submitted following is the form-data:\n%s\n", self.viewname, pformat(form.data))

        # check for validation
        try:
            if form.is_valid():
                response = self.process_valid_form(request, form, create)
            else:
                response = self.process_invalid_form(form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_form(self, request, form, create):
        resp = None
        log.info("guard tour form processing/saving [ START ]")
        import json
        try:
            utils.PD(cleaned = form.data)
            report = form.save(commit = False)
            report.buincludes = json.dumps(request.POST.getlist('buincludes', []))
            report.site_grp_includes = json.dumps(request.POST.getlist('site_grp_includes', []))
            report.site_type_includes = json.dumps(request.POST.getlist('site_type_includes', []))
            report.parent_id  = -1
            report.save()
            report = putils.save_userinfo(report, request.user, request.session, create = create)
            log.debug("report saved:%s", (report.qsetname))
        except Exception as ex:
            log.critical("%s form is failed to process", self.viewname, exc_info = True)
            resp = rp.JsonResponse(
                {'errors': "saving %s template form failed..."%self.viewname}, status = 404)
            raise ex
        else:
            log.info("%s template form is processed successfully", self.viewname)
            resp = rp.JsonResponse({'msg': report.qsetname,
                'url': reverse("reports:sitereport_template_form"),
                'id':report.id},
                status = 200)
        log.info("%s template form processing/saving [ END ]", self.viewname)
        return resp

    @staticmethod
    def process_invalid_form(form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    def get_reports(self, R):
        qset,count = [], 0
        if parent := R.get('parent_id'):
            qset = self.model.objects.filter(  
                parent_id = parent
            ).values('id', 'qsetname', 'asset_id', 'seqno')
            count = qset.count()
        logger.info('site reports found for the parent with id %s'%R['id'] if qset else "Not found any reports")
        resp = {
            'data':list(qset)
        }
        return JsonResponse(data = resp, status = 200)

class MasterReportBelonging(LoginRequiredMixin, View):
    model = am.QuestionSet
    def get(self, request, *args, **kwargs):
        R = request.GET
        if R.get('dataSource') == 'sitereporttemplate'  and R.get('parent'):
            objs = self.model.objects.filter(
                parent_id = int(R['parent'])
            ).values(
                'id', 'qsetname',  'enable', 'seqno', 'parent_id',
                'type', 'bu_id', 'buincludes', 'assetincludes', 'site_grp_includes',
                'site_type_includes'
            )

    pass

class SiteReportTemplateForm(MasterReportForm):
    template_path = MasterReportForm.template_path
    form_class    = MasterReportForm.form_class
    viewname    = 'site report'
    initial       = MasterReportForm.initial
    model         = MasterReportForm.model
    template_path = "reports/sitereport_tempform.html"
    form_class    = rp_forms.SiteReportTemplate
    initial.update({'type':am.QuestionSet.Type.SITEREPORTTEMPLATE})

class IncidentReportTemplateForm(MasterReportForm):
    template_path = MasterReportForm.template_path
    form_class    = MasterReportForm.form_class
    initial       = MasterReportForm.initial
    model         = MasterReportForm.model
    template_path = "reports/incidentreport_tempform.html"
    form_class    = rp_forms.IncidentReportTemplate
    initial       = {
        'type':am.QuestionSet.Type.INCIDENTREPORTTEMPLATE
    }



class SiteReportTemplate(MasterReportTemplateList):
    type          = MasterReportTemplateList.type
    template_path = MasterReportTemplateList.template_path
    type          = am.QuestionSet.Type.SITEREPORTTEMPLATE
    template_path = 'reports/sitereport_template_list.html'

class IncidentReportTemplate(MasterReportTemplateList):
    type          = MasterReportTemplateList.type
    template_path = MasterReportTemplateList.template_path
    type          = am.QuestionSet.Type.INCIDENTREPORTTEMPLATE
    template_path = 'reports/incidentreport_template_list.html'


class ConfigSiteReportTemplate(LoginRequiredMixin, View):
    params = {
        'template_form': "reports/sitereport_tempform.html",
        'template_list': 'reports/sitereport_template_list.html',
        "model":am.QuestionSet,
        'form_class':rp_forms.SiteReportTemplate,
        "initial":{
            'type':am.QuestionSet.Type.SITEREPORTTEMPLATE
        },
        'related':[],
        'fields':['id', 'qsetname', 'enable']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('template'):return render(request, P['template_list'])

        if R.get('action') == 'list':
            objs =  P['model'].objects.get_configured_sitereporttemplates(
                    request, P['related'], P['fields'],P['initial']['type']
                )
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        if R.get('action') == 'form':
            cxt = {'reporttemp_form':P['form_class'](initial = P['initial'], request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)
        
        if R.get('action') == 'get_sections':
            parent_id = 0 if R['parent_id'] == 'undefined' else R['parent_id']
            qset = P['model'].objects.get_qset_with_questionscount(parent_id)
            return rp.JsonResponse({'data':list(qset)}, status=200)
        
        if R.get('action') == 'delete' and R.get('id') not in [None, 'None']:
            P['model'].objects.filter(id=R['id']).update(enable=False)
            log.info(f'site report template with this id : {R["id"]} is deleted')
            return rp.JsonResponse(data={},status=200)
        
        if R.get('id'):
            obj = utils.get_model_obj(R['id'], request, {'model': P['model']})
            cxt = {'reporttemp_form':P['form_class'](instance=obj, request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)
        
        
         
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = "site report template updated successfully"
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), {'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, data)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp
    
    @staticmethod
    def handle_valid_form(form, request, data):
        try:
            print("Request", request.POST)
            print("Data", data)
            with transaction.atomic(using=utils.get_current_db_name()):
                template = form.save()
                template.parent_id = data.get('parent_id', 1)
                template = putils.save_userinfo(template, request.user, request.session)
                return rp.JsonResponse({'parent_id':template.id}, status=200)
        except Exception:
            return utils.handle_Exception(request)
        
        
class ConfigIncidentReportTemplate(LoginRequiredMixin, View):
    params = {
        'template_form': "reports/incidentreport_tempform.html",
        'template_list': 'reports/incidentreport_template_list.html',
        "model":am.QuestionSet,
        'form_class':rp_forms.SiteReportTemplate,
        "initial":{
            'type':am.QuestionSet.Type.INCIDENTREPORTTEMPLATE
        },
        'related':[],
        'fields':['id', 'qsetname', 'enable']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('template'):return render(request, P['template_list'])

        if R.get('action') == 'list':
            objs =  P['model'].objects.get_configured_sitereporttemplates(
                    request, P['related'], P['fields'], P['initial']['type'])
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        if R.get('action') == 'form':
            cxt = {'reporttemp_form':P['form_class'](initial = P['initial'], request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)

        if R.get('action') =='loadQuestions':
            qset =  am.Question.objects.questions_of_client(request, R)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)
        
        if R.get('action') == 'get_sections':
            parent_id = 0 if R['parent_id'] == 'undefined' else R['parent_id']
            qset = P['model'].objects.get_qset_with_questionscount(parent_id)
            return rp.JsonResponse({'data':list(qset)}, status=200)
        
        if R.get('action') == 'delete' and R.get('id') not in [None, 'None']:
            P['model'].objects.filter(id=R['id']).update(enable=False)
            log.info(f'site report template with this id : {R["id"]} is deleted')
            return rp.JsonResponse(data={},status=200)
        
        if R.get('id'):
            obj = utils.get_model_obj(R['id'], request, {'model': P['model']})
            cxt = {'reporttemp_form':P['form_class'](instance=obj, request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)
        
        
         
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = "incident report template updated successfully"
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), {'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, data)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp
    
    @staticmethod
    def handle_valid_form(form, request, data):
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                template = form.save()
                template.parent_id = data.get('parent_id', 1)
                template = putils.save_userinfo(template, request.user, request.session)
                return rp.JsonResponse({'parent_id':template.id}, status=200)
        except Exception:
            return utils.handle_Exception(request)

class ConfigWorkPermitReportTemplate(LoginRequiredMixin, View):
    params = {
        'template_form': "reports/workpermitreport_tempform.html",
        'template_list': 'reports/workpermitreport_template_list.html',
        "model":am.QuestionSet,
        'form_class':rp_forms.SiteReportTemplate,
        "initial":{
            'type':am.QuestionSet.Type.WORKPERMITTEMPLATE
        },
        'related':[],
        'fields':['id', 'qsetname', 'enable']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('template'):return render(request, P['template_list'])

        if R.get('action') == 'list':
            objs =  P['model'].objects.get_configured_sitereporttemplates(
                    P['related'], P['fields'], P['initial']['type']
                )
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        if R.get('action') == 'form':
            cxt = {'reporttemp_form':P['form_class'](initial = P['initial'], request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)

        if R.get('action') =='loadQuestions':
            qset =  am.Question.objects.questions_of_client(request, R)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)
        
        if R.get('action') == 'get_sections':
            parent_id = 0 if R['parent_id'] == 'undefined' else R['parent_id']
            qset = P['model'].objects.get_qset_with_questionscount(parent_id)
            return rp.JsonResponse({'data':list(qset)}, status=200)
        
        if R.get('action') == 'delete' and R.get('id') not in [None, 'None']:
            P['model'].objects.filter(id=R['id']).update(enable=False)
            log.info(f'site report template with this id : {R["id"]} is deleted')
            return rp.JsonResponse(data={},status=200)
        
        if R.get('id'):
            obj = utils.get_model_obj(R['id'], request, {'model': P['model']})
            cxt = {'reporttemp_form':P['form_class'](instance=obj, request = request), 'test':rp_forms.TestForm}
            return render(request, P['template_form'], cxt)
        
        
         
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = f'{self.label}_view'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), {'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, data)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp
    
    @staticmethod
    def handle_valid_form(form, request, data):
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                template = form.save()
                template.parent_id = data.get('parent_id', 1)
                template = putils.save_userinfo(template, request.user, request.session)
                return rp.JsonResponse({'parent_id':template.id}, status=200)
        except Exception:
            return utils.handle_Exception(request)



    
class DownloadReports(LoginRequiredMixin, View):
    PARAMS = {
        'template_form':"reports/report_export_form.html",
        'form':rp_forms.ReportForm,
        'ReportEssentials':rutils.ReportEssentials,
        "nodata":"No data found matching your report criteria.\
        Please check your entries and try generating the report again"
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.PARAMS
        S = request.session
        if R.get('action') == 'form_behaviour':
            return self.form_behaviour(R)
        
        if R.get('action') == 'get_site' and R.get('of_site') and R.get('of_type'):
            qset = on.TypeAssist.objects.filter(
                bu_id = R['of_site'],
                client_id = S['client_id'],
                tatype__tacode = R['of_type']
                ).values('id','taname').distinct()
            return rp.JsonResponse(
                data = {'options': list(qset)},status = 200
            )

        if R.get('action') == 'get_asset' and R.get('of_type'):
            qset = am.Asset.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type_id=R['of_type']).values('id', 'assetname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )

        if R.get('action') == 'get_qset' and R.get('of_asset'):
            qset = am.QuestionSet.objects.filter(
                client_id=S['client_id'],
                bu_id = S['bu_id'],
                type__in=['CHECKLIST', 'ASSETMAINTENANCE'],
                parent_id=1,
                enable=True,
                assetincludes__contains=[R.get('of_asset')]).values('id', 'qsetname').distinct()
            return rp.JsonResponse(
                data={'options':list(qset)}, status=200
            )
    

        form = P['form'](request=request)
        cxt = {
            'form':form,
        }
        return render(request, P['template_form'], context=cxt)
    
    def post(self, request, *args, **kwargs):
        form = self.PARAMS['form'](data=request.POST, request=request)
        if not form.is_valid():
            return render(request, self.PARAMS['template_form'], {'form': form})
        log.info('form is valid')
        formdata = form.cleaned_data
        log.info(f"Formdata submitted by user: {pformat(formdata)}")

        try:
            return self.export_report(formdata, dict(request.session), request, form)
        except Exception as e:
            log.critical("Something went wrong while exporting report", exc_info=True)
            messages.error(request, "Error while exporting report", 'alert-danger')
        return render(request, self.PARAMS['template_form'], {'form': form})

    def export_report(self, formdata, session, request, form):
        returnfile = formdata.get('export_type') == 'SEND'
        if returnfile:
            messages.success(
                request,
                "Report has been processed for sending on email. You will receive the report shortly.",
                'alert-success')
        else:
            messages.success(request,
                            "Report has been processed to download. Check status with 'Check Report Status' button",
                            'alert-success')
        task_id = create_save_report_async.delay(formdata, session['client_id'], request.user.email, request.user.id)
        return render(request, self.PARAMS['template_form'], {'form': form, 'task_id':task_id})



    def form_behaviour(self, R):
        report_essentials = self.PARAMS['ReportEssentials'](report_name=R['report_name'])
        return rp.JsonResponse({'behaviour':report_essentials.behaviour_json})


@login_required
def return_status_of_report(request):
    if request.method == 'GET':
        form = rp_forms.ReportForm(request=request)
        template = "reports/report_export_form.html"
        cxt = {
            'form':form,
        }
        R = request.GET
        task = AsyncResult(R['task_id'])
        if task.status == 'SUCCESS':
            result = task.get()
            if result['status'] == 200 and result.get('filepath'):
                if not os.path.exists(result['filepath']):
                    messages.error(request, "Report file not found on server", 'alert-danger')
                    return render(request, template, cxt)
                else:
                    try:
                        file = open(result['filepath'], 'rb')
                        response = FileResponse(file)
                        filename = result['filename']
                        response['Content-Disposition'] = f'attachment; filename="{filename}"'
                        return response
                    finally:
                        remove_reportfile(result['filepath'])
            if result['status'] == 404:
                messages.error(request,  result['message'], 'alert-danger')
                return render(request, template, cxt)
            if result['status'] == 500:
                messages.error(request, result['message'], 'alert-danger')
                return render(request, template, cxt)
            if result['status'] == 201:
                messages.success(request, result['message'], 'alert-success')
                return render(request, template, cxt)
        elif task.status == 'FAILURE':
            messages.error(request, "Report generation failed. Please try again later.", 'alert-danger')
            return render(request, template, cxt)
        else:
            messages.info(request, "Report is still in queue", 'alert-info')
            return render(request, template, cxt)
            
                
    
class DesignReport(LoginRequiredMixin, View):
    # change this file according to your design
    design_file = "reports/pdf_reports/testdesign.html"
    
    
    def get(self, request):
        R = request.GET  # Presuming you will use this for something later
        if R.get('text') == 'html': return render(request, self.design_file)
        html_string = render_to_string(self.design_file, request=request)
        # pandoc rendering
        if R.get('text') == 'pandoc': return self.render_using_pandoc(html_string)
        # excel file
        if R.get('text') == 'xl':
            from apps.onboarding.models import Bt
            data = Bt.objects.get_sample_data()
            return self.render_excelfile(data)
        # defalult weasyprint
        return self.render_using_weasyprint(html_string)

    def render_using_weasyprint(self, html_string):
        html = HTML(string=html_string)
        # Specify the path to your local CSS file
        css = CSS(filename='frontend/static/assets/css/local/reports.css')
        font_config = FontConfiguration()
        pdf = html.write_pdf(stylesheets=[css], font_config=font_config)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="report.pdf"'
        return response
    
    def render_using_pandoc(self, html_string):
        with open("temp.html", "w") as file:
            file.write(html_string)

        # Specify the path to your local CSS file
        command = [
            'pandoc',
            'temp.html',
            '-o',
            'output.pdf',
            '--css=frontend/static/assets/css/local/reports.css',
            '--pdf-engine=xelatex'  # Replace with your preferred PDF engine
        ]
        subprocess.run(command)

        with open("output.pdf", "rb") as file:
            pdf = file.read()
        
        # Delete the temporary files
        os.remove("temp.html")
        os.remove("output.pdf")

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="report.pdf"'

        return response
    

    def render_excelfile(self, data):
        # Format data as a Pandas DataFrame
        df = pd.DataFrame(list(data))

        # Create a Pandas Excel writer using XlsxWriter as the engine and BytesIO as file-like object
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Sheet1', index=False, startrow=2, header=True)

        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        # Autofit the columns to fit the data
        for i, width in enumerate(self.get_col_widths(df)):
            worksheet.set_column(i, i, width)

        # Define the format for the merged cell
        merge_format = workbook.add_format({
            'bg_color': '#c1c1c1',
            'bold': True,
        })

        # Write the additional content with the defined format
        additional_content = "Client: Capgemini,  Report: Task Summary,  From 01-Jan-2023 To 30-Jan-2023"
        worksheet.merge_range("A1:E1", additional_content, merge_format)

        # Close the Pandas Excel writer and output the Excel file
        writer.save()

        # Rewind the buffer
        output.seek(0)

        # Set up the HTTP response with the appropriate Excel headers
        response = HttpResponse(
            output, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="downloaded_data.xlsx"'
        return response

    def get_col_widths(self, dataframe):
        """
        Get the maximum width of each column in a Pandas DataFrame.
        """
        return [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]



class ScheduleEmailReport(LoginRequiredMixin, View):
    P = {
        'template_form':"reports/schedule_email_report.html",
        'template_list':"reports/schedule_email_list.html",
        'form_class':rp_forms.EmailReportForm,
        'popup_form':rp_forms.ReportForm,
        'model':ScheduleReport,
        'ReportEssentials':rutils.ReportEssentials,
        "nodata":"No data found matching your report criteria.\
        Please check your entries and try generating the report again"
    }
    
    def get(self, request, *args, **kwargs):
        R, S = request.GET, request.session
        if R.get('template'):
            return render(request, self.P['template_list'])
        
        if R.get('id'):
            obj = utils.get_model_obj(R['id'], request, {'model': self.P['model']})
            params_initial = obj.report_params
            cxt = {
                'form':self.P['form_class'](instance=obj, request = request),
                'popup_form':self.P['popup_form'](request=request, initial=params_initial)}
            return render(request, self.P['template_form'], cxt)
        
        if R.get('action') == 'list':
            data = self.P['model'].objects.filter(bu_id=S['bu_id']).values()
            return rp.JsonResponse({'data':list(data)}, status=200)
        
        if R.get('action') == 'form':
            form = self.P['form_class'](request=request)
            form2 = self.P['popup_form'](request=request)
            cxt = {'form':form, 'popup_form': form2}
            return render(request, self.P['template_form'], context=cxt)
        
    
    def post(self, request, *args, **kwargs):
        data = QueryDict(request.POST['formData'])
        report_params = QueryDict(request.POST['report_params'])
        P = self.P
        try:
            if pk := request.POST.get('pk', None):
                msg = f"updating record with id {pk}"
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), {'request':request})
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                obj = form.save(commit=False)
                obj = putils.save_userinfo(obj, request.user, request.session)
                obj.report_params = report_params
                obj.save()
                return rp.JsonResponse({'pk':obj.id}, status=200)
            else:
                cxt = {'errors': form.errors}
                return utils.handle_invalid_form(request, self.P, cxt)
        except IntegrityError as e: 
            log.info("Integrity error occured")
            cxt = {'errors': "Scheduled report with these criteria is already exist"}
            return utils.handle_invalid_form(request, self.P, cxt)
        
class GeneratePdf(LoginRequiredMixin, View):
    PARAMS = {
        'template_form':"reports/generate_pdf/generate_pdf_file.html",
        'form':rp_forms.GeneratePDFForm,
    }
    def get(self, request, *args, **kwargs):
        import uuid
        P = self.PARAMS
        form = P['form'](request=request)
        cxt = {
            'form':form,
            'ownerid' : uuid.uuid4()
        }
        return render(request, P['template_form'], context=cxt)
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            file_name = data['file_name']
            file_path = rutils.find_file(data['file_name'])
            if file_path:
                if data["document_type"] == 'PF':
                    uan_list= getAllUAN(data['company'], data['customer'], data['site'], data['period_from'])[0]
                else:
                    uan_list= getAllUAN(data['company'], data['customer'], data['site'], data['period_from'])[1]
                input_pdf_path = file_path
                output_pdf_path = rutils.trim_filename_from_path(input_pdf_path) + 'downloaded_file.pdf'
                if len(uan_list) != 0 :
                    highlight_text_in_pdf(input_pdf_path, output_pdf_path, uan_list)
                
                    # Generate a response with the PDF file
                    with open(output_pdf_path, 'rb') as pdf:
                        pdf_content = pdf.read()
                    response = HttpResponse(pdf_content, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Highlighted-{file_name}.pdf"'
                    os.remove(output_pdf_path)
                    return response
                return HttpResponse("UAN Not Found", status=404)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
def get_data(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        if data:
            customer = getCustomer(data['company'])
            period   = getPeriod(data['company'])
            if 'customer_code' in data:
                site     = getCustomersSites(data['company'],data['customer_code'])
                return JsonResponse({'success': True, 'data': [{"name": "", "bu_name": ""}] + site})
            return JsonResponse({'success': True, 'data': [{"customer_code": "", "name": ""}] + customer, "period": [{'end_date': "", "name": None, "start_date": ""}] + period })
        else:
            return JsonResponse({'success': False})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    

def getClient(company):
    client= None
    server_url= None
    secerate_key= None
    api_key= None
    if company == 'SPS':
        server_url = 'http://leave.spsindia.com:8007'
        secerate_key= 'c7047cc28b4a14e'
        api_key= '3a6bfc7224a228c'
        client = FrappeClient(server_url, api_key=api_key, api_secret=secerate_key)
    elif company == 'SFS':
        server_url = 'http://leave.spsindia.com:8008'
        secerate_key= '8dc1421ac748917'
        api_key= 'ca9b240aa73a9b8'
        client = FrappeClient(server_url, api_key=api_key, api_secret=secerate_key)
    elif company == 'TARGET':
        server_url = 'http://leave.spsindia.com:8002'
        secerate_key= 'ff6806a3f9bf5a8'
        api_key= '87bf164dd684d03'
        client = FrappeClient(server_url, api_key=api_key, api_secret=secerate_key)
    else:
        return None
    client = FrappeClient(server_url, api_key=api_key, api_secret=secerate_key)
    return client

def getCustomer(company):
    filters= {'disabled': 0}
    fields= ['name', 'customer_code']
    frappe_data = get_frappe_data(company, 'Customer', filters, fields)
    return frappe_data

def getPeriod(company):
    filters= {'status': 'Active'}
    fields= ['name', 'start_date', 'end_date']
    frappe_data = get_frappe_data(company, 'Salary Payroll Period', filters, fields)
    return frappe_data

def getCustomersSites(company, customer_code):
    filters= {'status': 'Active', 'business_unit': customer_code, 'bu_type': 'Site'}
    fields= ['name', 'bu_name']
    frappe_data = get_frappe_data(company, 'Business Unit', filters, fields)
    return frappe_data
    # if client:
    #     sites = client.get_list('Salary Payroll Period', filters=filters, fields=fields)
    #     print("!!!!!!",sites)
    #     return sites

def getAllUAN(company, customer_code, site_code, periods):
    filters= None
    if site_code:
        filters= {'customer_code': customer_code, 'site': site_code, 'period': ['in', periods]}
    else:
        filters= {'customer_code': customer_code, 'period': ['in', periods]}
    fields= ['emp_id']
    client= getClient(company)
    processed_payroll_emp_list = get_frappe_data(company, 'Processed Payroll', filters, fields) or []
    difference_processed_payroll_emp_list = get_frappe_data(company, 'Difference Processed Payroll', filters, fields) or []
    emp_id_list= []
    if processed_payroll_emp_list or difference_processed_payroll_emp_list:
        for row in processed_payroll_emp_list + difference_processed_payroll_emp_list:
            emp_id_list.append(row["emp_id"])
    filters= {'name': ['in', emp_id_list]}
    fields= ['uan_number', "esi_number"]
    uan_data= get_frappe_data(company, 'Employee', filters, fields) or []
    return [uan_detail['uan_number'].strip() if uan_detail['uan_number'] else None for uan_detail in uan_data], [uan_detail['esi_number'].strip() if uan_detail['esi_number'] else None for uan_detail in uan_data]

def highlight_text_in_pdf(input_pdf_path, output_pdf_path, texts_to_highlight):
    import fitz  # PyMuPDF library

    # Open the PDF
    document = fitz.open(input_pdf_path)
    pages_to_keep = []
    orange_color = (1, 0.647, 0)  # RGB values for orange

    # Function to handle text splitting
    def find_and_highlight_text(page, text):
        """Search for text and highlight it even if it's split across lines or cells."""
        words = page.get_text("words")  # Extract words as bounding boxes
        for i, word in enumerate(words):
            if text.startswith(word[4]):
                combined_text = word[4]
                bbox = [word[:4]]  # Collect bounding boxes
                j = i + 1

                # Try to combine subsequent words
                while j < len(words) and not combined_text == text:
                    combined_text += words[j][4]
                    bbox.append(words[j][:4])
                    j += 1

                if combined_text == text:
                    # Highlight the combined bounding boxes
                    for box in bbox:
                        highlight = page.add_highlight_annot(fitz.Rect(box))
                        highlight.set_colors(stroke=orange_color)  # Set highlight color
                        highlight.update()
                    return True
        return False

    # Check and highlight text on each page
    for page_num in range(document.page_count):
        page = document[page_num]
        page_has_highlight = False
        for text in texts_to_highlight:
            if text and find_and_highlight_text(page, text):
                page_has_highlight = True

        if page_has_highlight or page_num == 0:  # Always keep the first page
            pages_to_keep.append(page_num)

    # Ensure the last page is included
    if document.page_count - 1 not in pages_to_keep:
        pages_to_keep.append(document.page_count - 1)

    # Create a new document with all pages to be kept
    new_document = fitz.open()
    for page_num in pages_to_keep:
        new_document.insert_pdf(document, from_page=page_num, to_page=page_num)

    # Save the updated PDF
    new_document.save(output_pdf_path)
    new_document.close()
    document.close()

# def highlight_text_in_pdf(input_pdf_path, output_pdf_path, texts_to_highlight):        
#     # Open the PDF
#     document = fitz.open(input_pdf_path)
#     pages_to_keep = []
#     orange_color = (1, 0.647, 0)  # RGB values for orange
#     # Check and highlight text on the first page
#     if document.page_count > 0:
#         first_page = document[0]
#         first_page_has_highlight = False

#         for text in texts_to_highlight:
#             if text:
#                 text_instances = first_page.search_for(text)
#                 if text_instances:
#                     first_page_has_highlight = True
#                     for inst in text_instances:
#                         highlight = first_page.add_highlight_annot(inst)
#                         highlight.set_colors(stroke=orange_color)  # Set highlight color
#                         highlight.update()
        
#         # Always keep the first page
#         pages_to_keep.append(0)

#     # Check and highlight text on subsequent pages
#     for page_num in range(1, document.page_count):  # Start from page 1
#         page = document[page_num]
#         page_has_highlight = False
#         for text in texts_to_highlight:
#             if text:
#                 text_instances = page.search_for(text)
#                 if text_instances:
#                     page_has_highlight = True
#                     for inst in text_instances:
#                         highlight = page.add_highlight_annot(inst)
#                         highlight.set_colors(stroke=orange_color)  # Set highlight color
#                         highlight.update()
#         if page_has_highlight:
#             pages_to_keep.append(page_num)

#     # Create a new document with all pages to be kept
#     new_document = fitz.open()
#     for page_num in pages_to_keep:
#         new_document.insert_pdf(document, from_page=page_num, to_page=page_num)

#     # Save the updated PDF
#     new_document.save(output_pdf_path)
#     new_document.close()
#     document.close()

# # Example usage
# input_pdf_path = '/home/vivek/vivek/highlight_pdf/ECR PF_ICICI_APR 2024THTHA0011774000.pdf'
# output_pdf_path = '/home/vivek/vivek/highlight_pdf/ECR PF_ICICI_APR 2024THTHA0011774000_test1.pdf'
# text_to_highlight = ['101196185843', '101267881769']

# highlight_text_in_pdf(input_pdf_path, output_pdf_path, text_to_highlight)

def get_frappe_data(company, document_type, filters, fields):
    client= getClient(company)
    all_frappe_data= []
    if client:
        start = 0
        limit = 100
        while True:
            frappe_data = client.get_list(document_type, filters=filters, fields=fields, limit_start=start, limit_page_length=limit)
            if not frappe_data:
                break
            all_frappe_data.extend(frappe_data)
            start += limit
        return all_frappe_data
    
def upload_pdf(request):
    if 'img' not in request.FILES:
        return
    people_id = request.POST['peopleid']
    home_dir = settings.MEDIA_ROOT
    foldertype = request.POST["foldertype"]
    
    filename = people_id + "-" + os.path.splitext(request.FILES['img'].name)[0] + os.path.splitext(request.FILES['img'].name)[1]
    fullpath = f'{home_dir}/{foldertype}/'
    if not os.path.exists(fullpath):    
        os.makedirs(fullpath)
    fileurl = f'{fullpath}{filename}'
    try:
        if not os.path.exists(fileurl):
            with open(fileurl, 'wb') as temp_file:
                temp_file.write(request.FILES['img'].read())
                temp_file.close()
    except Exception as e:
        logger.critical(e, exc_info=True)
        return False, None, None
    # return True, filename, fullpath
    response = {"filename": filename, "fullpath": fullpath}
    return HttpResponse(response, status=200)