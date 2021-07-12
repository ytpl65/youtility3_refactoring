from django.urls import path
from apps.onboarding import views

app_name = 'onboarding'
urlpatterns = [
    path('ta_form/',            views.TypeAssistCreate.as_view(),  name='ta_form'),
    path('ta_list/',            views.TypeAssistList.as_view(),    name='ta_list'),
    path('ta_form/<str:pk>/',   views.TypeAssistUpdate.as_view(),    name='ta_update'),
    path('bu_form/',            views.CreateBt.as_view(),          name='bu_form'),
    path('bu_list/',            views.ListBt.as_view(),            name='bu_list'),
    path('bu_form/<str:buid>/', views.UpdateBt.as_view(),          name='bu_edit'),
]