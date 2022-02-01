import apps.schedhuler.utils as sutils
import apps.peoples.utils as putils
from django.db.models import Q
import apps.core.utils 
import apps.schedhuler.filters as sdf
from django.http import HttpRequest, QueryDict
from pprint import pformat
import apps.onboarding.models as om
import apps.activity.models as am
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.exceptions import EmptyResultSet
from datetime import datetime, time, timedelta, timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render
import apps.schedhuler.forms as scd_forms
from django.http import Http404, response as rp
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
from django.db.models.deletion import RestrictedError
from django.urls import reverse
import json
log = logging.getLogger('__main__')
# Create your views here.


class SchedhuleTour(LoginRequiredMixin, View):
    params = {
        'form_class'    : scd_forms.SchdInternalTourForm,
        'template_form' : 'schedhuler/partials/partial_schd_tourform.html',
        'template_list' : 'schedhuler/schedule_tour.html',
        'partial_form'  : 'schedhuler/partials/partial_schd_tourform.html',
        'partial_list'  : 'peoples/partials/partial_people_list.html',
        'related'       : ['groupid', 'peopleid'],
        'model'         : am.Job,
        'filter'        : sdf.SchdTourFilter,
        'fields'        : ['jobname', 'peopleid', 'groupid', 'from_date', 'upto_date',
                            'planduration', 'gracetime', 'expirytime'],
        'form_initials' : {'initial': {}}
    }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "schdtour_list", 'filt_name': "schdtour_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(jobname='NONE')
            ).values(*self.params['fields'])
            resp = putils.render_grid(
                request, self.params, "schedhuled_tour_view", objs)

        # return questionset_form empty
        elif R.get('action', None) == 'form':
            cxt = {'schdtourform': self.params['form_class'](request=request),
                   'childtour_form'   : scd_forms.SchdChildInternalTourForm(),
                   'msg'              : "create schedhule tour requested"}
            resp = putils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get('id', None):
            questions = self.get_questions_for_form(int(R['id']))
            cxt = {'childtour_form': scd_forms.SchdChildInternalTourForm(),
                   "questions": questions}
            obj = putils.get_model_obj(int(R['id']), request, self.params)
            resp = putils.render_form_for_update(
                request, self.params, 'schdtourform', obj, cxt)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp = None
        try:
            log.debug(pformat(request.POST))
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "schedhuled_tour_view"
                form = putils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                log.debug(pformat(form.data, width=41, compact=True))
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = putils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = putils.handle_Exception(request)
        return resp


class CreateSchedhuleTour(LoginRequiredMixin, View):
    template_path = 'schedhuler/schd_internaltour_form.html'
    form_class    = scd_forms.SchdInternalTourForm
    subform       = scd_forms.SchdChildInternalTourForm
    model         = am.Job
    initial       = {
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'expirytime'  : 0,
        'identifier'  : 'INTERNALTOUR'
    }

    def get(self, request, *args, **kwargs):
        log.info("create a guard tour requested")
        cxt = {'schdtourform': self.form_class(request=request, initial=self.initial),
               'childtour_form': self.subform()}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('Guard Tour form submitted')
        data = QueryDict(request.POST['formData'])
        pk = request.POST.get('pk', None)
        response = None
        if pk:
            obj = putils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance=obj, data=data, initial=self.initial)
            log.info("retrieved existing guard tour jobname:= '%s'" %
                     (obj.jobname))
        else:
            form = self.form_class(data=data, initial=self.initial)
            log.info("new guard tour submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form)
                else:
                    response = self.process_invalid_schd_tourform(
                        form, self.subform, request, self.template_path)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info=True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status=404)
        return response

    def process_valid_schd_tourform(self, request, form):
        resp = None
        log.info("guard tour form processing/saving [ START ]")
        try:
            assigned_checkpoints = json.loads(
                request.POST.get("asssigned_checkpoints"))
            job         = form.save(commit=False)
            job.parent  = sutils.get_or_create_none_job()
            job.assetid = sutils.get_or_create_none_asset()
            job.qsetid  = sutils.get_or_create_none_qset()
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            self.save_checpoints_for_tour(assigned_checkpoints, job, request)
            log.info('guard tour  and its checkpoints saved success...')
        except Exception as ex:
            log.critical("guard tour form is processing failed", exc_info=True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status=404)
            raise ex
        else:
            log.info("guard tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': reverse("schedhuler:update_tour", args=[job.id])},
                status=200)
        log.info("guard tour form processing/saving [ END ]")
        return resp

    def process_invalid_schd_tourform(self, form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status=404)

    def save_checpoints_for_tour(self, checkpoints, job, request):
        try:
            log.info("saving Checkpoints [started]")
            self.insert_checkpoints(checkpoints, job, request)
            log.info("saving QuestionSet Belonging [Ended]")
        except Exception as ex:
            log.critical(
                "failed to save checkpoints, something went wrong", exc_info=True)
            raise ex

    def insert_checkpoints(self, checkpoints, job, request):
        log.info("inserting checkpoints started...")
        log.info("inserting checkpoints found %s checkpoints" %
                 (len(checkpoints)))
        try:
            for cp in checkpoints:
                cp['expirytime'] = cp[5]
                cp['assetid']    = cp[1]
                cp['qsetid']     = cp[3]
                cp['slno']       = cp[0]
                checkpoint, created = self.model.objects.update_or_create(
                    parent_id  = job.id,
                    assetid_id = cp['assetid'],
                    qsetid_id  = cp['qsetid'],
                    
                    defaults   = sutils.job_fields(job, cp)
                )
                checkpoint.save()
                status = "CREATED" if created else "UPDATED"
                log.info("\nsaving checkpoint:= '%s' for JOB:= '%s' with expirytime:= '%s'  %s\n" % (
                    cp[2],  job.jobname, cp[5], status))
                putils.save_userinfo(checkpoint, request.user, request.session)
        except Exception as ex:
            log.critical(
                "failed to insert checkpoints, something went wrong", exc_info=True)
            raise ex
        else:
            log.info("inserting checkpoints finished...")


class UpdateSchdhuledTour(CreateSchedhuleTour, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        log.info('Update Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            ic(pk)
            obj = self.model.objects.get(id=pk)
            log.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance=obj, initial=self.initial)
            checkpoints = self.get_checkpoints(obj=obj)
            cxt         = {'schdtourform': form, 'childtour_form': self.subform(), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path,  context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    def get_checkpoints(self, obj):
        log.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'assetid', 'qsetid', 'groupid',
                'peopleid',
            ).filter(parent_id=obj.id).values(
                'slno',
                'assetid__assetname',
                'assetid__id',
                'qsetid__qset_name',
                'qsetid__id',
                'expirytime',
                'id')
        except Exception:
            log.critical("something went wrong", exc_info=True)
            raise
        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints


class RetriveSchedhuledTours(LoginRequiredMixin, View):
    model = am.Job
    template_path = 'schedhuler/schedhuled_tours.html'
    fields = ['jobname', 'peopleid__peoplename', 'groupid__groupname', 'from_date', 'upto_date',
              'planduration', 'gracetime', 'expirytime', 'id']
    related = ['groupid', 'peopleid']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            log.info('Retrieve Schedhuled Tours view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE'
            ).values(*self.fields).order_by('-cdtz')
            log.info('Schedhuled Tours objects %s retrieved from db' %
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            log.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info=True)
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import SchdTourFilter
        if request.GET:
            objects = SchdTourFilter(request.GET, queryset=objects).qs
        filterform = SchdTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'schdtour_list': schdtour_list, 'schdtour_filter': filterform}


def deleteChekpointFromTour(request):
    if request.method != 'GET':
        return Http404

    datasource = request.GET.get('datasource')
    checkpointid = request.GET.get('checkpointid')
    checklistid = request.GET.get('checklistid')
    jobid = request.GET.get('jobid')
    statuscode, msg = 404, ""
    try:
        if datasource == 'job':
            sutils.delete_from_job(jobid, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
        elif datasource == "jobneed":
            sutils.delete_from_jobneed(jobid, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
    except RestrictedError:
        msg = "Unable to delete, due to its dependencies on other data!"
        log.error("something went wrong", exc_info=True)
    except Exception:
        msg = "Something went wrong"
        log.critical("something went wrong", exc_info=True)
    return rp.JsonResponse({'errors': msg}, status=statuscode)





class RetriveInternalTours(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'schedhuler/internaltour_list.html'
    fields    = ['jobdesc', 'peopleid__peoplename', 'groupid__groupname', 'id',
              'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performed_by__peoplename',]
    related   = ['groupid',  'ticket_category', 'assetid', 'clientid',
               'frequency', 'jobid', 'qsetid', 'peopleid', 'parent', 'buid']

    def get(self, request, *args, **kwargs):
        '''returns jobneed (internal-tours) from db'''
        response, session = None, request.session
        try:
            log.info('Retrieve internal tours(jobneed) view')
            dt = datetime.now(tz=timezone.utc) - timedelta(days=10)
            objects = self.model.objects.select_related(
                *self.related).filter(
                    Q(buid_id=session['buid']) & Q(parent__jobdesc='NONE')
                    & ~Q(jobdesc='NONE') & Q(plandatetime__gte=dt)
            ).values(*self.fields).order_by('-plandatetime')
            log.info('Internal Tours objects %s retrieved from db' %
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            log.info('Results paginated' if objects else "")
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info=True)
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start' if objects else "")
        from .filters import InternalTourFilter
        if request.GET:
            objects = InternalTourFilter(request.GET, queryset=objects).qs
        filterform = InternalTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            tour_list = paginator.page(page)
        except PageNotAnInteger:
            tour_list = paginator.page(1)
        except EmptyPage:
            tour_list = paginator.page(paginator.num_pages)
        return {'tour_list': tour_list, 'tour_filter': filterform}


class GetInternalTour(LoginRequiredMixin, View):
    model         = am.Jobneed
    template_path = 'schedhuler/internaltour_form.html'
    form_class    = scd_forms.InternalTourForm
    subform       = scd_forms.ChildInternalTourForm
    initial       = {
        'identifier'    : 'INTERNALTOUR',
        'frequency'     : 'NONE'
    }

    def get(self, request, *args, **kwargs):
        log.info("retrieving internal tour datasource[jobneed]")
        parent_jobneedid, response = kwargs.get('pk'), None
        try:
            obj = self.model.objects.get(id=parent_jobneedid)
            form = self.form_class(instance=obj, initial=self.initial)
            log.info("object retrieved %s" % (obj.jobdesc))
            checkpoints = self.get_checkpoints(obj=obj)
            cxt = {'internaltourform': form, 'child_internaltour': self.subform(prefix='child'), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            log.error('object does not exist', exc_info=True)
            response = redirect('schedhuler:retrieve_internaltours')
        except Exception:
            log.critical('something went wron', exc_info=True)
            response = redirect('schedhuler:retrieve_internaltours')
        return response

    def post(self, request, *args, **kwargs):
        log.info("saving internal tour datasource[jobneed]")

    def get_checkpoints(self, obj):
        log.info("getting checkpoints for the internal tour [start]")
        checkpoints = None
        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'assetid', 'qsetid', 'groupid',
                'peopleid', 'jobid', 'clientid', 'buid',
                'ticket_category'
            ).filter(parent_id=obj.id).values(
                'assetid__assetname', 'assetid__id', 'qsetid__id',
                'qsetid__qset_name', 'plandatetime', 'expirydatetime',
                'gracetime', 'slno', 'jobstatus', 'id').order_by('slno')
        except Exception:
            log.critical("something went wrong", exc_info=True)
            raise
        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints


def add_cp_internal_tour(request):  # jobneed
    resp = None
    if request.method == 'POST':
        formData = request.POST.get('formData')
        parentid = request.POST.get('parentid')
        try:
            parent = am.Jobneed.objects.get(id=parentid)
            data  = {'jobdesc' : parent.jobdesc, 'recievedon_server': parent.recievedon_server,
                    'starttime': parent.starttime, 'endtime': parent.endtime, 'gpslocation': parent.gpslocation,
                    'remarks'  : parent.remarks, 'frequency': parent.frequency, 'jobid': parent.jobid,
                    'jobstatus': parent.jobstatus, 'jobtype': parent.jobtype, 'performed_by': parent.performed_by,
                    'priority' : ""}
            form = scd_forms.ChildInternalTourForm(data=formData)

        except am.Jobneed.DoesNotExist:
            msg = "Parent not found failed to add checkpoint!"
            resp = rp.JsonResponse({'errors': msg}, status=404)
        except Exception:
            msg = "Something went wrong!"
            log.critical("%s" % (msg), exc_info=True)
            resp = rp.JsonResponse({"errors": msg}, status=200)


class CreateExternalTourSchdTour(LoginRequiredMixin, View):
    model         = am.Job
    form_class    = scd_forms.ExternalSchdTourForm
    subform       = scd_forms.EditAssignedSiteForm
    template_path = 'schedhuler/schd_external_tourform.html'
    initial       = {
        'slno'        : -1,
        'scantype'    : 'QR',
        'frequency'   : 'NONE',
        'identifier'  : "EXTERNALTOUR",
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'priority'    : 'HIGH',
        'expirytime'  : 0
        }

    def get(self, request, *args, **kwargs):
        
        log.info("create a guard tour requested")
        cxt = {'schdexternaltourform': self.form_class(
            request=request, initial=self.initial),
               'editsiteform':self.subform()}
        print("$$44444", self.subform().as_p().split('\n'))
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('External Tour form submitted')
        formData = QueryDict(request.POST.get('formData'))
        pk       = request.POST.get('pk', None)
        response = None
        if pk:
            obj = putils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance=obj, data=formData, initial=self.initial)
            log.info("retrieved existing guard tour jobname:= '%s'" %
                     (obj.jobname))
        else:
            form = self.form_class(data=formData, initial=self.initial)
            log.info("new guard tour submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        try:
            with transaction.atomic(using=get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form)
                else:
                    response = self.process_invalid_schd_tourform(form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info=True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status=404)
        return response


    def process_invalid_schd_tourform(self, form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status=404)


    def process_valid_schd_tourform(self, request, form):
        resp = None
        log.info("external tour form processing/saving [ START ]")
        try:
            job         = form.save(commit=False)
            job.parent  = sutils.get_or_create_none_job()
            job.assetid = sutils.get_or_create_none_asset()
            job.save()
            print("%%%%%%%%%5",  form.data, form.data.get('buid'))
            job = putils.save_userinfo(job, request.user, request.session,
            buid = form.data.get('buid'))
            log.info('external tour  and its checkpoints saved success...')
        except Exception as ex:
            log.critical(
                "external tour form is processing failed", exc_info=True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status=404)
            raise ex
        else:
            log.info("external tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                                    'url': reverse("schedhuler:update_externaltour", args=[job.id])},
                                   status=200)
        log.info("external tour form processing/saving [ END ]")
        return resp



class UpdateExternalSchdhuledTour(CreateExternalTourSchdTour, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        log.info('Update External Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id=pk)
            log.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance=obj, initial=self.initial)
            checkpoints = self.get_checkpoints(obj=obj)
            cxt         = {'schdexternaltourform': form, 'edit': True,
                        'editsiteform':self.subform(),
                        'checkpoints': checkpoints,
                        'qsetname':obj.qsetid.qset_name,
                        'qsetid':obj.qsetid.id}
            log.debug("qsetname %s qsetid %s"%(obj.qsetid.qset_name, obj.qsetid.id))
            response = render(request, self.template_path,  context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    def get_checkpoints(self, obj):
        log.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = om.Bt.objects.select_related(
                'identifier', 'butype', 'parent'
            ).filter(parent_id=obj.buid_id).values(
                'buname', 'id', 'bucode', 'gpslocation',
            )
        except Exception:
            log.critical("something went wrong", exc_info=True)
            raise
        else:
            if checkpoints:
                log.info("total %s checkpoints retrieved returned success"%(len(checkpoints)))
            else: log.info("checkpoints not found")
        return checkpoints



class RetriveExternalSchedhuledTours(LoginRequiredMixin, View):
    model = am.Job
    template_path = 'schedhuler/scheduled_externaltours.html'
    fields = ['jobname', 'peopleid__peoplename', 'groupid__groupname',
              'from_date', 'upto_date',
              'planduration', 'gracetime', 'expirytime', 'id', 'buid__buname']
    related = ['groupid', 'peopleid']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            log.info('Retrieve Schedhuled External Tours view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE', identifier="EXTERNALTOUR"
            ).values(*self.fields).order_by('-cdtz')
            log.info('Schedhuled External Tours objects %s retrieved from db'%len(objects) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            log.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info=True)
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import SchdExtTourFilter
        if request.GET:
            objects = SchdExtTourFilter(request.GET, queryset=objects).qs
        filterform = SchdExtTourFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'ext_schdtour_list': schdtour_list, 'ext_schdtour_filter': filterform}



def run_internal_tour_scheduler(request):
    if request.method != 'POST' or request.POST is None:
        return Http404
    padd = "#"*10
    log.info(
        "%s run_guardtour_scheduler initiated [START] %s" % (padd, padd))
    jobid, resp = request.POST.get('jobid'), None
    jobs = am.Job.objects.filter(
        id=jobid).select_related(
            "assetid", "groupid", "frequency",
            "cuser", "muser", "qsetid", "peopleid").values_list(named=True)
    if not jobs:
        msg = "Job not found unable to schedhule"
        log.error("%s" % (msg), exc_info=True)
        resp = rp.JsonResponse({"errors": msg}, status=404)
    else:
        try:
            log.info("%s create_job(jobs) %s" % (padd, padd))
            sutils.create_job(jobs)
            log.info("%s create_job(jobs) %s" % (padd, padd))
            resp = rp.JsonResponse({"msg": "success"}, status=200)
        except Exception:
            msg = "Unable to schedule job, something went wrong!"
            log.error("%s" % (msg), exc_info=True)
            resp = rp.JsonResponse({"errors": msg}, status=404)
    log.info(
        "%s run_guardtour_scheduler initiated [END] %s" % (padd, padd))
    del padd
    return resp


def get_cron_datetime(request):
    if request.method != 'GET':
        return Http404

    log.info("get_cron_datetime [start]")
    cron = request.GET.get('cron')
    log.info("get_cron_datetime cron:%s"%(cron))
    cronDateTime= itr= None
    startdtz= datetime.now()
    enddtz= datetime.now() + timedelta(days=1)
    DT, res= [], None
    try:
        from croniter import croniter
        itr= croniter(cron, startdtz)
        while True:
            cronDateTime = itr.get_next(datetime)
            if cronDateTime < enddtz:
                DT.append(cronDateTime)
            else: break
        res = rp.JsonResponse({'rows':DT}, status=200)
    except Exception as ex:
        msg = "croniter bad cron error"
        log.error(msg, exc_info=True)
        res = rp.JsonResponse({'errors':msg}, status=404)
    return res


def save_assigned_sites_for_externaltour(request):
    if request.method=='POST':
        log.info("save_assigned_sites_for_externaltour [start+]")
        formData = QueryDict(request.POST.get('formData'))
        parentJobId = request.POST.get('pk')
        with transaction.atomic(using=get_current_db_name()):
            save_sites_in_job(request, parentJobId)


def save_sites_in_job(request, parentid):
    try:
        checkpoints = json.loads(request.POST.get('assignedSites'))
        job = am.Job.objects.get(id = parentid)
        for cp in checkpoints:
            am.Job.objects.update_or_create(
                parent_id  = job.id,
                assetid_id = cp['assetid'],
                qsetid_id  = cp['qsetid'],
                breaktime  = cp['breaktime'],

                defaults=sutils.job_fields(job, cp, external=True)
            )
    except am.Job.DoesNotExist:
        msg = 'Parent job not found failed to save assigned sites!'
        log.error("%s"%(msg), exc_info=True)
        raise
    except Exception:
        log.critical("something went wrong!", exc_info=True)
        raise
    
    