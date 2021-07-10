from django.urls import path
from .views import TypeAssistCreate, TypeAssistList, TypeAssistUpdate, TypeAssistDelete


app_name = 'onboarding'
urlpatterns = [
    path('ta_form/', TypeAssistCreate.as_view(), name='ta_form'),
    path('ta_list/', TypeAssistList.as_view(), name='ta_list'),
    path('ta_update/<str:pk>', TypeAssistUpdate.as_view(), name='ta_update'),
    path('ta_delete/<str:pk>', TypeAssistDelete.as_view(), name='ta_delete'),
]
