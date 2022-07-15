from django.urls import path
from apps.attendance import views

app_name = 'attendance'
urlpatterns = [
    path('attendance/', views.Attendance.as_view(), name='attendance_view'),
    path('travel_expense/', views.Conveyance.as_view(), name='conveyance'),
    # path('markAttendance/', views.face_recognition, name='markAttendance'),# 
    #path('opencam/', views.face_recognition2, name='webcam')
]
