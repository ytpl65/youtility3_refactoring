from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.views import View

from .models import TypeAssist, Bt
from .forms import TypeAssistForm, BtForm, BuPrefForm


#======================== Begin TypeAssist View Classes ========================#

#create typeassist instance.
class TypeAssistCreate(CreateView):
    model = TypeAssist
    form_class = TypeAssistForm
    success_url = reverse_lazy('onboarding:ta_list')
    template_name = 'onboarding/ta_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ta_form'] = context['form']
        return context

#list out typeassist instances.
class TypeAssistList(ListView):
    model = TypeAssist
    template_name = 'onboarding/ta_list.html'
    context_object_name = 'ta_list'


#update typeassist instance.
class TypeAssistUpdate(UpdateView):
    model = TypeAssist
    template_name = 'onboarding/ta_form.html'
    success_url = reverse_lazy('onboarding:ta_list')
    form_class = TypeAssistForm

    def get_object(self):
        code = self.kwargs.get('pk')
        return get_object_or_404(self.model, tacode=code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ta_form'] = context['form']
        return context

class TypeAssistDelete(DeleteView):
    model = TypeAssist
    form_class = TypeAssistForm
    template_name = 'onboarding/ta_form.html'
    context_object_name = 'type_assist'
    success_url = reverse_lazy('ta_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        form_data = self.model.objects.values().filter(**kwargs)
        data['ta_form'] = self.form_class(initial=form_data)
        return data

#======================== End TypeAssist View Classes ========================#

#========================== Begin Bt View Classes ============================#

#create Bt instance.
class CreateBt(View):
    template_path = 'onboarding/bu_form.html'

    def get(self, request, *args, **kwargs):
        cxt = {'bu_prefsform':BuPrefForm(), 'buform':BtForm()}
        return render(request, self.template_path, context=cxt)
    
    def post(self, request, *args, **kwargs):
        from .utils import save_jsonfield_from_bu_prefsform
        
        bt           = Bt(),
        bu_prefsform = BuPrefForm(request.POST)
        buform       = BtForm(request.POST, instance = bt)
        context      = {'bu_prefsform':bu_prefsform, 'buform':buform}
        if bu_prefsform.is_valid() and buform.is_valid():
            save_jsonfield_from_bu_prefsform(bt, bu_prefsform, True)
            buform.save()
            return redirect('onboarding:bu_list')
        return render(request, self.template_path, context=context)


#list-out Bt data
class ListBt(View):
    template_path = 'onboarding/bu_list.html'

    def get(self, request, *args, **kwargs):
        columns = ['btid','bucode', 'buname', 'identifier', 'enable', 'parent', 'butype']
        context = {'bt_objects': Bt.objects.values(columns)}
        return render(request, self.template_path, context=context)


#update Bt instance
class UpdateBt(View):
    def get(self, request, *args, **kwargs):
        from .utils import get_bu_prefform
        bt = Bt.objects.get(**kwargs)
        
        form = BtForm(instance=bt)
        prefs_form =get_bu_prefform(bt) 
        cxt = {'bu_prefsform':prefs_form, 'buform':form , 'bt':bt}
        return render(request, 'onboarding/bu_form.html', context=cxt)
    

    def post(self, request, *args, **kwargs):
        from .utils import save_jsonfield_from_bu_prefsform
        print(kwargs)
        bt = Bt.objects.get(**kwargs)
        bu_prefsform = BuPrefForm(request.POST)
        buform       = BtForm(request.POST, instance=bt)
        print(bu_prefsform.as_p())
        if bu_prefsform.is_valid() and buform.is_valid():
            save_jsonfield_from_bu_prefsform(bt, bu_prefsform, tocreate=False)
            buform.save()
            return redirect('onboarding:bu_list')


#delete Bt instance
class DeleteBt(View):
    def post(self, request, *args, **kwargs):
        Bt.objects.get(**kwargs).delete()
        return redirect('onboarding:bu_list')

#========================== End Bt View Classes ============================#
