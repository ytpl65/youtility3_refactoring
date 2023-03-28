from django.shortcuts import render
from django.db import IntegrityError, transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import View
from .forms import VendorForm, WorkOrderForm
from .models import Vendor, Wom, WomDetails
from apps.activity.models import QuestionSetBelonging
from django.http import Http404, QueryDict, response as rp, HttpResponse
from apps.core  import utils
from apps.peoples import utils as putils
import psycopg2.errors as pg_errs
import logging
from django.utils import timezone
logger = logging.getLogger('__main__')
log = logger
# Create your views here.

# Create your views here.
class VendorView(LoginRequiredMixin, View):
    params = {
        'form_class'   : VendorForm,
        'template_form': 'work_order_management/vendor_form.html',
        'template_list': 'work_order_management/vendor_list.html',
        'related'      : ['cuser'],
        'model'        : Vendor,
        'fields'       : ['code', 'name', 'mobno', 'email', 'cdtz',
                          'cuser__peoplename', 'ctzoffset', 'id']
    }

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # return cap_list data
        if R.get('template'): return render(request, P['template_list'])
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_vendor_list(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
            

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'vendor_form': P['form_class'](request = request),
                   'msg': "create vendor requested"}
            resp = utils.render_form(request, P, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, True)
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            resp = utils.render_form_for_update(
                request, P, 'vendor_form', obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData']).copy()
            if pk := request.POST.get('pk', None):
                msg = "vendor_view"
                ven = utils.get_model_obj(pk, request, self.params)
                form = self.params['form_class'](
                    data, instance = ven, request = request)
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
        logger.info('vendor form is valid')
        try:
            vendor = form.save(commit=False)
            vendor.gpslocation = form.cleaned_data['gpslocation']
            vendor = putils.save_userinfo(
                vendor, request.user, request.session, create = create)
            logger.info("question form saved")
            data = {'msg': f"{vendor.name}",
            'row': Vendor.objects.values(*self.params['fields']).get(id = vendor.id)}
            logger.debug(data)
            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('Question')



# Create your views here.
class WorkOrderView(LoginRequiredMixin, View):
    params = {
        'form_class'   : WorkOrderForm,
        'template_form': 'work_order_management/work_order_form.html',
        'template_list': 'work_order_management/work_order_list.html',
        'related'      : ['vendor', 'cuser'],
        'model'        : Wom,
        'model_jnd'    : WomDetails,
        'fields'       : ['id', 'ctzoffset', 'cuser__peoplename', 'cuser__peoplecode', 'plandatetime', 'cdtz',
                          'expirydatetime', 'priority', 'description', 'vendor__name', 'categories', 'workstatus']
    }

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # return cap_list data
        if R.get('template'): return render(request, P['template_list'])
        
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_workorder_list(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
            

        # return cap_form empty
        elif R.get('action', None) == 'form':
            import uuid
            cxt = {'woform': P['form_class'](request = request),
                   'msg': "create workorder requested", 'ownerid':uuid.uuid4()}
            resp =  render(request, P['template_form'], cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, True)
            
        elif R.get('action') == 'send_workorder_email':
            from .utils import notify_wo_creation
            notify_wo_creation(id = R['id'])
            return rp.JsonResponse({'msg':"Email sent successfully"}, status=200)
        
        if R.get('action') == 'getAttachmentJND':
            att =  self.params['model_jnd'].objects.getAttachmentJND(R['id'])
            return rp.JsonResponse(data = {'data': list(att)})

        if R.get('action') == 'get_wo_details' and R.get('womid'):
            ic(R)
            objs = self.params['model_jnd'].objects.get_wo_details(R['womid'])
            return rp.JsonResponse({"data":list(objs)})
        
        
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            cxt = {'woform':P['form_class'](request=request, instance=obj), 'ownerid':obj.uuid}
            resp = render(request, P['template_form'], cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData']).copy()
            if pk := request.POST.get('pk', None):
                msg = "workorder_view"
                ven = utils.get_model_obj(pk, request, self.params)
                form = self.params['form_class'](
                    data, instance = ven, request = request)
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
        logger.info('workorder form is valid')
        try:
            import secrets
            from django.utils import timezone
            from .utils import notify_wo_creation
            workorder = form.save(commit=False)
            workorder.uuid = request.POST.get('uuid')
            workorder.other_data['created_at'] = timezone.now().strftime('%d-%b-%Y %H:%M:%S')
            workorder.other_data['token'] = secrets.token_urlsafe(16)
            workorder = putils.save_userinfo(
                workorder, request.user, request.session, create = create)
            if not workorder.ismailsent:
                notify_wo_creation(id=workorder.id)
            logger.info("workorder form saved")
            data = {'msg': f"{workorder.id}",
            'row': Wom.objects.values(*self.params['fields']).get(id = workorder.id), 'pk':workorder.id}
            logger.debug(data)

            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('WorkOrder')
        
        

class ReplyWorkOrder(View):
    params = {
        'template':'work_order_management/reply_workorder.html',
        'template_emailform':'work_order_management/wod_email_form.html',
        'model':Wom,
    }

    def get(self,request, *args, **kwargs):
        R = request.GET
        try:
            if  R['action'] == 'accepted' and R['womid']:
                wo = Wom.objects.get(id = R['womid'])
                wo.workstatus = Wom.Workstatus.INPROGRESS
                log.info("work order accepted by vendor")
                wo.starttime = timezone.now()
                wo.save()
                cxt = {'accepted':True, 'wo':wo}
                return render(request, self.params['template'], context=cxt)
            
            if  R['action'] == 'declined' and R['womid']:
                wo = Wom.objects.get(id = R['womid'])
                wo.isdenied = True
                wo.workstatus = Wom.Workstatus.CANCELLED
                log.info(f'work order cancelled/denied by vendor')
                wo.save()
                cxt = {'declined':True, 'wo':wo}
                return render(request, self.params['template'], context=cxt)
            
            if R['action'] == 'request_for_submit_wod':
                #check for work is already inprogress
                wo = Wom.objects.get(id = R['womid'])
                log.info(f'wo status {wo.workstatus}')
                if wo.workstatus == Wom.Workstatus.INPROGRESS:
                    questions = QuestionSetBelonging.objects.filter(qset_id = wo.qset_id).select_related('question')
                    cxt = {'qsetname':wo.qset.qsetname, 'qsb':questions, 'womid':wo.id}
                    return render(request, self.params['template_emailform'], cxt)
                elif wo.workstatus == Wom.Workstatus.CANCELLED:
                    return HttpResponse("Sorry the work order is cancelled already!")
                elif wo.workstatus == Wom.Workstatus.ASSIGNED:
                    return HttpResponse("Please accept the work order and start the work!")
                elif wo.workstatus == Wom.Workstatus.COMPLETED:
                    return HttpResponse("The work order are already submitted!")
                
        except wo['model'].DoesNotExist as e:
                return HttpResponse("The page you are looking for is not found")
        
    def post(self, request, *args, **kwargs):
        R = request.POST
        try:
            wo = self.params['model'].objects.get(id=R['womid'])
            if R.get('action') == 'reply_form':
                    #changes in db
                    wo.isdenied = True
                    wo.other_data['reply_from_vendor'] = R['reply_from_vendor']
                    wo.save()
                    return render(request, self.params['template'])
            if R.get('action') == 'save_work_order_details':
                self.save_work_order_details(R, wo, request)
                log.info('form saved successfully')
                return render(request, self.params['template_emailform'], {'wod_saved':True})
        except self.params['model'].DoesNotExist as e:
            return HttpResponse("The page you are looking for is not found")
    
    def save_work_order_details(self, R, wo, request):
        log.info(f'form post data {R}')
        post_data = R.copy()
        post_data.update(request.FILES)
        log.info(f'postData = {post_data}')
        for k, v in post_data.items():
            log.debug(f'form name, value {k}, {v}')
            if k not in ['ctzoffset', 'womid', 'action', 'csrfmiddlewaretoken'] and '_' in k:
                qsb_id = k.split('_')[0]
                qsb_obj = QuestionSetBelonging.objects.filter(id = qsb_id).select_related('question').first()
                if qsb_obj.answertype in ['CHECKBOX', 'DROPDOWN']:
                    alerts = v in qsb_obj.alerton
                elif qsb_obj.answertype in  ['NUMERIC'] and len(qsb_obj.alerton) > 0:
                    alerton = qsb_obj.alerton.replace('>', '').replace('<', '').split(',')
                    if len(alerton) > 1:
                        _min, _max = alerton[0], alerton[1]
                        alerts = float(v) < float(_min) or float(v) > float(_max)
                else:
                    alerts = False
                
                wod = WomDetails.objects.create(
                    seqno       = qsb_obj.seqno,
                    question_id = qsb_obj.question_id,
                    answertype  = qsb_obj.answertype,
                    answer      = v,
                    isavpt      = qsb_obj.isavpt,
                    options     = qsb_obj.options,
                    min         = qsb_obj.min,
                    max         = qsb_obj.max,
                    alerton     = qsb_obj.alerton,
                    ismandatory = qsb_obj.ismandatory,
                    wom_id      = wo.id,
                    alerts      = alerts,
                    client_id   = qsb_obj.client_id,
                    bu_id       = qsb_obj.bu_id,
                    cuser_id    = 1,
                    muser_id    = 1,
                )
                if qsb_obj.isavpt and request.FILES:
                    isuploaded, filename, filepath = utils.upload_vendor_file(request.FILES[k], womid = wo.id)
                    att = self.create_att_record(request.FILES[k], filename, filepath, wod)
                    log.info(f'Is file uploaded {isuploaded} and attachment is created {att.id}')
        wo.workstatus = Wom.Workstatus.COMPLETED
        wo.endtime = timezone.now()
        log.info('work order status changed to completed')
        wo.save()
        
    
    def create_att_record(self, file, filename, filepath, wod):
        from apps.activity.models import Attachment
        from apps.onboarding.models import TypeAssist
        ownername = TypeAssist.objects.filter(tacode = 'WOMDETAILS').first()
        return Attachment.objects.create(
            filepath = filepath, filename = filename, 
            size = file.size, owner = wod.uuid,
            bu_id = wod.bu_id,
            cuser_id = 1, muser_id = 1, cdtz = timezone.now(),
            mdtz = timezone.now(), ctzoffset = wod.ctzoffset, 
            attachmenttype = Attachment.AttachmentType.ATMT,
            ownername_id = ownername.id, 
        )