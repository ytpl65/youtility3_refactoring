from django.urls import path
from apps.onboarding import views
from apps.onboarding.views import FORMS


app_name = 'onboarding'
urlpatterns = [
    path('ta_form/',              views.CreateTypeassist.as_view(),    name='ta_form'),
    path('ta_list/',              views.RetrieveTypeassists.as_view(), name='ta_list'),
    path('ta_form/<str:pk>/',     views.UpdateTypeassist.as_view(),    name='ta_update'),
    path('ta_form/del/<str:pk>/', views.DeleteTypeassist.as_view(),    name='ta_delete'),
    path('ta_form/',              views.DeleteTypeassist.as_view(),    name='ta_form_popup'),
    
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
    path('client_onboarding/',       views.ClientOnboardingWizard.as_view(FORMS),  name='client_onboarding')
]