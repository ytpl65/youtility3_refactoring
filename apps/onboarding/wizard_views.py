#---------------------------- BEGIN client onboarding ---------------------------#
from django.http.response import JsonResponse
from django.views.generic.base import RedirectView
import apps.peoples.models as people_models
import apps.peoples.views as people_views
from . import views
from django.core.exceptions import NON_FIELD_ERRORS
from formtools.wizard.views import SessionWizardView
from icecream.icecream import indented_lines
import apps.onboarding.forms as obforms
import apps.peoples.forms as people_forms
from django.core.files.storage import FileSystemStorage
import apps.onboarding.models as ob
import apps.peoples.utils as people_utils
import django.contrib.messages as msg
import apps.peoples.models as pm
from .import utils as ob_utils
from django.views import View
import django.shortcuts as scts
import logging
from django.urls import resolve, reverse
log = logging.getLogger('django')
dbg = logging.getLogger('__main__')


FORMS = [("bt_form", obforms.BtForm),
         ("shift_form", obforms.ShiftForm),
         ('people_form', people_forms.PeopleForm),
         ('peoplecaps_form', people_forms.PeopleExtrasForm),
         ('pgroup_form', people_forms.PgroupForm),
         ]

TEMPLATES = {
    'bt_form': 'onboarding/client_onboarding/ob_bt_form.html',
    'shift_form': 'onboarding/client_onboarding/ob_shift_form.html',
    'people_form': 'onboarding/client_onboarding/ob_people_form.html',
    'peoplecaps_form': 'onboarding/client_onboarding/ob_peoplecaps_form.html',
    'pgroup_form': 'onboarding/client_onboarding/ob_pgroup_form.html',
}


class ClientOnboardingWizard(SessionWizardView):
    file_storage = FileSystemStorage(location=people_utils.upload_peopleimg)

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def done(self, form_list, **kwargs):
        self.process_bt_form(form_list[0])
        self.process_shift_form(form_list[1])
        people = self.process_people_form(form_list[2])
        self.process_peoplecaps_form(form_list[3], people)
        self.process_pgroup_form(form_list[4])
        return scts.HttpResponse("wizard saved successfully")

    def get_form_instance(self, step):
        return self.instance_dict.get('shift_form', None)

    def get_form_kwargs(self, step):
        kwargs = super(ClientOnboardingWizard, self).get_form_kwargs(step)
        if step in ('peoplecaps_form', 'sitegrp_temp_form'):
            kwargs['session'] = self.request.session
        return kwargs

    #-------------------- begin user-defined methods --------------------#

    def process_bt_form(self, form):
        bt = form.save(commit=True)
        people_utils.save_userinfo(bt, self.request.user, self.request.session)

    def process_shift_form(self, form):
        shift = form.save(commit=True)
        people_utils.save_userinfo(
            shift, self.request.user, self.request.session)

    def process_people_form(self, form):
        return form.save(commit=False)

    def process_peoplecaps_form(self, form, people):
        from apps.peoples.utils import save_jsonform
        save_jsonform(form, people)
        people.save()
        people_utils.save_userinfo(
            people, self.request.user, self.request.session)
        people_utils.save_user_paswd(people)

    def process_pgroup_form(self, form):
        pgroup = form.save(commit=True)
        people_utils.save_userinfo(
            pgroup, self.request.user, self.request.session)
    #-------------------- end user-defined methods --------------------#


class WizardView(View):
    wizard_steps = {
        'buform': 1,
        'shiftform': 2,
        'peopleform': 3,
        'pgroupform': 4,
        'final_step': 5 
    } # if you want to add more, add before final_step

    def get(self, request, *args, **kwargs):
        '''set wizard variables and call the first formview.'''
        import json
        # getdata = json.loads(request.GET)
        draft, res = self.check_user_has_unsaved_wizards(request),None

        if draft:#drafts continued
            request.session['wizard_data'] = draft.wizard_data['wizard_data']
            print(request.session['wizard_data'])
            url, pk  = self.get_appropriate_stage(request)
            print(f"url={url} pk={pk}")
            if pk:
                res = JsonResponse({'url':reverse(url, args=[pk]), 'draft':True})
            else:
                res = JsonResponse({'url':reverse(url), 'inst':False, 'draft':True})
        elif draft and request.GET.get('denied'):
            res = self.delete_from_draft(request)#draft denied by user
        else:
            res = self.open_new_wizard(request, False)#no drafts
        return res

    def check_user_has_unsaved_wizards(self, request):
        user = request.user
        try:
            return ob.WizardDraft.objects.get(createdby__peoplecode = user.peoplecode)
        except ob.WizardDraft.DoesNotExist:
            return False

    def get_appropriate_stage(self, request):
        wizard_data = request.session['wizard_data']
        if not wizard_data['current_inst']:
            return (wizard_data['current_url'], None)
        new_url = wizard_data['current_url'].replace('form', 'update')
        return (new_url, wizard_data['current_inst'])

    def open_new_wizard(self, request, denied):
        request.session['wizard_data'] = {
            'wizard_completed': False,
            'buids': [], 'pgroupids': [], 'peopleids': [], 'shiftids': [],
            'taids': [], 'wizard': True, 'count': len(self.wizard_steps), 'current_step': 0,
            'steps': self.wizard_steps
        }
        if not denied:
            return JsonResponse(
                {'url': reverse('onboarding:wiz_bu_form'), 'draft': False, 'denied': denied}
            )
        data = {'url':reverse('onboarding:wiz_bu_form'), 'draft':True,'isgranted':True }
        return JsonResponse(data)

    def delete_from_draft(self, request):
        if 'wizard_data' in request.session:
            del request.session['wizard_data']
            user = request.user
            ob.WizardDraft.objects.get(created_by__peoplecode = user.peoplecode).delete()
            return self.open_new_wizard(request, True)

    


class WizardDelete(View):
    def get(self, request, *args, **kwargs):  # sourcery skip: extract-method
        '''delete wizard and its data saved'''
        from apps.peoples.models import People, Pgroup

        if not request.session['wizard_data']['wizard_completed']:
            wizard_data = request.session['wizard_data']
            ob_utils.delete_unsaved_objects(
                ob.TypeAssist, wizard_data['taids'])
            ob_utils.delete_unsaved_objects(ob.Bt, wizard_data['buids'])
            ob_utils.delete_unsaved_objects(ob.Shift, wizard_data['shiftids'])
            ob_utils.delete_unsaved_objects(People, wizard_data['peopleids'])
            ob_utils.delete_unsaved_objects(Pgroup, wizard_data['pgroupids'])
        del request.session['wizard_data']
        return scts.redirect('home')

# Helper Methods


# STEP-1 BTFORM-VIEW
class WizardBt(views.CreateBt):
    model = ob.Bt
    wizard_data = {
        'current_ids': 'buids',
        'next_ids': 'shiftids',
        'instance_id': None,
        'next_url': 'onboarding:wiz_shift_form',
        'current_url': 'onboarding:wiz_bu_form',
        'next_update_url': 'onboarding:wiz_shift_update',
        'last_form': False}

    # HANDLES GET-REQUEST
    def get(self, request, *args, **kwargs):
        print(f'request get full path {request.get_full_path()}')
        log.info('onboarding wizard of step-1 buisness-unit')
        ob_utils.update_wizard_steps(
            request, 'buform', "", 'shiftform', 'id_buform')
        pk, res = kwargs.get('pk'), None
        print(f'pk={pk}')
        if pk:
            url_name = resolve(request.path_info).url_name
            if 'delete' in url_name:
                res = ob_utils.delete_object(request, self.model, {'id': pk}, 'buids',
                                             self.template_path, self.form_class, 'onboarding:wiz_bu_form', 'buform')
            else:
                res = self.get_form_for_update(request, pk)
        else:
            res = super().get(request, *args, **kwargs)
        return res

    # HANDLES POST-REQUEST
    def post(self, request, *args, **kwargs):
        log.info('onboarding wizard step-1 buisiness-unit submmitted')
        pk, update, res = kwargs.get('pk'), False, None

        try:
            form = self.form_class(request.POST)
            if pk:
                bt = self.model.objects.get(id=pk)
                form = self.form_class(request.POST, instance=bt)
                update = True
                log.info('onboarding wizard step-1 buisiness-unit retrieved')
            if form.is_valid():
                log.info('onboarding wizard step-1 is valid-form')
                res = self.process_valid_form(form, request, update)
            else:
                log.info('onboarding wizard step-1 is in-valid form')
                cxt = {'buform': form, 'edit': True,
                       'ta_form': obforms.TypeAssistForm()}
                res = scts.render(request, self.template_path, cxt)
        except self.model.DoesNotExist:
            res = res = ob_utils.handle_does_not_exist(
                request, 'onboarding:wiz_bu_form')
        except Exception:
            res = res = ob_utils.handle_other_exception(
                request, form, 'buform', self.template_path)
        return res

    def process_valid_form(self, form, request, update):
        try:
            res = None
            bt = form.save(commit=True)
            ob_utils.save_msg(request)
            self.wizard_data['instance_id'] = bt.id
            people_utils.save_userinfo(bt, request.user, request.session)
            res = ob_utils.process_wizard_form(
                request, self.wizard_data, update)
        except:
            raise
        else:
            return res

    def get_form_for_update(self, request, pk):
        res = None
        try:
            bt = self.model.objects.get(id=pk)
            form = self.form_class(instance=bt)
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm()}
            res = scts.render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            res = scts.redirect('onboarding:wiz_bu_form')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            msg.error(request, 'something went wrong', 'alert-danger')
            res = scts.redirect('onboarding:wiz_bu_form')
        return res

# STEP-2 SHIFT FORMOF WIZARD


class WizardShift(views.CreateShift):
    model = ob.Shift
    wizard_data = {
        'current_ids': 'shiftids',
        'next_ids': 'peopleids',
        'instance_id': None,
        'next_url': 'peoples:wiz_people_form',
        'current_url': 'onboarding:wiz_shift_form',
        'next_update_url': 'peoples:wiz_people_update',
        'last_form': False}

    # HANDLES GET-REQUEST
    def get(self, request, *args, **kwargs):
        ob_utils.update_wizard_steps(
            request, 'shiftform', 'buform', 'peopleform', 'id_shiftform')
        log.info('onboarding wizard of step-2 shift')
        pk, res = kwargs.get('pk'), None
        if pk:
            url_name = resolve(request.path_info).url_name
            if 'delete' in url_name:
                res = ob_utils.delete_object(request, self.model, {'id': pk}, 'shiftids',
                                             self.template_path, self.form_class, 'onboarding:wiz_shift_form', 'shift_form')
            else:
                res = self.get_form_for_update(request, pk)
        else:
            res = super().get(request, *args, **kwargs)
        return res

    # HANDLES POST-REQUEST
    def post(self, request, *args, **kwargs):
        log.info('onboarding wizard step-2 shift submmitted')
        pk, update, res = kwargs.get('pk'), False, None

        try:
            form = self.form_class(request.POST)
            if pk:
                shift = self.model.objects.get(id=pk)
                form = self.form_class(request.POST, instance=shift)
                update = True
                log.info('onboarding wizard step-2 shift retrieved')
            if form.is_valid():
                res = self.process_valid_form(form, request, update)
            else:
                log.info('onboarding wizard step-2 is in-valid form')
                cxt = {'shift_form': form, 'edit': True}
                res = scts.render(request, self.template_path, cxt)
        except self.model.DoesNotExist:
            res = ob_utils.handle_does_not_exist(
                request, 'onboarding:wiz_shift_form')
        except Exception:
            print('raised correct')
            res = ob_utils.handle_other_exception(
                request, form, 'shift_form', self.template_path)
        return res

    def process_valid_form(self, form, request, update):
        try:
            res = None
            log.info('step-2 is valid')
            shift = form.save(commit=True)
            ob_utils.save_msg(request)
            self.wizard_data['instance_id'] = shift.id
            people_utils.save_userinfo(shift, request.user, request.session)
            res = ob_utils.process_wizard_form(
                request, self.wizard_data, update)
        except:
            raise
        else:
            return res

    def get_form_for_update(self, request, pk):
        res = None
        try:
            shift = self.model.objects.get(id=pk)
            form = self.form_class(instance=shift)
            cxt = {'shift_form': form, 'edit': True}
            res = scts.render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            res = scts.redirect('onboarding:wiz_shift_form')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            msg.error(request, 'something went wrong', 'alert-danger')
            res = scts.redirect('onboarding:wiz_shift_form')
        return res


# STEP-3 PEOPLE FORM OF WIZARD
class WizardPeople(people_views.CreatePeople):
    model = people_models.People
    wizard_data = {
        'current_ids': 'peopleids',
        'next_ids': 'pgroupids',
        'instance_id': None,
        'next_url': 'peoples:wiz_pgroup_form',
        'current_url': 'peoples:wiz_people_form',
        'next_update_url': 'peoples:wiz_pgroup_update',
        'last_form': False}

    # HANDLES GET-REQUEST
    def get(self, request, *args, **kwargs):
        ob_utils.update_wizard_steps(
            request, 'peopleform', 'shiftform', 'pgroupform', 'id_peopleform')
        log.info('onboarding wizard of step-3 people')
        pk, res = kwargs.get('pk'), None
        if pk:
            res = self.get_form_for_update(request, pk)
        else:
            res = super().get(request, *args, **kwargs)
        return res

    # HANDLES POST-REQUEST
    def post(self, request, *args, **kwargs):
        log.info('onboarding wizard step-3 people submmitted')
        pk, update, res = kwargs.get('pk'), False, None

        try:
            json_form = self.jsonform(
                request.POST, session=request.session)
            form = self.form_class(request.POST)
            if pk:
                people = self.model.objects.get(id=pk)
                form = self.form_class(request.POST, instance=people)
                update = True
                log.info('onboarding wizard step-3 people retrieved')
            if form.is_valid() and json_form.is_valid():
                log.info('onboarding wizard step-3 is valid-form')
                res = self.process_valid_form(form, json_form, request, update)
            else:
                log.info('onboarding wizard step-3 is in-valid form')
                cxt = {'peopleform': form,
                       'pref_form': json_form, 'edit': True}
                res = scts.render(request, self.template_path, cxt)
        except self.model.DoesNotExist:
            res = ob_utils.handle_does_not_exist(
                request, 'peoples:wiz_people_form')
        except Exception:
            form = self.form_class(request.POST, request.FILES)
            json_form = self.jsonform(request.POST, session=request.session)
            res = ob_utils.handle_other_exception(
                request, form, 'peopleform', self.template_path, json_form, 'pref_form')
        return res

    def process_valid_form(self, form, json_form, request, update):
        try:
            log.info('step-3 is valid')
            res, people = None, form.save(commit=False)
            if people_utils.save_jsonform(json_form, people):
                people.peopleimg = request.FILES.get(
                    'peopleimg', 'master/people/blank.png')
                people.save()
                ob_utils.save_msg(request)
                people = people_utils.save_userinfo(
                    people, request.user, request.session)
                self.wizard_data['instance_id'] = people.id
            res = ob_utils.process_wizard_form(
                request, self.wizard_data, update)
        except:
            raise
        else:
            return res

    def get_form_for_update(self, request, pk):
        res = None
        try:
            people = self.model.objects.get(id=pk)
            url_name = resolve(request.path_info).url_name
            if 'delete' in url_name:
                res = ob_utils.delete_object(request, self.model, {'id': pk}, 'peopleids',
                                             self.template_path, self.form_class, 'peoples:wiz_people_form', 'peopleform',
                                             'pref_form', people_utils.get_people_prefform(people, request.session))
            else:
                form = self.form_class(instance=people)
                cxt = {'peopleform': form,
                       'pref_form': people_utils.get_people_prefform(people, request.session),
                       'edit': True}
                res = scts.render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            res = scts.redirect('peoples:wiz_people_form')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            msg.error(request, 'something went wrong', 'alert-danger')
            res = scts.redirect('peoples:wiz_people_form')
        return res


# STEP-3 PEOPLE GORUP FORM OF WIZARD
class WizardPgroup(people_views.CreatePgroup):
    model = people_models.Pgroup
    wizard_data = {
        'current_ids': 'pgroupids',
        'next_ids': None,
        'instance_id': None,
        'next_url': 'onboarding:preview',
        'current_url': 'peoples:wiz_pgroup_form',
        'next_update_url': 'peoples:wiz_people_update',
        'last_form': False}

    # HANDLES GET-REQUEST
    def get(self, request, *args, **kwargs):
        log.info('onboarding wizard of step-4 pgroup')
        ob_utils.update_wizard_steps(
            request, 'pgroupform', 'peopleform', 'final_step', 'id_pgroupform')
        pk, res = kwargs.get('pk'), None
        if pk:
            url_name = resolve(request.path_info).url_name
            if 'delete' in url_name:
                res = ob_utils.delete_object(request, self.model, {'id': pk}, 'ids',
                                             self.template_path, self.form_class, 'peoples:wiz_pgroup_form', 'pgroup_form')
            else:
                res = self.get_form_for_update(request, pk)
        else:
            res = super().get(request, *args, **kwargs)
        return res

    # HANDLES POST-REQUEST
    def post(self, request, *args, **kwargs):
        log.info('onboarding wizard step-4 pgroup submmitted')
        pk, update, res = kwargs.get('pk'), False, None

        try:
            form = self.form_class(request.POST)
            if pk:
                pg = self.model.objects.get(id=pk)
                form = self.form_class(request.POST, instance=pg)
                update = True
                log.info('onboarding wizard step-4 pgroup retrieved')
            if form.is_valid():
                log.info('onboarding wizard step-4 is valid-form')
                res = self.process_valid_form(form, request, update)
            else:
                log.info('onboarding wizard step-4 is in-valid form')
                cxt = {'shift_form': form, 'edit': True}
                res = scts.render(request, self.template_path, cxt)
        except self.model.DoesNotExist:
            res = ob_utils.handle_does_not_exist(
                request, 'onboarding:shift_form')
        except Exception:
            res = ob_utils.handle_other_exception(
                request, form, 'shift_form', self.template_path)
        return res

    def process_valid_form(self, form, request, update):
        try:
            log.info('step-4 is valid')
            res, pg = None, form.save(commit=True)
            people_utils.save_userinfo(pg, request.user, request.session)
            ob_utils.save_msg(request)
            self.wizard_data['instance_id'] = pg.id
            res = ob_utils.process_wizard_form(
                request, self.wizard_data, update)
        except:
            raise
        else:
            return res

    def get_form_for_update(self, request, pk):
        res = None
        try:
            pg = self.model.objects.get(id=pk)
            form = self.form_class(instance=pg)
            cxt = {'pgroup_form': form, 'edit': True}
            res = scts.render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            res = scts.redirect('peoples:pgroup_form')
        except Exception:
            log.critical('something went wrong', exc_info=True)
            msg.error(request, 'something went wrong', 'alert-danger')
            res = scts.redirect('peoples:pgroup_form')
        return res


# Final step (preview wizard)
class WizardPreview(View):
    wizard_submissions = {
        'buids': [], 'shiftids': [], 'peopleids': [],
        'pgroupids': [], 'taids': []}

    def get(self, request, *args, **kwargs):
        try:
            log.info('collecting data from session for preview...START')
            ob_utils.update_wizard_steps(
                request, 'final_step', 'pgroupform', "", None)
            # collect wizard submissions from session
            session_data = request.session
            steps = [(ob.TypeAssist, 'taids'), (ob.Bt, 'buids'), (ob.Shift, 'shiftids'),
                     (pm.People, 'peopleids'), (pm.Pgroup, 'pgroupids')]
            for model, ids in steps:
                self.get_data(model, session_data, ids)
        except:
            log.error(
                'Something went wrong while collecting data...FAILED', exc_info=True)
        else:
            cxt = {'wizard_subs': self.wizard_submissions}
            print(self.wizard_submissions)
            log.info('collecting data from session for preview...DONE')
            return scts.render(request, 'onboarding/preview_wizard.html', context=cxt)

    def get_data(self, model, sd, ids):
        if sd.get('wizard_data') and sd['wizard_data'].get(ids):
            log.info(f'Getting data from model {model} for ids {ids}')
            fields = {'buids': ['bucode', 'buname', 'butype__taname', 'parent__bucode'],
                      'taids': ['tacode', 'taname', 'tatype', 'parent__taname'],
                      'peopleids': ['peoplecode', 'peoplename', 'peopletype__taname', 'loginid'],
                      'shiftids': ['shiftname', 'starttime', 'endtime'],
                      'pgroupids': ['groupname']}

            data = model.objects.filter(
                pk__in=sd['wizard_data'][ids]).values(*fields[ids])
            self.wizard_submissions[ids] = data


def save_wizard(request):
    del request.session['wizard_data']
    return scts.redirect('home')


def save_as_draft(request):
    if request.method != 'GET':
        return

    user, session = request.user, request.session
    bu = ob.Bt.objects.get(pk=session['clientid'])
    wd = session['wizard_data']
    _, created = ob.WizardDraft.objects.update_or_create(
        createdby = user, buid = bu,
        defaults = {'wizard_data': {'wizard_data':wd}})
    status = 'created' if created else 'updated'
    log.info(f"wizard draft {status}")
    if request.GET.get('quit'):
        print('session is free from wizard')
        del request.session['wizard_data']
    return JsonResponse({'saved':True, 'status':status})


def delete_from_draft(request):
    if request.method == 'GET':
        try:
            ob.WizardDraft.objects.get(
                createdby__peoplecode = request.user.peoplecode).delete()
            log.info("object deleted from draft")
        except ob.WizardDraft.DoesNotExist:
            status = "already deleted or no draft to delete."
            log.info("object DoesNotExist")
        else:
            status = 'deleted'
        return JsonResponse({'status':status})
        
