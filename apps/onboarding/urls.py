from django.urls import path, include
from apps.onboarding import views
from .wizard_urls import wizard_url_patterns1

app_name = 'onboarding'
urlpatterns = [
    path('ta_form/',              views.CreateTypeassist.as_view(),    name='ta_form'),
    path('ta_list/',              views.RetrieveTypeassists.as_view(), name='ta_list'),
    path('ta_form/<str:pk>/',     views.UpdateTypeassist.as_view(),    name='ta_update'),
    path('ta_form/del/<str:pk>/', views.DeleteTypeassist.as_view(),    name='ta_delete'),
    path('test/jq', views.test_ta_grid,    name='ta_jq'),
    
    path('superta_form/',              views.CreateTypeassist.as_view(),    name='superta_form'),
    path('superta_list/',              views.RetrieveTypeassists.as_view(), name='superta_list'),
    path('superta_form/<str:pk>/',     views.UpdateTypeassist.as_view(),    name='superta_update'),
    path('superta_form/del/<str:pk>/', views.DeleteTypeassist.as_view(),    name='superta_delete'),
    
    path('bu_form/',              views.CreateBt.as_view(),   name='bu_form'),
    path('bu_list/',              views.RetrieveBt.as_view(), name='bu_list'),
    path('bu_form/<str:pk>/',     views.UpdateBt.as_view(),   name='bu_update'),
    path('bu_form/del/<str:pk>/', views.DeleteBt.as_view(),   name='bu_delete'),
    
    path('shift_form/',              views.CreateShift.as_view(),   name='shift_form'),
    path('shift_list/',              views.RetrieveShift.as_view(), name='shift_list'),
    path('shift_form/<str:pk>/',     views.UpdateShift.as_view(),   name='shift_update'),
    path('shift_form/del/<str:pk>/', views.DeleteShift.as_view(),   name='shift_delete'),
    
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
    path('pop-up/ta/', views.handle_pop_forms, name="ta_popup")
]