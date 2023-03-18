from django.urls import path
from apps.work_order_management import views
app_name = 'work_order_management'
urlpatterns = [
    path('vendor/', views.VendorView.as_view(), name="vendor")
]
