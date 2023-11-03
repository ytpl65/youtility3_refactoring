from asyncio.log import logger
from pprint import pformat
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic.base import View
from django.contrib import messages
from django.http import JsonResponse, QueryDict, response as rp, FileResponse, HttpResponseRedirect, HttpResponse
from io import BytesIO
from django.template.loader import render_to_string
from weasyprint import HTML
from django.urls import reverse
from apps.activity  import models as am
from apps.peoples import utils as putils
from apps.core import utils
from apps.activity.forms import QsetBelongingForm
from apps.reports import forms as rp_forms
import logging
from background_tasks.tasks import execute_report, send_report_on_email, create_report_history
from django.contrib import messages as msg
from django.apps import apps
from django.urls import reverse_lazy
from django.conf import settings
import time, base64, sys, json
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
        ic(R)
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
                ic(pk)
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
                ic(pk)
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
        ic(R)
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
                ic(pk)
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



class ExportReports(LoginRequiredMixin, View):
    P = {
        'template_form':"reports/report_export_form.html",
        'form':rp_forms.ReportForm
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        if R.get('template'):
            form = P['form'](request=request)
            report_names = json.dumps(P['form'].report_templates)
            fields_map = json.dumps(form.get_fields_report_map())
            cxt = {
                'form':form,
                'report_names':report_names,
                'fields_map':fields_map
            }
            return render(request, P['template_form'], context=cxt)
        
    def post(self, request, *args, **kwargs):
        R,P = request.POST, self.P
        data = R
        form = P['form'](data = data, request=request)
        report_names = json.dumps(P['form'].report_templates)
        fields_map = json.dumps(form.get_fields_report_map())
        if not form.is_valid():
            print("form is not valid", form.errors)
            return render(request, P['template_form'], context={
                'form':form, 'report_names':report_names,
                'fields_map':fields_map})
        log.info('form is valid')
        formdata = form.cleaned_data
        params = self.prepare_parameters(formdata, request)
        result = execute_report(params, formdata)
        log.info(f'Report form data {formdata}')
        try:
            if result.status_code == 200:
                if formdata.get('export_type') == 'SEND': #send on email
                    log.info('report sending on mail')
                    encoded_data = base64.b64encode(result.content)
                    json_report_data = json.dumps({'report': encoded_data.decode('utf-8')})
                    send_report_on_email.delay(formdata, json_report_data)
                    time.sleep(2)
                    msg.success(request, "Report has been sent on mail successfully")
                    return render(request, P['template_form'], context={'form':form, 'report_names':report_names, 'fields_map':fields_map})
                
                if formdata.get('preview') == 'true': #preview report
                    log.info('previewing the file')
                    response = HttpResponse(result.content, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
                    return response
                
                response = FileResponse(BytesIO(result.content))
                response['Content-Disposition'] = f'attachment; filename="{formdata["report_name"]}.{formdata["format"]}"'
                return response #download report
            else:
                msg.error(request, "Failed to download the report, something went wrong")
                return HttpResponseRedirect(reverse('reports:exportreports') + "?template=true") #report-export failure
        except Exception as e:
            log.error("something went wron in export reports", exc_info=True)
            msg.error(request, "Failed to download the report, something went wrong")
            return render(request, P['template_form'], context={'form':form, 'report_names':report_names, 'fields_map':fields_map})
        finally:
            EI = sys.exc_info()
            create_report_history.delay(formdata, request.user.id, request.session['bu_id'], EI)

    
    def prepare_parameters(self, formdata, request):
        log.info("prepare params started")
        timezone, client_logo_url = self.get_other_common_params(request)
        common_params = [
            {"urlName":"timezone", "values":[timezone]},
            {"urlName":"connectionName", "values":[settings.KNOWAGE_DATASOURCE]},
            {"urlName":"CompanyName", "values":[settings.COMPANYNAME]},
            {"urlName":"clientname", "values":[request.session['clientname']]},
            {"urlName":"clientlogopath", "values":[client_logo_url]},
        ]
        
        report_params = self.return_report_params(formdata)
        report_params.extend(common_params)
        log.info('params prepared and returned')
        return report_params
        
        
    def get_other_common_params(self, request):
        from django.templatetags.static import static
        S          = request.session
        timezone   = utils.get_timezone(S['ctzoffset'])
        Attachment = apps.get_model('activity', 'Attachment')
        Bt         = apps.get_model('onboarding', 'Bt')
        uuid       = Bt.objects.filter(id = S['client_id']).values('uuid').first()['uuid']
        
        applogo_url         = request.build_absolute_uri(static('assets/media/images/logo.png'))
        clientlogo_att = Attachment.objects.get_att_given_owner(uuid, request)
        if clientlogo_att:
            clientlogo_filepath = settings.MEDIA_URL + clientlogo_att[0]['filepath'] + clientlogo_att[0]['filename']
        else:
            clientlogo_filepath = "No Client Logo"
        
        clientlogo_url      = request.build_absolute_uri(clientlogo_filepath)
        log.info("common parameters are returned")
        return timezone, clientlogo_url

    def return_report_params(self, formdata):
        if formdata.get('report_name') in [settings.KNOWAGE_REPORTS['TASKSUMMARY'],settings.KNOWAGE_REPORTS['TOURSUMMARY'],
                        settings.KNOWAGE_REPORTS['LISTOFTASKS'],settings.KNOWAGE_REPORTS['LISTOFINTERNALTOURS'],
                        settings.KNOWAGE_REPORTS['PPMSUMMARY'],settings.KNOWAGE_REPORTS['LISTOFTICKETS'], settings.KNOWAGE_REPORTS['WORKORDERLIST']]:
            return [
                 {"urlName":"fromdate", "values":[formdata['fromdate'].strftime('%d/%m/%Y')]},
                {"urlName":"uptodate", "values":[formdata['uptodate'].strftime('%d/%m/%Y')]},
                {"urlName":"siteids", "values":[formdata['site']]},
            ]
        if formdata.get('report_name') == settings.KNOWAGE_REPORTS['SITEREPORT']:
            return [
                {"urlName":"fromdate", "values":[formdata['fromdate'].strftime('%d/%m/%Y')]},
                {"urlName":"uptodate", "values":[formdata['uptodate'].strftime('%d/%m/%Y')]},
                {"urlName":"sgroupids", "values":[formdata['sitegroup']]},
            ]
            
        

class DesignReport(LoginRequiredMixin, View):
    # change this file according to your design
    design_file = "task_summary.html" 
    
    
    def get(self, request):
        R = request.GET
        return render(request, self.design_file)
        