from django.urls import path
from django.urls.conf import include
from apps.activity import views

app_name = 'activity'
urlpatterns = [
    path('question/', views.Question.as_view(), name='question'),
    path('checklist/', views.Checklist.as_view(), name='checklist'),
    path('questionset/', views.QuestionSet.as_view(), name='questionset'),
    path('checkpoint/', views.Checkpoint.as_view(), name='checkpoint'),
    path('smartplace/', views.Smartplace.as_view(), name='smartplace'),
    path('delete_qsb/', views.deleteQSB, name='delete_qsb'),
    path('esclist/', views.RetriveEscList.as_view(), name='esc_list'),
]