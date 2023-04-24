from django.http import Http404, QueryDict, response as rp, HttpResponse
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import resolve
from django.conf import settings
from django.contrib.gis.db.models.functions import  AsWKT
from django.core.exceptions import  EmptyResultSet
from django.views.generic.base import View
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
import psycopg2.errors as pg_errs
import apps.activity.models as am
from pprint import pformat
import apps.activity.filters as aft
import apps.activity.forms as af
import apps.peoples.utils as putils
import apps.core.utils as utils
import apps.activity.utils as av_utils
import apps.onboarding.forms as obf
import apps.onboarding.models as obm
import apps.peoples.models as pm
from apps.service.utils import get_model_or_form
import logging
import mimetypes
from datetime import datetime, timedelta
import pytz
logger = logging.getLogger('__main__')
log = logger

# Create your views here.
class Question(LoginRequiredMixin, View):
    params = {
        'form_class'   : af.QuestionForm,
        'template_form': 'activity/partials/partial_ques_form.html',
        'template_list': 'activity/question.html',
        'partial_form' : 'peoples/partials/partial_ques_form.html',
        'partial_list' : 'peoples/partials/partial_people_list.html',
        'related'      : ['unit'],
        'model'        : am.Question,
        'filter'       : aft.QuestionFilter,
        'fields'       : ['id', 'quesname', 'answertype', 'isworkflow', 'unit__tacode', 'cdtz', 'cuser__peoplename' ],
        'form_initials': {
        'answertype'   : am.Question.AnswerType.DROPDOWN,
        'category'     : 1,                               'unit': 1}
    }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return cap_list data
        if R.get('template'): return render(request, self.params['template_list'])
        if R.get('action', None) == 'list':
            objs = self.params['model'].objects.questions_listview(request, self.params['fields'], self.params['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
            

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'ques_form': self.params['form_class'](request = request, initial = self.params['form_initials']),
                   'msg': "create question requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, 'ques_form', obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData']).copy()
            if pk := request.POST.get('pk', None):
                msg = "question_view"
                ques = utils.get_model_obj(pk, request, self.params)
                form = self.params['form_class'](
                    data, instance = ques, request = request)
                create = False
            else:
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form,  request, create)
            else:
                ic(form.cleaned_data, form.data, form.errors)
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form,  request, create):
        logger.info('ques form is valid')
        ques = None
        try:
            ques = form.save()
            ques = putils.save_userinfo(
                ques, request.user, request.session, create = create)
            logger.info("question form saved")
            data = {'msg': f"{ques.quesname}",
            'row': am.Question.objects.values(*self.params['fields']).get(id = ques.id)}
            logger.debug(data)
            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('Question')

class QuestionSet(LoginRequiredMixin, View):
    params = {
        'form_class'   : af.QuestionSetForm,
        'template_form': 'activity/questionset_form.html',
        'template_list' : 'activity/questionset.html',
        'related'      : ['unit'],
        'model'        : am.QuestionSet,
        'fields'       : ['qsetname', 'type', 'id', 'ctzoffset', 'cdtz', 'mdtz'],
        'form_initials': { 'type':'QUESTIONSET'}
    }

    def get(self, request, *args, **kwargs):
        R, P, resp = request.GET, self.params, None
        # first load the template
        if R.get('template'):
            return render(request, P['template_list'])

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.questionset_listview(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {
                'questionsetform': self.params['form_class'](
                    request=request, initial=self.params['form_initials']
                ),
                'msg': "create questionset requested",
            }
            resp = render(request, self.params['template_form'], context = cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            log.info('detail view requested')
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'questionsetform': self.params['form_class'](request = request, instance = obj)}
            resp = render(request, self.params['template_form'], context = cxt)
            log.debug(resp)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            logger.debug(pformat(request.POST))
            data = QueryDict(request.POST['formData'])
            ic(data)
            if pk := request.POST.get('pk', None):
                logger.debug("form is with instance")
                msg = 'questionset'
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request':request})
                logger.debug(pformat(form.data, width = 41, compact = True))
                create = False
            else:
                logger.debug("form is without instance")
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def get_questions_for_form(qset):
        try:
            questions = list(am.QuestionSetBelonging.objects.select_related(
                "question").filter(qset_id = qset).values(
                'ismandatory', 'seqno', 'max', 'min', 'alerton','isavpt', 'avpttype',
                'options', 'question__quesname', 'answertype', 'question__id'
            ))
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise
        else:
            return questions

    def handle_valid_form(self, form, request, create):
        logger.info('questionset form is valid')
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                #assigned_questions = json.loads(
                #    request.POST.get("asssigned_questions"))
                ic(form.data)
                qset = form.save()
                putils.save_userinfo(qset, request.user,
                                    request.session, create = create)
                logger.info('questionset form is valid')
                fields = {'qset': qset.id, 'qsetname': qset.qsetname,
                        'client': qset.client_id}
                #self.save_qset_belonging(request, assigned_questions, fields)
                data = {'success': "Record has been saved successfully",
                        'parent_id':qset.id
                        }
                return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Question Set')

    @staticmethod
    def save_qset_belonging(request, assigned_questions, fields):
        try:
            logger.info("saving QuestoinSet Belonging [started]")
            logger.info(f'{" " * 4} saving QuestoinSet Belonging found {len(assigned_questions)} questions')

            logger.debug(
                f"\nassigned_questoins, {pformat(assigned_questions, depth = 1, width = 60)}, qset {fields['qset']}")
            av_utils.insert_questions_to_qsetblng(
                assigned_questions, am.QuestionSetBelonging, fields, request)
            logger.info("saving QuestionSet Belongin [Ended]")
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise

class MasterAsset(LoginRequiredMixin, View):
    params = {
        'form_class': None,
        'template_form': 'activity/partials/partial_masterasset_form.html',
        'template_list': 'activity/master_asset_list.html',
        'partial_form': 'peoples/partials/partial_masterasset_form.html',
        'partial_list': 'peoples/partials/master_asset_list.html',
        'related': ['parent', 'type'],
        'model': am.Asset,
        'filter': aft.MasterAssetFilter,
        'fields': ['assetname', 'assetcode', 'runningstatus',
                   'parent__assetcode', 'gps', 'id', 'enable'],
        'form_initials': {}
    }
    list_grid_lookups = {}
    view_of = label = None

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'], {'label':self.label})
        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "master_assetlist", 'filt_name': "master_asset_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.annotate(
                gps = AsWKT('gpslocation')
                ).select_related(
                *self.params['related']).filter(
                    **self.list_grid_lookups).values(*self.params['fields'])
            utils.printsql(objs)
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            self.params['form_initials'].update({
                'type': 1,
                'parent': 1})
            cxt = {'master_assetform': self.params['form_class'](request = request, initial = self.params['form_initials']),
                   'msg': f"create {self.label} requested",
                   'label': self.label}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'label': self.label}
            resp = utils.render_form_for_update(
                request, self.params, 'master_assetform', obj, extra_cxt = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, False
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = f'{self.label}_view'
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                create = False
            else:
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        raise NotImplementedError()

class Checklist(LoginRequiredMixin, View):
    params = {
        'form_class'   : af.ChecklistForm,
        'template_form': 'activity/checklist_form.html',
        'template_list' : 'activity/checklist.html',
        'related'      : ['unit'],
        'model'        : am.QuestionSet,
        'filter'       : aft.MasterQsetFilter,
        'fields'       : ['qsetname', 'type', 'id', 'ctzoffset', 'cdtz', 'mdtz'],
        'form_initials': { 'type':'CHECKLIST'}
    }
    
    def get(self, request, *args, **kwargs):
        R, P, resp = request.GET, self.params, None
        # first load the template
        if R.get('template'):
            return render(request, P['template_list'])

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.checklist_listview(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'checklistform': self.params['form_class'](request=request, initial=self.params['form_initials']),
                   'qsetbng': af.QsetBelongingForm(initial={'ismandatory': True}), 'msg': "create checklist form requested"}

            resp = render(request, self.params['template_form'], context = cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, False)

        elif R.get('id', None):
            log.info('detail view requested')
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'checklistform': self.params['form_class'](request = request, instance = obj)}
            resp = render(request, self.params['template_form'], context = cxt)
            log.debug(resp)
        return resp
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            logger.debug(pformat(request.POST))
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                logger.debug("form is with instance")
                msg = 'checklist'
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request':request})
                logger.debug(pformat(form.data, width = 41, compact = True))
                create = False
            else:
                logger.debug("form is without instance")
                form = self.params['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp
    
    @staticmethod
    def get_questions_for_form(qset):
        try:
            questions = list(am.QuestionSetBelonging.objects.select_related(
                "question").filter(qset_id = qset).values(
                'ismandatory', 'seqno', 'max', 'min', 'alerton','isavpt', 'avpttype',
                'options', 'question__quesname', 'answertype', 'question__id'
            ))
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise
        else:
            return questions


    def handle_valid_form(self, form, request, create):
        logger.info('checklist form is valid')
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                # assigned_questions = json.loads(
                #     request.POST.get("asssigned_questions"))
                qset = form.save()
                putils.save_userinfo(qset, request.user,
                                    request.session, create = create)
                logger.info('checklist form is valid')
                fields = {'qset': qset.id, 'qsetname': qset.qsetname,
                        'client': qset.client_id}
                #self.save_qset_belonging(request, assigned_questions, fields)
                data = {'success': "Record has been saved successfully",
                        'parent_id':qset.id
                        }
                return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Question Set')

    @staticmethod
    def save_qset_belonging(request, assigned_questions, fields):
        try:
            logger.info("saving QuestoinSet Belonging [started]")
            logger.info(f'{" " * 4} saving QuestoinSet Belonging found {len(assigned_questions)} questions')

            logger.debug(
                f"\nassigned_questoins, {pformat(assigned_questions, depth = 1, width = 60)}, qset {fields['qset']}")
            av_utils.insert_questions_to_qsetblng(
                assigned_questions, am.QuestionSetBelonging, fields, request)
            logger.info("saving QuestionSet Belongin [Ended]")
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise

def deleteQSB(request):
    if request.method != 'GET':
        return Http404

    status = None
    try:
        quesname = request.GET.get('quesname')
        answertype = request.GET.get('answertype')
        qset = request.GET.get('qset')
        logger.info("request for delete QSB '%s' start", (quesname))
        am.QuestionSetBelonging.objects.get(
            question__quesname = quesname,
            answertype = answertype,
            qset_id = qset).delete()
        statuscode = 200
        logger.info("Delete request executed successfully")
    except Exception:
        logger.critical("something went wrong", exc_info = True)
        statuscode = 404
        raise
    status = "success" if statuscode == 200 else "failed"
    data = {"status": status}
    return rp.JsonResponse(data, status = statuscode)

class Checkpoint(LoginRequiredMixin, View):
    params = {
        'form_class': af.CheckpointForm,
        'template_form': 'activity/partials/partial_masterasset_form.html',
        'template_list': 'activity/master_asset_list.html',
        'partial_form': 'peoples/partials/partial_masterasset_form.html',
        'partial_list': 'peoples/partials/master_asset_list.html',
        'related': ['parent', 'type'],
        'model': am.Asset,
        'fields': ['assetname', 'assetcode', 'runningstatus', 'identifier','location__locname',
                   'parent__assetname', 'gps', 'id', 'enable'],
        'form_initials': {'runningstatus': 'WORKING',
                          'identifier': 'CHECKPOINT',
                          'iscritical': False, 'enable': True}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # first load the template
        if R.get('template'): return render(request, P['template_list'], {'label':"Checkpoint"})
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_checkpointlistview(request, P['related'], P['fields'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            P['form_initials'].update({
                'type': 1,
                'parent': 1})
            cxt = {'master_assetform': P['form_class'](request=request, initial=P['form_initials']),
                   'msg': "create checkpoint requested",
                   'label': "Checkpoint"}

            resp = utils.render_form(request, P, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, True)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'label': "Checkpoint"}
            resp = utils.render_form_for_update(
                request, P, 'master_assetform', obj, extra_cxt = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create, P = None, False, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = 'Checkpoint_view'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk), kwargs={'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('checkpoint form is valid')
        P = self.params
        try:
            cp = form.save(commit=False)
            cp.gpslocation = form.cleaned_data['gpslocation']
            putils.save_userinfo(
                cp, request.user, request.session, create = create)
            logger.info("checkpoint form saved")
            data = {'msg': f"{cp.assetcode}",
            'row': am.Asset.objects.get_checkpointlistview(request, P['related'], P['fields'], id=cp.id)}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Checkpoint')

class Smartplace(LoginRequiredMixin, View):
    params = {
        'form_class': af.SmartPlaceForm,
        'template_form': 'activity/partials/partial_masterasset_form.html',
        'template_list': 'activity/master_asset_list.html',
        'partial_form': 'peoples/partials/partial_masterasset_form.html',
        'partial_list': 'peoples/partials/master_asset_list.html',
        'related': ['parent', 'type'],
        'model': am.Asset,
        'fields': ['assetname', 'assetcode', 'runningstatus', 'identifier',
                   'parent__assetname', 'gps', 'id', 'enable'],
        'form_initials': {'runningstatus': 'WORKING',
                          'identifier': 'SMARTPLACE',
                          'iscritical': False, 'enable': True}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # first load the template
        if R.get('template'): return render(request, P['template_list'], {'label':"Smartplace"})
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_smartplacelistview(request, P['related'], P['fields'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        if R.get('action', None) == 'form':
            P['form_initials'].update({
                'type': 1,
                'parent': 1})
            cxt = {'master_assetform': P['form_class'](request=request, initial=P['form_initials']),
                   'msg': "create Smartplace requested",
                   'label': "Smartplace"}

            resp = utils.render_form(request, P, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, True)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'label': "Smartplace"}
            resp = utils.render_form_for_update(
                request, P, 'master_assetform', obj, extra_cxt = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create, P = None, False, self.params
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = 'Smartplace_view'
                form = utils.get_instance_for_update(
                    data, P, msg, int(pk),  kwargs={'request':request})
                create = False
            else:
                form = P['form_class'](data, request = request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('smarplace form is valid')
        P = self.params
        try:
            sp = form.save(commit=False)
            sp.gpslocation = form.cleaned_data['gpslocation']
            putils.save_userinfo(
                sp, request.user, request.session, create = create)
            logger.info("smartplace form saved")
            data = {'msg': f"{sp.assetcode}",
            'row': am.Asset.objects.get_smartplacelistview(request, P['related'], P['fields'], id=sp.id)}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Smartplace')


class AdhocTasks(LoginRequiredMixin, View):
    params = {
        'form_class'   : af.AdhocTaskForm,
        'template_form': 'activity/adhoc_jobneed_taskform.html',
        'template_list': 'activity/adhoc_jobneed_task.html',
        'related'      : ['performedby', 'qset', 'asset'],
        'model'        : am.Jobneed,
        'fields'       : ['id', 'plandatetime', 'jobdesc', 'performedby__peoplename', 'jobstatus',
                   'qset__qsetname', 'asset__assetname', 'ctzoffset'],
        'form_initials': {},
        'idf'          : ''}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        from datetime import datetime
        now = datetime.now()

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_adhoctasks_listview(R, self.params['idf'])
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)

        if R.get('action', None) == 'form':
            cxt = {'adhoctaskform': self.params['form_class'](request = request),
                   'msg': "create adhoc task requested"}
            return render(request, self.params['template_form'], context = cxt)


class AdhocTours(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/adhoc_jobneed_tours.html',
        'model':am.Jobneed,
        'fields':['id', 'plandatetime', 'jobdesc', 'performedby__peoplename', 'jobstatus',
                  'ctzoffset', 'qset__qsetname', 'asset__assetname'],
        'related':['performedby', 'qset', 'asset'],
    }
    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        from datetime import datetime
        now = datetime.now()
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_adhoctour_listview(R)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
    


class AssetMaintainceList(LoginRequiredMixin, View):
    params = {
        'template_list': 'activity/assetmaintainance_list.html',
        'model'        : am.Jobneed,
        'fields':['id', 'plandatetime', 'jobdesc', 'people__peoplename', 'asset__assetname',
        'ctzoffset', 'asset__runningstatus', 'gpslocation', 'identifier'],
        'related':['asset', 'people']
    }
    
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        if R.get('action') == 'list':
            #last 3 months
            objs = P['model'].objects.get_assetmaintainance_list(request, P['related'], P['fields'])
            return rp.JsonResponse({'data':list(objs)}, status=200)



class QsetNQsetBelonging(LoginRequiredMixin, View):
    params = {
        'model1':am.QuestionSet,
        'qsb':am.QuestionSetBelonging,
        'fields':['id', 'quesname', 'answertype', 'min', 'max', 'options', 'alerton',
                  'ismandatory', 'isavpt', 'avpttype']
    }
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if(R.get('action') == 'loadQuestions'):
            qset =  am.Question.objects.questions_of_client(request, R)
            return rp.JsonResponse({'items':list(qset), 'total_count':len(qset)}, status = 200)

        if(R.get('action') == 'getquestion') and R.get('questionid') not in [None, 'null']:
            objs = am.Question.objects.get_questiondetails(R['questionid'])
            return rp.JsonResponse({'qsetbng':list(objs)}, status=200)
        
        if R.get('action') == 'get_questions_of_qset':
            objs = P['qsb'].objects.get_questions_of_qset(R)
            return rp.JsonResponse({'data':list(objs)}, status=200)

        
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if R.get('questionset'):
            data = P['model1'].objects.handle_qsetpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)
        if R.get('question'):
            data = P['qsb'].objects.handle_questionpostdata(request)
            return rp.JsonResponse({'data':list(data)}, status = 200, safe=False)
        
        
class MobileUserLog(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/mobileuserlog.html',
        'model':am.DeviceEventlog,
        'related':['bu', 'people'],
        'fields':['cdtz', 'bu__buname', 'startlocation', 'endlocation', 'signalstrength',
                  'availintmemory', 'availextmemory', 'signalbandwidth', 'ctzoffset',
                  'people__peoplename', 'gpslocation', 'eventvalue', 'batterylevel']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_mobileuserlog(request)
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
            
            

class MobileUserDetails(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/mobileuserlog.html',
        'model':am.DeviceEventlog,
        'related':['bu', 'people'],
        'fields':['cdtz', 'bu__buname', 'signalstrength',
                  'availintmemory', 'availextmemory', 'signalbandwidth', 'ctzoffset',
                  'people__peoplename', 'gpslocation', 'eventvalue', 'batterylevel']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            total, filtered, objs = self.params['model'].objects.get_mobileuserlog(request)
            ic(utils.printsql(objs))
            return  rp.JsonResponse(data = {
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total,
            }, safe = False)
            

class PeopleNearAsset(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/peoplenearasset.html',
        'model':am.Asset,
        'related':[],
        'fields':['id', 'assetcode', 'assetname', 'identifier', 'gpslocation']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_peoplenearasset(request)
            ic(utils.printsql(objs))
            return  rp.JsonResponse(data = {
                'data':list(objs)}, safe = False)
            

class WorkPermit(LoginRequiredMixin, View):
    params = {
        'template_list':'activity/workpermit_list.html',
        'model':am.WorkPermit,
        'related':[],
        'fields':['id', 'assetcode', 'assetname', 'identifier', 'gpslocation']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])
        
        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_workpermitlist(request)
            return  rp.JsonResponse(data = {
                'data':list(objs)}, safe = False)
            

class Attachments(LoginRequiredMixin, View):
    params = {
        'model':am.Attachment
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        ic(R)
        if R.get('action') == 'delete_att'  and R.get('id'):
            res = P['model'].objects.filter(id=R['id']).delete()
            if R['ownername'].lower() in ['ticket', 'jobneed', 'jobneeddetails']:
                #update attachment count
                model = get_model_or_form(R['ownername'].lower())
                model.objects.filter(uuid = R['ownerid']).update(
                    attachmentcount = P['model'].objects.filter(owner = R['ownerid']).count()
                )
                log.info('attachment count updated')
            return rp.JsonResponse({'result':res}, status=200)
        
        if R.get('action') == 'get_attachments_of_owner' and R.get('owner'):
            objs = P['model'].objects.get_att_given_owner(R['owner'])   
            return rp.JsonResponse({'data':list(objs)}, status=200)

        if R.get('action') == 'download' and R.get('filepath') and R.get('filename'):
            file = f"{settings.MEDIA_URL}{R['filepath'].replace('youtility4_media/', '')}/{R['filename']}"
            file = open(file, 'r')
            mime_type, _ = mimetypes.guess_type(R['filepath'])
            response = HttpResponse(file, content_type=mime_type)
            response['Content-Disposition'] = f"attachment; filename={R['filename']}"
            return response
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        ic(P)
        if 'img' in request.FILES:
            isUploaded, filename, filepath = utils.upload(request)
            filepath = filepath.replace(settings.MEDIA_ROOT, "")
            if isUploaded:
                if data := P['model'].objects.create_att_record(request, filename, filepath):
                    #update attachment count
                    if data['ownername'].lower() in ['ticket' ,'jobneed', 'jobneeddetails', 'wom']:
                        model = get_model_or_form(data['ownername'].lower())
                        model.objects.filter(uuid = R['ownerid']).update(attachmentcount = data['attcount'])
                        log.info('attachment count updated')
                return rp.JsonResponse(data, status = 200, safe=False)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)



class PreviewImage(LoginRequiredMixin, View):
    P = {
        'model':am.Attachment
    }
    
    
    def get(self, request, *args, **kwargs):
        R = request.GET
        
        if R.get('action') == 'getFRStatus'  and R.get('uuid'):
            resp = self.P['model'].objects.get_fr_status(R['uuid'])
            log.info(resp)
            return rp.JsonResponse(resp, status=200)
    
class GetAllSites(LoginRequiredMixin, View):
   
    def get(self, request):
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%55")
        try:
            qset = obm.Bt.objects.get_all_sites_of_client(request.session['client_id'])
            sites = qset.values('id', 'bucode','buname')
            return rp.JsonResponse(list(sites), status=200)
        except Exception as e:
            logger.error("get_allsites() exception: %s", e)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)       

class GetAssignedSites(LoginRequiredMixin, View):
    def get(self, request):
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%55")
        try:
            if data := pm.Pgbelonging.objects.get_assigned_sites_to_people(request.user.id).values_list('buid', flat=True):
                ic(data)
                sites    = obm.Bt.objects.filter(id__in = data).values('id', 'bucode','buname')
                ic(sites)
                return rp.JsonResponse(list(sites), status=200, safe=False)
        except Exception as e:
            logger.error("get_assignedsites() exception: %s", e)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)

class SwitchSite(LoginRequiredMixin, View):
    def post(self, request):
        req_buid= request.POST["buid"]
        resp = {}
        if req_buid !=" ":
            print(" iff  req_buid", req_buid )
            sites = obm.Bt.objects.filter(id=req_buid).values('id', 'bucode','buname', 'enable')[:1]
            if len(sites) > 0:
                if sites[0]['enable'] == True:
                    request.session['bu_id']  = sites[0]['id']
                    request.session['sitecode'] = sites[0]['bucode']
                    request.session['sitename'] = sites[0]['buname']
                    resp["rc"] = 0
                    resp['message'] = "successfully switched to site."
                    log.info('successfully switched to site')
                else:
                    resp["rc"] = 1
                    resp['errMsg'] = "Inactive Site"
                    log.info('Inactive Site')
            else:
                    resp["rc"] = 1
                    resp['errMsg'] = "unable to find site."
                    log.info('unable to find site.')
        else:  
            resp["rc"] = 1
            resp['errMsg'] = "unable to find site."
            log.info('unable to find site.')
        return rp.JsonResponse(resp, status=200)



# class ShowTicket(LoginRequiredMixin, View):
#     template_path = 'activity/ticket_list.html'
#     fields = ['id', 'ticketdesc','status','level','cdtz','ticketno',
#               'performedby__peoplename', 'assignedtopeople', 'assignedtogroup','ticketlog','events']
#     model = am.Ticket

#     def get(self, request, *args, **kwargs):
#         '''returns the paginated results from db'''
#         response = None
#         try:
#             print("requestttt",request.GET.get('columns', None))
#             if request.GET.get('action', None) is None:
#                 logger.info('Show Ticket view')
#                 response = render(request, self.template_path, context={})
#             if request.GET.get('action', None) =='list':
#                 kwargs={}
#                 kwargs['ticketsource']=request.GET['generatedby']
#                 length, start, objects = av_utils.list_viewdata(request, self.model, self.fields, kwargs)
#                 draw = request.GET.get('draw')
#                 count = objects.count()
#                 filtered = count
#                 logger.info(f'count {count}')
#                 return rp.JsonResponse(data={'draw': draw, 'recordsTotal': count, 'data': list(list(objects[start : start + length])), 'recordsFiltered': filtered}, status=200, safe=False)
#             if request.GET.get('action',None) == 'childlist':
#                 hostname = utils.tenant_db_from_request(request)
#                 records, length, start = av_utils.childlist_viewdata(request, hostname)
#                 draw = request.GET.get('draw')
#                 count = len(records)
#                 filtered = count
#                 return rp.JsonResponse(data={'draw': draw, 'recordsTotal': filtered, 'data': list(list(records[start : start + length])), 'recordsFiltered': filtered}, status=200, safe=False)
#         except EmptyResultSet:
#             logger.warning('empty objects retrieved', exc_info=True)
#             response = render(request, self.template_path, context={})
#             messages.error(request, 'List view not found',
#                            'alert alert-danger')
#         except Exception:
#             logger.critical('something went wrong...', exc_info=True)
#             messages.error(request, 'Something went wrong',
#                            "alert alert-danger")
#             response = redirect('/dashboard')
#         return response
    
# class CreateTicket(LoginRequiredMixin, View):
#     template_path = 'activity/ticket_form.html'
#     form_class = af.TicketForm
   
#     def get(self, request, *args, **kwargs):
#         logger.info('Create Ticket view')
#         cxt = {'ticket_form': self.form_class(request=request)}
#         return render(request, self.template_path, context=cxt)

#     def post(self, request, *args, **kwargs):
#         logger.info(f'Create Ticket form submiited {request.POST}')
#         form, response = self.form_class(request.POST, request=request), None
#         form = af.TicketForm(request.POST, request=request)
#         logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@ logged {form}")
#         status_dict = {'statusjbdata': []} 
#         try:
#             if form.is_valid():
#                 logger.info('TicketForm Form is valid')
#                 tkt = form.save(commit=False)
#                 tkt.ticketno = av_utils.increment_ticket_number()
#                 tkt.ticketsource= am.Ticket.TicketSource.USERDEFINED
#                 tkt = putils.save_userinfo(tkt, request.user, request.session)
#                 print("request session", request.session)
#                 asset =form.cleaned_data['asset']
#                 location =form.cleaned_data['location']
#                 tkt = av_utils.savejsonbdata(request, tkt, asset, location )
#                 tkt.save()
#                 av_utils.sendTicketMail(tkt.id, 'add')
#                 logger.info('TicketForm Form saved')
#                 messages.success(request, "Success record saved successfully!",
#                                  "alert alert-success")
#                 response = redirect(
#                     'activity:update_ticket', pk=tkt.id)
#             else:
#                 logger.info('Form is not valid')
#                 cxt = {'ticket_form': form, 'edit': True}
#                 response = render(request, self.template_path, context=cxt)
#         except Exception as e:
#             logger.critical("something went wrong...", exc_info=True)
#             logger.error("create ticket() exception: %s", (e))  
#             messages.error(request, "[ERROR] Something went wrong",
#                            "alert alert-danger")
#             cxt = {'ticket_form': form, 'edit': True}
#             response = render(request, self.template_path, context=cxt)
#         return response
    
# class UpdateTicket(LoginRequiredMixin, View):
#     template_path = 'activity/ticket_form.html'
#     form_class = af.TicketForm
#     model = am.Ticket

#     def get(self, request, *args, **kwargs):
#         logger.info('Update Ticket view')
#         response = None
#         try:
#             pk = kwargs.get('pk')
#             id_id = self.model.objects.get(id=pk)
#             print("id_id",id_id)
#             logger.info(f'object retrieved {id_id}')
#             form = self.form_class(instance=id_id, request= request)
#             listObj = av_utils.datastatus(request, id_id)
#             cxt = {'ticket_form': form, 'edit': True, 'tdata':listObj}
#             response = render(request, self.template_path, context=cxt)
#         except self.model.DoesNotExist:
#             messages.error(request, 'Unable to edit object not found',
#                            'alert alert-danger')
#             response = redirect('activity:ticket_form')
#         except Exception:
#             logger.critical('something went wrong', exc_info=True)
#             messages.error(request, 'Something went wrong',
#                            'alert alert-danger')
#             response = redirect('activity:ticket_form')
#         return response

#     def post(self, request, *args, **kwargs):
#         logger.info('Ticket Form submitted')
#         response = None
#         try:
#             pk = kwargs.get('pk')
#             id_id = self.model.objects.get(id=pk)
#             form = self.form_class(request.POST, instance=id_id, request= request)
#             if form.is_valid():
#                 logger.info('Ticket Form is valid')
#                 id_id = form.save(commit=False)
#                 id_id = putils.save_userinfo(
#                     id_id, request.user, request.session)
#                 asset =form.cleaned_data['asset']
#                 location =form.cleaned_data['location']
#                 id_id =     (request, id_id, asset, location)
#                 id_id.save()
#                 av_utils.sendTicketMail(id_id.id, 'edit')
#                 messages.success(request, "Success record saved successfully!",
#                                  "alert-success")
#                 response = redirect('activity:update_ticket', pk=pk)
#             else:
#                 logger.info('Form is not valid')
#                 cxt = {'ticket_form': form, 'edit': True}
#                 response = render(request, self.template_path, context=cxt)
#         except self.model.DoesNotExist:
#             logger.error('Object does not exist', exc_info=True)
#             messages.error(request, "Object does not exist",
#                            "alert alert-danger")
#             cxt = {'ticket_form': form, 'edit': True}
#             response = render(request, self.template_path, context=cxt)
#         except Exception:
#             logger.critical("something went wrong...", exc_info=True)
#             messages.error(request, "[ERROR] Something went wrong",
#                            "alert alert-danger")
#             cxt = {'ticket_form': form, 'edit': True}
#             response = render(request, self.template_path, context=cxt)
#         return response
    
# def get_allticket(request):
#     att       = 0
#     try:
#         startdate = datetime.now() - timedelta(hours = 24)
#         start_utc = startdate.astimezone(pytz.UTC).replace(microsecond=0)
#         enddate = datetime.now().astimezone(pytz.UTC).replace(microsecond=0)
#         print("start_utc", start_utc, enddate, request.session['is_superadmin']);
#         if request.method == "GET":
#             if request.session['is_superadmin']:
#                 att = am.Ticket.objects.filter(ticketsource='SYSTEMGENERATED',cdtz__range=[start_utc, enddate]).count()
#             else:
#                 bu_list = av_utils.get_assignedsitedata(request)
#                 if len(bu_list) > 0 :
#                     print("bu_list", bu_list)
#                     att = am.Ticket.objects.filter(Q(ticketsource='SYSTEMGENERATED'), Q(bu__in = bu_list),cdtz__range=[start_utc, enddate]).count()
#                     print("att", att, am.Ticket.objects.filter(Q(ticketsource='SYSTEMGENERATED'), Q(bu__in = bu_list),cdtz__range=[start_utc, enddate]).query)
#     except Exception as e:
#         logger.error("get_allticket() exception: %s", (e))  
 
#     return HttpResponse(att)

# def get_last24hrticket(request):
#     draw, count, start, filtered, length = 1, 0, 0, 0, 0
#     att = []
#     try:
#         draw = request.GET['draw']
#         startdate = datetime.now() - timedelta(hours = 24)
#         start_utc = startdate.astimezone(pytz.UTC).replace(microsecond=0)
#         enddate = datetime.now().astimezone(pytz.UTC).replace(microsecond=0)
#         jsondata={'data':[]}
#         col0, col1, col2, col3,col4, col5, colval0, colval1, colval2, colval3, colval4, colval5,length, start = av_utils.getdatatable_filter(request)
#         kwargs = av_utils.column_filter(col0, col1, col2, col3, col4, col5, colval0, colval1, colval2, colval3, colval4, colval5, start_utc)
#         print("start_utc, enddate", start_utc, enddate)
#         if request.session['is_superadmin']:
#             att = am.Ticket.objects.filter(ticketsource="SYSTEMGENERATED", cdtz__range=[start_utc, enddate]).values('id', 'ticketdesc', 'ticketno', 'cdtz', 'status', 'level', 'performedby__peoplename', 'bu__buname')
#         else:
#             bu_list = av_utils.get_assignedsitedata(request)
#             kwargs['bu__in'] = bu_list
#             print("kwargs", kwargs['bu__in'])
#             if len(bu_list) > 0 :
#                 att = am.Ticket.objects.filter(ticketsource='SYSTEMGENERATED',cdtz__range=[start_utc, enddate] ,bu__in = bu_list).order_by('-cdtz').values('id', 'ticketdesc', 'ticketno', 'cdtz', 'status', 'level', 'performedby__peoplename', 'bu__buname')
#         count= att.count()
#         print("count", count)
#         if colval0 !="" or colval1!="" or colval2 !="" or colval3!="" or colval4!="" or colval5!="":
#             att = am.Ticket.objects.filter(ticketsource='SYSTEMGENERATED',  **kwargs).order_by('-cdtz').values('id', 'ticketdesc', 'ticketno', 'cdtz', 'status', 'level', 'performedby__peoplename', 'bu__buname')
#             filtered = att.count()
#             print("att", att.query)
#         else:
#             filtered = count
#         jsondata = {'data': list(att[start: start+length])}
#         print("jsondata",jsondata, jsondata)  
#         print("att", att.query)  
#     except Exception as e: 
#         pass
#     return rp.JsonResponse(data = {
#     'draw':draw, 'recordsTotal':count,
#     'data' : list(list(att[start: start+length])), 
#     'recordsFiltered': filtered}, status=200, safe=False)
    

class Asset(LoginRequiredMixin,View):
    P = {
        'template_form':'activity/asset_form.html',
        'template_list':'activity/asset_list.html',
        'model':am.Asset,
        'form':af.AssetForm,
        'jsonform':af.AssetExtrasForm,
        'related':['parent'],
        'fields':['assetcode', 'assetname', 'id', 'parent__assetname',
                  'runningstatus', 'enable', 'gps', 'identifier', 'location__locname']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_assetlistview(P['related'], P['fields'], request)
            ic(objs)
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'assetform': P['form'](request=request),
                   'assetextrasform': P['jsonform'](request=request),
                   'msg': "create asset requested"}
            resp = render(request, P['template_form'], cxt)
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)
        
        # return form with instance
        elif R.get('id', None):
            from .utils import get_asset_jsonform
            asset = utils.get_model_obj(R['id'], request, P)
            cxt = {'assetform': P['form'](instance = asset, request=request),
                   'assetextrasform': get_asset_jsonform(asset, request),
                   'msg': "Asset Update Requested"}
            resp = render(request, P['template_form'], context = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        ic(data)
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "asset_view", False  
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            ic(form.instance.id)
            jsonform = self.P['jsonform'](data, request=request)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request, create)
            else:
                ic(form.errors)
                cxt = {'errors': form.errors}
                if jsonform.errors:
                    cxt.update({'errors': jsonform.errors})
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request ,create):
        logger.info('asset form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ic(request.POST, request.FILES)
            asset = form.save(commit=False)
            asset.gpslocation = form.cleaned_data['gpslocation']
            asset.save()
            if av_utils.save_assetjsonform(jsonform, asset):
                asset = putils.save_userinfo(
                    asset, request.user, request.session, create = create)
                logger.info("asset form saved")
            data = {'pk':asset.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('Asset')
        
        
class LocationView(LoginRequiredMixin, View):
    P = {
        'template_form':'activity/location_form.html',
        'template_list':'activity/location_list.html',
        'model':am.Location,
        'form':af.LocationForm,
        'related':['parent'],
        'fields':['id', 'loccode', 'locname', 'parent__locname',
                  'locstatus', 'enable']
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        
        # first load the template
        if R.get('template'): return render(request, P['template_list'])
        
        # return qset_list data
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_locationlistview(P['related'], P['fields'], request)
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'locationform': P['form'](request=request),
                   'msg': "create location requested"}
            resp = render(request, P['template_form'], cxt)
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)
        
        # return form with instance
        elif R.get('id', None):
            asset = utils.get_model_obj(R['id'], request, P)
            cxt = {'locationform': P['form'](instance = asset, request=request),
                   'msg': "Location Update Requested"}
            resp = render(request, P['template_form'], context = cxt)
        return resp
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        ic(data)
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "location_view", False
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            ic(form.instance.id)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                ic(form.errors)
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request ,create):
        logger.info('location form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ic(request.POST, request.FILES)
            location = form.save(commit=False)
            location.gpslocation = form.cleaned_data['gpslocation']
            location.save()
            location = putils.save_userinfo(
                location, request.user, request.session, create = create)
            logger.info("location form saved")
            data = {'pk':location.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('Location')
        
    
class PPMView(LoginRequiredMixin, View):
    P = {
        'template_list':'activity/ppm/ppm_list.html',
        'template_form':'activity/ppm/ppm_form.html',
        'template_form_jn':'activity/ppm/jobneed_ppmform.html',
        'model_jn':am.Jobneed,
        'model':am.Job,
        'related':['asset', 'qset', 'people', 'pgroup'],
        'fields':['plandatetime', 'expirydatetime', 'gracetime', 'asset__assetname', 
                  'assignedto', 'performedby__peoplename', 'jobdesc', 'frequency', 
                  'qset__qsetname', 'id', 'ctzoffset'],
        'form':af.PPMForm,
        'form_jn':af.PPMFormJobneed
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        # first load the template
        cxt = {
            'status_options':[
                ('COMPLETED', 'Completed'),
                ('AUTOCLOSED', 'AutoClosed'),
                ('ASSIGNED', 'Assigned'),
            ]
        }
        if R.get('template'): return render(request, P['template_list'], context=cxt)
        
        
        if R.get('action') == 'job_ppmlist':
            objs = P['model'].objects.get_jobppm_listview(request)
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        # return questionset_form empty
        if R.get('action', None) == 'form':
            cxt = {'ppmform': P['form'](request=request),
                   'msg': "create PPM requested"}
            return render(request, P['template_form'], cxt)
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)


        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = am.Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form_jn'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form_jn'], context = cxt)
        
        
        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = am.Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form_jn'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form_jn'], context = cxt)
        
        # return form with instance
        elif R.get('id', None):
            ppm = utils.get_model_obj(R['id'], request, P)
            cxt = {'ppmform': P['form'](instance = ppm, request=request),
                   'msg': "PPM Update Requested"}
            return render(request, P['template_form'], context = cxt)
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST.get('formData'))
        ic(data)
        try:
            if request.POST.get('action') == 'runScheduler':
                from background_tasks.tasks import create_ppm_job
                resp, F, d, story =  create_ppm_job(request.POST.get('job_id'))
                return rp.JsonResponse(resp, status=200)
            if pk := request.POST.get('pk', None):
                msg, create = "ppm view", False
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            ic(form.instance.id)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                ic(form.errors)
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request ,create):
        logger.info('ppm form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ic(request.POST, request.FILES)
            ppm = form.save()
            ppm = putils.save_userinfo(
                ppm, request.user, request.session, create = create)
            logger.info("ppm form saved")
            data = {'pk':ppm.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('PPM')
        
        
class PPMJobneedView(LoginRequiredMixin, View):
    P = {
        'template_list':'activity/ppm/ppm_jobneed_list.html',
        'template_form':'activity/ppm/jobneed_ppmform.html',
        'model':am.Jobneed,
        'related':['asset', 'qset', 'people', 'pgroup'],
        'fields':['plandatetime', 'expirydatetime', 'gracetime', 'asset__assetname', 
                  'assignedto', 'performedby__peoplename', 'jobdesc', 'frequency', 
                  'qset__qsetname', 'id', 'ctzoffset', 'jobstatus'],
        'form':af.PPMFormJobneed,
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        ic(R)
        # first load the template
        cxt = {
            'status_options':[
                ('COMPLETED', 'Completed'),
                ('AUTOCLOSED', 'AutoClosed'),
                ('ASSIGNED', 'Assigned'),
            ]
        }
        if R.get('template'): return render(request, P['template_list'], context=cxt)
        
        if R.get('action') == 'jobneed_ppmlist':
            objs = P['model'].objects.get_ppm_listview(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
        
        if R.get('action') == 'get_ppmtask_details' and R.get('taskid'):
            objs = am.JobneedDetails.objects.get_ppm_details(request)
            return rp.JsonResponse({"data":list(objs)})
        
        if R.get('action', None) == "delete" and R.get('id', None):
            return utils.render_form_for_delete(request, P, True)

        # return form with instance
        elif R.get('action') == "getppm_jobneedform" and  R.get('id', None):
            obj = am.Jobneed.objects.get(id = R['id'])
            cxt = {'ppmjobneedform': P['form'](instance = obj, request=request),
                   'msg': "PPM Jobneed Update Requested"}
            return render(request, P['template_form'], context = cxt)
        
    
    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        ic(data)
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "ppm view", False
                people = utils.get_model_obj(pk, request,  self.P)
                form = self.P['form'](data, request=request, instance = people)
            else:
                form = self.P['form'](data, request = request)
            ic(form.instance.id)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                ic(form.errors)
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, request ,create):
        logger.info('ppm form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ic(request.POST, request.FILES)
            ppm = form.save()
            ppm = putils.save_userinfo(
                ppm, request.user, request.session, create = create)
            logger.info("ppm form saved")
            data = {'pk':ppm.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('PPM')

        