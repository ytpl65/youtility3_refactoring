from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy

from .models import TypeAssist
from .forms import TypeAssistForm



# Create your views here.
class TypeAssistCreate(CreateView):
    model = TypeAssist
    form_class = TypeAssistForm
    success_url = reverse_lazy('ta_list')
    template_name = 'onboarding/ta_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ta_form'] = self.get_form()
        return context


class TypeAssistList(ListView):
    model = TypeAssist
    template_name = 'onboarding/ta_list.html'
    context_object_name = 'ta_list'


class TypeAssistUpdate(UpdateView):
    model = TypeAssist
    form_class = TypeAssistForm
    template_name = 'onboarding/ta_form.html'
    context_object_name = 'type_assist'
    success_url = reverse_lazy('ta_list')


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

