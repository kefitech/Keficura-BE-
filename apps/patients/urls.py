from django.urls import path
from .views import *

urlpatterns = [
    # ============================================================================
    # PATIENT REGISTRATION URLs
    # ============================================================================
    path('patient-registration/', PatientRegistrationView.as_view(), name='patient-registration'),

    # ============================================================================
    # PATIENT SEARCH URLs
    # ============================================================================
    path('patient-search/', PatientSearchView.as_view(), name='patient-search'),
]

