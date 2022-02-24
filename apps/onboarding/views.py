import logging
from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.http import response as rp
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.utils import IntegrityError
from django.conf import settings
from icecream import ic
from django.core.exceptions import (EmptyResultSet)
from django.db.models import RestrictedError
from django.http.request import QueryDict
from django.core import serializers
from django.urls import resolve
from .models import Shift, SitePeople, TypeAssist, Bt
from apps.peoples.utils import  save_userinfo
import apps.onboarding.forms as obforms
import apps.peoples.utils as putils
from apps.core import utils

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
logger = logging.getLogger('django')

#-------------------- Begin TypeAssist View Classes --------------------#


class CreateTypeassist(LoginRequiredMixin, View):
    template_path = 'onboarding/ta_form.html'
    template_path2 = 'onboarding/super_ta.html'
    form_class = obforms.TypeAssistForm
    form_class2 = obforms.SuperTypeAssistForm

    def get(self, request, *args, **kwargs):
        """Returns typeassist form on html"""
        logger.info('create typeassist view...')
        urlname = resolve(request.path_info).url_name
        logger.info(f"url {urlname}")

        if 'super' in urlname:
            cxt = {'superta_form': self.form_class2()}
            return render(request, self.template_path2, context=cxt)
        else:
            cxt = {'ta_form': self.form_class()}
            return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of typeassist instance."""
        logger.info('create typeassist form submiited for saving...')
        urlname = resolve(request.path_info).url_name
        taform = self.form_class2 if 'super' in urlname else self.form_class
        response, form = None, taform(request.POST)
        try:
            if form.is_valid():
                super = 'super' in urlname
                response = self.handle_valid_form(form, request, super)
            else:
                logger.info('Form is not valid')
                cxt = {'ta_form': form, 'edit': True}
                temp = self.template_path
                if 'super' in urlname:
                    cxt = {'superta_form': form, 'edit': True}
                    temp = self.template_path2
                response = render(request, temp, context=cxt)
        except Exception:
            response = self.handle_exception(request, form, urlname)
        return response

    def handle_valid_form(self, form, request, super=False):
        logger.info('TypeAssistForm Form is valid')
        ta = form.save(commit=False)
        ta.save()
        save_userinfo(ta, request.user, request.session)
        logger.info('TypeAssistForm Form saved')
        messages.success(request, "Success record saved successfully!",
                         "alert alert-success")
        if super:
            return redirect('onboarding:superta_form')
        return redirect('onboarding:ta_form')

    def handle_exception(self, request, form, url):
        logger.critical(
            "something went wrong please follow the traceback to fix it... ", exc_info=True)
        messages.error(request, "[ERROR] Something went wrong",
                       "alert alert-danger")
        cxt = {'ta_form': form, 'edit': True}
        temp = self.template_path
        if 'super' in url:
            cxt = {'superta_form': form, 'edit': True}
            temp = self.template_path2
        return render(request, temp, context=cxt)


# @method_decorator(cache_page(CACHE_TTL), name='dispatch')
class RetrieveTypeassists(LoginRequiredMixin, View):
    template_path = 'onboarding/ta_list.html'
    related = ['parent', 'id', 'cuser', 'muser']
    fields = ['id', 'tatype__tacode', 'tacode',
              'taname', 'cuser__peoplecode']
    model = TypeAssist

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            objects = self.model.objects.select_related(
                *self.related).filter(~Q(tacode='NONE')).values(*self.fields)
            logger.info('TypeAssist objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
            cxt = self.paginate_results(request, objects)
            logger.info('Results paginated' if objects else "")
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
        logger.info('Pagination Start' if objects else "")
        from .filters import TypeAssistFilter
        if request.GET:
            objects = TypeAssistFilter(request.GET, queryset=objects).qs
        filterform = TypeAssistFilter().form
        page = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            ta_list = paginator.page(page)
        except PageNotAnInteger:
            ta_list = paginator.page(1)
        except EmptyPage:
            ta_list = paginator.page(paginator.num_pages)
        url = resolve(request.path_info).url_name
        logger.info(f"url---------{url}-----")
        super = 'super' in url
        return {'ta_list': ta_list, 'ta_filter': filterform, 'superta': super}


def test_ta_grid(request):
    import math
    fields = ['id', 'tatype', 'parent__tacode', 'tacode',
              'taname', 'cuser__peoplecode']
    if request.method == 'POST':
        return
    page = request.GET.get('page')
    limit = request.GET.get('rows')
    sidx = request.GET.get('sidx', 1)
    sord = request.GET.get('sord')
    objects = TypeAssist.objects.select_related().values(*fields)
    count = objects.count()
    total_pages = math.ceil(count/int(limit)) if count else 0
    page = min(int(page), total_pages)
    start = int(limit) * page - int(limit)
    response = {'page': page, 'total': total_pages, 'records': count}
    rows = []
    for i in range(objects.count()):
        response.setdefault("rows", []).append(objects[i])
    return JsonResponse(response)


class UpdateTypeassist(LoginRequiredMixin, View):
    template_path = 'onboarding/ta_form.html'
    template_path2 = 'onboarding/super_ta.html'
    form_class = obforms.TypeAssistForm
    form_class2 = obforms.SuperTypeAssistForm
    model = TypeAssist

    def get(self, request, *args, **kwargs):
        response = None
        url = resolve(request.path_info).url_name
        try:
            logger.info('Update typeassist view')
            pk = kwargs.get('pk')
            ta = self.model.objects.select_related().get(id=pk)
            logger.info('object retrieved {}'.format(ta))
            cxt = {'ta_form': self.form_class(instance=ta), 'edit': True}
            response = render(request, self.template_path,  context=cxt)
            if 'super' in url:
                cxt = {'superta_form': self.form_class2(
                    instance=ta), 'edit': True}
                response = render(request, self.template_path2, context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
                           'alert alert-danger')
            response = redirect('onboarding:ta_form')
            if 'super' in url:
                response = redirect('onboarding:superta_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
                           'alert alert-danger')
            response = redirect('onboarding:ta_form')
            if 'super' in url:
                response = redirect('onboarding:superta_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('TypeAssistForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            ta = self.model.objects.select_related().get(id=pk)
            url = resolve(request.path_info).url_name
            taform = self.form_class2 if 'super' in url else self.form_class
            form = taform(request.POST, instance=ta)
            if form.is_valid():
                super = 'super' in url
                response = self.handle_valid_form(form, request, super)
            else:
                logger.info('form is not valid...')
                response = render(request, self.template_path, context={
                                  'ta_form': form, 'edit': True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
                           "alert alert-danger")
            cxt = {'ta_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            response = self.handle_exception(request, form, url)
        return response

    def handle_valid_form(self, form, request, super=False):
        logger.info('TypeAssistForm form is valid..')
        ta = form.save()
        ta = save_userinfo(ta, request.user, request.session)
        logger.info('TypeAssistForm Form saved')
        messages.success(request, "Success record saved successfully!",
                         "alert-success")
        if super:
            return redirect('onboarding:superta_form')
        return redirect('onboarding:ta_form')

    def handle_exception(self, request, form, url):
        logger.critical(
            "something went wrong please follow the traceback to fix it... ", exc_info=True)
        messages.error(request, "[ERROR] Something went wrong",
                       "alert alert-danger")
        cxt = {'ta_form': form, 'edit': True}
        temp = self.template_path
        if 'super' in url:
            cxt = {'superta_form': form, 'edit': True}
            temp = self.template_path2
        return render(request, temp, context=cxt)


class DeleteTypeassist(LoginRequiredMixin, View):
    form_class = obforms.TypeAssistForm
    form_class2 = obforms.SuperTypeAssistForm
    template_path = 'onboarding/ta_form.html'
    template_path2 = 'onboarding/super_ta.html'
    model = TypeAssist

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        ic(pk)
        url = resolve(request.path_info).url_name
        try:
            if pk:
                ta = self.model.objects.get(id=pk)
                taform = self.form_class2 if 'super' in url else self.form_class
                form = taform(instance=ta)
                ta.delete()
                logger.info('TypeAssist object deleted')
                response = redirect('onboarding:ta_list')
        except self.model.DoesNotExist:
            logger.warn('Unable to delete, object does not exist')
            messages.error(request, 'TypeAssist does not exist',
                           "alert alert-danger")
            response = redirect('onboarding:ta_form')
            if 'super' in url:
                response = redirect('onboarding:superta_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(
                request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'ta_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
            if 'super' in url:
                response = redirect('onboarding:superta_form')
        except Exception:
            messages.error(
                request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'ta_form': form, 'edit': True}
            response = render(request, self.template_path, context=cxt)
        return response

#-------------------- END TypeAssist View Classes --------------------#


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
        ic(cxt['buform'].as_p().split('\n'))
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
            logger.info('Retrieve Bt view')
            objects = self.model.objects.select_related(*self.related
                                                        ).values(*self.fields)
            logger.info('Bt objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
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
            logger.info('object retrieved {}'.format(bt))
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
                bt = save_userinfo(bt, request.user, request.session)
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
            logger.info('Shift objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
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
            logger.info('object retrieved {}'.format(shift))
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
                shift = save_userinfo(shift, request.user, request.session)
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
            logger.info('SitePeople objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
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
            logger.info('object retrieved {}'.format(sp))
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
                sp = save_userinfo(sp, request.user, request.session)
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

class CreateClient(View):
    form_class = obforms.BtForm
    json_form = obforms.ClentForm
    template_path = 'onboarding/client_buform.html'
    model = Bt

    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('Create ClientBt view')

        cxt = {'clientform': self.form_class(),
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
    logger.info('selected_parents {}'.format(selected_parents))
    cfor = request.GET.get('cfor')
    logger.info('cfor {}'.format(cfor))
    if selected_parents:
        from apps.peoples.models import Capability
        from django.http import JsonResponse
        import json
        childs = []
        for i in selected_parents:
            child = Capability.objects.get_child_data(i, cfor)
            childs.extend({'capscode': j.capscode} for j in child)
        logger.info('childs = [] {}'.format(childs))
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
            logger.info('Cleint objects %s retrieved from db' %
                        (len(objects)) if objects else "No Records!")
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
            logger.info('object retrieved {}'.format(bt))
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
                        client, request.user, request.session)
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
    ta = form.save(commit=True) if not len(t) else t[0]
    save_userinfo(ta, request.user, request.session)
    if request.session.get('wizard_data'):
        request.session['wizard_data']['taids'].append(ta.id)
        print(ta.id)
    return JsonResponse({'saved': True, 'id': ta.id, 'tacode': ta.tacode})


#-------------------- END Client View Classes ------------------------------#


#---------------------------- END client onboarding   ---------------------------#



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
        'fields': ['id', 'tatype__tacode', 'tacode',
              'taname', 'cuser__peoplecode'],
        'form_initials': {} }
    lookup = {}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'): return render(request, self.params['template_list'])
        #then load the table with objects
        if R.get('action', None) == 'list' or R.get('search_term'):
            d = {'list': "ta_list", 'filt_name': "ta_filter"}
            self.params.update(d)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(tacode='NONE'),  **self.lookup
            ).values(*self.params['fields'])
            count = objs.count()
            logger.info('Typeassist objects %s retrieved from db' %(count or "No Records!"))
            if count:
                objects, filtered = utils.get_paginated_results(
                    R, objs, count, self.params['fields'], self.params['related'], self.params['model'])
                logger.info('Results paginated'if count else "")

            resp = rp.JsonResponse(data = {
                'draw':R['draw'], 'recordsTotal':count,
                'data' : list(objects), 
                'recordsFiltered': filtered
            }, status=200, safe=False)

        # return cap_form empty for creation
        elif R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create typeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        # handle delete request
        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, False)
        # return form with instance for update
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
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
                msg = "typeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk))
                print(form.data)
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request):
        logger.info('typeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(ta, request.user, request.session)
            logger.info("typeassist form saved")
            data = {'msg': f"{ta.tacode}", }
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