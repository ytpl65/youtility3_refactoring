from asyncio.log import logger
from pprint import pformat
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic.base import View
from django.contrib import messages
from django.http import JsonResponse, QueryDict, response as rp
from django.urls import reverse
from apps.activity  import models as am
from apps.peoples import utils as putils
from apps.core import utils
from apps.activity.forms import QsetBelongingForm
from apps.reports import forms as rp_forms
import logging
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
                type='SITEREPORTTEMPLATE'
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
                parent = int(R['parent'])
            ).values(
                'id', 'qsetname', 'asset_id', 'enable', 'seqno', 'parent',
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
                    P['related'], P['fields'],P['initial']['type']
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
                    P['related'], P['fields'], P['initial']['type'])
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
                    data, P, msg, int(pk))
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
        

