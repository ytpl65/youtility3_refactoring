from django.urls import path
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
    path('adhoctasks/', views.AdhocTasks.as_view(), name='adhoctasks'),
    path('adhoctours/', views.AdhocTours.as_view(), name='adhoctours'),
    path('assetmaintainance/', views.AssetMaintainceList.as_view(), name='assetmaintainance'),
    path('qsetnQsetblng/', views.QsetNQsetBelonging.as_view(), name='qset_qsetblng'),
    path('mobileuserlogs/', views.MobileUserLog.as_view(), name='mobileuserlogs'),
    path('mobileuserdetails/', views.MobileUserDetails.as_view(), name='mobileuserdetails'),
    path('peoplenearassets/', views.PeopleNearAsset.as_view(), name='peoplenearasset'),
    path('workpermit/', views.WorkPermit.as_view(), name='workpermit'),
    path('attachments/', views.Attachments.as_view(), name='attachments'),
]
