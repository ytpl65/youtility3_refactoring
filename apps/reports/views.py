from django.shortcuts import render

# Create your views here.
class RetrieveSiteReportList(LoginRequiredMixin, View):
    params = {
        'form_class':None,
        'template_lst':'reports/sitereport_list.html'
    }