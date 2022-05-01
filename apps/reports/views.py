from asyncio.log import logger
from pprint import pformat
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import View
from apps.activity  import models as am
from apps.onboarding  import models as om
from apps.peoples import utils as putils
from apps.core import utils as utils
from django.http import JsonResponse, QueryDict, response as rp
from django.urls import reverse
from django.contrib import messages
from apps.reports import forms as rp_forms
from django.db.models import Q
from django.shortcuts import redirect
from datetime import datetime, timedelta, timezone
import logging
from apps.activity.forms import QsetBelongingForm
from django.forms.models import model_to_dict
log = logging.getLogger('__main__')
# Create your views here.

class RetriveSiteReports(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'reports/sitereport_list.html'

    
    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        from apps.core.raw_queries import query
        response, requestData, objects = None, request.GET, am.Jobneed.objects.none()
        filtered=None
        if requestData.get('template'):
            return render(request, self.template_path)
        try:
            pdt1 = datetime.now(tz=timezone.utc) - timedelta(days=7)
            pdt2 = datetime.now(tz = timezone.utc)
            log.info('Retrieve siteReports view')
            pbs = om.Bt.objects.get_people_bu_list(request.user)
            tl = am.QuestionSet.objects.get_template_list(pbs)
            if pbs and tl: objects = self.model.objects.raw(query['sitereportlist'], [pbs, tl, pdt1, pdt2])
            count = objects.count()
            if count:
                log.info('Site report objects %s retrieved from db' % (count or "No Records!"))
                objects, filtered = utils.get_paginated_results(requestData, objects, count, self.fields,
                [], self.model)
            filtered=count
            log.info('Results paginated'if count else "")
            response = rp.JsonResponse(data = {
                'draw':requestData['draw'], 'recordsTotal':count, 'data' : list(objects), 
                'recordsFiltered': filtered
            }, status=200)
        except Exception:
            log.critical(
                'something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response





class MasterReportTemplateList(View, LoginRequiredMixin):
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
                log.info('Site report template objects %s retrieved from db' % (count or "No Records!"))
                objects, filtered = utils.get_paginated_results(R, objects, count, self.fields,
                [], self.model)
            filtered=count
            log.info('Results paginated'if count else "")
            resp = rp.JsonResponse(data = {
                'draw':R['draw'], 'recordsTotal':count, 'data' : list(objects), 
                'recordsFiltered': filtered
            }, status=200)
        except Exception:
            log.critical('something went wrong', exc_info=True)
            return redirect('/dashboard')
        return resp



class MasterReportForm(View, LoginRequiredMixin):
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
        utils.PD(get=R)
        if R.get('template'):
            #return empty form if no id
            if not R.get('id'):
                log.info("create a %s form requested"%self.viewname)
                cxt = {'reporttemp_form': self.form_class(request=request, initial=self.initial),
                       'qsetbng':self.subform(auto_id=False)}
                return render(request, self.template_path, context=cxt)
            
            #return for with instance loaded
            elif R.get('id') or kwargs.get('id'):
                import json
                pk = R['id'] or kwargs.get('id')
                obj = self.model.objects.get(id=pk)
                self.initial.update({
                    'buincludes': [8,6],
                })
                form = self.form_class(instance = obj, initial=self.initial, request=request)
                cxt = {'reporttemp_form':form, 'qsetbng':self.subform(auto_id=False)}
                return render(request, self.template_path, context=cxt)
        
        #return reports for list view
        elif R.get('get_reports'):
            resp = self.get_reports(R)
        return resp

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('%s form submitted'%self.viewname)
        R, create = QueryDict(request.POST), True
        utils.PD(post=R)
        response = None
        #process already existing data for update
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                request=request, instance=obj, data=request.POST)
            create=False
            log.info("retrieved existing %s template:= '%s'" %
                     (obj.qsetname, obj.id))
        
        #process new data for creation
        else:
            form = self.form_class(data=request.POST, request=request, initial=self.initial)
            log.info("new %s submitted following is the form-data:\n%s\n" %
                     (self.viewname, pformat(form.data)))
        
        #check for validation
        try:
            if form.is_valid():
                response = self.process_valid_form(request, form, create)
            else:
                response = self.process_invalid_form(form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info=True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status=404)
        return response

    def process_valid_form(self, request, form, create):
        resp = None
        log.info("guard tour form processing/saving [ START ]")
        import json
        try:
            utils.PD(cleaned=form.data)
            report = form.save(commit=False)
            report.buincludes = json.dumps(request.POST.getlist('buincludes', []))
            report.site_grp_includes = json.dumps(request.POST.getlist('site_grp_includes', []))
            report.site_type_includes = json.dumps(request.POST.getlist('site_type_includes', []))
            report.parent_id  = -1
            report.save()
            report = putils.save_userinfo(report, request.user, request.session, create=create)
            log.debug("report saved:%s"%(report.qsetname))
        except Exception as ex:
            log.critical("%s form is failed to process"%self.viewname, exc_info=True)
            resp = rp.JsonResponse(
                {'errors': "saving %s template form failed..."%self.viewname}, status=404)
            raise ex
        else:
            log.info("%s template form is processed successfully"%self.viewname)
            resp = rp.JsonResponse({'msg': report.qsetname,
                'url': reverse("reports:sitereport_template_form"),
                'id':report.id},
                status=200)
        log.info("%s template form processing/saving [ END ]"%self.viewname)
        return resp
    
    def process_invalid_form(self, form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status=404)
    

    def get_reports(self, R):
        qset,count = [], 0
        if parent := R.get('parent_id'):
            qset = self.model.objects.filter(  
                parent_id = parent
            ).values('id', 'qsetname', 'asset_id', 'slno')
            count = qset.count()
        logger.info('site reports found for the parent with id %s'%R['id'] if qset else "Not found any reports")
        resp = {
            'recordsTotal':count, 'recordsFiltered':count,
            'draw':R['draw'], 'data':list(qset)
        }
        return JsonResponse(data=resp, status=200)


class MasterReportBelonging(LoginRequiredMixin, View):
    model=am.QuestionSet
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
    
