from django.http.request import QueryDict
from django.urls.base import reverse
from icecream import ic
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import EmptyResultSet
from django.http import response as rp
from django.template.loader import render_to_string
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
from django.core import serializers as ss
from apps.onboarding.models import TypeAssist
from apps.peoples.filters import CapabilityFilter
import apps.peoples.forms as pf  # people forms
import apps.peoples.models as pm  # people models
import apps.onboarding.forms as obf  # onboarding-modes
from django.contrib import messages
from django.db.models import RestrictedError
from .models import Capability, Pgroup, People
from .utils import save_userinfo, save_pgroupbelonging
import apps.peoples.utils as putils
from .forms import CapabilityForm, PgroupForm, PeopleForm, PeopleExtrasForm, LoginForm
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

    def get(self, request, *args, **kwargs):
        logger.info('SignIn View')
        request.session.set_test_cookie()
        form = LoginForm()
        return render(request, self.template_path, context={'loginform': form})

    def post(self, request, *args, **kwargs):
        from .utils import save_user_session, display_user_session_info
        form, response = LoginForm(request.POST), None
        logger.info('form submitted')
        try:
            if not request.session.test_cookie_worked():
                logger.warn(
                    'cookies are not enabled in user browser', exc_info=True)
                form.add_error(None, self.error_msgs['invalid-cookies'])
                cxt = {'loginform': form}
                response = render(request, self.template_path, context=cxt)
            elif form.is_valid():
                logger.info('Signin form is valid')
                loginid = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                people = authenticate(
                    request, username=loginid, password=password)
                if people:
                    login(request, people)
                    save_user_session(request, request.user)
                    display_user_session_info(request.session)
                    logger.info("User logged in {}".format(
                        request.user.peoplecode))
                    response = redirect('/dashboard') if not request.session.get(
                        'wizard_data') else redirect('onboarding:wizard_delete')
                else:
                    logger.warn(
                        self.error_msgs['auth-error'] % (loginid, '********'))
                    form.add_error(
                        None, self.error_msgs['invalid-details'])
                    cxt = {'loginform': form}
                    response = render(
                        request, self.template_path, context=cxt)
            else:
                logger.warn(self.error_msgs['invalid-form'])
                cxt = {'loginform': form}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(self.error_msgs['critical-error'], exc_info=True)
            form.add_error(None, self.error_msgs['critical-error'])
            cxt = {'loginform': form}
            response = render(request, self.template_path, context=cxt)
        return response


class SignOut(View):
    def get(self, request, *args, **kwargs):
        response = None
        try:
            logout(request)
            logger.info("User logged out DONE!")
            response = redirect("/")
        except Exception:
            logger.error('unable to log out user', exc_info=True)
            messages.warning(request, 'Unable to log out user...',
                             'alert alert-danger')
            response = redirect('/dashboard')
        return response


class ChangePeoplePassword(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    def post(self, request, *args, **kwargs):
        from django.contrib.auth.forms import SetPasswordForm
        from django.http import JsonResponse
        id, response = request.POST.get('people'), None
        people = People.objects.get(id=id)
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
               'pref_form': self.jsonform(session=request.session),
               'ta_form': TypeAssistForm(auto_id=False)}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        logger.info('Create People form submiited')
        from .utils import save_jsonform, save_user_paswd
        from django_email_verification import send_email

        response = None
        peopleform = self.form_class(request.POST, request.FILES)
        peoplepref_form = self.jsonform(
            request.POST, session=request.session)  # a json form for json data
        try:
            if peoplepref_form.is_valid() and peopleform.is_valid():
                logger.info('People Form is valid')
                people = peopleform.save(commit=False)
                ic(dir(people))
                if save_jsonform(peoplepref_form, people):
                    people.save()
                    people = save_userinfo(
                        people, request.user, request.session)
                    people.peopleimg = request.FILES.get('peopleimg',
                                                         'master/people/blank.png')
                    save_user_paswd(people)
                    send_email(people, request)
                    logger.info('People Form saved... DONE')
                    messages.success(request, "Success record saved DONE!",
                                     "alert alert-success")
                    response = redirect('peoples:people_form')
            else:
                logger.info('Form is not valid')
                cxt = {'peopleform': peopleform,
                       'pref_form': peoplepref_form,
                       'edit': True, 'ta_form': obf.TypeAssistForm(auto_id=False)}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'peopleform': peopleform,
                   'pref_form': peoplepref_form,
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


class RetrievePeoples(LoginRequiredMixin, View):
    template_path = 'peoples/people_list.html'

    related = ['peopletype', 'siteid']
    fields = ['id', 'peoplecode', 'peoplename', 'peopletype__tacode', 'siteid__bucode',
              'isadmin']
    model = People

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve People view')
            objects = self.model.objects.select_related(*self.related
                                                        ).values(*self.fields)
            logger.info('People objects retrieved from db')
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboad')
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import PeopleFilter
        if request.GET:
            objects = PeopleFilter(request.GET, queryset=objects).qs
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
            people = self.model.objects.get(id=pk)
            logger.info('object retrieved {}'.format(people))
            form = self.form_class(instance=people)
            cxt = {'peopleform': form,
                   'pref_form': get_people_prefform(people, request.session),
                   'ta_form': obf.TypeAssistForm(auto_id=False),
                   'edit': True}
            response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:people_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:people_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('PeopleForm Form submitted')
        from .utils import save_jsonform
        try:
            pk, response = kwargs.get('pk'), None
            people = self.model.objects.get(id=pk)
            form = self.form_class(
                request.POST, request.FILES, instance=people)
            jsonform = self.json_form(request.POST, session=request.session)
            if form.is_valid() and jsonform.is_valid():
                logger.info('PeopleForm Form is valid')
                if save_jsonform(jsonform, people):
                    people = save_userinfo(
                        people, request.user, request.session)
                    people.peopleimg = request.FILES.get(
                        'peopleimg', 'master/people/blank.png')
                    people.save()
                    logger.info('PeopleForm Form saved')
                    messages.success(request, "Success record updated successfully!",
                                     "alert alert-success")
                    response = redirect('peoples:people_form')
            else:
                logger.info('Form is not valid')
                cxt = {'peopleform': form,
                       'pref_form': jsonform,
                       'edit': True,
                       'ta_form': obf.TypeAssistForm(auto_id=False)}
                response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'peopleform': form, 'pref_form': jsonform,
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'peopleform': form, 'pref_form': jsonform, 'edit': True,
                   'ta_form': obf.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


class DeletePeople(LoginRequiredMixin, View):
    template_path = 'peoples/people_form.html'
    form_class = PeopleForm
    json_form = PeopleExtrasForm
    model = People

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        from .utils import get_people_prefform
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                people = self.model.objects.get(id=pk)
                logger.info('deleting people %s ...' % people.peoplecode)
                form = self.form_class(instance=people)
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
                   'edit': True, 'ta_form': obf.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
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
        cxt = {'pgroup_form': self.form_class(request=request), }
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('Create Pgroup form submiited')
        form, response = self.form_class(request.POST, request=request), None
        try:
            if form.is_valid():
                logger.info('Pgroup Form is valid')
                pg = form.save(commit=False)
                pg.identifier, _ = TypeAssist.objects.get_or_create(
                    tacode="PEOPLE_GROUP",taname="People Group", defaults={'tacode':"NONE", "parent_id":1})
                pg.save()
                pg = save_userinfo(pg, request.user, request.session)
                save_pgroupbelonging(pg, request)
                logger.info('Pgroup Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('peoples:pgroup_form')
            else:
                logger.info('Form is not valid')
                cxt = {'pgroup_form': form, 'edit': True, }
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True, }
            response = render(request, self.template_path, context=cxt)
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
            logger.info('Pgroup objects retrieved from db')
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import PgroupFilter
        if request.GET:
            objects = PgroupFilter(request.GET, queryset=objects).qs
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
            pg = self.model.objects.get(id=pk)
            logger.info('object retrieved {}'.format(pg))
            peoples = pm.Pgbelonging.objects.filter(
                groupid=pg).values_list('peopleid', flat=True)
            print(f"peoples {peoples}")
            form = self.form_class(instance=pg, initial={
                                   'peoples': list(peoples)}, request=request)
            response = render(request, self.template_path,  context={
                'pgroup_form': form, 'edit': True})
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:pgroup_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:pgroup_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('PgroupForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            pg = self.model.objects.get(id=pk)
            form = self.form_class(request.POST, instance=pg, request=request)
            if form.is_valid():
                logger.info('PgroupForm Form is valid')
                pg = form.save(commit=False)
                pg = save_userinfo(pg, request.user, request.session)
                pg.save()
                save_pgroupbelonging(pg, request)
                logger.info('PgroupForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('peoples:pgroup_form')
            else:
                logger.info('Form is not valid')
                cxt = {'pgroup_form': form, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


class DeletePgroup(LoginRequiredMixin, View):
    form_class = PgroupForm
    template_path = 'peoples/pgroup_form.html'
    model = Pgroup

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                pg = self.model.objects.get(id=pk)
                form = self.form_class(instance=pg, request=request)
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
            logger.warn('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'pgroup_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
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
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Pgroup instance."""
        logger.info('Create Capability form submiited')
        form, response = self.form_class(request.POST), None
        try:
            if form.is_valid():
                logger.info('CapabilityForm Form is valid')
                cap = form.save(commit=False)
                cap.save()
                cap = save_userinfo(cap, request.user, request.session)
                logger.info('CapabilityForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('peoples:cap_form')
            else:
                logger.info('Form is not valid')
                cxt = {'cap_form': form, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
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
            logger.info('Capabilities objects retrieved from db')
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            logger.warning('empty objects retrieved', exc_info=True)
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
                           'alert alert-danger')
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info=True)
            messages.error(request, 'Something went wrong',
                           "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import CapabilityFilter
        if request.GET:
            objects = CapabilityFilter(request.GET, queryset=objects).qs
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
            cap = self.model.objects.get(id=pk)
            logger.info('object retrieved {}'.format(cap))
            form = self.form_class(instance=cap)
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path,  context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('peoples:cap_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('peoples:cap_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('CapabilityForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            cap = self.model.objects.get(id=pk)
            form = self.form_class(request.POST, instance=cap)
            if form.is_valid():
                logger.info('CapabilityForm Form is valid')
                cap = form.save(commit=False)
                cap = save_userinfo(cap, request.user, request.session)
                cap.save()
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('peoples:cap_form')
            else:
                logger.info('Form is not valid')
                cxt = {'cap_form': form, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


class DeleteCapability(LoginRequiredMixin, View):
    model = Capability
    template_path = 'peoples/capability_form.html'
    form_class = CapabilityForm

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        from django.db.models import RestrictedError
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                cap = self.model.objects.get(id=pk)
                form = self.form_class(instance=cap)
                cap.delete()
                logger.info('Capability object deleted')
                messages.info(request, 'Record deleted successfully',
                              'alert alert-success')
                response = redirect('peoples:cap_form')
        except self.model.DoesNotExist:
            logger.warn('Unable to delete, object does not exist')
            messages.error(request, 'Capability does not exist',
                           "alert alert-danger")
            response = redirect('peoples:cap_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies',
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(request, '[ERROR] Something went wrong',
                           "alert alert-danger")
            cxt = {'cap_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response

#=========================== End Capability View Classes ==============================#
def delete_master(request, params):
    pass




class Capability(View):
    params = {
    'form_class'    : pf.CapabilityForm,
    'template_form' : 'peoples/partials/partial_cap_form.html',
    'template_list' : 'peoples/capability.html',
    'partial_form'  : 'peoples/partials/partial_cap_form.html',
    'partial_list'  : 'peoples/partials/partial_cap_list.html',
    'related'       : ['parent'],
    'model'         : pm.Capability,
    'filter'        : CapabilityFilter,
    'fields'        : ['id', 'capscode', 'capsname',
                    'cfor', 'parent__capscode']}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # return cap_list data
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "cap_list", 'filt_name': "cap_filter"}
            self.params.update(d)
            lookup = {'enable': True}
            resp = putils.render_grid(request, self.params, "capability_view", lookup)
        
        # return cap_form empty
        elif R.get('action', None) == 'form':
            cxt = {'cap_form': self.params['form_class'](),
                 'msg': "create capability requested"}
            resp = putils.render_form(request, self.params, cxt)
        
        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = putils.render_form_for_delete(request, self.params, True)
        # return form with instance
        elif R.get('id', None):
            resp = putils.render_form_for_update(request, self.params, "cap_form")
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
                msg = "capability_view"
                form = putils.get_instance_for_update(data, self.params, msg, int(pk))
                print(form.data)
            else:
                form = self.params['form_class'](data)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = putils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = putils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request):
        logger.info('capability form is valid')
        import json
        cap = form.save()
        putils.save_userinfo(cap, request.user, request.session)
        logger.info("capability form saved")
        data = {'success': "Record has been saved successfully", 
        'code':cap.capscode, 'name':cap.capsname, 'cfor':cap.cfor, 
        'parent':cap.parent.capscode}
        return rp.JsonResponse(data, status=200)
