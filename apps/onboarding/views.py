from distutils.log import Log, error
import logging
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.http import Http404, HttpResponse, response as rp
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.utils import IntegrityError
from django.conf import settings
from icecream import ic
from django.core.exceptions import (EmptyResultSet)
from django.db.models import RestrictedError
from django.http.request import QueryDict
from pydantic import Json
from pytest import param
from .models import Shift, SitePeople, TypeAssist, Bt, GeofenceMaster
from apps.peoples.utils import  save_userinfo
import apps.onboarding.forms as obforms
import apps.peoples.utils as putils
from django.db import transaction
from apps.core import utils
from pprint import pformat
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
logger = logging.getLogger('django')


#-------------------- Begin Bt View Classes --------------------#

# create Bt instance.
class CreateBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = obforms.BtForm

    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('create bt view...')
        cxt = {'buform': self.form_class(),
               'ta_form': obforms.TypeAssistForm(auto_id=False)}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Bt instance."""
        logger.info('create bt form submiited for saving...')
        form, response = self.form_class(request.POST), None
        try:
            if form.is_valid():
                logger.info('BtForm Form is valid')
                bt = form.save(commit=False)
                bt.save()
                save_userinfo(bt, request.user, request.session)
                logger.info('BtForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('onboarding:bu_form')
            else:
                logger.info('BtForm Form is not valid')
                cxt = {'buform': form, 'edit': True,
                       'ta_form': obforms.TypeAssistForm(auto_id=False)}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


# list-out Bt data
class RetrieveBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_list.html'
    related = ['parent', 'identifier', 'butype']
    fields = ['id', 'bucode', 'buname', 'butree', 'identifier__tacode',
              'enable', 'parent__bucode', 'butype__tacode']
    model = Bt

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            if request.GET.get('template'): return render(request, self.template_path)
            if request.GET.get('action', None) == 'list':
                logger.info('Retrieve Bt view')
                objects = self.model.objects.select_related(
                    *self.related
                    ).values(*self.fields)
                logger.info(
                    f'Bt objects {len(objects)} retrieved from db'
                    if objects
                    else "No Records!"
                )

                cxt = self.paginate_results(request, objects)
                logger.info('Results paginated'if objects else "")
                response = rp.JsonResponse(data = {'data':list(objects)})
        except EmptyResultSet:
            response = redirect('/dashboard')
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
        logger.info('Pagination Start'if objects else "")
        from .filters import BtFilter
        if request.GET:
            objects = BtFilter(request.GET, queryset=objects).qs
        filterform = BtFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            bt_list = paginator.page(page)
        except PageNotAnInteger:
            bt_list = paginator.page(1)
        except EmptyPage:
            bt_list = paginator.page(paginator.num_pages)
        return {'bt_list': bt_list, 'bt_filter': filterform}


# update Bt instance
class UpdateBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = obforms.BtForm
    model = Bt

    def get(self, request, *args, **kwargs):
        response = None
        try:
            logger.info('Update Bt view')
            pk = kwargs.get('pk')
            bt = self.model.objects.get(id=pk)
            logger.info(f'object retrieved {bt}')
            form = self.form_class(instance=bt)
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            response = redirect('onboarding:bu_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert-danger')
            response = redirect('onboarding:bu_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('BtForm form submitted...')
        response = None
        try:
            pk = kwargs.get('pk')
            bt = self.model.objects.get(id=pk)
            form = self.form_class(request.POST, instance=bt)
            if form.is_valid():
                logger.info('BtForm Form is valid')
                bt = form.save()
                bt = save_userinfo(bt, request.user, request.session, create=False)
                logger.info('BtForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('onboarding:bu_form')
            else:
                logger.info('BtForm Form is not valid')
                response = render(request, self.template_path, context={
                                  'buform': form, 'edit': True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


# delete Bt instance
class DeleteBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = obforms.BtForm
    model = Bt

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                bt = self.model.objects.get(id=pk)
                form = self.form_class(instance=bt)
                bt.delete()
                logger.info('Bt object deleted')
                messages.info(request, 'Record deleted successfully',
                              'alert alert-success')
                response = redirect('onboarding:bu_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist',
                           "alert alert-danger")
            response = redirect('onboarding:bu_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'buform': form, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response

#-------------------- END Bt View Classes --------------------#


# #-------------------- Begin Shift View Classes --------------------#
class CreateShift(LoginRequiredMixin, View):
    template_path = 'onboarding/shift_form.html'
    form_class = obforms.ShiftForm

    def get(self, request, *args, **kwargs):
        """Returns shift form on html"""
        logger.info('create shift view...')
        cxt = {'shift_form': self.form_class()}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of shift instance."""
        logger.info('create shift form submiited for saving...')
        response, form = None, self.form_class(request.POST)
        try:
            print("form data", form.data)
            if form.is_valid():
                logger.info('ShiftForm Form is valid')
                shift = form.save()
                shift.bu_id = int(request.session['client_id'])
                save_userinfo(shift, request.user, request.session)
                logger.info('ShiftForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('onboarding:shift_form')
            else:
                logger.info('Form is not valid')
                cxt = {'shift_form': form, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'shift_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


# @method_decorator(cache_page(CACHE_TTL), name='dispatch')
class RetrieveShift(LoginRequiredMixin, View):
    template_path = 'onboarding/shift_list.html'
    fields = ['id', 'shiftname', 'starttime', 'endtime']
    model = Shift

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            objects = self.model.objects.select_related(*self.related
                                                        ).values(*self.fields)
            logger.info(
                f'Shift objects {len(objects)} retrieved from db'
                if objects
                else "No Records!"
            )

            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
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
        logger.info('Pagination Start'if objects else "")
        from .filters import ShiftFlter
        if request.GET:
            objects = ShiftFlter(request.GET, queryset=objects).qs
        filterform = ShiftFlter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            ta_list = paginator.page(page)
        except PageNotAnInteger:
            ta_list = paginator.page(1)
        except EmptyPage:
            ta_list = paginator.page(paginator.num_pages)
        return {'ta_list': ta_list, 'ta_filter': filterform}


class UpdateShift(LoginRequiredMixin, View):
    template_path = 'onboarding/shift_form.html'
    form_class = obforms.ShiftForm
    model = Shift

    def get(self, request, *args, **kwargs):
        response = None
        try:
            logger.info('Update shift view')
            pk = kwargs.get('pk')
            shift = self.model.objects.select_related().get(id=pk)
            logger.info(f'object retrieved {shift}')
            form = self.form_class(instance=shift)
            response = render(request, self.template_path,  context={
                              'shift_form': form, 'edit': True})
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('onboarding:shift_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('onboarding:shift_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('Shift Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            shift = self.model.objects.select_related().get(id=pk)
            form = self.form_class(request.POST, instance=shift)
            if form.is_valid():
                logger.info('ShiftForm form is valid..')
                shift = form.save()
                shift.bu_id = int(request.session['client_id'])
                shift = save_userinfo(shift, request.user, request.session, create=False)
                logger.info('ShiftForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert-success")
                response = redirect('onboarding:shift_form')
            else:
                logger.info('form is not valid...')
                response = render(request, self.template_path,
                                  context={'shift_form': form, 'edit': True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'shift_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'shift_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


class DeleteShift(LoginRequiredMixin, View):
    form_class = obforms.ShiftForm
    template_path = 'onboarding/shift_form.html'
    model = Shift

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        ic(pk)
        try:
            if pk:
                shift = self.model.objects.get(id=pk)
                form = self.form_class(instance=shift)
                shift.delete()
                logger.info('Shift object deleted')
                response = redirect('onboarding:shift_form')
        except self.model.DoesNotExist:
            logger.warn('Unable to delete, object does not exist')
            messages.error(request, 'Shift does not exist',
                           "alert alert-danger")
            response = redirect('onboarding:shift_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'shift_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'shift_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response
# #-------------------- END Shift View Classes --------------------#


#-------------------- Begin SitePeople View Classes --------------------#

class CreateSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/sitepeople_form.html'
    form_class = obforms.SitePeopleForm

    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('Create SitePeople view')
        cxt = {'sitepeople_form': self.form_class()}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of Bt instance."""
        logger.info('Create SitePeople form submiited')
        response, form = None, self.form_class(request.POST)
        try:
            if form.is_valid():
                logger.info('SitePeopleForm Form is valid')
                sp = form.save()
                save_userinfo(sp, request.user, request.session)
                logger.info('SitePeopleForm Form saved')
                messages.success(
                    request, "Success record saved successfully!", "alert-success")
                response = redirect('onboarding:sitepeople_form')
            else:
                logger.info('SitePeopleForm is not valid')
                cxt = {'sitepeople_form': form, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                'something went wrong please follow the traceback to fix it... ', exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'sitepeople_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


# list-out Bt data
class RetrieveSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/sitepeople_list.html'
    related = ['parent', 'identifier', 'butype']
    fields = ['id', 'bucode', 'buname', 'identifier',
              'enable', 'parent__bucode', 'butype']
    model = SitePeople

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve SitePeoples view')
            objects = self.model.objects.select_related(*self.related
                                                        ).values(*self.fields)
            logger.info(
                f'SitePeople objects {len(objects)} retrieved from db'
                if objects
                else "No Records!"
            )

            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboard')
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
        logger.info('Pagination Start'if objects else "")
        from .filters import BtFilter
        if request.GET:
            objects = BtFilter(request.GET, queryset=objects).qs
        filterform = BtFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            bt_list = paginator.page(page)
        except PageNotAnInteger:
            bt_list = paginator.page(1)
        except EmptyPage:
            bt_list = paginator.page(paginator.num_pages)
        return {'sitepeople_list': bt_list, 'sitepeople_filter': filterform}


# update Bt instance
class UpdateSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = obforms.SitePeopleForm
    model = SitePeople

    def get(self, request, *args, **kwargs):
        logger.info('Update SitePeople view')
        response = None
        try:
            pk = kwargs.get('pk')
            sp = self.model.objects.get(id=pk)
            logger.info(f'object retrieved {sp}')
            form = self.form_class(instance=sp)
            response = render(request, self.template_path, context={
                              'sitepeople_form': form, 'edit': True})
        except self.model.DoesNotExist:
            response = redirect('onboarding:sitepeople_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('onboarding:sitepeople_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('SitePeopleForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            sp = self.model.objects.get(id=pk)
            form = self.form_class(request.POST, instance=sp)
            if form.is_valid():
                logger.info('SitePeopleForm Form is valid')
                sp = form.save()
                sp = save_userinfo(sp, request.user, request.session, create=False)
                logger.info('SitePeopleForm Form saved')
                messages.success(
                    request, "Success record saved successfully!", "alert-success")
                response = redirect('onboarding:sitepeople_form')
            else:
                logger.info('SitePeopleForm is not valid')
                response = render(request, self.template_path, context={
                                  'sitepeople_form': form, 'edit': True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'sitepeople_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'sitepeople_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


# delete Bt instance
class DeleteSitePeople(LoginRequiredMixin, View):
    model = SitePeople
    form_class = obforms.SitePeopleForm
    model = SitePeople

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                sp = self.model.objects.get(id=pk)
                form = self.form_class(instance=sp)
                sp.delete()
                logger.info('SitePeople object deleted')
                messages.info(request, 'Record deleted successfully',
                              'alert alert-success')
                response = redirect('onboarding:sitepeople_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist',
                           "alert alert-danger")
            response = redirect('onboarding:sitepeople_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies',
                           "alert alert-danger")
            cxt = {'sitepeople_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'sitepeople_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response


#-------------------- END SitePeople View Classes --------------------#

#-------------------- Begin Client View Classes --------------------#

class CreateClient(LoginRequiredMixin, View):
    form_class = obforms.BtForm
    json_form = obforms.ClentForm
    template_path = 'onboarding/client_buform.html'
    model = Bt

    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('Create ClientBt view')

        cxt = {'clientform': self.form_class(client=True),
               'clientprefsform': self.json_form(),
               'ta_form': obforms.TypeAssistForm(auto_id=False)
               }
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        from .utils import save_json_from_bu_prefsform, get_or_create_none_bv
        logger.info('Create ClientBt form submiited')
        response = None
        form = self.form_class(request.POST)
        jsonform = self.json_form(request.POST)
        try:
            if form.is_valid() and jsonform.is_valid():
                logger.info('ClientBt Form is valid')
                from .utils import (save_json_from_bu_prefsform, create_tenant,
                                    create_default_admin_for_client)
                bt = form.save(commit=False)
                bt.parent = get_or_create_none_bv()
                if save_json_from_bu_prefsform(bt, jsonform):
                    create_tenant(bt.buname, bt.bucode)
                    # create_default_admin_for_client(bt)
                    bt.save()
                    bt = save_userinfo(bt, request.user, request.session)
                    logger.info('ClientBt Form saved')
                    messages.success(
                        request, "Success record saved successfully!", "alert-success")
                    response = redirect('onboarding:client_form')
            else:
                ic(form.errors, jsonform.errors)
                logger.info('ClientBt Form is not valid')
                cxt = {'clientform': form, 'clientprefsform': jsonform, 'edit': True,
                       'ta_form': obforms.TypeAssistForm(auto_id=False)}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'clientform': form, 'clientprefsform': jsonform, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


def get_caps(request):  # sourcery skip: extract-method
    logger.info('get_caps requested')
    selected_parents = request.GET.getlist('webparents[]')
    logger.info(f'selected_parents {selected_parents}')
    cfor = request.GET.get('cfor')
    logger.info(f'cfor {cfor}')
    if selected_parents:
        from apps.peoples.models import Capability
        from django.http import JsonResponse
        import json
        childs = []
        for i in selected_parents:
            child = Capability.objects.get_child_data(i, cfor)
            childs.extend({'capscode': j.capscode} for j in child)
        logger.info(f'childs = [] {childs}')
        return JsonResponse(data=childs, safe=False)


class RetriveClients(LoginRequiredMixin, View):
    template_path = 'onboarding/client_bulist.html'
    fields = ['id', 'bucode', 'buname', 'enable', 'bu_preferences__webcapability',
              'bu_preferences__mobilecapability', 'bu_preferences__reportcapability']
    model = Bt

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Client view')
            objects = self.model.objects.values(*self.fields)
            logger.info(
                f'Cleint objects {len(objects)} retrieved from db'
                if objects
                else "No Records!"
            )

            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated'if objects else "")
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboad')
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
        logger.info('Pagination Start'if objects else "")
        from .filters import ClientFiler
        if request.GET:
            objects = ClientFiler(request.GET, queryset=objects).qs
        filterform = ClientFiler().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            client_list = paginator.page(page)
        except PageNotAnInteger:
            client_list = paginator.page(1)
        except EmptyPage:
            client_list = paginator.page(paginator.num_pages)
        return {'client_list': client_list, 'client_filter': filterform}


class UpdateClient(LoginRequiredMixin, View):
    template_path = 'onboarding/client_buform.html'
    form_class = obforms.BtForm
    json_form = obforms.ClentForm
    model = Bt

    def get(self, request, *args, **kwargs):
        logger.info('Update Bt view')
        response = None
        try:
            from .utils import get_bt_prefform
            pk = kwargs.get('pk')
            bt = self.model.objects.select_related('butype').get(id=pk)
            logger.info(f'object retrieved {bt}')
            form = self.form_class(instance=bt)
            cxt = {'clientform': form, 'clientprefsform': get_bt_prefform(bt), 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('onboarding:client_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('onboarding:client_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('ClientForm Form submitted')
        from .utils import save_json_from_bu_prefsform, create_tenant
        pk, response = kwargs.get('pk'), None
        client = self.model.objects.get(id=pk)
        form = self.form_class(request.POST, instance=client)
        jsonform = self.json_form(request.POST)
        try:
            if form.is_valid() and jsonform.is_valid():
                logger.info('ClientForm Form is valid')
                create_tenant(form.data['buname'], form.data['bucode'])
                client = form.save(commit=False)
                if save_json_from_bu_prefsform(client, jsonform):
                    client.save()
                    client = save_userinfo(
                        client, request.user, request.session, create=False)
                    logger.info('ClientForm Form saved')
                    messages.success(request, "Success record saved successfully!",
                                     "alert alert-success")
                    response = redirect('onboarding:client_form')
            else:
                logger.warn('ClientForm is not valid\n Following are the form errors: %s\n%s' % (
                    form.errors, jsonform.errors))
                cxt = {'clientform': form,
                       'clientprefsform': jsonform, 'edit': True}
                response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'clientform': form, 'clientprefsform': jsonform, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical(
                "something went wrong please follow the traceback to fix it... ", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
                           "alert alert-danger")
            cxt = {'clientform': form, 'clientprefsform': jsonform, 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


class DeleteClient(LoginRequiredMixin, View):
    model = Bt
    template_path = 'onboarding/client_buform.html'
    form_class = obforms.BtForm
    json_form = obforms.ClentForm

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        from django.db import models
        from .utils import get_bt_prefform
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                bt = self.model.objects.get(id=pk)
                form = self.form_class(instance=bt)
                bt.delete()
                logger.info('Client object deleted...')
                messages.info(request, 'Record deleted successfully',
                              'alert alert-success')
                response = redirect('onboarding:client_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist',
                           "alert alert-danger")
            response = redirect('onboarding:client_form')
        except models.RestrictedError:
            logger.error('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'clientform': form, 'clientprefsform': get_bt_prefform(bt), 'edit': True,
                   'ta_form': obforms.TypeAssistForm(auto_id=False)}
            response = render(request, self.template_path, context=cxt)
        return response


def handle_pop_forms(request):
    if request.method != 'POST':
        return

    form_name = request.POST.get('form_name')
    form_dict = {
        'ta_form': obforms.TypeAssistForm,
    }
    form = form_dict[form_name](request.POST)
    ic(request.POST)
    if not form.is_valid():
        ic(form.errors)
        return JsonResponse({'saved': False, 'errors': form.errors})
    ta = form.save(commit=False)
    t = TypeAssist.objects.filter(tacode=ta.tacode)
    ta = t[0] if len(t) else form.save(commit=True)
    save_userinfo(ta, request.user, request.session)
    if request.session.get('wizard_data'):
        request.session['wizard_data']['taids'].append(ta.id)
        print(ta.id)
    return JsonResponse({'saved': True, 'id': ta.id, 'tacode': ta.tacode})


#-------------------- END Client View Classes ------------------------------#


#---------------------------- END client onboarding   ---------------------------#


@method_decorator(cache_page(40), name='dispatch')
class MasterTypeAssist(LoginRequiredMixin, View):
    from .filters import TypeAssistFilter
    params = {
        'form_class': '',
        'template_form': 'onboarding/partials/partial_ta_form.html',
        'template_list': 'onboarding/typeassist.html',
        'partial_form': 'onboarding/partials/partial_ta_form.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': TypeAssist,
        'filter': TypeAssistFilter,
        'fields': ['id', 'tacode',
              'taname', 'tatype__tacode', 'cuser__peoplecode'],
        'form_initials': {} }
    lookup = {}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        ic(R)
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])
        #then load the table with objects for table_view
        if R.get('action') == 'list':
            objs = self.params['model'].objects.select_related(
                 *self.params['related']).filter(
                     ~Q(tacode='NONE'),  **self.lookup
             ).values(*self.params['fields'])
            return  rp.JsonResponse(data = {'data':list(objs)})

        elif R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create typeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, False)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp , create= None, True
        R = request.POST
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "typeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                print(form.data)
                create=False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('typeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(ta, request.user, request.session, create=create)
            logger.info("typeassist form saved")
            data = {'msg': f"{ta.tacode}",
            'row': TypeAssist.objects.values(*self.params['fields']).get(id=ta.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("TypeAssist")



class SuperTypeAssist(MasterTypeAssist):
    params = MasterTypeAssist.params
    lookup = MasterTypeAssist.lookup
    lookup = {'cuser__peoplecode':'SUPERADMIN'}
    params.update({'form_class':obforms.SuperTypeAssistForm})

class TypeAssistAjax(MasterTypeAssist):
    params = MasterTypeAssist.params
    params.update({'form_class':obforms.TypeAssistForm})
    pass


class Shift(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.ShiftForm,
        'template_form': 'onboarding/partials/partial_shiftform.html',
        'template_list': 'onboarding/shift.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': Shift,
        'fields': ['id', 'shiftname', 'starttime', 'endtime', 'nightshiftappicable'],
        'form_initials': {} }

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])
        #then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    enable=True,
            ).values(*self.params['fields'])
            count = objs.count()
            logger.info(f'Shift objects {count or "No Records!"} retrieved from db')
            if count:
                objects, filtered = utils.get_paginated_results(
                    R, objs, count, self.params['fields'], self.params['related'], self.params['model'])
                logger.info('Results paginated'if count else "")

            resp = rp.JsonResponse(data = {
                'draw':R['draw'], 'recordsTotal':count,
                'data' : list(objects), 
                'recordsFiltered': filtered
            }, status=200, safe=False)

        elif R.get('action', None) == 'form':
            cxt = {'shift_form': self.params['form_class'](request=request),
                   'msg': "create shift requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, False)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "shift_form", obj)
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
                msg = "shift_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                create=False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error("SHIFT saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('shift form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            shift = form.save()
            shift.bu_id = int(request.session['client_id'])
            putils.save_userinfo(shift, request.user, request.session, create=create)
            logger.info("shift form saved")
            data = {'msg': f"{shift.shiftname}",
            'row': Shift.objects.values(*self.params['fields']).get(id=shift.id) }
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Shift")



class EditorTa(LoginRequiredMixin, View):
    template = 'onboarding/testEditorTa.html'
    fields = ['id', 'tacode', 'taname', 'tatype__tacode', 'cuser__peoplecode']
    model = TypeAssist
    related = ['cuser', 'tatype']

    def get(self, request, *args, **kwargs):
        R = request.GET
        if R.get('template'): return render(request, self.template)
    def post(self, request, *args, **kwargs):
        R = request.POST
        ic(pformat(request.POST, compact=True))
        objs = self.model.objects.select_related(
                *self.related).filter(
            ).values(*self.fields)
        count = objs.count()
        logger.info(f'Shift objects {count or "No Records!"} retrieved from db')
        if count:
            objects, filtered = utils.get_paginated_results(
                R, objs, count, self.fields, self.related, self.model)
            logger.info('Results paginated'if count else "")
        return JsonResponse(
            data = {
            'draw':R['draw'], 'recordsTotal':count,
            'data' : list(objects), 
            'recordsFiltered': filtered}, status = 200
        )



class GeoFence(LoginRequiredMixin, View):
    params = {
        'form_class':obforms.GeoFenceForm,
        'template_list':'onboarding/geofence_list.html',
        'template_form':'onboarding/geofence_form.html',
        'fields': ['id', 'gfcode',
              'gfname', 'alerttogroup__groupname', 'alerttopeople__peoplename'],
        'related':['alerttogroup', 'alerttopeople'],
        'model':GeofenceMaster
    }

    def get(self, request, *args, **kwargs):
        R = request.GET
        params = self.params
        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])

        #then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_geofence_list(params['fields'], params['related'], request.session)
            return  rp.JsonResponse(data = {'data':list(objs)})

        elif R.get('action', None) == 'form':
            cxt = {'geofenceform':self.params['form_class']()}
            return render(request, self.params['template_form'], context=cxt)

        elif R.get('action') == 'drawgeofence':
            return get_geofence_from_point_radii(R)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'geofenceform':self.params['form_class'](request=request, instance=obj),
                    'edit':True,
                'geofencejson': GeofenceMaster.objects.get_geofence_json(pk=obj.id)}
            return render(request, self.params['template_form'], context=cxt)


    def post(self, request, *args, **kwargs):
        resp=None
        try:
            data = QueryDict(request.POST['formData'])
            geofence = request.POST['geofence']
            ic('geofence form data', data)
            ic(geofence)
            if pk := request.POST.get('pk', None):
                msg = "geofence_view"
                form = utils.get_instance_for_update(
                data, self.params, msg, int(pk))
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, geofence)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error('GEOFENCE saving error!', exc_info=True)
            resp = utils.handle_Exception(request)
        return resp


    def handle_valid_form(self, form, request, geofence):
        logger.info('geofence form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                gf = form.save()
                self.save_geofence_field(gf, geofence)
                gf = putils.save_userinfo(gf, request.user, request.session)
                logger.info("geofence form saved")
                return JsonResponse(data={'pk':gf.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("GeoFence")


    def save_geofence_field(self, gf, geofence):
        try:
            from django.contrib.gis.geos import LinearRing, Polygon
            import json
            geofencedata = json.loads(geofence)
            ic(geofencedata)
            ic(type(geofencedata))
            coords = [(i['lng'], i['lat']) for i in geofencedata]
            ic(coords)
            pg = Polygon(LinearRing(coords, srid=4326), srid=4326)
            gf.geofence = pg
            gf.save()
        except Exception:
            logger.error('geofence polygon field saving error', exc_info=True)
            raise



def get_geofence_from_point_radii(R):
    try:
        lat, lng, radii = R.get('lat'), R.get('lng'), R.get('radii')
        if all([lat, lng, radii]):
            from django.contrib.gis import geos
            point = geos.Point(float(lng),float(lat), srid=4326)
            point.transform(3857)
            geofence = point.buffer(int(radii))
            geofence.transform(4326)
            return rp.JsonResponse(data={'geojson':utils.getformatedjson(geofence)}, status=200)
        else:
            return rp.JsonResponse(data={'errors':"Invalid data provided unable to compute geofence!"}, status=404)
    except Exception:
        logger.error("something went wrong while computing geofence..", exc_info=True)
        return rp.JsonResponse(data={'errors':'something went wrong while computing geofence!'}, status=404)



class ImportFile(LoginRequiredMixin, View):
    params = {
       'template_form':'onboarding/',
       'form_class':obforms.ImportForm
    }

    def get(self, request, *args, **kwargs):
        R = request.GET
        match(R.get('model')):
            case "typeassist":
                return render(request, f"{self.params['template_form']}/ta_imp_exp.html")


    def post(self, request, *args, **kwargs):
        from tablib import Dataset
        from .admin import TaResource
        import json
        #utils.set_db_for_router('testDB2')
        ic(request.POST)
        form = obforms.ImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['importfile']
            default_types = Dataset().load(file)
            res = TaResource(is_superuser=True)
            res = res.import_data(
                dataset=default_types, dry_run=False, raise_errors=False,
                collect_failed_rows=True, use_transactions=False)
            columns = json.dumps(columns)
            data = []
            for rowerr in res.row_errors():
                for err in rowerr[1]:
                    d = dict(err.row).update({'rowno':rowerr[0]})
                    data.append(d)
            data = json.dumps(data)
            cxt = {'columns':columns, 'data':data, 'importform':self.params['form_class']()}
            return render(request, self.params['template_form'], context=cxt)


        else:
            ic(form.errors)
