import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.transaction import commit
from django.shortcuts import render
import psycopg2.errors as pg_errs
from django.views.generic.base import View
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
import apps.activity.models as am
from pprint import pformat
from django.db.models import Q
from django.db import IntegrityError
import apps.activity.filters as aft
import apps.activity.forms as af
import apps.peoples.utils as putils
import apps.activity.utils as av_utils
import apps.onboarding.forms as obf
from django.http import QueryDict
import logging
logger = logging.getLogger('__main__')
from django.http import response as rp



# Create your views here.
class Question(LoginRequiredMixin, View):
    params = {
        'form_class'    : af.QuestionForm,
        'template_form' : 'activity/partials/partial_ques_form.html',
        'template_list' : 'activity/question.html',
        'partial_form'  : 'peoples/partials/partial_ques_form.html',
        'partial_list'  : 'peoples/partials/partial_people_list.html',
        'related'       : ['unit'],
        'model'         : am.Question,
        'filter'        : aft.QuestionFilter,
        'fields'        : ['id', 'ques_name', 'answertype', 'isworkflow', 'unit__tacode',],
        'form_initials' : {'initial':{}}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return cap_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "ques_list", 'filt_name': "ques_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                   enable=True
                ).values(*self.params['fields'])
            resp   = putils.render_grid(request, self.params, "question_view", objs)
        
        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'ques_form': self.params['form_class'](request = request),
                    'ta_form' : obf.TypeAssistForm(auto_id=False),
                    'msg'     : "create question requested"}
            resp = putils.render_form(request, self.params, cxt)
        
        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = putils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'ta_form': obf.TypeAssistForm(auto_id=False)}
            resp = putils.render_form_for_update(request, self.params, 'ques_form',obj, cxt)
        print(f'return resp={resp}')
        return resp
    
    def post(self, request, *args, **kwargs):
        resp = None
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "question_view"
                ques = putils.get_model_obj(pk, request, self.params)
                form = self.params['form_class'](data, instance=ques, request=request)
                print(form.data)
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form,  request)
            else:
                cxt = {'errors': form.errors}
                resp = putils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = putils.handle_Exception(request)
        return resp
    
    def handle_valid_form(self, form,  request):
        logger.info('ques form is valid')
        ques = None
        try:
            ques = form.save()
            ques = putils.save_userinfo(ques, request.user, request.session)
            logger.info("question form saved")
            data = {'success': "Record has been saved successfully", 
            'name':ques.ques_name, 'type':ques.answertype, 'unit':ques.unit.tacode}
            logger.debug(data)
            return rp.JsonResponse(data, status=200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return putils.handle_intergrity_error('Question')

            
    

class Checklist(LoginRequiredMixin, View):
    params = {
        'form_class'    : af.ChecklistForm,
        'template_form' : 'activity/partials/partial_qset_form.html',
        'template_list' : 'activity/checklist.html',
        'partial_form'  : 'peoples/partials/partial_qset_form.html',
        'partial_list'  : 'peoples/partials/partial_people_list.html',
        'related'       : ['unit'],
        'model'         : am.QuestionSet,
        'filter'        : aft.ChecklistFilter,
        'fields'        : ['qset_name', 'type', 'id'],
        'form_initials' : {'initial':{}}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "qset_list", 'filt_name': "qset_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(qset_name='NONE'), enable=True
                ).values(*self.params['fields'])
            resp   = putils.render_grid(request, self.params, "questionset_view", objs)
        
        # return questionset_form empty
        elif R.get('action', None) == 'form':
            cxt = {'qset_form': self.params['form_class'](request=request),
                   'qsetbng'  :af.QsetBelongingForm(),
                    'msg'     : "create question_set requested"}
            resp = putils.render_form(request, self.params, cxt)
        
        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params, True)
            
        # return form with instance
        elif R.get('id', None):
            questions = self.get_questions_for_form(int(R['id']))
            cxt = {'qsetbng':af.QsetBelongingForm(), "questions":questions}
            obj = putils.get_model_obj(int(R['id']), request, self.params)
            self.params['form_initials']['initial'] = {'assetincludes':json.loads(obj.assetincludes)}
            resp = putils.render_form_for_update(request, self.params, 'qset_form',obj, cxt)
        print(f'return resp={resp}')
        return resp
    
    
    def post(self, request, *args, **kwargs):
        resp = None
        try:
            logger.debug(pformat(request.POST))
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            if pk:
                msg = "questionset_view"
                form = putils.get_instance_for_update(data, self.params, msg, int(pk))
                logger.debug(pformat(form.data, width=41, compact=True))
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
    
    def handle_valid_form(self, form, request):
        logger.info('questionset form is valid')
        try:
            assigned_questions = json.loads(request.POST.get("asssigned_questions"))
            qset = form.save()
            putils.save_userinfo(qset, request.user, request.session)
            logger.info("questionset form saved")
            fields = {'qsetid':qset.id, 'qset_name':qset.qset_name, 'clientid':qset.clientid_id}
            self.save_qset_belonging(request, assigned_questions, fields)
            data = {'success': "Record has been saved successfully", 
            'type':qset.type, 'name':qset.qset_name, 'id':qset.id
            }
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return putils.handle_intergrity_error('Question Set')
    
    def save_qset_belonging(self, request, assigned_questions, fields):
        try:
            logger.info("saving QuestoinSet Belonging [started]")
            logger.info("%s saving QuestoinSet Belonging found %s questions"%(" "*4, len(assigned_questions)))
            logger.debug(f"\nassigned_questoins, {pformat(assigned_questions, depth=1, width=60)}, qsetid {fields['qsetid']}")
            av_utils.insert_questions_to_qsetblng(assigned_questions, am.QuestionSetBelonging, fields, request)
            logger.info("saving QuestionSet Belongin [Ended]")
        except Exception:
            logger.critical("Something went wrong", exc_info=True)
            raise
            
            
    def get_questions_for_form(self, qsetid):
        try:
            questions = list(am.QuestionSetBelonging.objects.select_related(
                "quesid").filter(qsetid_id = qsetid).values(
                    'ismandatory', 'slno', 'max', 'min', 'alerton',
                    'options', 'quesid__ques_name','answertype', 'quesid__id'
                ))
        except Exception:
            logger.critical("Something went wrong", exc_info=True)
            raise
        else:
            return questions


def deleteQSB(request):
    if request.method =='GET':
        status = None
        try:
            quesname = request.GET.get('quesname')
            answertype = request.GET.get('answertype')
            qsetid = request.GET.get('qsetid')
            print("%%%%%%%%%%%", dict(request.GET))
            logger.info("request for delete QSB '%s' start"%(quesname))
            am.QuestionSetBelonging.objects.get(
                quesid__ques_name = quesname,
                answertype = answertype,
                qsetid_id = qsetid).delete()
            statuscode=200
            logger.info("Delete request executed successfully")
        except Exception:
            logger.critical("something went wrong", exc_info=True)
            statuscode = 404
            raise
        status = "success" if statuscode == 200 else "failed"
        data = {"status":status}
        return rp.JsonResponse(data, status=statuscode)
        
        
        
class Checkpoint(LoginRequiredMixin, View):
    params = {
        'form_class'    : af.CheckpointForm,
        'template_form' : 'activity/partials/partial_checkpoint_form.html',
        'template_list' : 'activity/checkpoint.html',
        'partial_form'  : 'peoples/partials/partial_checkpoint_form.html',
        'partial_list'  : 'peoples/partials/partial_people_list.html',
        'related'       : ['parent'],
        'model'         : am.Asset,
        'filter'        : aft.CheckpointFilter,
        'fields'        : ['assetname', 'assetcode', 'runningstatus', 'parent__assetcode', 'gpslocation', 'id', 'enable'],
        'form_initials' : {'initial':{}}
    }
    
    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return qset_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "checkpoint_list", 'filt_name': "checkpoint_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(assetcode='NONE')).values(*self.params['fields'])
            resp   = putils.render_grid(request, self.params, "checkpoint_view", objs)
        
        # return questionset_form empty
        elif R.get('action', None) == 'form':
            cxt = {'checkpoint_form': self.params['form_class'](request=request),
                    'msg'     : "create checkpoint requested"}
            resp = putils.render_form(request, self.params, cxt)
        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            obj = putils.get_model_obj(int(R['id']), request, self.params)
            resp = putils.render_form_for_update(request, self.params, 'checkpoint_form', obj)
        print(f'return resp={resp}')
        return resp
    
    
    def post(self, request, *args, **kwargs):
        resp = None
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "checkpoint_view"
                form = putils.get_instance_for_update(data, self.params, msg, int(pk))
                print(form.data)
            else:
                form = self.params['form_class'](data, request=request)
                print("%%%%%%%%%5", form.data)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = putils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = putils.handle_Exception(request)
        return resp
    
    def handle_valid_form(self, form, request):
        logger.info('checkpoint form is valid')
        try:
            cp = form.save()
            putils.save_userinfo(cp, request.user, request.session)
            logger.info("checkpoint form saved")
            data = {'success': "Record has been saved successfully", 
            'code':cp.assetcode, 'id':cp.id
        }
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return putils.handle_intergrity_error('Checkpoint')