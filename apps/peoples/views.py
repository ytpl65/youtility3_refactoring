from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import edit
from django.urls import reverse_lazy
from .models import Pgroup
from .forms import PgroupForm
# Create your views here.


#========================== Begin Pgroup View Classes ============================#

class ListPgroup(View):
    template_path = 'peoples/pgroup_list.html'

    def get(self, request, *args, **kwargs):
        columns = ['groupname', 'enable']
        context = {'pgroup_objects': Pgroup.objects.values(columns)}
        return render(request, self.template_path, context=context)


class CreatePgroup(edit.UpdateView):
    model = Pgroup
    form_class = PgroupForm
    template_name = 'peoples/people_form.html'
    success_url = reverse_lazy('peoples:pgroup_list')

    def get_context_data(self, kwargs):
        context = super().get_context_data(**kwargs)
        context['pgroup_form'] = context['form']
        return context


class UpdatePgroup(edit.UpdateView):
    model = Pgroup
    form_class = PgroupForm
    template_name = 'peoples/people_form.html'
    success_url = reverse_lazy('peoples:pgroup_list')

    def get_object(self):
        id = self.kwargs.get('pk')
        return get_object_or_404(self.model, pgbid=id)
    
    def get_context_data(self, kwargs):
        context = super().get_context_data(**kwargs)
        context['pgroup_form'] = context['form']
        return context


class DeletePgroup(edit.UpdateView):
    model = Pgroup
    form_class = PgroupForm
    template_name = 'peoples/people_form.html'
    success_url = reverse_lazy('peoples:pgroup_list')

    def get_object(self):
        id = self.kwargs.get('pk')
        return get_object_or_404(self.model, pgbid=id)

#=========================== End Pgroup View Classes ==============================#