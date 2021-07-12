from django.urls import path
from apps.peoples import views

app_name = 'peoples'
urlpatterns = [
    path('pgroup_form/', views.CreatePgroup.as_view(), name='pgroup_form'),
    path('pgroup_list/', views.ListPgroup.as_view(), name='pgroup_list'),
    path('pgroup_form/<int:pk>', views.ListPgroup.as_view(), name='pgroup_list'),
  
]
