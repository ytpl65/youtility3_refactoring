from django.urls import path
from apps.reports.views import (
    ConfigSiteReportTemplate, IncidentReportTemplate, MasterReportBelonging, 
    RetriveSiteReports, ConfigIncidentReportTemplate,ConfigWorkPermitReportTemplate,
    SiteReportTemplateForm, IncidentReportTemplateForm) 

app_name='reports'
urlpatterns = [
    path('sitereport_list/',           RetriveSiteReports.as_view(),         name='sitereport_list'),
   #path('incidentreport_list/',           RetriveIncidentReports.as_view(),         name='incidentreport_list'),
    path('sitereport_template/',      ConfigSiteReportTemplate.as_view(),   name='config_sitereport_template'),
    path('incidentreport_template/',      ConfigIncidentReportTemplate.as_view(),   name='config_incidentreport_template'),
    path('workpermitreport_template/',      ConfigWorkPermitReportTemplate.as_view(),   name='config_workpermitreport_template'),
    path('incidentreport_temp_list/',  IncidentReportTemplate.as_view(),     name='incidentreport_template_list'),
    path('sitereport_temp_form/',      SiteReportTemplateForm.as_view(),     name='sitereport_template_form'),
    path('incidentreport_temp_form/',  IncidentReportTemplateForm.as_view(), name='incident_template_form'),
    path('srqsetbelonging/',           MasterReportBelonging.as_view(),      name='srqsetbelonging'),
]
