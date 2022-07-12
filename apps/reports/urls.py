from django.urls import path
from apps.reports.views import (
    IncidentReportTemplate, MasterReportBelonging, RetriveSiteReports, SiteReportTemplate,
    SiteReportTemplateForm, IncidentReportTemplateForm) 

app_name='reports'
urlpatterns = [
    path('sitereport_list/',           RetriveSiteReports.as_view(),         name='sitereport_list'),
    path('sitereport_temp_list/',      SiteReportTemplate.as_view(),         name='sitereport_template_list'),
    path('incidentreport_temp_list/',  IncidentReportTemplate.as_view(),     name='incidentreport_template_list'),
    path('sitereport_temp_form/',      SiteReportTemplateForm.as_view(),     name='sitereport_template_form'),
    path('incidentreport_temp_form/',  IncidentReportTemplateForm.as_view(), name='incident_template_form'),
    path('srqsetbelonging/',           MasterReportBelonging.as_view(),      name='srqsetbelonging'),
]
