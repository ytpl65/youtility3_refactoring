from django.http import Http404, QueryDict, response as rp
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q, F, Count, Case, When, Value
from django.shortcuts import redirect, render
from django.urls import resolve
from django.contrib.gis.db.models.functions import  AsWKT
from django.views.generic.base import View
import json
from django.contrib.auth.mixins import LoginRequiredMixin
import psycopg2.errors as pg_errs
import apps.activity.models as am
from pprint import pformat
import apps.activity.filters as aft
import apps.activity.forms as af
import apps.peoples.utils as putils
import apps.core.utils as utils
import apps.activity.utils as av_utils
import apps.onboarding.forms as obf
import logging
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
        'fields'       : ['id', 'quesname', 'answertype', 'isworkflow', 'unit__tacode', ],
        'form_initials': {
        'answertype'   : am.Question.AnswerType.DROPDOWN,
        'category'     : 1,                               'unit': 1}
    }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return cap_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "ques_list", 'filt_name': "ques_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                enable = True
            ).values(*self.params['fields'])
            resp = utils.render_grid(
                request, self.params, "question_view", objs)

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'ques_form': self.params['form_class'](request = request, initial = self.params['form_initials']),
                   'ta_form': obf.TypeAssistForm(auto_id = False),
                   'msg': "create question requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'ta_form': obf.TypeAssistForm(auto_id = False)}
            resp = utils.render_form_for_update(
                request, self.params, 'ques_form', obj, cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
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
            data = {'success': "Record has been saved successfully",
                    'name': ques.quesname, 'type': ques.answertype, 'unit': ques.unit.tacode}
            logger.debug(data)
            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('Question')

class MasterQuestionSet(LoginRequiredMixin, View):
    params = {
        'form_class'   : None,
        'template_form': 'activity/partials/partial_masterqset_form.html',
        'template_list': 'activity/master_qset_list.html',
        'partial_form' : 'peoples/partials/partial_masterqset_form.html',
        'partial_list' : 'peoples/partials/master_qset_list.html',
        'related'      : ['unit'],
        'model'        : am.QuestionSet,
        'filter'       : aft.MasterQsetFilter,
        'fields'       : ['qsetname', 'type', 'id'],
        'form_initials': {}
    }
    label=""
    list_grid_lookups = label = None
    view_of = ''

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        urlname = resolve(request.path_info).url_name
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'], context={'label':self.label})
        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(qsetname='NONE'), **self.list_grid_lookups
            ).values(*self.params['fields'])
            resp = utils.render_grid(request, self.params,
                                     "questionset_view", objs, extra_cxt={'label': self.label})
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        elif R.get('action', None) == 'form':
            self.params['form_initials'].update(
                {'parent': utils.get_or_create_none_qset().id})
            cxt = {
                'masterqset_form': self.params['form_class'](
                    request = request,
                    initial = self.params['form_initials']),
                'qsetbng': af.QsetBelongingForm(initial={'ismandatory': True}),
                'label': self.label,
                'msg': f"create {self.view_of} requested"}
            ic(cxt['masterqset_form'].as_p())
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get('id', None):
            questions = self.get_questions_for_form(int(R['id']))
            cxt = {'qsetbng': af.QsetBelongingForm(), "questions": questions,
                   'label': self.label}
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            self.params['form_initials'] = {
                'assetincludes': obj.assetincludes}
            resp = utils.render_form_for_update(
                request, self.params, 'masterqset_form', obj, cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            logger.debug(pformat(request.POST))
            data = QueryDict(request.POST['formData'])
            ic(data)
            if pk := request.POST.get('pk', None):
                logger.debug("form is with instance")
                msg = self.view_of
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
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

    def get_questions_for_form(self, qset):
        try:
            questions = list(am.QuestionSetBelonging.objects.select_related(
                "question").filter(qset_id = qset).values(
                'ismandatory', 'seqno', 'max', 'min', 'alerton',
                'options', 'question__quesname', 'answertype', 'question__id'
            ))
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise
        else:
            return questions

    def handle_valid_form(form, request, create):
        raise NotImplementedError()

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
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return questionset_form empty
        elif R.get('action', None) == 'form':
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

class Checklist(MasterQuestionSet):
    params = MasterQuestionSet.params
    list_grid_lookups = MasterQuestionSet.list_grid_lookups
    view_of = MasterQuestionSet.view_of
    label = MasterQuestionSet.label
    params.update({
        'form_class': af.ChecklistForm,
        'form_initials': {
            'type': am.QuestionSet.Type.CHECKLIST
        }
    })
    list_grid_lookups = {'enable': True, 'type': 'CHECKLIST'}
    view_of = 'checklist'
    label = 'Checklist'

    def handle_valid_form(self, form, request, create):
        logger.info(f'{self.view_of} form is valid')
        try:
            assigned_questions = json.loads(
                request.POST.get("asssigned_questions"))
            qset = form.save()
            putils.save_userinfo(qset, request.user,
                                 request.session, create = create)
            logger.info(f'{self.view_of} form is valid')
            fields = {'qset': qset.id, 'qsetname': qset.qsetname,
                      'client': qset.client_id}
            self.save_qset_belonging(request, assigned_questions, fields)
            data = {'success': "Record has been saved successfully",
                    'row':{'qsetname':qset.qsetname, 'id':qset.id}
                    }
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Question Set')

    def save_qset_belonging(self, request, assigned_questions, fields):
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

class QuestionSet(MasterQuestionSet):
    params = MasterQuestionSet.params
    list_grid_lookups = MasterQuestionSet.list_grid_lookups
    view_of = MasterQuestionSet.view_of
    label = MasterQuestionSet.label
    params.update({
        'form_class': af.QuestionSetForm,
        'form_initials': {
            'type': am.QuestionSet.Type.QUESTIONSET
        }
    })
    list_grid_lookups = {'enable': True, 'type': 'QUESTIONSET'}
    view_of = 'questionset'
    label = 'Question Set'

    def handle_valid_form(self, form, request, create):
        logger.info(f'{self.view_of} form is valid')
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                assigned_questions = json.loads(
                    request.POST.get("asssigned_questions"))
                qset = form.save()
                putils.save_userinfo(qset, request.user,
                                    request.session, create = create)
                logger.info(f'{self.view_of} form is valid')
                fields = {'qset': qset.id, 'qsetname': qset.qsetname,
                        'client': qset.client_id}
                self.save_qset_belonging(request, assigned_questions, fields)
                data = {'success': "Record has been saved successfully",
                        'row':{'qsetname':qset.qsetname, 'id':qset.id}
                        }
                return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Question Set')
        except Exception:
            logger.critical("Something went wrong", exc_info = True)
            raise

    def save_qset_belonging(self, request, assigned_questions, fields):
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
        logger.info("request for delete QSB '%s' start" % (quesname))
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

class Checkpoint(MasterAsset):
    params = MasterAsset.params
    label = MasterAsset.label
    view_of = MasterAsset.view_of
    list_grid_lookups = MasterAsset.list_grid_lookups
    params.update({
        'form_class': af.CheckpointForm,
        'form_initials': {'runningstatus': 'WORKING',
                          'identifier': 'CHECKPOINT',
                          'iscritical': False, 'enable': True}
    })
    list_grid_lookups = {'enable': True, 'identifier': 'CHECKPOINT'}
    view_of = 'checkpoint'
    label = 'Checkpoint'

    def handle_valid_form(self, form, request, create):
        logger.info('checkpoint form is valid')
        try:
            cp = form.save()
            putils.save_userinfo(
                cp, request.user, request.session, create = create)
            logger.info("checkpoint form saved")
            data = {'success': "Record has been saved successfully",
                    'code': cp.assetcode, 'id': cp.id
                    }
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Checkpoint')

class Smartplace(MasterAsset):
    params = MasterAsset.params
    label = MasterAsset.label
    view_of = MasterAsset.view_of
    list_grid_lookups = MasterAsset.params
    params.update({
        'form_class': af.SmartPlaceForm,
        'form_initials': {'identifier': 'SMARTPLACE',
                          'runningstatus': 'WORKING',
                          'iscritical': False, 'enable': True}
    })
    list_grid_lookups = {'enable': True, 'identifier': 'SMARTPLACE'}
    view_of = 'smartplace'
    label = 'Smartplace'

    def handle_valid_form(self, form, request, create):
        logger.info('smarplace form is valid')
        try:
            cp = form.save()
            putils.save_userinfo(
                cp, request.user, request.session, create = create)
            logger.info("smartplace form saved")
            data = {'success': "Record has been saved successfully",
                    'code': cp.assetcode, 'id': cp.id
                    }
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return utils.handle_intergrity_error('Smartplace')

class RetriveEscList(LoginRequiredMixin, View):
    model = am.EscalationMatrix
    fields = ['id', 'esctemplate__taname', 'cdtz']
    template_path = 'activity/escalation_list.html'
    related = ['esctemplate']

    def get(self, request, *args, **kwargs):
        resp, requestData = None, request.GET
        if requestData.get('template'):
            return render(request, self.template_path)
        try:
            log.info('Retrieve Escalation view')
            objects = self.model.objects.select_related(
                *self.related).filter().values(*self.fields).order_by('-cdtz')
            count = objects.count()
            log.info(f'Escalation objects {count or "No Records!"} retrieved from db')
            if count:
                objects, filtered = utils.get_paginated_results(
                    requestData, objects, count, self.fields, self.related, self.model)
                log.info('Results paginated'if count else "")
            filtered = count
            resp = rp.JsonResponse(data={
                'draw': requestData['draw'], 'recordsTotal': count, 'data': list(objects),
                'recordsFiltered': filtered
            }, status = 200)
        except Exception:
            log.critical(
                'something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            resp = redirect('/dashboard')
        return resp


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

        elif R.get('action', None) == 'form':
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
                  'ismandatory']
    }
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        if R.get('action') == 'get_questions_of_qset' and R.get('qset_id'):
            objs = P['qsb'].objects.get_questions_of_qset(R)
            return rp.JsonResponse({'data':list(objs)}, status=200)
        return rp.JsonResponse({'data':[]}, status=200)
    
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
            ic(utils.printsql(objs))
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
        if R.get('action') == 'get_attachments_of_owner' and R.get('owner'):
            ic("returning")
            objs = P['model'].objects.get_att_given_owner(R['owner'])   
            return rp.JsonResponse({'data':list(objs)}, status=200)
        return rp.JsonResponse({'data':[]}, status=200)
    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        ic(R, request.FILES)
        if 'img' in request.FILES:
            isUploaded, filename, filepath, docnumber = utils.upload(request)
            if isUploaded:
                data = P['model'].objects.create_att_record(request, filename, filepath)
                ic(data)
                return rp.JsonResponse(data, status = 200, safe=False)
        return rp.JsonResponse({'error':"Invalid Request"}, status=404)