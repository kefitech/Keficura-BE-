from django.urls import path
from .views import *

urlpatterns = [
    # ============================================================================
    # DEPARTMENT MANAGEMENT URLs
    # ============================================================================
    path('add-department/', CreateDepartment.as_view(), name='add-department'),

    # ============================================================================
    # SPECIALIZATION MANAGEMENT URLs
    # ============================================================================
    path('add-specialization/', CreateSpecialization.as_view(), name='add-specialization'),

    # ============================================================================
    # DOCTOR MANAGEMENT URLs
    # ============================================================================
    path('add-doctor/', CreateDoctorView.as_view(), name='add-doctor'),
    path('doctor-department/', DoctorDepartmentViewset.as_view(), name='doctor-department'),

    # ============================================================================
    # DOCTOR SCHEDULE URLs
    # ============================================================================
    path('doctor-schedule/', DoctorSchedulesViewSet.as_view(), name='doctor-schedule'),

    # ============================================================================
    # APPOINTMENT MANAGEMENT URLs
    # ============================================================================
    path('patient-appointment/', PatientAppointmentView.as_view(), name='patient-appointment'),
    path('update-appoointment-status/', AppointmentStatusView.as_view(), name='update-appoointment-status'),
    path('daily-appointment-view/', TodayPatientAppointment.as_view(), name='daily-appointment-view'),

    # ============================================================================
    # DOCTOR APPOINTMENT VIEWS URLs
    # ============================================================================
    path('doctor-appointment-view/', DoctorAppointmentView.as_view(), name='doctor-appointment-view'),

    # ============================================================================
    # APPOINTMENT HISTORY & CONSULTATION URLs
    # ============================================================================
    path('appointment-history/', PharmacyAppointmentsView.as_view(), name='pharmacy-appointments'),
    path('patient-consultation-history/', PatientConsultationHistoryView.as_view(), name='patient-consultation-history'),
]