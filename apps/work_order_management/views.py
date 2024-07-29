from django.shortcuts import render
from django.db import IntegrityError, transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import View
from .forms import VendorForm, WorkOrderForm, WorkPermitForm, ApproverForm,SlaForm
from .models import Vendor, Wom, WomDetails, Approver
from apps.peoples.models import People
from apps.activity.models import QuestionSetBelonging, QuestionSet
from background_tasks.tasks import send_email_notification_for_sla_vendor,send_email_notification_for_wp,send_email_notification_for_vendor_and_security
from django.http import Http404, QueryDict, response as rp, HttpResponse
from apps.core  import utils
from apps.peoples import utils as putils
import psycopg2.errors as pg_errs
from django.template.loader import render_to_string
from apps.work_order_management.utils import check_all_approved,reject_workpermit, save_approvers_injson
import logging
from django.utils import timezone
from apps.reports import utils as rutils
from apps.work_order_management import utils as wom_utils
from apps.reports.report_designs.workpermit import GeneralWorkPermit
from apps.reports.report_designs.service_level_agreement import ServiceLevelAgreement
from apps.onboarding.models import TypeAssist,Bt

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
        'fields'       : ['code', 'name', 'mobno', 'email', 'cdtz', 'type__taname',
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
        'related'      : ['vendor', 'cuser', 'bu'],
        'model'        : Wom,
        'model_jnd'    : WomDetails,
        'fields'       : ['id', 'ctzoffset', 'cuser__peoplename', 'cuser__peoplecode', 'plandatetime', 'cdtz', 'bu__buname',
                          'expirydatetime', 'priority', 'description', 'vendor__name', 'categories', 'workstatus', 'bu__bucode']
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
        
        #close the work order
        elif R.get('action') == 'close_wo' and R.get('womid'):
            Wom.objects.filter(id = R['womid']).update(workstatus = 'CLOSED')
            return rp.JsonResponse({'pk':R['womid']}, status=200)
        
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
                workorder = notify_wo_creation(id=workorder.id)
            workorder.add_history()
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
                if wo.workstatus == Wom.Workstatus.COMPLETED: return HttpResponse("The work order are already submitted!")
                wo.workstatus = Wom.Workstatus.INPROGRESS
                log.info("work order accepted by vendor")
                wo.starttime = timezone.now()
                wo.save()
                cxt = {'accepted':True, 'wo':wo}
                return render(request, self.params['template'], context=cxt)
            
            if  R['action'] == 'declined' and R['womid']:
                wo = Wom.objects.get(id = R['womid'])
                if wo.workstatus == Wom.Workstatus.COMPLETED: return HttpResponse("The work order are already submitted!")
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
                
        except self.params['model'].DoesNotExist as e:
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
                
                wod, _ = WomDetails.objects.update_or_create(
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
                    cuser_id    = 1,
                    muser_id    = 1,
                )
                if qsb_obj.isavpt and request.FILES:
                    k = f'{qsb_id}-{qsb_obj.answertype}'
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
            cuser_id = 1, muser_id = 1, cdtz = timezone.now(),
            mdtz = timezone.now(), ctzoffset = wod.ctzoffset, 
            attachmenttype = Attachment.AttachmentType.ATMT,
            ownername_id = ownername.id, 
        )
        
        
class WorkPermit(LoginRequiredMixin, View):
    params = {
        'template_list':'work_order_management/workpermit_list.html',
        'template_form':'work_order_management/workpermit_form.html',
        'partial_form':'work_order_management/partial_wp_questionform.html',
        'email_template':'work_order_management/workpermit_approver_action.html',
        'model':Wom,
        'form':WorkPermitForm,
        'related':['qset', 'cuser', 'bu'],
        'fields':['cdtz', 'id', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'cuser__peoplename', 'bu__bucode', 'bu__buname'],
        'valid_workpermit':','.join(['General Work Permit'])

    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        action = R.get('action')
        if action == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_workpermitlist(request)
            return rp.JsonResponse(data={'data': list(objs)}, safe=False)

        if action == 'approve_wp' and R.get('womid'):
            S = request.session
            wom = P['model'].objects.get(id=R['womid'])
            is_submit_button_flow='true'
            permit_name = 'General Work Permit'
            sitename = Bt.objects.model(id=wom.bu_id).buname
            workpermit_obj = GeneralWorkPermit(filename=permit_name, client_id=S['client_id'], formdata={'id':R['womid'],'sitename':sitename,'submit_button_flow':is_submit_button_flow,'filename':permit_name,'workpermit':wom.workpermit})
            workpermit_attachment = workpermit_obj.execute()
            if is_all_approved := check_all_approved(wom.uuid, request.user.peoplecode):
                Wom.objects.filter(id=R['womid']).update(workpermit=Wom.WorkPermitStatus.APPROVED.value)
                if is_all_approved:
                    workpermit_status = 'APPROVED'
                    send_email_notification_for_vendor_and_security.delay(R['womid'],workpermit_attachment,sitename,workpermit_status)
            return rp.JsonResponse(data={'status': 'Approved'}, status=200)
        
        if action == 'reject_wp' and R.get('womid'):
            wom = P['model'].objects.get(id=R['womid'])
            Wom.objects.filter(id=R['womid']).update(workpermit=Wom.WorkPermitStatus.REJECTED.value)
            reject_workpermit(wom.uuid, request.user.peoplecode)
            return rp.JsonResponse(data={'status': 'Approved'}, status=200)

        if action == 'form':
            print("Here I am in form view")
            import uuid
            cxt = {'wpform': P['form'](request=request), 'msg': "create workpermit requested", 'ownerid': uuid.uuid4(),'valid_workpermit':self.params['valid_workpermit']}
            return render(request, P['template_form'], cxt)
        
        if action == 'approver_list':
            objs = Wom.objects.get_approver_list(R['womid'])
            return rp.JsonResponse({'data': objs}, status=200)

        if R.get('qsetid'):
            import uuid
            wp_details = Wom.objects.get_workpermit_details(request, R['qsetid'])
            approver_codes = R['approvers'].split(',')
            approvers = wom_utils.get_approvers(approver_codes)
            form = P['form'](request=request, initial={'qset': R['qsetid'], 'approvers': R['approvers'].split(','),'vendor':R['vendor']})
            context = {"wp_details": wp_details, 'wpform': form, 'ownerid': uuid.uuid4(),'valid_workpermit':self.params['valid_workpermit'],'approvers':approvers}
            return render(request, P['template_form'], context=context)

        if action == 'get_answers_of_template' and R.get('qsetid') and R.get('womid'):
            wp_answers = Wom.objects.get_wp_answers(R['womid'])
            questionsform = render_to_string(P['partial_form'], context={"wp_details": wp_answers[1]})
            return rp.JsonResponse({'html': questionsform}, status=200)

        if action == 'getAttachments':
            att =  P['model'].objects.get_attachments(R['id'])
            return rp.JsonResponse(data = {'data': list(att)})
        
        if action == 'printReport':
            return self.send_report(R, request)

        if 'id' in R:
            print("After Submission Here I am")
            log.info("In this view")
            print("R:  ",R)
            # get work permit questionnaire
            obj = utils.get_model_obj(int(R['id']), request, P)
            wp_answers = Wom.objects.get_wp_answers(obj.id)
            cxt = {'wpform': P['form'](request=request, instance=obj), 'ownerid': obj.uuid, 'wp_details': wp_answers[1],'valid_workpermit':self.params['valid_workpermit']}
            if obj.workpermit == Wom.WorkPermitStatus.APPROVED and obj.workstatus != Wom.Workstatus.COMPLETED:
                rwp_details = Wom.objects.get_return_wp_details(request)
                log.info(f"return work permit details are as follows: {rwp_details}")
                cxt['rwp_details'] = rwp_details
            return render(request, P['template_form'], cxt)


    
    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        try:
            
            if R.get('action') == 'submit_return_workpermit':
                log.info("submitting return work permit")
                wom = Wom.objects.get(id = R['wom_id'])
                return_wp_formdata = QueryDict(request.POST['return_work_permit_formdata']).copy()
                rwp_seqno =Wom.objects.filter(parent_id=R['wom_id']).count() + 1
                log.info(f"return work permit seqno is {rwp_seqno}")
                self.create_workpermit_details(R['wom_id'], wom, request, return_wp_formdata, rwp_seqno=rwp_seqno)
                wom.workstatus = Wom.Workstatus.COMPLETED
                wom.save()
                return rp.JsonResponse({'pk':wom.id})
            if pk := R.get('pk', None):
                log.info("Here I am going after submission")
                data = QueryDict(R['formData']).copy()
                wp = utils.get_model_obj(pk, request, P)
                form = self.params['form'](
                    data, instance = wp, request = request)
                create = False
            else:
                data = QueryDict(R['formData']).copy()
                print("Data: ",data)
                form = self.params['form'](data, request = request)
                create=True
            if form.is_valid():
                print("Here I am going after submission")
                resp = self.handle_valid_form(form, R, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception as e:
            resp = utils.handle_Exception(request)
        return resp
    
    def handle_valid_form(self, form, R,request, create=True):
        S = request.session
        workpermit = form.save(commit=False)
        workpermit.uuid = request.POST.get('uuid')
        workpermit = putils.save_userinfo(
            workpermit, request.user, request.session, create = create)
        workpermit = save_approvers_injson(workpermit)
        formdata = QueryDict(request.POST['workpermitdetails']).copy()
        self.create_workpermit_details(request.POST, workpermit, request, formdata)
        print("Session",S)
        wom = Wom.objects.get(id = workpermit.id)
        sitename = S.get('sitename','demo')
        workpermit_obj = GeneralWorkPermit(filename=R['permit_name'], client_id=S['client_id'], formdata={'id':workpermit.id,'bu__buname':sitename,'submit_button_flow':R['submit_button_flow'],'filename':R['permit_name'],'site_name':S['sitename'],'workpermit':wom.workpermit})
        workpermit_attachment = workpermit_obj.execute()
        print("Workpermit Path: ",workpermit_attachment)
        workpermit_status = 'PENDING'
        send_email_notification_for_wp.delay(workpermit.id, workpermit.qset_id, workpermit.approvers, S['client_id'], S['bu_id'],workpermit_attachment,sitename,workpermit_status)

        return rp.JsonResponse({'pk':workpermit.id})

    def create_child_wom(self, wom, qset_id, rwp_seqno=None):
        qset = QuestionSet.objects.get(id =qset_id)
        if childwom := Wom.objects.filter(
            parent_id=wom.id, qset_id=qset.id, seqno=rwp_seqno or qset.seqno
        ).first():
            log.info(f"wom already exist with qset_id {qset_id} so returning it")
            return childwom
        else:
            log.info(f'creating wom for qset_id {qset_id}')
            return Wom.objects.create(
                parent_id      = wom.id,
                description    = qset.qsetname,
                plandatetime   = wom.plandatetime,
                expirydatetime = wom.expirydatetime,
                starttime      = wom.starttime,
                gpslocation    = wom.gpslocation,
                asset          = wom.asset,
                location       = wom.location,
                workstatus     = wom.workstatus,
                seqno          = rwp_seqno or qset.seqno,
                approvers      = wom.approvers,
                workpermit     = wom.workpermit,
                priority       = wom.priority,
                vendor         = wom.vendor,
                performedby    = wom.performedby,
                alerts         = wom.alerts,
                client         = wom.client,
                bu             = wom.bu,
                ticketcategory = wom.ticketcategory,
                other_data     = wom.other_data,
                qset           = qset,
                cuser          = wom.cuser,
                muser          = wom.muser,
                ctzoffset      = wom.ctzoffset
            )
    
    def create_workpermit_details(self, R, wom,  request, formdata, rwp_seqno=None):
        log.info(f'creating wp_details started {R}')
        S = request.session
        
        for k,v in formdata.items():
            log.debug(f'form name, value {k}, {v}')
            if k not in ['ctzoffset', 'wom_id', 'action', 'csrfmiddlewaretoken'] and '_' in k:
                ids = k.split('_')
                qsb_id = ids[0]
                qset_id = ids[1]
                qsb_obj = QuestionSetBelonging.objects.filter(id = qsb_id).first()
                if qsb_obj.answertype in ['CHECKBOX', 'DROPDOWN']:
                    alerts = (qsb_obj.alerton and v in qsb_obj.alerton) or False
                    # alerts = v in qsb_obj.alerton
                elif qsb_obj.answertype == 'MULTISELECT':
                    selected_values = formdata.getlist(k)
                    if selected_values:
                        if qsb_obj.alerton:
                            alerts = any(value in qsb_obj.alerton for value in selected_values)
                        else:
                            alerts = False
                        v = ','.join(selected_values)
                    else:
                        alerts = False
                        v = ''
                elif qsb_obj.answertype in  ['NUMERIC'] and len(qsb_obj.alerton) > 0:
                    alerton = qsb_obj.alerton.replace('>', '').replace('<', '').split(',')
                    if len(alerton) > 1:
                        _min, _max = alerton[0], alerton[1]
                        alerts = float(v) < float(_min) or float(v) > float(_max)
                else:
                    alerts = False
                    
                childwom = self.create_child_wom(wom, qset_id, rwp_seqno=rwp_seqno)
                
                lookup_args = {
                    'wom_id':childwom.id,
                    'question_id':qsb_obj.question_id,
                    'qset_id':qset_id
                }
                default_data = {
                    'seqno'       : qsb_obj.seqno,
                    'answertype'  : qsb_obj.answertype,
                    'answer'      : v,
                    'isavpt'      : qsb_obj.isavpt,
                    'options'     : qsb_obj.options,
                    'min'         : qsb_obj.min,
                    'max'         : qsb_obj.max,
                    'alerton'     : qsb_obj.alerton,
                    'ismandatory' : qsb_obj.ismandatory,
                    'alerts'      : alerts,
                    'cuser_id'    : request.user.id,
                    'muser_id'    : request.user.id,
                }
                data = lookup_args | default_data
                WomDetails.objects.create(
                    **data
                )
                log.info(f"wom detail is created for the for the child wom: {childwom.description}")

    
    def getReportFormatBasedOnWorkpermitType(self, R):
        from apps.reports.report_designs import workpermit as wp
        return {
            'General Work Permit':wp.GeneralWorkPermit
        }.get(R['qset__qsetname'])
    
    
    def send_report(self, R, request):
        ReportFormat = self.getReportFormatBasedOnWorkpermitType(R)
        print("R: ",R)
        print("Request: ",request)
        report = ReportFormat(
            filename=R['qset__qsetname'], client_id=request.session['client_id'], formdata=R, request=request)
        return report.execute()
        
    
class ReplyWorkPermit(View):
    P = {
        'email_template': "work_order_management/workpermit_server_reply.html",
        'model':Wom,
    }
    
    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.P
        S = request.session
        if R.get('action') == "accepted" and R.get('womid') and R.get('peopleid'):
            is_submit_button_flow='true'
            permit_name = 'General Work Permit'
            wom = Wom.objects.get(id = R['womid'])
            wp = Wom.objects.filter(id = R['womid']).first()
            p = People.objects.filter(id = R['peopleid']).first()
            log.info("R:%s",R)
            if is_all_approved := check_all_approved(wp.uuid, p.peoplecode):
                if Wom.WorkPermitStatus.APPROVED != Wom.objects.get(id = R['womid']).workpermit:
                    Wom.objects.filter(id = R['womid']).update(workpermit = Wom.WorkPermitStatus.APPROVED.value)
                    if is_all_approved:
                        wom_id = R['womid']
                        wom = Wom.objects.get(id = wom_id)
                        sitename = Bt.objects.get(id=wom.bu_id).buname
                        log.info("Inside of the if sitename %s",sitename)
                        workpermit_obj = GeneralWorkPermit(filename=permit_name, formdata={'id':R['womid'],'bu__buname':sitename,'submit_button_flow':is_submit_button_flow,'filename':permit_name,'workpermit':wom.workpermit})
                        workpermit_attachment = workpermit_obj.execute()
                        workpermit_status = 'APPROVED'
                        send_email_notification_for_vendor_and_security.delay(R['womid'],workpermit_attachment,sitename,workpermit_status)
                else:
                    return render(request, P['email_template'], context={'alreadyapproved':True})
            cxt = {'status': Wom.WorkPermitStatus.APPROVED.value, 'action_acknowledged':True, 'seqno':wp.other_data['wp_seqno']}
            log.info("work permit accepted through email")
            return render(request, P['email_template'], context=cxt)
        
        elif R.get('action') == "rejected" and R.get('womid')  and R.get('peopleid'):
            log.info("work permit rejected")
            wp = Wom.objects.filter(id = R['womid']).first()
            if wp.workpermit == Wom.WorkPermitStatus.APPROVED:
                return render(request, P['email_template'], context={'alreadyapproved':True})
            p = People.objects.filter(id = R['peopleid']).first()
            wp.workpermit = Wom.WorkPermitStatus.REJECTED.value
            wp.save()
            reject_workpermit(wp.uuid, p.peoplecode)
            cxt = {'status': Wom.WorkPermitStatus.REJECTED.value, 'action_acknowledged':True, 'seqno':wp.other_data['wp_seqno']}
            log.info('work permit rejected through email')
            return render(request, P['email_template'], context=cxt)
        
        
class ReplySla(View):
    P = {
        'email_template': "work_order_management/sla_server_reply.html",
        'model':Wom,
    }

    def get(self,request,*args,**kwargs):
        R,P = request.GET, self.P
        S = request.session
        if R.get('action') == 'accepted' and R.get('womid') and R.get('peopleid'):
            log.info("Service level agreement report accepted")
            log.info("R:%s",R)
            log.info("Workpermit value",Wom.objects.get(uuid = R['womid']).workpermit)
            p = People.objects.filter(id = R['peopleid']).first()
            if is_all_approved := check_all_approved(R['womid'], p.peoplecode):
                log.info("Inside of the if")
                if Wom.WorkPermitStatus.APPROVED.value != Wom.objects.get(uuid = R['womid']).workpermit:
                    Wom.objects.filter(uuid = R['womid']).update(workpermit = Wom.WorkPermitStatus.APPROVED.value)
                    log.info("Inside of the second if")
                    if is_all_approved:
                        log.info("Inside of the third if")
                        wom_id = R['womid']
                        wom = Wom.objects.get(uuid = wom_id)
                        sitename = Bt.objects.get(id=wom.bu_id).buname
                        id = wom.id
                        sla_report_obj = ServiceLevelAgreement(filename='Service Level Agreement', formdata={'id':id,'bu__buname':sitename,'submit_button_flow':'true','filename':'Service Level Agreement','workpermit':wom.workpermit})
                        workpermit_attachment = sla_report_obj.execute()
                        send_email_notification_for_sla_vendor.delay(R['womid'],workpermit_attachment,sitename)
                else:
                    log.info("Else case")
                    return render(request, P['email_template'], context={'alreadyapproved':True})
            cxt = {
                'status': Wom.WorkPermitStatus.APPROVED.value,
                'action_acknowledged':True,
                'seqno':Wom.objects.get(uuid = R['womid']).other_data['wp_seqno']
            }
            log.info("is approved",is_all_approved)
            log.info("Service level agreement report accepted through email")
            return render(request, P['email_template'], context=cxt)
        elif R.get('action') == 'rejected' and R.get('womid') and R.get('peopleid'):
            wp = Wom.objects.filter(uuid = R['womid']).first()
            if wp.workpermit == Wom.WorkPermitStatus.APPROVED:
                return render(request, P['email_template'], context={'alreadyapproved':True})
            p = People.objects.filter(id = R['peopleid']).first()
            wp.workpermit = Wom.WorkPermitStatus.REJECTED.value
            wp.save()
            reject_workpermit(wp.uuid, p.peoplecode)
            cxt = {'status': Wom.WorkPermitStatus.REJECTED.value, 'action_acknowledged':True, 'seqno':wp.other_data['wp_seqno']}
            log.info('work permit rejected through email')
            return render(request, P['email_template'], context=cxt)


class ApproverView(LoginRequiredMixin, View):
    params = {
        'form_class'   : ApproverForm,
        'template_form': 'work_order_management/approver_form.html',
        'template_list': 'work_order_management/approver_list.html',
        'related'      : ['people', 'cuser'],
        'model'        : Approver,
        'fields'       : ['approverfor', 'id','sites', 'cuser__peoplename', 'people__peoplename', 'forallsites', 'bu__buname', 'bu__bucode']
    }

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # return cap_list data
        if R.get('template'): return render(request, P['template_list'])
        if R.get('action', None) == 'list':
            objs = P['model'].objects.get_approver_list(request, P['fields'], P['related'])
            return  rp.JsonResponse(data = {'data':list(objs)})
            

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'approver_form': P['form_class'](request = request),
                   'msg': "create approver requested"}
            resp = utils.render_form(request, P, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, P, False)
        
        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, P)
            resp = utils.render_form_for_update(
                request, P, 'approver_form', obj)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData']).copy()
            if pk := request.POST.get('pk', None):
                msg = "approver_view"
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
            approver = form.save(commit=False)
            approver = putils.save_userinfo(
                approver, request.user, request.session, create = create)
            logger.info("approver form saved")
            data = {'msg': f"{approver.people.peoplename}",
            'row': Approver.objects.values(*self.params['fields']).get(id = approver.id)}
            logger.debug(data)
            return rp.JsonResponse(data, status = 200)
        except (IntegrityError, pg_errs.UniqueViolation):
            return utils.handle_intergrity_error('Question')

class SLA_View(LoginRequiredMixin, View):
    params = {
        'template_form': 'work_order_management/sla_form.html',
        'template_list': 'work_order_management/sla_list.html',
        'model'        : Wom,
        'form'         : SlaForm,
        'template_form': 'work_order_management/sla_form.html',
        'template_list': 'work_order_management/sla_list.html',
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params
        action = R.get('action')
        if R.get('template'):
            return render(request,P['template_list'])
        
        if action == 'list':
            objs = self.params['model'].objects.get_slalist(request)
            return rp.JsonResponse(data = {'data':list(objs)},safe = False)

        if action == 'approver_list':
            objs = Wom.objects.get_approver_list(R['womid'])
            return rp.JsonResponse({'data': objs}, status=200)
        
        if action == 'printReport':
            print("Here I am in print report")
            return self.send_report(R, request)
        
        if action == 'form':
            import uuid
            cxt = {
                'slaform': P['form'](request = request),
                'msg': "create sla requested",
                'ownerid':uuid.uuid4()
            }
            return render(request, P['template_form'], cxt)
        
        if 'id' in R:
            obj = utils.get_model_obj(int(R['id']), request, P)
            sla_answer = Wom.objects.get_wp_answers(obj.id)
            wom_utils.get_overall_score(obj.id)
            cxt = {'slaform':P['form'](request=request, instance=obj), 'ownerid':obj.uuid,'sla_details':sla_answer[1]}
            return render(request, P['template_form'], cxt)
        
        if R.get('qsetid'):
            import uuid
            wp_details = Wom.objects.get_workpermit_details(request, R['qsetid'])
            approver_codes = R['approvers'].split(',')
            approvers = wom_utils.get_approvers(approver_codes)
            form = P['form'](request=request, initial={'qset': R['qsetid'], 'approvers': R['approvers'].split(','),'vendor':R['vendor']})
            context = {"sla_details": wp_details, 'slaform': form, 'ownerid': uuid.uuid4(),'approvers':approvers}
            return render(request, P['template_form'], context=context)
        
    def send_report(self, R, request):
        from apps.reports.report_designs import service_level_agreement as sla
        report = sla.ServiceLevelAgreement(filename=R['qset__qsetname'], client_id=request.session['client_id'], formdata=R, request=request)
        print("Report: ",report)
        return report.execute()

    def post(self,request,*args,**kwargs):
        R, P = request.POST, self.params

        try:
            if pk := R.get('pk', None):
                data = QueryDict(R['formData']).copy()
                wp = utils.get_model_obj(pk, request, P)
                form = self.params['form'](
                    data, instance = wp, request = request)
                create = False
            else:
                data = QueryDict(R['formData']).copy()
                form = self.params['form'](data, request = request)
                create=True
            if form.is_valid():
                print("Here I am going after submission")
                resp = wom_utils.handle_valid_form(form, R, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception as e:
            resp = utils.handle_Exception(request)
        return resp

