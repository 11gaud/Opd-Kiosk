from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    # Auth
    path('login/',  LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='dashboard:login'),         name='logout'),

    # Home
    path('', views.DashboardHomeView.as_view(), name='home'),

    # Patients
    path('patients/',               views.PatientListView.as_view(),   name='patient_list'),
    path('patients/<int:pk>/',      views.PatientDetailView.as_view(), name='patient_detail'),
    path('patients/<int:pk>/edit/', views.PatientEditView.as_view(),   name='patient_edit'),

    # Doctors
    path('doctors/',                      views.DoctorListView.as_view(),             name='doctor_list'),
    path('doctors/add/',                  views.DoctorCreateView.as_view(),           name='doctor_add'),
    path('doctors/<int:pk>/edit/',        views.DoctorEditView.as_view(),             name='doctor_edit'),
    path('doctors/<int:pk>/toggle/',      views.DoctorToggleAvailabilityView.as_view(), name='doctor_toggle'),
    path('doctors/<int:pk>/schedule/',    views.DoctorScheduleView.as_view(),          name='doctor_schedule'),
    path('doctors/<int:pk>/schedule/<str:date_str>/save/',       views.DoctorScheduleSaveDayView.as_view(),      name='doctor_schedule_save_day'),
    path('doctors/<int:pk>/schedule/<str:date_str>/toggle-off/', views.DoctorScheduleToggleDayOffView.as_view(), name='doctor_schedule_toggle_off'),

    # Queue
    path('queue/',                                    views.QueueBoardView.as_view(),    name='queue_board'),
    path('queue/<int:service_pk>/call-next/',          views.QueueCallNextView.as_view(), name='queue_call_next'),
    path('queue/<int:service_pk>/reset/',              views.QueueResetView.as_view(),    name='queue_reset'),
    path('queue/entry/<int:pk>/status/',               views.QueueEntryStatusView.as_view(), name='queue_entry_status'),

    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),

    # Reports
    path('reports/', views.ReportsView.as_view(), name='reports'),

]
