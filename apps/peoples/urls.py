from django.conf import settings
from django.urls import path
from django.urls.conf import include
from apps.peoples import views
from django.conf.urls.static import static
from apps.onboarding.wizard_urls import wizard_url_patterns2
from apps.onboarding import wizard_views
app_name = 'peoples'
urlpatterns = [
        path('people_form/',              views.CreatePeople.as_view(),         name='people_form'),
        path('people_list/',              views.RetrievePeoples.as_view(),      name='people_list'),
        path('people_form/<str:pk>/',     views.UpdatePeople.as_view(),         name='people_update'),
        path('people_form/del/<str:pk>/', views.DeletePeople.as_view(),         name='people_delete'),
        path('peole_form/change_paswd/',  views.ChangePeoplePassword.as_view(), name='people_change_paswd'),
        
        path('pgroup_form/',              views.CreatePgroup.as_view(),    name='pgroup_form'),
        path('pgroup_list/',              views.RetrivePgroups.as_view(),  name='pgroup_list'),
        path('pgroup_form/<str:pk>',      views.UpdatePgroup.as_view(),    name='pgroup_update'),
        path('pgroup_form/del/<str:pk>',  views.DeletePgroup.as_view(),    name='pgroup_delete'),
        
        path('cap_form/',              views.CreateCapability.as_view(),    name='cap_form'),
        path('cap_list/',              views.RetriveCapability.as_view(),   name='cap_list'),
        path('cap_form/<str:pk>',      views.UpdateCapability.as_view(),    name='cap_update'),
        path('cap_form/del/<str:pk>',  views.DeleteCapability.as_view(),    name='cap_delete'),
        
        path('capability/',  views.Capability.as_view(),    name='capability'),
        path('peoplegroup/',  views.Pgroup.as_view(),    name='peoplegroup'),
        path('people/',  views.People.as_view(),    name='people'),
        
        path('wizard/', include(wizard_url_patterns2)),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)