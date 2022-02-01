from django.urls import path
from apps.schedhuler import views

app_name = 'schedhuler'
urlpatterns = [
    path('schedhule_tour/', views.CreateSchedhuleTour.as_view(), name='create_tour'),#job
    path('external_schedhule_tour/', views.CreateExternalTourSchdTour.as_view(), name='create_externaltour'),#job
    path('external_schedhule_tour/saveSites/', views.save_assigned_sites_for_externaltour, name='save_assigned_sites'),#job
    path('schedhule_tour/<str:pk>/', views.UpdateSchdhuledTour.as_view(), name='update_tour'),#job
    path('external_schedhule_tour/<str:pk>/', views.UpdateExternalSchdhuledTour.as_view(), name='update_externaltour'),#job
    path('schedhule_tours/', views.RetriveSchedhuledTours.as_view(), name='retrieve_tours'),#job
    path('schedhule_externaltours/', views.RetriveExternalSchedhuledTours.as_view(), name='retrieve_externaltours'),#job
    path('delete-checkpoint/', views.deleteChekpointFromTour, name='delete_checkpointTour'),#job
    path('internal-tours/', views.RetriveInternalTours.as_view(), name='retrieve_internaltours'),#jobneed
    path('internal-tour/<str:pk>/', views.GetInternalTour.as_view(), name='internaltour'),#jobneed
    #path('jobnneeddetails/', views.get_jobneed_details, name='jobnneeddetails'),#jobneed
    path('internal-tour/add/', views.add_cp_internal_tour, name='add_checkpoint'),#jobneed
    path('runJob/', views.run_internal_tour_scheduler, name='runJob'),
    path('getCronDateTime/', views.get_cron_datetime, name='getCronDateTime'),
    #path('schedhule_tour/', views.CreateSchedhuleTour.as_view(), name='create_tour'),
]