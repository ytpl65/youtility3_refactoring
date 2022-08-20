from operator import iconcat
import apps.schedhuler.utils as sutils
import apps.peoples.utils as putils
from django.db.models import Q, F
from django.contrib import messages
from django.core.exceptions import EmptyResultSet
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, QueryDict, response as rp
from django.shortcuts import redirect, render
from django.views import View
from apps.core import  utils 
from django.contrib.gis.db.models.functions import  AsGeoJSON
import apps.schedhuler.filters as sdf
from pprint import pformat
import apps.onboarding.models as om
import apps.activity.models as am
import apps.peoples.models as pm
from datetime import datetime, time, timedelta, timezone, date
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
import apps.schedhuler.forms as scd_forms
import logging
from django.db.models.deletion import RestrictedError
from django.urls import reverse
import json
log = logging.getLogger('__main__')
# Create your views here.


class Schd_I_TourFormJob(LoginRequiredMixin, View):
    template_path = 'schedhuler/schd_i_tourform_job.html'
    form_class    = scd_forms.Schd_I_TourJobForm
    subform       = scd_forms.SchdChild_I_TourJobForm
    model         = am.Job
    initial       = {
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'expirytime'  : 0,
        'identifier'  :am.Job.Identifier.INTERNALTOUR,
        'priority'    :am.Job.Priority.LOW,
        'scantype'    :am.Job.Scantype.QR,
        'gracetime'   : 5,
        'fromdate'   : datetime.combine(date.today(), time(00, 00, 00)),
        'uptodate'   : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
    }

    def get(self, request, *args, **kwargs):
        log.info("create a guard tour requested")
        cxt = {'schdtourform': self.form_class(request = request, initial = self.initial),
               'childtour_form': self.subform()}
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('Guard Tour form submitted')
        data, create = QueryDict(request.POST['formData']), True
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = data, initial = self.initial, request = request)
            log.info("retrieved existing guard tour jobname:= '%s'" %
                     (obj.jobname))
            create = False
        else:
            form = self.form_class(data = data, initial = self.initial, request = request)
            log.info("new guard tour submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form, create)
                else:
                    response = self.process_invalid_schd_tourform(form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_schd_tourform(self, request, form, create):
        resp = None
        log.info("guard tour form processing/saving [ START ]")
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                assigned_checkpoints = json.loads(
                request.POST.get("asssigned_checkpoints"))
                job         = form.save(commit = False)
                job.parent_id  = -1
                job.asset_id = -1
                job.qset_id  = -1
                job.save()
                job = putils.save_userinfo(job, request.user, request.session, create = create)
                self.save_checpoints_for_tour(assigned_checkpoints, job, request)
                log.info('guard tour  and its checkpoints saved success...')
        except Exception as ex:
            log.critical("guard tour form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status = 404)
            raise ex
        else:
            log.info("guard tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': reverse("schedhuler:update_tour", args=[job.id])},
                status = 200)
        log.info("guard tour form processing/saving [ END ]")
        return resp

    def process_invalid_schd_tourform(self, form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    def save_checpoints_for_tour(self, checkpoints, job, request):
        try:
            log.info("saving Checkpoints [started]")
            self.insert_checkpoints(checkpoints, job, request)
            log.info("saving QuestionSet Belonging [Ended]")
        except Exception as ex:
            log.critical(
                "failed to save checkpoints, something went wrong", exc_info = True)
            raise ex

    def insert_checkpoints(self, checkpoints, job, request):
        log.info("inserting checkpoints started...")
        log.info("inserting checkpoints found %s checkpoints" %
                 (len(checkpoints)))
        log.debug(checkpoints)
        CP = {}
        try:
            for cp in checkpoints:
                CP['expirytime'] = cp[5]
                CP['asset']    = cp[1]
                CP['qset']     = cp[3]
                CP['seqno']       = cp[0]
                checkpoint, created = self.model.objects.update_or_create(
                    parent_id  = job.id,
                    asset_id = CP['asset'],
                    qset_id  = CP['qset'],

                    defaults   = sutils.job_fields(job, cp)
                )
                checkpoint.save()
                status = "CREATED" if created else "UPDATED"
                log.info("\nsaving checkpoint:= '%s' for JOB:= '%s' with expirytime:= '%s'  %s\n" % (
                    cp[2],  job.jobname, cp[5], status))
                putils.save_userinfo(checkpoint, request.user, request.session, create = created)
        except Exception as ex:
            log.critical(
                "failed to insert checkpoints, something went wrong", exc_info = True)
            raise ex
        else:
            log.info("inserting checkpoints finished...")

class Update_I_TourFormJob(Schd_I_TourFormJob, View):

    def get(self, request, *args, **kwargs):
        log.info('Update Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            ic(pk)
            obj = self.model.objects.get(id = pk)
            log.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance = obj, initial = self.initial)
            checkpoints = self.get_checkpoints(obj = obj)
            cxt         = {'schdtourform': form, 'childtour_form': self.subform(), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            log.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    def get_checkpoints(self, obj):
        log.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people',
            ).filter(parent_id = obj.id).values(
                'seqno',
                'asset__assetname',
                'asset__id',
                'qset__qset_name',
                'qset__id',
                'expirytime',
                'id')
        except Exception:
            log.critical("something went wrong", exc_info = True)
            raise
        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints

class Retrive_I_ToursJob(LoginRequiredMixin, View):
    params = {
        'model'        : am.Job,
        'template_path': 'schedhuler/schd_i_tourlist_job.html',
        'fields'       : ['jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                        'planduration', 'gracetime', 'expirytime', 'id'],
        'related': ['pgroup', 'people']
    }

    model = am.Job
    template_path = 'schedhuler/schd_i_tourlist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
              'planduration', 'gracetime', 'expirytime', 'id']
    related = ['pgroup', 'people']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            log.info('Retrieve Schedhuled Tours view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE'
            ).values(*self.fields).order_by('-cdtz')
            log.info(f'Schedhuled Tours objects {len(objects)} retrieved from db' if objects else "No Records!")

            cxt = self.paginate_results(request, objects)
            log.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import SchdTourFilter
        if request.GET:
            objects = SchdTourFilter(request.GET, queryset = objects).qs
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
    job = request.GET.get('job')
    statuscode, msg = 404, ""
    try:
        if datasource == 'job':
            sutils.delete_from_job(job, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
        elif datasource == "jobneed":
            sutils.delete_from_jobneed(job, checkpointid, checklistid)
            statuscode, msg = 200, "Success"
    except RestrictedError:
        msg = "Unable to delete, due to its dependencies on other data!"
        log.error("something went wrong", exc_info = True)
    except Exception:
        msg = "Something went wrong"
        log.critical("something went wrong", exc_info = True)
    return rp.JsonResponse({'errors': msg}, status = statuscode)



class Retrive_I_ToursJobneed(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'schedhuler/i_tourlist_jobneed.html'
    fields    = ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
              'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename',]
    related   = ['pgroup',  'ticketcategory', 'asset', 'client',
               'frequency', 'job', 'qset', 'people', 'parent', 'bu']

    def get(self, request, *args, **kwargs):
        '''returns jobneed (internal-tours) from db'''
        response, session = None, request.session

        try:
            log.info('Retrieve internal tours(jobneed) view')
            dt = datetime.now(tz = timezone.utc) - timedelta(days = 10)
            objects = self.model.objects.select_related(
                *self.related).filter(
                    Q(bu_id = session['bu_id']) & Q(parent__jobdesc='NONE')
                    & ~Q(jobdesc='NONE') & Q(plandatetime__gte = dt)
            ).values(*self.fields).order_by('-plandatetime')
            log.info('Internal Tours objects %s retrieved from db' %
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            log.info('Results paginated' if objects else "")
            response = render(request, self.template_path, context = cxt)

        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start' if objects else "")
        from .filters import InternalTourFilter

        if request.GET:
            objects = InternalTourFilter(request.GET, queryset = objects).qs
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

class Get_I_TourJobneed(LoginRequiredMixin, View):
    model         = am.Jobneed
    template_path = 'schedhuler/i_tourform_jobneed.html'
    form_class    = scd_forms.I_TourFormJobneed
    subform       = scd_forms.Child_I_TourFormJobneed
    initial       = {
        'identifier': am.Jobneed.Identifier.INTERNALTOUR,
        'frequency' : am.Jobneed.Frequency.NONE
    }

    def get(self, request, *args, **kwargs):
        log.info("retrieving internal tour datasource[jobneed]")
        parent_jobneed, response = kwargs.get('pk'), None

        try:
            obj = self.model.objects.get(id = parent_jobneed)
            form = self.form_class(instance = obj, initial = self.initial)
            log.info("object retrieved %s" % (obj.jobdesc))
            checkpoints = self.get_checkpoints(obj = obj)
            cxt = {'internaltourform': form, 'child_internaltour': self.subform(prefix='child'), 'edit': True,
                   'checkpoints': checkpoints}
            response = render(request, self.template_path, context = cxt)

        except self.model.DoesNotExist:
            log.error('object does not exist', exc_info = True)
            response = redirect('schedhuler:retrieve_internaltours')

        except Exception:
            log.critical('something went wron', exc_info = True)
            response = redirect('schedhuler:retrieve_internaltours')
        return response

    def post(self, request, *args, **kwargs):
        log.info("saving internal tour datasource[jobneed]")

    def get_checkpoints(self, obj):
        log.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = self.model.objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory'
            ).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qset_name', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            log.critical("something went wrong", exc_info = True)
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
            parent = am.Jobneed.objects.get(id = parentid)
            data  = {'jobdesc' : parent.jobdesc, 'receivedonserver': parent.receivedonserver,
                    'starttime': parent.starttime, 'endtime': parent.endtime, 'gpslocation': parent.gpslocation,
                    'remarks'  : parent.remarks, 'frequency': parent.frequency, 'job': parent.job,
                    'jobstatus': parent.jobstatus, 'jobtype': parent.jobtype, 'performedby': parent.performedby,
                    'priority' : ""}
            form = scd_forms.ChildInternalTourForm(data = formData)

        except am.Jobneed.DoesNotExist:
            msg = "Parent not found failed to add checkpoint!"
            resp = rp.JsonResponse({'errors': msg}, status = 404)
        except Exception:
            msg = "Something went wrong!"
            log.critical(f"{msg}", exc_info = True)
            resp = rp.JsonResponse({"errors": msg}, status = 200)

class Schd_E_TourFormJob(LoginRequiredMixin, View):
    params = {
        'model':am.Jobneed,
        'form_class':scd_forms.Schd_E_TourJobForm,
        'subform':scd_forms.EditAssignedSiteForm,
        'template_path':'schedhuler/schd_e_tourform_job.html',
        'initial':{
            'seqno':-1,
            'scantype':am.Job.Scantype.QR,
            'frequency':am.Job.Frequency.NONE,
            'identifier':am.Job.Identifier.EXTERNALTOUR,
            'starttime':time(00,00,00),
            'endtime':time(00,00,00),
            'priority':am.Job.Priority.HIGH,
            'expirytime':0
        }
    }

    def get(self, request, *args, **kwargs):

        log.info("create a guard tour requested")
        cxt = {'schdexternaltourform': self.form_class(
            request = request, initial = self.initial),
               'editsiteform':self.subform()}
        print("$$44444", self.subform().as_p().split('\n'))
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        log.info('External Tour form submitted')
        formData, create = QueryDict(request.POST.get('formData')), True
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = formData, initial = self.initial)
            log.info("retrieved existing guard tour jobname:= '%s'" %
                     (obj.jobname))
            create = False
        else:
            form = self.form_class(data = formData, initial = self.initial)
            log.info("new guard tour submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_tourform(request, form, create)
                else:
                    response = self.process_invalid_schd_tourform(form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_invalid_schd_tourform(self, form):
        log.info(
            "processing invalid forms sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalid forms sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    def process_valid_schd_tourform(self, request, form, create):
        resp = None
        log.info("external tour form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.asset_id = 1
            job.save()
            print("%%%%%%%%%5",  form.data, form.data.get('bu'))
            job = putils.save_userinfo(job, request.user, request.session)
            log.info('external tour  and its checkpoints saved success...')
        except Exception as ex:
            log.critical(
                "external tour form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_tourform failed..."}, status = 404)
            raise ex
        else:
            log.info("external tour form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                                    'url': reverse("schedhuler:update_externaltour", args=[job.id])},
                                   status = 200)
        log.info("external tour form processing/saving [ END ]")
        return resp


class Update_E_TourFormJob(Schd_E_TourFormJob, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        log.info('Update External Schedhule Tour form view')
        response = None
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id = pk)
            log.info('object retrieved {}'.format(obj))
            form        = self.form_class(instance = obj, initial = self.initial)
            checkpoints = self.get_checkpoints(obj = obj)
            cxt         = {'schdexternaltourform': form, 'edit': True,
                        'editsiteform':self.subform(),
                        'checkpoints': checkpoints,
                        'qsetname':obj.qset.qsetname,
                        'qset':obj.qset.id}
            log.debug("qsetname %s qset %s"%(obj.qset.qsetname, obj.qset.id))
            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            log.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        return response

    def get_checkpoints(self, obj):
        log.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = pm.Pgbelonging.objects.select_related(
                'assignsites', 'identifier'
            ).filter(pgroup_id = obj.sgroup_id).values(
                'assignsites__buname', 'assignsites_id', 'assignsites__bucode', 'assignsites__gpslocation'
            )
        except Exception:
            log.critical("something went wrong", exc_info = True)
            raise
        else:
            if checkpoints:
                log.info("total %s checkpoints retrieved returned success"%(len(checkpoints)))
            else: log.info("checkpoints not found")
        return checkpoints


class Retrive_E_ToursJob(LoginRequiredMixin, View):
    model = am.Job
    template_path = 'schedhuler/schd_e_tourlist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname',
              'fromdate', 'uptodate',
              'planduration', 'gracetime', 'expirytime', 'id', 'bu__buname']
    related = ['pgroup', 'people']

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
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import SchdExtTourFilter
        if request.GET:
            objects = SchdExtTourFilter(request.GET, queryset = objects).qs
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
    log.info(f"{padd} run_guardtour_scheduler initiated [START] {padd}")
    R, job, resp = request.POST, request.POST.get('job'), None
    if (
        jobs := am.Job.objects.filter(id = job)
        .select_related(
            "asset",
            "pgroup",
            'sgroup',
            "frequency",
            "cuser",
            "muser",
            "qset",
            "people",
        )
        
    ):
        #check if it is random external tour
        if jobs[0].other_info['is_randomized'] in [True, 'true'] and R.get('action')=='saveCheckpoints':
            ic(dir(jobs[0]))
            #save checkpoints
            checkpoints =  json.loads(R.get('checkpoints'))
            am.Job.objects.filter(parent_id = jobs[0].id).delete()
            log.info("saving checkpoints startted...")
            for cp in checkpoints:
                obj = am.Job.objects.create(
                    **sutils.job_fields(jobs[0], cp, external=True))
                putils.save_userinfo(obj, request.user, request.session, bu=cp['buid'])
                log.info(f"checkpoint saved {obj.jobname}")
            log.info("saving checkpoints ended...")
        log.info(f"{padd} create_job(jobs) {padd}")
        resp = sutils.create_job(jobs)
    else:
        msg = "Job not found unable to schedhule"
        log.error(f"{msg}", exc_info = True)
        resp = rp.JsonResponse({"errors": msg}, status = 404)
    log.info(f"{padd} run_guardtour_scheduler initiated [END] {padd}")
    ic("resp in run_internal_tour_scheduler()", resp)
    return resp

def get_cron_datetime(request):
    if request.method != 'GET':
        return Http404

    log.info("get_cron_datetime [start]")
    cron = request.GET.get('cron')
    log.info(f"get_cron_datetime cron:{cron}")
    cronDateTime= itr= None
    startdtz= datetime.now()
    enddtz= datetime.now() + timedelta(days = 1)
    DT, res= [], None
    try:
        from croniter import croniter
        itr= croniter(cron, startdtz)
        while True:
            cronDateTime = itr.get_next(datetime)
            if cronDateTime < enddtz:
                DT.append(cronDateTime)
            else: break
        res = rp.JsonResponse({'rows':DT}, status = 200)
    except Exception as ex:
        msg = "croniter bad cron error"
        log.error(msg, exc_info = True)
        res = rp.JsonResponse({'errors':msg}, status = 404)
    return res

def save_assigned_sites_for_externaltour(request):
    if request.method=='POST':
        log.info("save_assigned_sites_for_externaltour [start+]")
        formData = QueryDict(request.POST.get('formData'))
        parentJobId = request.POST.get('pk')
        with transaction.atomic(using = utils.get_current_db_name()):
            save_sites_in_job(request, parentJobId)

def save_sites_in_job(request, parentid):
    try:
        checkpoints = json.loads(request.POST.get('assignedSites'))
        job = am.Job.objects.get(id=parentid)
        for cp in checkpoints:
            am.Job.objects.update_or_create(
                parent_id=job.id, asset_id=cp['asset'], qset_id=cp['qset'], breaktime=cp['breaktime'],
                defaults=sutils.job_fields(job, cp, external=True))

    except am.Job.DoesNotExist:
        msg = 'Parent job not found failed to save assigned sites!'
        log.error(f"{msg}", exc_info=True)
        raise
    except Exception:
        log.critical("something went wrong!", exc_info=True)
        raise


class SchdTaskFormJob(LoginRequiredMixin, View):
    template_path = 'schedhuler/schd_taskform_job.html'
    form_class    = scd_forms.SchdTaskFormJob
    model         = am.Job
    initial       = {
        'starttime'   : time(00, 00, 00),
        'endtime'     : time(00, 00, 00),
        'fromdate'   : datetime.combine(date.today(), time(00, 00, 00)),
        'uptodate'   : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
        'identifier'  : am.Job.Identifier.TASK,
        'frequency'   : am.Job.Frequency.NONE,
        'scantype'    : am.Job.Scantype.QR,
        'priority'    : am.Job.Priority.LOW,
        'planduration': 5,
        'gracetime'   : 5,
        'expirytime'  : 5
    }

    def get(self, request, *args, **kwargs):
        log.info('create task to schedule is requested')
        cxt = {
            'schdtaskform':self.form_class(initial = self.initial)
        }
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        log.info('Task form submitted')
        data, create = QueryDict(request.POST['formData']), True
        utils.display_post_data(data)
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = data, initial = self.initial)
            log.info("retrieved existing task whose jobname:= '%s'" %
                     (obj.jobname))
        else:
            form = self.form_class(data = data, initial = self.initial)
            log.info("new task submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_taskform(request, form)
                else:
                    response = self.process_invalid_schd_taskform(
                        form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_schd_taskform(self, request, form):
        resp = None
        log.info("task form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            log.info('task form saved success...')
        except Exception as ex:
            log.critical("task form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_taskform failed..."}, status = 404)
            raise ex from ex
        else:
            log.info("task form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': reverse("schedhuler:update_task", args=[job.id])},
                status = 200)
        log.info("task form processing/saving [ END ]")
        return resp

    def process_invalid_schd_taskform(self, form):
        log.info(
            "processing invalidt task form sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalidt task form sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)


class RetriveSchdTasksJob(LoginRequiredMixin, View):
    model = am.Job
    template_path = 'schedhuler/schd_tasklist_job.html'
    fields = ['jobname', 'people__peoplename', 'pgroup__groupname',
              'fromdate', 'uptodate', 'qset__qsetname', 'asset__assetname',
              'planduration', 'gracetime', 'expirytime', 'id']
    related = ['pgroup', 'people', 'asset']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        R, resp = request.GET, None
        try:
            # first load the template
            if R.get('template'): return render(request, self.template_path)

            # then load the table with objects for table_view
            if R.get('action') == 'list':
                log.info('Retrieve Tasks view')
                objects = self.model.objects.select_related(
                    *self.related).filter(
                        ~Q(jobname='NONE'), parent__jobname='NONE', identifier="TASK"
                ).values(*self.fields).order_by('-cdtz')
                log.info(f'Tasks objects {len(objects)} retrieved from db' if objects else "No Records!")
                response = rp.JsonResponse(data = {'data':list(objects)})
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import SchdTaskFilter
        if request.GET:
            objects = SchdTaskFilter(request.GET, queryset = objects).qs
        filterform = SchdTaskFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            schdtour_list = paginator.page(page)
        except PageNotAnInteger:
            schdtour_list = paginator.page(1)
        except EmptyPage:
            schdtour_list = paginator.page(paginator.num_pages)
        return {'schd_task_list': schdtour_list, 'schd_task_filter': filterform}

class UpdateSchdTaskJob(SchdTaskFormJob):
    def get(self, request, *args, **kwargs):
        log.info('Update task form view')
        try:
            pk = kwargs.get('pk')
            obj = self.model.objects.get(id = pk)
            log.info(f'object retrieved {obj}')
            form        = self.form_class(instance = obj)
            cxt         = {'schdtaskform': form, 'edit': True}

            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('schedhuler:create_tour')
        except Exception:
            log.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('schedhuler:create_task')
        return response

class RetrieveTasksJobneed(LoginRequiredMixin, View):
    model         = am.Jobneed
    template_path = 'schedhuler/tasklist_jobneed.html'

    fields  = [
        'jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
        'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime',
        'performedby__peoplename', 'asset__assetname', 'qset__qsetname'
    ]
    related = [
        'pgroup',  'ticketcategory', 'asset', 'client',
        'frequency', 'job', 'qset', 'people', 'parent', 'bu' 
    ]

    def get(self, request, *args, **kwargs):
        '''returns jobneed (tasks) from db'''
        response, session = None, request.session

        try:
            log.info('Retrieve tasks(jobneed) view')
            dt      = datetime.now(tz = timezone.utc) - timedelta(days = 10)
            objects = self.model.objects.select_related(
                *self.related).filter(
                Q(bu_id = session['bu_id']),  ~Q(parent__jobdesc='NONE')
                , ~Q(jobdesc='NONE') , Q(plandatetime__gte = dt)
                ,Q(identifier = am.Jobneed.Identifier.TASK)
            ).values(*self.fields).order_by('-plandatetime')
            log.info('tasks objects %s retrieved from db' %
                     (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            log.info('Results paginated' if objects else "")
            response = render(request, self.template_path, context = cxt)

        except EmptyResultSet:
            log.warning('no objects found', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start' if objects else "")
        from .filters import TaskListJobneedFilter

        if request.GET:
            objects = TaskListJobneedFilter(request.GET, queryset = objects).qs
        filterform = TaskListJobneedFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)

        try:
            tour_list = paginator.page(page)
        except PageNotAnInteger:
            tour_list = paginator.page(1)
        except EmptyPage:
            tour_list = paginator.page(paginator.num_pages)
        return {'task_list': tour_list, 'task_filter': filterform}

class GetTaskFormJobneed(LoginRequiredMixin, View):
    model         = am.Jobneed
    template_path = 'schedhuler/taskform_jobneed.html'
    form_class    = scd_forms.TaskFormJobneed
    initial       = {
        'identifier'    : am.Jobneed.Identifier.TASK,
        'frequency'     : am.Jobneed.Frequency.NONE
    }

    def get(self, request, *args, **kwargs):
        log.info("retrieving task datasource[jobneed]")
        parent_jobneed, response = kwargs.get('pk'), None

        try:
            obj = self.model.objects.get(id = parent_jobneed)
            form = self.form_class(instance = obj)
            ic(form.data)
            log.info(f"object retrieved {obj.jobdesc}")
            cxt = {'taskformjobneed': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)

        except self.model.DoesNotExist:
            log.error('object does not exist', exc_info = True)
            response = redirect('schedhuler:retrieve_tasksjobneed')

        except Exception:
            log.critical('something went wron', exc_info = True)
            response = redirect('schedhuler:retrieve_tasksjobneed')
        return response

    def post(self, request, *args, **kwargs):
        log.info("saving tasks datasource[jobneed]")



class Ticket(LoginRequiredMixin, View):
    model = am.Jobneed
    form_class = scd_forms.TicketForm
    template_path = 'schedhuler/ticket_form.html'
    initial = {
        'starttime'  : datetime.utcnow().replace(microsecond = 0),
        'endtime'    : datetime.utcnow().replace(microsecond = 0),
        'frequency'  : am.Jobneed.Frequency.NONE,
        'gpslocation': '0.0,0.0',
        'scantype'   : am.Jobneed.Scantype.NONE,
        'jobstatus'  : am.Jobneed.JobStatus.NEW,
        'priority'   : am.Jobneed.Priority.MEDIUM,
    }

    def get(self, request, *args, **kwargs):
        log.info('create ticket requested!')
        if request.GET.get('delete_ticket'):
            self.delete_ticket(self, request)
        cxt = {
            'ticketform':self.form_class(initial = self.initial)
        }
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        log.info('ticket form submitted!')
        data, create = QueryDict(request.POST['formData']), True
        utils.display_post_data(data)
        if pk := request.POST.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.model})
            form = self.form_class(
                instance = obj, data = data, initial = self.initial)
            log.info("retrieved existing ticket whose ticketno:= '%s'" %
                     (obj.ticketno))
            create = False
        else:
            form = self.form_class(data = data, initial = self.initial)
            log.info("new ticket submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_form(request, form, create)
                else:
                    response = self.process_invalid_form(
                        form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_form(request, form, create):
        resp = None
        try:
            ticket             = form.save(commit = False)
            ticket.qset_id      = -1
            ticket.performedby_id = -1
            ticket.pgroup_id     = -1
            ticket.parent_id      = -1
            ticket.job_id       = -1
            ticket.save()
            ticket = putils.save_userinfo(ticket, request.user, create = create)
        except Exception as ex:
            log.critical("ticket form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_taskform failed..."}, status = 404)
            raise ex
        else:
            log.info("ticket form is processed successfully")
            resp = rp.JsonResponse({'jobdesc': ticket.jobdesc,
                'url': reverse("schedhuler:update_ticket", args=[ticket.id])},
                status = 200)
        log.info("ticket form processing/saving [ END ]")
        return resp

    def process_invalid_form(self, form):
        log.info(
            "processing invalidt ticket form sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalidt ticket form sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)

    def delete_ticket(self, request):
        raise NotImplementedError()

class RetriveTickets(LoginRequiredMixin, View):
    model = am.Jobneed
    template_path = 'schedhuler/ticket_list.html'
    fields = [
        'cdtz', 'ticketno', 'bu__buname', 'pgroup__name',
        'jobdesc', 'people__peoplename',  'performedby__peoplename',
        'ticketcategory__taname', 'expirydatetime', 'jobstatus', 'priority',
        'cuser__peoplename', 'id']
    related = [
        'pgroup', 'people', 'cuser',
        'performedby', 'bu', 'ticketcategory']

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            log.info('Retrieve Ticket view')
            objects = self.model.objects.select_related(
                *self.related).filter(
                    ~Q(jobdesc='NONE'), parent__jobdesc='NONE', identifier='TICKET'
            ).values(*self.fields).order_by('-cdtz')
            log.info(f'Ticket objects {len(objects)} retrieved from db' if objects else "No Records!")

            cxt = self.paginate_results(request, objects)
            log.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            log.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        log.info('Pagination Start'if objects else "")
        from .filters import TicketListFilter
        if request.GET:
            objects = TicketListFilter(request.GET, queryset = objects).qs
        filterform = TicketListFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            ticket_list = paginator.page(page)
        except PageNotAnInteger:
            ticket_list = paginator.page(1)
        except EmptyPage:
            ticket_list = paginator.page(paginator.num_pages)
        return {'ticket_list': ticket_list, 'ticket_filter': filterform}


class JobneedTours(LoginRequiredMixin, View):
    params = {
        'model'        : am.Jobneed,
        'template_path': 'schedhuler/i_tourlist_jobneed.html',
        'template_form': 'schedhuler/i_tourform_jobneed.html',
        'fields'       : ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id', 'ctzoffset',
            'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename'],
        'related': ['pgroup',  'ticketcategory', 'asset', 'client',
               'frequency', 'job', 'qset', 'people', 'parent', 'bu'],
        'form_class':scd_forms.I_TourFormJobneed,
        'subform' : scd_forms.Child_I_TourFormJobneed,
        'initial': {
        'identifier': am.Jobneed.Identifier.INTERNALTOUR,
        'frequency' : am.Jobneed.Frequency.NONE
        }
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        ic(R)
        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = P['model'].objects.get_internaltourlist_jobneed(request, P['related'], P['fields'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        elif R.get('id'):
            obj = P['model'].objects.get(id = R['id'])
            form = P['form_class'](instance = obj, initial = P['initial'])
            log.info("object retrieved %s" % (obj.jobdesc))
            checkpoints = self.get_checkpoints(P, obj = obj)
            cxt = {'internaltourform': form, 'child_internaltour': P['subform'](prefix='child'), 'edit': True,
                'checkpoints': checkpoints}
            return render(request, P['template_form'], context = cxt)
    
    def get_checkpoints(self, P, obj):
        log.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = P['model'].objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory'
            ).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qsetname', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            log.critical("something went wrong", exc_info = True)
            raise

        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints



class JobneedExternalTours(LoginRequiredMixin, View):
    params = {
        'model'        : am.Jobneed,
        'template_path': 'schedhuler/e_tourlist_jobneed.html',
        'template_form': 'schedhuler/e_tourform_jobneed.html',
        'fields'       : ['jobdesc', 'people__peoplename', 'pgroup__groupname', 'id', 'ctzoffset',
            'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime', 'performedby__peoplename'],
        'related': ['pgroup',  'ticketcategory', 'asset', 'client',
               'frequency', 'job', 'qset', 'people', 'parent', 'bu'],
        'form_class': scd_forms.E_TourFormJobneed,
        'initial'   : {
            'identifier': am.Jobneed.Identifier.EXTERNALTOUR,
            'frequency' : am.Jobneed.Frequency.NONE
        }
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        ic(R)
        # first load the template
        if R.get('template'): return render(request, P['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = P['model'].objects.get_externaltourlist_jobneed(request, P['related'], P['fields'])
            return rp.JsonResponse(data = {'data':list(objs)})
        
        elif R.get('id'):
            obj = P['model'].objects.get(id = R['id'])
            form = P['form_class'](instance = obj, initial = P['initial'])
            log.info("object retrieved %s" % (obj.jobdesc))
            checkpoints = self.get_checkpoints(P, obj = obj)
            cxt = {'externaltourform': form, 'edit': True,
                'checkpoints': checkpoints}
            return render(request, P['template_form'], context = cxt)
    
    def get_checkpoints(self, P, obj):
        log.info("getting checkpoints for the internal tour [start]")
        checkpoints = None

        try:
            checkpoints = P['model'].objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people', 'job', 'client', 'bu',
                'ticketcategory'
            ).filter(parent_id = obj.id).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qsetname', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id').order_by('seqno')

        except Exception:
            log.critical("something went wrong", exc_info = True)
            raise

        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints

class JobneedTasks(LoginRequiredMixin, View):
    params = {
        'model'        : am.Jobneed,
        'template_path':  'schedhuler/tasklist_jobneed.html',
        'fields'       : [
                    'jobdesc', 'people__peoplename', 'pgroup__groupname', 'id',
                    'plandatetime', 'expirydatetime', 'jobstatus', 'gracetime',
                    'performedby__peoplename', 'asset__assetname', 'qset__qsetname',
                    'ctzoffset'],
        'related': [
                'pgroup',  'ticketcategory', 'asset', 'client','ctzoffset',
                'frequency', 'job', 'qset', 'people', 'parent', 'bu'],
        'template_form': 'schedhuler/taskform_jobneed.html',
        'form_class':scd_forms.TaskFormJobneed
    }

    def get(self, request, *args, **kwargs):
        R = request.GET

        # first load the template
        if R.get('template'): return render(request, self.params['template_path'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            p = self.params
            objs = self.params['model'].objects.get_last10days_jobneedtasks(
                p['related'], p['fields'], request)
            resp = rp.JsonResponse(data = {'data':list(objs)})
            return resp

        # load form with instance
        elif R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'taskformjobneed':self.params['form_class'](request = request, instance = obj),
                    'edit':True}
            return render(request, self.params['template_form'], context = cxt)


class SchdTasks(LoginRequiredMixin, View):
    params={
        'model'        : am.Job,
        'template_path': 'schedhuler/schd_tasklist_job.html',
        'fields'       : ['jobname', 'people__peoplename', 'pgroup__groupname',
                        'fromdate', 'uptodate', 'qset__qsetname', 'asset__assetname',
                        'planduration', 'gracetime', 'expirytime', 'id', 'ctzoffset'],
        'related'      : ['pgroup', 'people', 'asset'],
        'form_class': scd_forms.SchdTaskFormJob,
        'template_form': 'schedhuler/schd_taskform_job.html',
        'initial': {
                'starttime'   : time(00, 00, 00),
                'endtime'     : time(00, 00, 00),
                'fromdate'   : datetime.combine(date.today(), time(00, 00, 00)),
                'uptodate'   : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
                'identifier'  : am.Job.Identifier.TASK,
                'frequency'   : am.Job.Frequency.NONE,
                'scantype'    : am.Job.Scantype.QR,
                'priority'    : am.Job.Priority.LOW,
                'planduration': 5,
                'gracetime'   : 5,
                'expirytime'  : 5
            }
    }

    def get(self, request, *args, **kwargs):
        R = request.GET
        # first load the template
        if R.get('template'): return render(request, self.params['template_path'])

        # then load the table with objects for table_view
        if R.get('action') == 'list':
            log.info('Retrieve Tasks view')
            objects = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(jobname='NONE'), parent__jobname='NONE', identifier="TASK"
            ).values(*self.params['fields']).order_by('-cdtz')
            log.info(f'Tasks objects {len(objects)} retrieved from db' if objects else "No Records!")
            return rp.JsonResponse(data = {'data':list(objects)})

        # load form with instance
        elif R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'schdtaskform':self.params['form_class'](request = request, instance = obj),
                    'edit':True}
            return render(request, self.params['template_form'], context = cxt)

        # return empty form
        elif R.get('action') == 'form':
            cxt = {
            'schdtaskform':self.params['form_class'](initial = self.params['initial'], request = request)
            }
            return render(request, self.params['template_form'], context = cxt)

        elif R.get('runscheduler'):
            # run job scheduler
            pass

    def post(self, request, *args, **kwargs):
        R = request.POST

        log.info('Task form submitted')
        data, create = QueryDict(R['formData']), True
        utils.display_post_data(data)
        if pk := R.get('pk', None):
            obj = utils.get_model_obj(pk, request, {'model': self.params['model']})
            form = self.params['form_class'](
                instance = obj, data = data, request = request)
            log.info("retrieved existing task whose jobname:= '%s'" %
                     (obj.jobname))
        else:
            form = self.params['form_class'](data = data, request = request)
            log.info("new task submitted following is the form-data:\n%s\n" %
                     (pformat(form.data)))
        response = None
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                if form.is_valid():
                    response = self.process_valid_schd_taskform(request, form)
                else:
                    response = self.process_invalid_schd_taskform(
                        form)
        except Exception:
            log.critical(
                "failed to process form, something went wrong", exc_info = True)
            response = rp.JsonResponse(
                {'errors': 'Failed to process form, something went wrong'}, status = 404)
        return response

    def process_valid_schd_taskform(self, request, form):
        resp = None
        log.info("task form processing/saving [ START ]")
        try:
            job         = form.save(commit = False)
            job.parent_id  = 1
            job.save()
            job = putils.save_userinfo(job, request.user, request.session)
            log.info('task form saved success...')
        except Exception as ex:
            log.critical("task form is processing failed", exc_info = True)
            resp = rp.JsonResponse(
                {'error': "saving schd_taskform failed..."}, status = 404)
            raise ex from ex
        else:
            log.info("task form is processed successfully")
            resp = rp.JsonResponse({'jobname': job.jobname,
                'url': f'{reverse("schedhuler:jobschdtasks")}?id={job.id}'},
                status = 200)
        log.info("task form processing/saving [ END ]")
        return resp

    def process_invalid_schd_taskform(self, form):
        log.info(
            "processing invalidt task form sending errors to the client [ START ]")
        cxt = {"errors": form.errors}
        log.info(
            "processing invalidt task form sending errors to the client [ END ]")
        return rp.JsonResponse(cxt, status = 404)


class InternalTourScheduling(LoginRequiredMixin, View):
    params = {
        'template_form': 'schedhuler/schd_i_tourform_job.html',
        'template_list': 'schedhuler/schd_i_tourlist_job.html',
        'form_class'   : scd_forms.Schd_I_TourJobForm,
        'subform'      : scd_forms.SchdChild_I_TourJobForm,
        'model'        : am.Job,
        'related'      : ['pgroup', 'people'],
        'initial'      : {
            'starttime' : time(00, 00, 00),
            'endtime'   : time(00, 00, 00),
            'expirytime': 0,
            'identifier': am.Job.Identifier.INTERNALTOUR,
            'priority'  : am.Job.Priority.LOW,
            'scantype'  : am.Job.Scantype.QR,
            'gracetime' : 5,
            'planduration' : 5,
            'fromdate'  : datetime.combine(date.today(), time(00, 00, 00)),
            'uptodate'  : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
        },
        'fields'       : ['id', 'jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                        'planduration', 'gracetime', 'expirytime']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # return template
        if R.get('template') == 'true':
            return render(request, P['template_list'])

        if R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            log.info(f'object retrieved {obj}')
            form        = P['form_class'](instance = obj)
            checkpoints = self.get_checkpoints(obj, P)
            cxt = {'schdtourform': form, 'childtour_form': P['subform'](), 'edit': True,
                   'checkpoints': checkpoints}
            return render(request, P['template_form'], cxt)


        if R.get('action') == 'list':
            objs = P['model'].objects.get_scheduled_internal_tours(
                P['related'], P['fields']
            )
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        elif R.get('action') == 'list':
            cxt = {'schdtourform':P['form_class'](request = request, initial = P['initial']),
                    'childtour_form':P['json_form']()}
            return render(request, P['template_form'], cxt)

    def post(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        pk, data = request.POST.get('pk', None), QueryDict(request.POST.get('formData'))
        try:
            if pk:
                msg = 'internal scheduler tour'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), kwargs = {'request':request})
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp


    def handle_valid_form(self, form, request):
        data = request.POST.get("asssigned_checkpoints")
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                assigned_checkpoints = json.loads(data)
                ic(form.data)
                job = form.save(commit = False)
                job.parent_id = job.asset_id = job.qset_id = 1
                job.save()
                job = putils.save_userinfo(job, request.user, request.session)
                self.save_checpoints_for_tour(assigned_checkpoints, job, request)
                log.info('guard tour  and its checkpoints saved success...')
                return rp.JsonResponse({'jobname': job.jobname,
                    'url': f'{reverse("schedhuler:schd_internal_tour")}?id={job.id}'},
                    status = 200)
        except Exception as ex:
            log.info("error handling valid form", exc_info = True)
            raise ex


    def save_checpoints_for_tour(self, checkpoints, job, request):
        try:
            log.info(f"saving Checkpoints found {len(checkpoints)} [started]")
            ic(checkpoints)
            CP = {}
            for cp in checkpoints:
                CP['expirytime'] = cp[5]
                CP['asset']    = cp[1]
                CP['qset']     = cp[3]
                CP['seqno']       = cp[0]
                checkpoint, created = self.params['model'].objects.update_or_create(
                    parent_id  = job.id,
                    asset_id = CP['asset'],
                    qset_id  = CP['qset'],

                    defaults   = sutils.job_fields(job, CP)
                )
                checkpoint.save()
                status = "CREATED" if created else "UPDATED"
                log.info("\nsaving checkpoint:= '%s' for JOB:= '%s' with expirytime:= '%s'  %s\n" % (
                    cp[2],  job.jobname, cp[5], status))
                putils.save_userinfo(checkpoint, request.user, request.session)
        except Exception as ex:
            log.error(
                "failed to insert checkpoints, something went wrong", exc_info = True)
            raise ex
        else:
            log.info("inserting checkpoints finished...")

    def get_checkpoints(self, obj, P):
        log.info("getting checkpoints started...")
        checkpoints = None
        try:
            checkpoints = P['model'].objects.select_related(
                'parent', 'asset', 'qset', 'pgroup',
                'people',
            ).filter(parent_id = obj.id).annotate(
                assetname = F('asset__assetname'),
                qsetname = F('qset__qsetname')
                ).values(
                'seqno',
                'assetname',
                'asset_id',
                'qsetname',
                'qset_id',
                'expirytime',
                'id')
        except Exception:
            log.critical("something went wrong", exc_info = True)
            raise
        else:
            log.info("checkpoints retrieved returned success")
        return checkpoints


class ExternalTourScheduling(LoginRequiredMixin, View):
    params = {
        'template_form': 'schedhuler/schd_e_tourform_job.html',
        'template_list': 'schedhuler/schd_e_tourlist_job.html',
        'form_class'   : scd_forms.Schd_E_TourJobForm,
        'model'        : am.Job,
        'related'      : ['pgroup', 'people'],
        'initial'      : {
            'seqno':-1,
            'identifier': am.Job.Identifier.EXTERNALTOUR,
            'scantype':am.Job.Scantype.QR,
            'frequency':am.Job.Frequency.NONE,
            'starttime':time(00,00,00),
            'endtime':time(00,00,00),
            'priority':am.Job.Priority.HIGH,
            'expirytime':0,
            'gracetime' : 5,
            'planduration' : 5,
            'fromdate'  : datetime.combine(date.today(), time(00, 00, 00)),
            'uptodate'  : datetime.combine(date.today(), time(23, 00, 00)) + timedelta(days = 2),
        },
        'fields'       : ['id', 'jobname', 'people__peoplename', 'pgroup__groupname', 'fromdate', 'uptodate',
                        'planduration', 'gracetime', 'expirytime', 'bu__buname']
    }


    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params

        # return template first
        if R.get('template') == 'true':
            return render(request, P['template_list'])
        
        # return resp for for list view
        if R.get('action') == 'list':
            objs = P['model'].objects.get_listview_objs_schdexttour(request)
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        # return resp for job creation 
        elif R.get('action') == 'form':
            cxt = {'schdexternaltourform': P['form_class'](
            request = request, initial = P['initial'])}
            return render(request, P['template_form'], context = cxt)
        
        # return resp to populate the sites from sitgroup 
        elif R.get('action') == "get_sitesfromgroup":
            if R['id'] == 'None': return rp.JsonResponse({'data':[]}, status = 200)
            job = utils.get_model_obj(int(R['id']), request, P)
            objs = pm.Pgbelonging.objects.get_sitesfromgroup(job)
            return rp.JsonResponse({'data':list(objs)}, status = 200)
        
        # return resp to load checklist
        elif R.get('action') == "loadChecklist":
            qset =  am.QuestionSet.objects.load_checklist()
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)
        
        # return resp for updation of job
        elif R.get('id'):
            obj = utils.get_model_obj(int(R['id']), request, P)
            initial = {'israndom':obj.other_info['is_randomized'],
                       'tourfrequency':obj.other_info['tour_frequency'],
                       'breaktime':obj.other_info['breaktime']}     #obj.other_info['breaktime']}
            cxt = {'schdexternaltourform': P['form_class'](instance=obj, request = request, initial=initial)}
            ic(cxt['schdexternaltourform'].as_p())
            return render(request, P['template_form'], context = cxt)
        



    def post(self, request, *args, **kwargs):
        P = self.params
        pk, R = request.POST.get('pk', None), request.POST
        formData = QueryDict(request.POST.get('formData'))
        try:
            if R.get('action')=='saveCheckpoints':
                checkpoints =  json.loads(R.get('checkpoints'))
                return self.saveCheckpointsinJob(R, checkpoints, P, request)
            elif pk:
                msg = 'external scheduler tour'
                form = utils.get_instance_for_update(
                    formData, P, msg, int(pk), kwargs = {'request':request})
            else:
                form = P['form_class'](formData)
            if form.is_valid():
                return self.handle_valid_form(form, request, P)
            cxt = {'errors': form.errors}
            return utils.handle_invalid_form(request, self.params, cxt)
        except Exception as ex:
            return utils.handle_Exception(request)


    def handle_valid_form(self, form, request, P):
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                job = form.save(commit=False)
                job.other_info['tour_frequency'] = form.cleaned_data['tourfrequency']
                job.other_info['is_randomized'] = form.cleaned_data['israndom']
                job.other_info['breaktime'] = form.cleaned_data['breaktime']
                job.save()
                job = putils.save_userinfo(job, request.user,request.session)
                #self.save_checkpoints_injob_fromgroup(job, P)
                return rp.JsonResponse({'pk':job.id}, status = 200)
        except Exception as ex:
            log.error("external tour form, handle valid form failed", exc_info = True)
            return utils.handle_Exception(request)
        
    def saveCheckpointsinJob(self, R, checkpoints, P, request):
        try:
            #ic(checkpoints)
            job = utils.get_model_obj(R['parent_id'], request, P)   
            P['model'].objects.filter(parent_id = job.id).delete()
            count=0
            for cp in checkpoints:
                ic(cp)
                #ic(sutils.job_fields(job, cp, external=True))
                obj = am.Job.objects.create(
                    **sutils.job_fields(job, cp, external=True))
                putils.save_userinfo(obj, request.user, request.session, bu=cp['buid'])
                count+=1
            if count == len(checkpoints):
                objs = P['model'].objects.get_sitecheckpoints_exttour(job)
                return rp.JsonResponse({'count':count, 'data':list(objs)}, status = 200 )
            return rp.JsonResponse({"error":"Checkpoints not saved"}, status = 400)
        except Exception:
            log.error("something went wrong...", exc_info=True)
            raise
        

class TourJobneedEditorView(LoginRequiredMixin, View):
    params = {
        'model':am.Jobneed,

    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params

        if R.get('action') == 'get_tourdetails':
            qset = P['model'].objects.get_tourdetails(R)
            return rp.JsonResponse({'data':list(qset)}, status = 200)



class JobneednJNDEditor(LoginRequiredMixin, View):
    params = {
        'model':am.Jobneed,
        'jnd':am.JobneedDetails,
        'fields':['id', 'quesname', 'answertype', 'min', 'max', 'options', 'alerton',
                  'ismandatory']
    }
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        ic(R)
        if R.get('action') == 'get_jndofjobneed' and R.get('jobneedid'):
            objs = P['jnd'].objects.get_jndofjobneed(R)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        return rp.JsonResponse({'data':[]}, status=200)
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        ic(R)
        if R.get('tourjobneed'):
            data = P['model'].objects.handle_jobneedpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)
        if R.get('question'):
            data = P['qsb'].objects.handle_questionpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)