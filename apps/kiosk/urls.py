from django.urls import path
from . import views

app_name = 'kiosk'

urlpatterns = [
    path('', views.StartView.as_view(), name='start'),
    path('step/1/', views.Step1ServicesView.as_view(), name='step1'),
    path('step/2/', views.Step2PatientTypeView.as_view(), name='step2'),
    path('step/3/', views.Step3LookupView.as_view(), name='step3'),
    path('step/4/', views.Step4PersonalInfoView.as_view(), name='step4'),
    path('step/5/', views.Step5ContactView.as_view(), name='step5'),
    path('step/6/', views.Step6PaymentView.as_view(), name='step6'),
    path('step/7/', views.Step7DoctorView.as_view(), name='step7'),
    path('step/8/', views.Step8SignatureView.as_view(), name='step8'),
    path('step/9/', views.Step9SummaryView.as_view(), name='step9'),
    path('step/10/', views.Step10TicketView.as_view(), name='step10'),
    # HTMX & AJAX
    path('htmx/patient-search/', views.PatientSearchView.as_view(), name='patient_search'),
    path('api/save-signature/', views.SaveSignatureView.as_view(), name='save_signature'),
    path('api/confirm/', views.ConfirmTransactionView.as_view(), name='confirm'),
    path('api/reset/', views.ResetSessionView.as_view(), name='reset'),
    path('queue-display/', views.QueueDisplayView.as_view(), name='queue_display'),
]
