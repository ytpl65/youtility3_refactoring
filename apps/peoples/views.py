from django.db.utils import IntegrityError
from django.db import transaction
from django.forms import model_to_dict
from django.http.request import QueryDict
from django.db.models import Q, RestrictedError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import EmptyResultSet
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import response as rp
from django.shortcuts import redirect, render
from django.views import View
from icecream import ic
import logging
from apps.onboarding.models import TypeAssist, Bt
from apps.peoples.filters import CapabilityFilter
from apps.core import utils
import apps.peoples.filters as pft
import apps.peoples.forms as pf  # people forms
import apps.peoples.models as pm  # people models
import apps.onboarding.forms as obf  # onboarding-modes
from .models import Capability, Pgbelonging, Pgroup, People
from .utils import save_userinfo, save_pgroupbelonging
import apps.peoples.utils as putils
from django.contrib import messages
from .forms import CapabilityForm, PgroupForm, PeopleForm, PeopleExtrasForm, LoginForm
from django_email_verification import send_email
from django.views.decorators.cache import never_cache

logger = logging.getLogger('django')

# Create your views here.
#========================== Begin People View Classes ===========================#

class SignIn(View):
    template_path = 'peoples/login.html'
    error_msgs = {
        'invalid-details': "Sorry that didn't work <br> try again \
                            with proper username and password",
        'invalid-cookies': 'Please enable cookies in your browser...',
        'auth-error': 'Authentication failed of user with loginid = %s\
                            password = %s',
        'invalid-form': 'sign in form is not valid...',
        'critical-error': 'something went wrong please follow the traceback to fix it... '}

    @never_cache
    def get(self, request, *args, **kwargs):
        logger.info('SignIn View')
        request.session.set_test_cookie()
        form = LoginForm()
        return render(request, self.template_path, context={'loginform': form})

    def post(self, request, *args, **kwargs):
        from .utils import  display_user_session_info
        form, response = LoginForm(request.POST), None
        logger.info('form submitted')
        try:
            if not request.session.test_cookie_worked():
                logger.warning(
                    'cookies are not enabled in user browser', exc_info = True)
                form.add_error(None, self.error_msgs['invalid-cookies'])
                cxt = {'loginform': form}
                response = render(request, self.template_path, context = cxt)
            elif form.is_valid():
                logger.info('Signin form is valid')
                loginid = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                #utils.set_db_for_router('icicibank')
                if people := authenticate(
                    request, username = loginid, password = password
                ):
                    login(request, people)
                    #response = redirect('onboarding:wizard_delete') if request.session.get('wizard_data') else redirect('/dashboard')
                    logger.info(
                        'Login Successfull for people "%s" with loginid "%s" client "%s" site "%s"', people.peoplename, people.loginid, people.client.buname if people.client else "None", people.bu.buname if people.bu else "None")
                    utils.save_user_session(request, request.user)
                    display_user_session_info(request.session)
                    logger.info(f"User logged in {request.user.peoplecode}")
                    if request.session.get('bu_id') in [1, None]: return redirect('peoples:no_site')
                    response = redirect('onboarding:wizard_delete') if request.session.get('wizard_data') else redirect('onboarding:rp_dashboard')

                else:
                    logger.warning(
                        self.error_msgs['auth-error'], loginid, '********')
                    form.add_error(
                        None, self.error_msgs['invalid-details'])
                    cxt = {'loginform': form}
                    response = render(
                        request, self.template_path, context = cxt)
            else:
                logger.warning(self.error_msgs['invalid-form'])
                cxt = {'loginform': form}
                response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(self.error_msgs['critical-error'], exc_info = True)
            form.add_error(None, self.error_msgs['critical-error'])
            cxt = {'loginform': form}
            response = render(request, self.template_path, context = cxt)
        return response

class SignOut(LoginRequiredMixin, View):
    @staticmethod
    def get(request, *args, **kwargs):
        response = None
        try:
            logout(request)
            logger.info("User logged out DONE!")
            response = redirect("/")
        except Exception:
            logger.error('unable to log out user', exc_info = True)
            messages.warning(request, 'Unable to log out user...',
                             'alert alert-danger')
            response = redirect('/dashboard')
        return response

class ChangePeoplePassword(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    @staticmethod
    def post(request, *args, **kwargs):
        from django.contrib.auth.forms import SetPasswordForm
        from django.http import JsonResponse
        id, response = request.POST.get('people'), None
        people = People.objects.get(id = id)
        form = SetPasswordForm(people, request.POST)
        if form.is_valid():
            form.save()
            response = JsonResponse({'res': 'Password is changed successfully!',
                                     'status': 200})
        else:
            response = JsonResponse({'res': form.errors,
                                     'status': 500})
        return response

# @method_decorator(login_required, name='dispatch')
class CreatePeople(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    jsonform = PeopleExtrasForm
    form_class = PeopleForm

    def get(self, request, *args, **kwargs):
        logger.info('Create People view')
        from apps.onboarding.forms import TypeAssistForm
        cxt = {'peopleform': self.form_class(),
               'pref_form': self.jsonform(session = request.session),
               'ta_form': TypeAssistForm(auto_id = False)}
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        logger.info('Create People form submiited')
        from .utils import save_jsonform, save_user_paswd
        from django_email_verification import send_email

        response = None
        peopleform = self.form_class(request.POST, request.FILES)
        peoplepref_form = self.jsonform(
            request.POST, session = request.session)  # a json form for json data
        try:
            if peoplepref_form.is_valid() and peopleform.is_valid():
                logger.info('People Form is valid')
                people = peopleform.save(commit = False)
                ic(dir(people))
                if save_jsonform(peoplepref_form, people):
                    people.save()
                    people = save_userinfo(
                        people, request.user, request.session, bu = people.bu_id)
                    people.peopleimg = request.FILES.get('peopleimg',
                                                         'master/people/blank.png')
                    save_user_paswd(people)
                    send_email(people, request)
                    # insert_people_attachment()
                    logger.info('People Form saved... DONE')
                    messages.success(request, "Success record saved DONE!",
                                     "alert alert-success")
                    response = redirect('peoples:people_form')
            else:
                logger.info('Form is not valid')
                cxt = {'peopleform': peopleform,
                       'pref_form': peoplepref_form,
                       'edit': True, 'ta_form': obf.TypeAssistForm(auto_id = False)}
                response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'peopleform': peopleform,
                   'pref_form': peoplepref_form,
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id = False)}
            response = render(request, self.template_path, context = cxt)
        return response

class RetrievePeoples(LoginRequiredMixin, View):
    template_path = 'peoples/people_list.html'

    related = ['peopletype', 'bu']
    fields = ['id', 'peoplecode', 'peoplename', 'peopletype__tacode', 'bu__bucode',
              'isadmin']
    model = People

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve People view')
            objects = self.model.objects.select_related(*self.related
                                                        ).values(*self.fields)
            logger.info('People objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            response = redirect('/dashboad')
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        from .filters import PeopleFilter
        if request.GET:
            objects = PeopleFilter(request.GET, queryset = objects).qs
        filterform = PeopleFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            people_list = paginator.page(page)
        except PageNotAnInteger:
            people_list = paginator.page(1)
        except EmptyPage:
            people_list = paginator.page(paginator.num_pages)
        return {'people_list': people_list, 'people_filter': filterform}

# update People instance
class UpdatePeople(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    def get(self, request, *args, **kwargs):
        logger.info('Update People view')
        response = None
        try:
            from .utils import get_people_prefform
            pk = kwargs.get('pk')
            people = self.model.objects.get(id = pk)
            logger.info('object retrieved {}'.format(people))
            form = self.form_class(instance = people)
            cxt = {'peopleform': form,
                   'pref_form': get_people_prefform(people, request.session),
                   'ta_form': obf.TypeAssistForm(auto_id = False),
                   'edit': True}
            response = render(request, self.template_path, context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:people_form')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:people_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('PeopleForm Form submitted')
        from .utils import save_jsonform
        try:
            pk, response = kwargs.get('pk'), None
            people = self.model.objects.get(id = pk)
            form = self.form_class(
                request.POST, request.FILES, instance = people)
            jsonform = self.json_form(request.POST, session = request.session)
            if form.is_valid() and jsonform.is_valid():
                logger.info('PeopleForm Form is valid')
                if save_jsonform(jsonform, people):
                    people.peopleimg = request.FILES.get(
                        'peopleimg', 'master/people/blank.png')
                    people.save()
                    people = save_userinfo(
                        people, request.user, request.session, create = False)
                    logger.info('PeopleForm Form saved')
                    messages.success(request, "Success record updated successfully!",
                                     "alert alert-success")
                    response = redirect('peoples:people_form')
            else:
                logger.info('Form is not valid')
                cxt = {'peopleform': form,
                       'pref_form': jsonform,
                       'edit': True,
                       'ta_form': obf.TypeAssistForm(auto_id = False)}
                response = render(request, self.template_path, context = cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info = True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'peopleform': form, 'pref_form': jsonform,
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id = False)}
            response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'peopleform': form, 'pref_form': jsonform, 'edit': True,
                   'ta_form': obf.TypeAssistForm(auto_id = False)}
            response = render(request, self.template_path, context = cxt)
        return response

class DeletePeople(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        from .utils import get_people_prefform
        pk, response = kwargs.get('pk'), None
        try:
            if pk:
                people = self.model.objects.get(id = pk)
                logger.info('deleting people %s ...', people.peoplecode)
                form = self.form_class(instance = people)
                people.delete()
                logger.info('People object deleted... DONE')
                messages.info(request, 'Record deleted successfully!',
                              'alert alert-success')
                response = redirect('peoples:people_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'People does not exist',
                           "alert alert-danger")
            response = redirect('peoples:people_form')
        except RestrictedError:
            logger.error('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'peopleform': form,
                   'pref_form': get_people_prefform(people, request.session),
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id = False)}
            response = render(request, self.template_path, context = cxt)
        return response
#=========================== End People View Classes ==============================#

#========================== Begin Pgroup View Classes ============================#

class CreatePgroup(LoginRequiredMixin, View):
    template_path = 'peoples/pgroup_form.html'
    form_class = PgroupForm
    form_class2 = pf.PeopleGrpAllocation

    def get(self, request, *args, **kwargs):
        """Returns Pgroup form on html"""
        logger.info('Create Pgroup view')
        cxt = {'pgroup_form': self.form_class(request = request), }
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('Create Pgroup form submiited')
        form, response = self.form_class(request.POST, request = request), None
        try:
            if form.is_valid():
                logger.info('Pgroup Form is valid')
                pg = form.save()
                pg.identifier, _ = TypeAssist.objects.get_or_create(
                    tacode="PEOPLE_GROUP", taname="People Group",
                    defaults={'tacode': "PEOPLEGROUP", 'taname': "People Group", 'tatype_id': -1})
                pg = save_userinfo(pg, request.user, request.session)
                save_pgroupbelonging(pg, request)
                logger.info('Pgroup Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('peoples:pgroup_form')
            else:
                logger.info('Form is not valid')
                cxt = {'pgroup_form': form, 'edit': True, }
                response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True, }
            response = render(request, self.template_path, context = cxt)
        return response

class RetrivePgroups(LoginRequiredMixin, View):
    template_path = 'peoples/pgroup_list.html'
    fields = ['id', 'groupname', 'enable']
    model = Pgroup

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            objects = self.model.objects.values(*self.fields)
            logger.info('Pgroup objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        from .filters import PgroupFilter
        if request.GET:
            objects = PgroupFilter(request.GET, queryset = objects).qs
        filterform = PgroupFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            pgroup_list = paginator.page(page)
        except PageNotAnInteger:
            pgroup_list = paginator.page(1)
        except EmptyPage:
            pgroup_list = paginator.page(paginator.num_pages)
        return {'pgroup_list': pgroup_list, 'pg_filter': filterform}

class UpdatePgroup(LoginRequiredMixin, View):
    template_path = 'peoples/pgroup_form.html'
    form_class = PgroupForm
    form_class2 = pf.PeopleGrpAllocation
    model = Pgroup

    def get(self, request, *args, **kwargs):
        logger.info('Update Pgroup view')
        response = None
        try:
            pk = kwargs.get('pk')
            pg = self.model.objects.get(id = pk)
            logger.info('object retrieved {}'.format(pg))
            peoples = pm.Pgbelonging.objects.filter(
                pgroup = pg).values_list('people', flat = True)
            print(f"peoples {peoples}")
            form = self.form_class(instance = pg, initial={
                                   'peoples': list(peoples)}, request = request)
            response = render(request, self.template_path,  context={
                'pgroup_form': form, 'edit': True})
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:pgroup_form')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:pgroup_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('PgroupForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            pg = self.model.objects.get(id = pk)
            form = self.form_class(request.POST, instance = pg, request = request)
            if form.is_valid():
                logger.info('PgroupForm Form is valid')
                pg = form.save(commit = True)
                pg = save_userinfo(pg, request.user, request.session, create = False)
                save_pgroupbelonging(pg, request)
                logger.info('PgroupForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('peoples:pgroup_form')
            else:
                logger.info('Form is not valid')
                cxt = {'pgroup_form': form, 'edit': True}
                response = render(request, self.template_path, context = cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info = True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        return response

class DeletePgroup(LoginRequiredMixin, View):
    form_class = PgroupForm
    template_path = 'peoples/pgroup_form.html'
    model = Pgroup

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk'), None
        try:
            if pk:
                pg = self.model.objects.get(id = pk)
                form = self.form_class(instance = pg, request = request)
                pg.enable = False
                logger.info('Pgroup object deleted')
                messages.info(request, 'Record deleted successfully!',
                              'alert alert-success')
                response = redirect('peoples:pgroup_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist',
                           "alert alert-danger")
            response = redirect('peoples:pgroup_form')
        except RestrictedError:
            logger.warning('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        return response
#=========================== End Pgroup View Classes ==============================#

#=========================== Begin  Capability View Classes ==============================#
class CreateCapability(LoginRequiredMixin, View):
    template_path = 'peoples/capability_form.html'
    form_class = CapabilityForm

    def get(self, request, *args, **kwargs):
        """Returns Pgroup form on html"""
        logger.info('Create Capability view')
        cxt = {'cap_form': self.form_class()}
        return render(request, self.template_path, context = cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('Create Capability form submiited')
        form, response = self.form_class(request.POST), None
        try:
            if form.is_valid():
                logger.info('CapabilityForm Form is valid')
                cap = form.save()
                cap = save_userinfo(cap, request.user, request.session)
                logger.info('CapabilityForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('peoples:cap_form')
            else:
                logger.info('Form is not valid')
                cxt = {'cap_form': form, 'edit': True}
                response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        return response

class RetriveCapability(LoginRequiredMixin, View):
    template_path = 'peoples/capability_list.html'
    fields = ['id', 'capscode', 'capsname', 'cfor', 'parent__capscode']
    model = Capability

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Capabilities view')
            objects = self.model.objects.select_related(
                'parent').values(*self.fields).order_by('-cdtz')
            logger.info('Capabilities objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context = cxt)
        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info = True)
            response = render(request, self.template_path, context = cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info = True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    @staticmethod
    def paginate_results(request, objects):
        '''paginate the results'''
        logger.info('Pagination Start'if objects else "")
        if request.GET:
            objects = CapabilityFilter(request.GET, queryset = objects).qs
        filterform = CapabilityFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            cap_list = paginator.page(page)
        except PageNotAnInteger:
            cap_list = paginator.page(1)
        except EmptyPage:
            cap_list = paginator.page(paginator.num_pages)
        return {'cap_list': cap_list, 'cap_filter': filterform}

class UpdateCapability(LoginRequiredMixin, View):
    template_path = 'peoples/capability_form.html'
    form_class = CapabilityForm
    model = Capability

    def get(self, request, *args, **kwargs):
        logger.info('Update Capability view')
        response = None
        try:
            pk = kwargs.get('pk')
            cap = self.model.objects.get(id = pk)
            logger.info('object retrieved {}'.format(cap))
            form = self.form_class(instance = cap)
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path,  context = cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:cap_form')
        except Exception:
            logger.critical('something went wrong', exc_info = True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:cap_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('CapabilityForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            cap = self.model.objects.get(id = pk)
            form = self.form_class(request.POST, instance = cap)
            if form.is_valid():
                logger.info('CapabilityForm Form is valid')
                cap = form.save()
                cap = save_userinfo(cap, request.user, request.session, create = False)
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('peoples:cap_form')
            else:
                logger.info('Form is not valid')
                cxt = {'cap_form': form, 'edit': True}
                response = render(request, self.template_path, context = cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info = True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info = True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        return response

class DeleteCapability(LoginRequiredMixin, View):
    model = Capability
    template_path = 'peoples/capability_form.html'
    form_class = CapabilityForm

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk'), None
        try:
            if pk:
                cap = self.model.objects.get(id = pk)
                form = self.form_class(instance = cap)
                cap.delete()
                logger.info('Capability object deleted')
                messages.info(request, 'Record deleted successfully',
                              'alert alert-success')
                response = redirect('peoples:cap_form')
        except self.model.DoesNotExist:
            logger.warning('Unable to delete, object does not exist')
            messages.error(request, 'Capability does not exist',
                           "alert alert-danger")
            response = redirect('peoples:cap_form')
        except RestrictedError:
            logger.warning('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies',
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        except Exception:
            messages.error(request, '[ERROR] Something went wrong',
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context = cxt)
        return response

#=========================== End Capability View Classes ==============================#

def delete_master(request, params):
    raise NotImplementedError()

class Capability(LoginRequiredMixin, View):
    params = {
        'form_class': pf.CapabilityForm,
        'template_form': 'peoples/partials/partial_cap_form.html',
        'template_list': 'peoples/capability.html',
        'partial_form': 'peoples/partials/partial_cap_form.html',
        'partial_list': 'peoples/partials/partial_cap_list.html',
        'related': ['parent'],
        'model': pm.Capability,
        'filter': CapabilityFilter,
        'fields': ['id', 'capscode', 'capsname',
                   'cfor', 'parent__capscode'],
        'form_initials': {'initial': {}}}

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # return cap_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "cap_list", 'filt_name': "cap_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(capscode='NONE'), enable = True
            ).values(*self.params['fields'])
            resp = rp.JsonResponse(data = {
                'data' : list(objs)
            }, status = 200, safe = False)

        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'cap_form': self.params['form_class'](request = request),
                   'msg': "create capability requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "cap_form", obj)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg, create = "capability_view", False
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                print(form.data)

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
        logger.info('capability form is valid')
        from apps.core.utils import handle_intergrity_error

        try:
            cap = form.save()
            putils.save_userinfo(cap, request.user, request.session, create = create)
            logger.info("capability form saved")
            data = {'success': "Record has been saved successfully",
                    'row':pm.Capability.objects.values(
                        *self.params['fields']).get(id = cap.id)}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error("Capability")

class PeopleView(LoginRequiredMixin, View):
    params = {
        'form_class': pf.PeopleForm,
        'json_form': pf.PeopleExtrasForm,
        'template_form': 'peoples/people_form.html',
        'template_list': 'peoples/people_list.html',
        'related': ['peopletype', 'bu'],
        'model': pm.People,
        'filter': pft.PeopleFilter,
        'fields': ['id', 'peoplecode', 'peoplename', 'peopletype__tacode', 'bu__bucode',
                   'isadmin', 'enable'],
        'form_initials': {'initial': {}}}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        if R.get('template') == 'true':
            return render(request, self.params['template_list'])

        # return cap_list data
        if R.get('action', None) == 'list' or R.get('search_term'):

            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(peoplecode='NONE'), 
                    client_id = request.session['client_id']
            ).values(*self.params['fields'])
            return rp.JsonResponse(data = {'data':list(objs)}, status = 200)

        # return cap_form empty
        if R.get('action', None) == 'form':
            cxt = {'peopleform': self.params['form_class'](request=request),
                   'pref_form': self.params['json_form'](session = request.session, request=request),
                   'ta_form': obf.TypeAssistForm(auto_id = False, request=request),
                   'msg': "create people requested"}
            resp = render(request, self.params['template_form'], cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, True)

        # return form with instance
        elif R.get('id', None):
            from .utils import get_people_prefform
            people = utils.get_model_obj(R['id'], request, self.params)
            cxt = {'peopleform': self.params['form_class'](instance = people, request=request),
                   'pref_form': get_people_prefform(people, request.session, request),
                   'ta_form': obf.TypeAssistForm(auto_id = False, request=request),
                   'msg': "update people requested"}
            resp = render(request, self.params['template_form'], context = cxt)
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        data = QueryDict(request.POST['formData'])
        ic(data)
        try:
            if pk := request.POST.get('pk', None):
                msg, create = "people_view", False  
                people = utils.get_model_obj(pk, request,  self.params)
                form = self.params['form_class'](data, request.FILES, instance = people, request=request)
            else:
                form = self.params['form_class'](data, request = request)
            ic(form.instance.id)
            jsonform = self.params['json_form'](data, session = request.session, request=request)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request, create)
            else:
                cxt = {'errors': form.errors}
                if jsonform.errors:
                    cxt.update({'errors': jsonform.errors})
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request ,create):
        logger.info('people form is valid')
        from apps.core.utils import handle_intergrity_error
        
        try:
            ic(request.POST, request.FILES)
            people = form.save()
            if request.FILES.get('peopleimg'):
                people.peopleimg = request.FILES['peopleimg']
            if not people.password:
                people.set_password(form.cleaned_data["peoplecode"])
            if putils.save_jsonform(jsonform, people):
                buid = people.bu.id if people.bu else None
                people = putils.save_userinfo(
                    people, request.user, request.session, create = create, bu = buid)
                logger.info("people form saved")
            data = {'pk':people.id}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error('People')

class PeopleGroup(LoginRequiredMixin, View):
    params = {
        'form_class'   : pf.PeopleGroupForm,
        'template_form': 'peoples/partials/partial_pgroup_form.html',
        'template_list': 'peoples/peoplegroup.html',
        'partial_form' : 'peoples/partials/partial_pgroup_form.html',
        'related'      : ['identifier'],
        'model'        : pm.Pgroup,
        'fields'       : ['groupname', 'enable', 'id'],
        'form_initials': {}
    }

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # return list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.select_related(
                 *self.params['related']).filter(
                    ~Q(id=-1), enable = True, identifier__tacode='PEOPLEGROUP', client_id = request.session['client_id']
            ).values(*self.params['fields']).order_by('-mdtz')
            return  rp.JsonResponse(data = {'data':list(objs)})

        # return form empty
        if R.get('action', None) == 'form':
            ic('fksnfksnfkjsdkjfsjdfkamsdfkmaskf')
            cxt = {'pgroup_form': self.params['form_class'](request = request),
                   'msg': "create people group requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            obj = utils.get_model_obj(R['id'], request, self.params)
            pm.Pgbelonging.objects.filter(pgroup = obj).delete()
            resp = utils.render_form_for_delete(request, self.params, False)

        # return form with instance
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            peoples = pm.Pgbelonging.objects.filter(
                pgroup = obj).values_list('people', flat = True)
            ic(peoples)
            FORM = self.params['form_class'](request = request, instance = obj, initial = {'peoples':list(peoples)})
            resp = utils.render_form_for_update(
                request, self.params, "pgroup_form", obj, FORM=FORM)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            data = QueryDict(request.POST['formData'])
            if pk := request.POST.get('pk', None):
                msg = "pgroup_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs = {'request':request})
                create= False
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
        logger.info('pgroup form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            pg = form.save(commit = False)
            putils.save_userinfo(pg, request.user, request.session, create = create)
            save_pgroupbelonging(pg, request)
            logger.info("people group form saved")
            data = {'row': Pgroup.objects.values(*self.params['fields']).get(id = pg.id)}
            return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error("Pgroup")


class SiteGroup(LoginRequiredMixin, View):
    params = {
        'form_class'   : pf.SiteGroupForm,
        'template_form': 'peoples/sitegroup_form.html',
        'template_list': 'peoples/sitegroup_list.html',
        'related'      : ['identifier'],
        'model'        : pm.Pgroup,
        'fields'       : ['groupname', 'enable', 'id'],
        'form_initials': {}
    }

    def get(self, request, *args, **kwargs):
        R, resp, objects, filtered = request.GET, None, [], 0
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        # for list view of group
        if R.get('action') == 'list':
            total, filtered, objs = pm.Pgroup.objects.list_view_sitegrp(R, request)
            logger.info('SiteGroup objects %s retrieved from db', (total or "No Records!"))
            utils.printsql(objs)
            resp = rp.JsonResponse(data = { 
                'draw':R['draw'],
                'data':list(objs),
                'recordsFiltered':filtered,
                'recordsTotal':total
            })
            return resp

        # to populate all sites table
        if R.get('action', None) == 'allsites':
            objs, idfs  = Bt.objects.get_bus_idfs(R, request=request, idf= R['sel_butype'])

            resp = rp.JsonResponse(data = {
                'data':list(objs),
                'idfs':list(idfs)
            })
            return resp

        if R.get('action') == "loadSites":
            data = Pgbelonging.objects.get_assigned_sitesto_sitegrp(R['id'])
            print(data)
            resp = rp.JsonResponse(data = {
                'assigned_sites':list(data),
            })
            return resp

        # form without instance to create new data
        if R.get('action', None) == 'form':
            # options = self.get_options()
            cxt = {'sitegrpform': self.params['form_class'](request = request),
                   'msg': "create site group requested"}
            return render(request, self.params['template_form'], context = cxt)
        
        # handle delete request
        if R.get('action', None) == "delete" and R.get('id', None):
            ic('here')
            obj = utils.get_model_obj(R['id'])
            pm.Pgbelonging.objects.filter(pgroup_id = obj.id).delete()
            return rp.JsonResponse(data = None, status = 200)

        # form with instance to load existing data
        if R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            sites = pm.Pgbelonging.objects.filter(
                pgroup = obj).values_list('assignsites', flat = True)
            ic(sites)
            cxt = {'sitegrpform': self.params['form_class'](request = request, instance = obj),
                   'assignedsites': sites}
            resp = render(request, self.params['template_form'], context = cxt)
            return resp

        

    def post(self, request, *args, **kwargs):
        import json
        data = QueryDict(request.POST['formData'])
        assignedSites = json.loads(request.POST['assignedSites'])
        pk = data.get('pk', None)
        ic(data)
        try:
            if pk not in [None, 'None']:
                msg = "pgroup_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs = {'request':request})
                create= False
            else:
                form = self.params['form_class'](data, request = request)

            if form.is_valid():
                resp = self.handle_valid_form(form, assignedSites, request)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)    
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, assignedSites, request):
        logger.info('pgroup form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            with transaction.atomic(using = utils.get_current_db_name()):
                pg = form.save(commit = False)
                putils.save_userinfo(pg, request.user, request.session)
                self.save_assignedSites(pg, assignedSites, request)
                logger.info("people group form saved")
                data = {'success': "Record has been saved successfully",
                        'pk': pg.pk, 'row':model_to_dict(pg)}
                return rp.JsonResponse(data, status = 200)
        except IntegrityError:
            return handle_intergrity_error("Pgroup")

    @staticmethod
    def resest_assignedsites(pg):
        pm.Pgbelonging.objects.filter(pgroup_id=pg.id).delete()
        ic('reset successfully')

    def save_assignedSites(self, pg, sitesArray, request):
        S = request.session
        self.resest_assignedsites(pg)
        for site in sitesArray:
            pgb = pm.Pgbelonging(
                pgroup         = pg,
                people_id      = 1,
                assignsites_id = site['buid'],
                client_id      = S['client_id'],
                bu_id          = S['bu_id'],
                tenant_id      = S.get('tenantid', 1)
            )
            putils.save_userinfo(pgb, request.user, request.session)



class NoSite(View):
    def get(self, request):
        
        cxt = {'nositeform':pf.NoSiteForm(session=request.session)}
        return render(request, 'peoples/nosite.html', cxt)
    
    def post(self, request):
        form = pf.NoSiteForm(request.POST, session=request.session)
        if form.is_valid():
            ic(request.session['bu_id'])
            bu_id = form.cleaned_data['site']
            request.session['bu_id'] = bu_id
            pm.People.objects.filter(id=request.user.id).update(bu_id=bu_id)
            ic(request.session['bu_id'])
            return redirect('/dashboard')


def verifyemail(request):
    logger.info('verify email requested for user id %s', request.GET.get('userid'))
    user = People.objects.get(id = request.GET.get('userid'))
    try:
        send_email(user)
        messages.success(request, 'Verification email has been sent to your email address','alert alert-success')
        logger.info("message sent to %s", user.email)
    except Exception as e:
        messages.error(request, 'Unable to send verification email', 'alert alert-danger')
        logger.error("email verification failed", exc_info=True)
    return redirect('login')