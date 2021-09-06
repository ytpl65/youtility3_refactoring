import logging
from django.db.models.expressions import RawSQL
from django.http import response
from django.shortcuts import  redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator , EmptyPage, PageNotAnInteger
from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.cache import cache_page
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings
from icecream import ic
from django.core.exceptions import (ValidationError, EmptyResultSet, 
ObjectDoesNotExist)
from django.db.models import RestrictedError

from .models import SitePeople, TypeAssist, Bt
from apps.peoples.utils import  save_userinfo
from .forms import  BtForm,  ClentForm, SitePeopleForm, TypeAssistForm

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
logger = logging.getLogger('django')

#-------------------- Begin TypeAssist View Classes --------------------#
class CreateTypeassist(LoginRequiredMixin, View):
    template_path = 'onboarding/ta_form.html'
    form_class = TypeAssistForm
    
    def get(self, request, *args, **kwargs):
        """Returns typeassist form on html"""
        logger.info('create typeassist view...')
        cxt = {'ta_form':self.form_class()}
        return render(request, self.template_path, context=cxt)

    def post(self, request, *args, **kwargs):
        """Handles creation of typeassist instance."""
        logger.info('create typeassist form submiited for saving...')
        response, form = None, self.form_class(request.POST)
        try:
            if form.is_valid():
                logger.info('TypeAssistForm Form is valid')
                ta = form.save(commit=False)
                ta = save_userinfo(ta, request.user, request.session)
                ta.save()
                logger.info('TypeAssistForm Form saved')
                messages.success(request, "Success record saved successfully!",
                                 "alert alert-success")
                response = redirect('onboarding:ta_form')
            else:
                logger.info('Form is not valid')
                cxt = {'ta_form':form, 'edit':True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
             "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response
        
            
#@method_decorator(cache_page(CACHE_TTL), name='dispatch')
class RetrieveTypeassists(LoginRequiredMixin, View):
    template_path = 'onboarding/ta_list.html'
    related       = ['parent', 'buid', 'cuser', 'muser']
    fields        = ['taid', 'tatype', 'parent__tacode','tacode', 'taname']
    model         = TypeAssist
    
    
    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            objects = self.model.objects.select_related(*self.related
            ).values(*self.fields)
            logger.info('TypeAssist objects retrieved from db')
            cxt   = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = render(request, self.template_path, context=cxt)
            messages.error(request, 'List view not found',
            'alert alert-danger')
        except Exception:
            logger.critical('something went wrong...', exc_info=True)
            messages.error(request, 'Something went wrong',
            "alert alert-danger")
            response = redirect('/dashboard')
        return response
        

    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import TypeAssistFilter
        if request.GET:
            objects = TypeAssistFilter(request.GET, queryset = objects).qs
        filterform = TypeAssistFilter().form
        page      = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            ta_list = paginator.page(page)
        except PageNotAnInteger:
            ta_list = paginator.page(1)
        except EmptyPage:
            ta_list = paginator.page(paginator.num_pages)
        cxt = {'ta_list':ta_list, 'ta_filter':filterform}
        return cxt


class UpdateTypeassist(LoginRequiredMixin,View):
    template_path = 'onboarding/ta_form.html'
    form_class = TypeAssistForm
    model = TypeAssist
    
    def get(self, request, *args, **kwargs):
        response = None
        try:
            logger.info('Update typeassist view')
            pk = kwargs.get('pk')
            ta = self.model.objects.select_related().get(taid=pk)
            logger.info('object retrieved {}'.format(ta))
            form = self.form_class(instance=ta)
            response = render(request, self.template_path,  context={'ta_form':form, 'edit':True})
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
            'alert alert-danger')
            response = redirect('onboarding:ta_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
            'alert alert-danger' )
            response = redirect('onboarding:ta_form')
        return response

    
    def post(self, request, *args, **kwargs):
        logger.info('TypeAssistForm Form submitted')
        response = None
        try:
            pk   = kwargs.get('pk')
            ta   = self.model.objects.select_related().get(taid=pk)
            form = self.form_class(request.POST, instance=ta)
            if form.is_valid():
                logger.info('TypeAssistForm form is valid..')
                ta = form.save(commit=False)
                ta = save_userinfo(ta, request.user, request.session)
                ta.save()
                logger.info('TypeAssistForm Form saved')
                messages.success(request, "Success record saved successfully!",
                 "alert-success")
                response = redirect('onboarding:ta_form')
            else:
                logger.info('form is not valid...')
                response = render(request, self.template_path, context={'ta_form':form, 'edit':True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
            "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
            "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response



class DeleteTypeassist(LoginRequiredMixin, View):
    form_class = TypeAssistForm
    template_path = 'onboarding/ta_form.html'
    model = TypeAssist

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        ic(pk)
        try:
            if pk:
                ta = self.model.objects.get(tacode=pk)
                form = self.form_class(instance = ta)
                ta.delete()
                logger.info('TypeAssist object deleted')
                response = redirect('onboarding:ta_list')
        except self.model.DoesNotExist:
            logger.warn('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist', "alert alert-danger")
            response = redirect('onboarding:ta_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response



#========================== Begin Bt View Classes ============================#

#create Bt instance.
class CreateBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = BtForm
    
    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('create bt view...')
        cxt = {'buform':self.form_class()}
        return render(request, self.template_path, context=cxt)
    
    def post(self, request, *args, **kwargs):
        """Handles creation of Bt instance."""
        logger.info('create bt form submiited for saving...')
        form, response = self.form_class(request.POST), None
        try:
            if form.is_valid():
                logger.info('BtForm Form is valid')
                bt = form.save(commit=False)
                bt = save_userinfo(bt, request.user, request.session)
                bt.save()
                logger.info('BtForm Form saved')
                messages.success(request, "Success record saved successfully!",
                 "alert-success")
                response = redirect('onboarding:bu_form')
            else:
                logger.info('BtForm Form is not valid')
                cxt = {'buform':form, 'edit':True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
             "alert alert-danger")
            cxt = {'buform':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


#list-out Bt data
class RetrieveBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_list.html'
    related = ['parent', 'identifier', 'butype']
    fields =  ['btid','bucode', 'buname', 'identifier__tacode',
             'enable', 'parent__bucode', 'butype__tacode']
    model = Bt
    
    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Bt view')
            objects = self.model.objects.select_related(*self.related
            ).values(*self.fields)
            logger.info('Bt objects retrieved from db')
            cxt   = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboard')
            messages.error(request, 'List view not found',
            'alert alert-danger')
        except Exception:
            logger.critical('something went wrong...', exc_info=True)
            messages.error(request, 'Something went wrong',
            "alert alert-danger")
            response = redirect('/dashboard')
        return response


    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import BtFilter
        if request.GET:
            objects = BtFilter(request.GET, queryset = objects).qs
        filterform = BtFilter().form
        page      = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            bt_list = paginator.page(page)
        except PageNotAnInteger:
            bt_list = paginator.page(1)
        except EmptyPage:
            bt_list = paginator.page(paginator.num_pages)
        cxt = {'bt_list':bt_list, 'bt_filter':filterform}
        return cxt

    

#update Bt instance
class UpdateBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = BtForm
    model = Bt

    def get(self, request, *args, **kwargs):
        response = None
        try:
            logger.info('Update Bt view')
            pk = kwargs.get('pk')
            bt = self.model.objects.get(btid=pk)
            logger.info('object retrieved {}'.format(bt))
            form = self.form_class(instance=bt)
            response = render(request, self.template_path, context={'buform':form, 'edit':True})
        except self.model.DoesNotExist:
            response = redirect('onboarding:bu_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
            'alert alert-danger' )
            response = redirect('onboarding:bu_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('BtForm form submitted...')
        response = None
        try:
            pk = kwargs.get('pk')
            bt = self.model.objects.get(btid=pk)
            form = self.form_class(request.POST, instance=bt)
            if form.is_valid():
                logger.info('BtForm Form is valid')
                bt = form.save(commit=False)
                bt = save_userinfo(bt, request.user, request.session)
                bt.save()
                logger.info('BtForm Form saved')
                messages.success(request, "Success record saved successfully!",
                 "alert-success")
                response = redirect('onboarding:bu_form')
            else:
                logger.info('BtForm Form is not valid')
                response = render(request, self.template_path, context={'buform':form, 'edit':True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info= True)
            messages.error(request, "Object does not exist",
            "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
            "alert alert-danger")
            cxt = {'ta_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


#delete Bt instance
class DeleteBt(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = BtForm
    model = Bt

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                bt = self.model.objects.get(btid=pk)
                form = self.form_class(instance = bt) 
                bt.delete()
                logger.info('Bt object deleted')
                messages.info(request, 'Record deleted successfully',
                'alert alert-success')
                response = redirect('onboarding:bu_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist', "alert alert-danger")
            response = redirect('onboarding:bu_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'buform':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'buform':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response

#========================== End Bt View Classes ============================#


#========================== Begin Site-people View Classes ============================#
class CreateSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/sitepeople_form.html'
    form_class = SitePeopleForm
    
    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('Create SitePeople view')
        cxt = {'sitepeople_form':self.form_class()}
        return render(request, self.template_path, context=cxt)
    
    def post(self, request, *args, **kwargs):
        """Handles creation of Bt instance."""
        logger.info('Create SitePeople form submiited')
        response, form = None, self.form_class(request.POST)
        try:
            if form.is_valid():
                logger.info('SitePeopleForm Form is valid')
                sp = form.save(commit=False)
                sp = save_userinfo(sp, request.user, request.session)
                sp.save()
                logger.info('SitePeopleForm Form saved')
                messages.success(request, "Success record saved successfully!", "alert-success")
                response = redirect('onboarding:sitepeople_form')
            else:
                logger.info('SitePeopleForm is not valid')
                cxt = {'sitepeople_form':form, 'edit':True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical('something went wrong...', exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
             "alert alert-danger")
            cxt = {'sitepeople_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


#list-out Bt data
class RetrieveSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/sitepeople_list.html'
    related = ['parent', 'identifier', 'butype']
    fields =  ['btid','bucode', 'buname', 'identifier',
             'enable', 'parent__bucode', 'butype']
    model = SitePeople
    
    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve SitePeoples view')
            objects = self.model.objects.select_related(*self.related
            ).values(*self.fields)
            logger.info('SitePeople objects retrieved from db')
            cxt   = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboard')
            messages.error(request, 'List view not found',
            'alert alert-danger')
        except Exception:
            logger.critical('something went wrong...', exc_info=True)
            messages.error(request, 'Something went wrong',
            "alert alert-danger")
            response = redirect('/dashboard')
        return response


    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import BtFilter
        if request.GET:
            objects = BtFilter(request.GET, queryset = objects).qs
        filterform = BtFilter().form
        page      = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            bt_list = paginator.page(page)
        except PageNotAnInteger:
            bt_list = paginator.page(1)
        except EmptyPage:
            bt_list = paginator.page(paginator.num_pages)
        cxt = {'sitepeople_list':bt_list, 'sitepeople_filter':filterform}
        return cxt


#update Bt instance
class UpdateSitePeople(LoginRequiredMixin, View):
    template_path = 'onboarding/bu_form.html'
    form_class = SitePeopleForm
    model = SitePeople

    def get(self, request, *args, **kwargs):
        logger.info('Update SitePeople view')
        response = None
        try:
            pk = kwargs.get('pk')
            sp = self.model.objects.get(sitepeopleid=pk)
            logger.info('object retrieved {}'.format(sp))
            form = self.form_class(instance=sp)
            response = render(request, self.template_path, context={'sitepeople_form':form, 'edit':True})
        except self.model.DoesNotExist:
            response = redirect('onboarding:sitepeople_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
            'alert alert-danger' )
            response = redirect('onboarding:sitepeople_form')
        return response

    def post(self, request, *args, **kwargs):
        logger.info('SitePeopleForm Form submitted')
        response = None
        try:
            pk = kwargs.get('pk')
            sp = self.model.objects.get(sitepeopleid=pk)
            form = self.form_class(request.POST, instance=sp)
            if form.is_valid():
                logger.info('SitePeopleForm Form is valid')
                sp = form.save(commit=False)
                sp = save_userinfo(sp, request.user, request.session)
                sp.save()
                logger.info('SitePeopleForm Form saved')
                messages.success(request, "Success record saved successfully!", "alert-success")
                response = redirect('onboarding:sitepeople_form')
            else:
                logger.info('SitePeopleForm is not valid')
                response = render(request, self.template_path, context={'sitepeople_form':form, 'edit':True})
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
            "alert alert-danger")
            cxt = {'sitepeople_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
            "alert alert-danger")
            cxt = {'sitepeople_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


#delete Bt instance
class DeleteSitePeople(LoginRequiredMixin, View):
    model = SitePeople
    form_class = SitePeopleForm
    model = SitePeople

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        pk, response = kwargs.get('pk', None),None
        try:
            if pk:
                sp = self.model.objects.get(sitepeopleid=pk)
                form = self.form_class(instance = sp)
                sp.delete()
                logger.info('SitePeople object deleted')
                messages.info(request, 'Record deleted successfully',
                'alert alert-success')
                response = redirect('onboarding:sitepeople_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist', "alert alert-danger")
            response = redirect('onboarding:sitepeople_form')
        except RestrictedError:
            logger.warn('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies',
             "alert alert-danger")
            cxt = {'sitepeople_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            messages.error(request, '[ERROR] Something went wrong', "alert alert-danger")
            cxt = {'sitepeople_form':form, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


#========================== End Site-people View Classes ============================#
class CreateClient(View):
    form_class = BtForm
    json_form = ClentForm
    template_path = 'onboarding/client_buform.html'
    model = Bt

    def get(self, request, *args, **kwargs):
        """Returns Bt form on html"""
        logger.info('Create ClientBt view')

        cxt = {'clientform':self.form_class(),
            'clientprefsform':self.json_form(),
        }
        return render(request, self.template_path, context=cxt)


    def post(self, request, *args, **kwargs):
        from .utils import save_json_from_bu_prefsform
        logger.info('Create ClientBt form submiited')
        response  = None
        form      = self.form_class(request.POST)
        jsonform  = self.json_form(request.POST)
        try:
            if form.is_valid() and jsonform.is_valid():
                logger.info('ClientBt Form is valid')
                from .utils import save_json_from_bu_prefsform
                bt = form.save(commit=False)
                if save_json_from_bu_prefsform(bt, jsonform):
                    bt = save_userinfo(bt, request.user, request.session)
                    bt.save()
                    logger.info('ClientBt Form saved')
                    messages.success(request, "Success record saved successfully!", "alert-success")
                    response =  redirect('onboarding:client_form')
            else:
                ic(form.errors, jsonform.errors)
                logger.info('ClientBt Form is not valid')
                cxt = {'clientform':form, 'clientprefsform':jsonform, 'edit':True}
                response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
             "alert alert-danger")
            cxt = {'clientform':form, 'clientprefsform':jsonform, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response


def get_caps(request):
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
            for j in child:
                childs.append({'capscode': j.capscode})
        logger.info('childs = [] {}'.format(childs))
        return JsonResponse(data = childs, safe=False)



class RetriveClients(LoginRequiredMixin, View):
    template_path = 'onboarding/client_bulist.html'
    fields =  ['btid','bucode','buname', 'enable', 'bu_preferences__webcapability',
            'bu_preferences__mobilecapability', 'bu_preferences__reportcapability']
    model = Bt

    def get(self, request, *args, **kwargs):
        '''returns the paginated results from db'''
        response = None
        try:
            logger.info('Retrieve Client view')
            objects = self.model.objects.values(*self.fields)
            logger.info('Cleint objects retrieved from db')
            cxt   = self.paginate_results(request, objects)
            logger.info('Results paginated')
            response = render(request, self.template_path, context=cxt)
        except EmptyResultSet:
            response = redirect('/dashboad')
            messages.error(request, 'List view not found',
            'alert alert-danger')
        except Exception:
            logger.critical('something went wrong...', exc_info=True)
            messages.error(request, 'Something went wrong',
            "alert alert-danger")
            response = redirect('/dashboard')
        return response

    def paginate_results(self, request, objects):
        '''paginate the results'''
        logger.info('Pagination Start')
        from .filters import ClientFiler
        if request.GET:
            objects = ClientFiler(request.GET, queryset = objects).qs
        filterform = ClientFiler().form
        page      = request.GET.get('page', 1)
        paginator = Paginator(objects, 25)
        try:
            client_list = paginator.page(page)
        except PageNotAnInteger:
            client_list = paginator.page(1)
        except EmptyPage:
            client_list = paginator.page(paginator.num_pages)
        cxt = {'client_list':client_list, 'client_filter':filterform}
        return cxt



class UpdateClient(LoginRequiredMixin, View):
    template_path = 'onboarding/client_buform.html'
    form_class = BtForm
    json_form = ClentForm
    model = Bt

    def get(self, request, *args, **kwargs):
        logger.info('Update Bt view')
        response = None
        try:
            from .utils import get_bt_prefform
            pk = kwargs.get('pk')
            bt = self.model.objects.select_related('butype').get(btid=pk)
            logger.info('object retrieved {}'.format(bt))
            form = self.form_class(instance=bt)
            cxt = {'clientform':form, 'clientprefsform':get_bt_prefform(bt), 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            messages.error(request, 'Unable to edit object not found',
            'alert alert-danger')
            response = redirect('onboarding:client_form')
        except Exception:
            logger.critical('something went wrong', exc_info=True)
            messages.error(request, 'Something went wrong',
            'alert alert-danger' )
            response = redirect('onboarding:client_form')
        return response
    

    def post(self, request, *args, **kwargs):
        logger.info('ClientForm Form submitted')
        from .utils import save_json_from_bu_prefsform
        try:
            pk, response = kwargs.get('pk'), None
            client = self.model.objects.get(btid=pk)
            form = self.form_class(request.POST, instance=client)
            jsonform = self.json_form(request.POST)
            if form.is_valid() and jsonform.is_valid():
                logger.info('ClientForm Form is valid')
                client = form.save(commit=False)
                if save_json_from_bu_prefsform(client, jsonform):
                    client = save_userinfo(client, request.user, request.session)
                    client.save()
                    logger.info('ClientForm Form saved')
                    messages.success(request, "Success record saved successfully!", "alert alert-success")
                    response =  redirect('onboarding:client_form')
            else:
                logger.info('ClientForm is not valid')
                cxt = {'clientform':form, 'clientprefsform':jsonform, 'edit':True}
                response =  render(request, self.template_path, context=cxt)
        except self.model.DoesNotExist:
            logger.error('Object does not exist', exc_info=True)
            messages.error(request, "Object does not exist",
            "alert alert-danger")
            cxt = {'clientform':form, 'clientprefsform':jsonform, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        except Exception:
            logger.critical("something went wrong...", exc_info=True)
            messages.error(request, "[ERROR] Something went wrong",
            "alert alert-danger")
            cxt = {'clientform':form, 'clientprefsform':jsonform, 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response



class DeleteClient(LoginRequiredMixin, View):
    model = Bt
    template_path = 'onboarding/client_buform.html'
    form_class = BtForm
    json_form = ClentForm

    def get(self, request, *args, **kwargs):
        """Handles deletion of object"""
        from django.db import models
        from .utils import get_bt_prefform
        pk, response = kwargs.get('pk', None), None
        try:
            if pk:
                bt = self.model.objects.get(btid=pk)
                form = self.form_class(instance=bt)
                bt.delete()
                logger.info('Client object deleted...')
                messages.info(request, 'Record deleted successfully',
                 'alert alert-success')
                response = redirect('onboarding:client_form')
        except self.model.DoesNotExist:
            logger.error('Unable to delete, object does not exist')
            messages.error(request, 'Client does not exist', "alert alert-danger")
            response = redirect('onboarding:client_form')
        except models.RestrictedError:
            logger.error('Unable to delete, due to dependencies')
            messages.error(request, 'Unable to delete, due to dependencies', "alert alert-danger")
            cxt = {'clientform':form, 'clientprefsform':get_bt_prefform(bt), 'edit':True}
            response = render(request, self.template_path, context=cxt)
        return response