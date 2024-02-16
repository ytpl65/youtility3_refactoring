from django.urls import path, include
from apps.onboarding import views


app_name = 'onboarding'
urlpatterns = [
    path('client_form/get_caps/',    views.get_caps,                  name="get_caps"),
    path('pop-up/ta/', views.handle_pop_forms, name="ta_popup"),
    path('typeassist/', views.TypeAssistView.as_view(), name="typeassist"),
    path('super_typeassist/', views.SuperTypeAssist.as_view(), name="super_typeassist"),
    path('shift/', views.ShiftView.as_view(), name="shift"),
    path('editor/', views.EditorTa.as_view(), name="editortypeassist"),
    path('geofence/', views.GeoFence.as_view(), name='geofence'),
    path('import/', views.BulkImportData.as_view(), name="import"),
    path('client/', views.Client.as_view(), name="client"),
    path('bu/', views.BtView.as_view(), name="bu"),
    path('rp_dashboard/', views.DashboardView.as_view(), name="rp_dashboard"),
    path('fileUpload/', views.FileUpload.as_view(), name="file_upload"),
    path('subscription/', views.LicenseSubscriptionView.as_view(), name="subscription")
]
