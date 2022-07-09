from django.urls import path, include
from apps.onboarding import views
from .wizard_urls import wizard_url_patterns1

app_name = 'onboarding'
urlpatterns = [    
    path('bu_form/',              views.CreateBt.as_view(),   name='bu_form'),
    path('bu_list/',              views.RetrieveBt.as_view(), name='bu_list'),
    path('bu_form/<str:pk>/',     views.UpdateBt.as_view(),   name='bu_update'),
    path('bu_form/del/<str:pk>/', views.DeleteBt.as_view(),   name='bu_delete'),
    
    path('sitepeople_form/',              views.CreateSitePeople.as_view(),   name='sitepeople_form'),
    path('sitepeople_list/',              views.RetrieveSitePeople.as_view(), name='sitepeople_list'),
    path('sitepeople_form/<str:pk>/',     views.UpdateSitePeople.as_view(),   name='sitepeople_update'),
    path('sitepeople_form/del/<str:pk>/', views.DeleteSitePeople.as_view(),   name='sitepeople_delete'),

    path('client_form/',             views.CreateClient.as_view() ,   name='client_form'),
    path('client_list/',             views.RetriveClients.as_view() , name='client_list'),
    path('client_form/<str:pk>',     views.UpdateClient.as_view() ,   name='client_update'),
    path('client_form/del/<str:pk>', views.DeleteClient.as_view() ,   name='client_delete'),
    path('client_form/get_caps/',    views.get_caps,                  name="get_caps"),
    path('wizard/',                 include(wizard_url_patterns1)),
    path('pop-up/ta/', views.handle_pop_forms, name="ta_popup"),
    
    path('typeassist/', views.TypeAssistAjax.as_view(), name="typeassist"),
    path('super_typeassist/', views.SuperTypeAssist.as_view(), name="super_typeassist"),
    path('shift/', views.Shift.as_view(), name="shift"),
    path('editor/', views.EditorTa.as_view(), name="editortypeassist"),

    path('geofence/', views.GeoFence.as_view(), name='geofence'),
    path('import/', views.ImportFile.as_view(), name="import"),
    #path('listbu/', views.ListOfBu.as_view(), name="list_bu")
]