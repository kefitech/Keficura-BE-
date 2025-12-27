from django.urls import path
from .views import *

urlpatterns = [
    # ============================================================================
    # NURSE MANAGEMENT URLs
    # ============================================================================
    path('add-nurse/', CreateNurseView.as_view(), name='add-nurse'),

    # ============================================================================
    # NURSE SHIFT ASSIGNMENT URLs
    # ============================================================================
    path('nurse-shift-api/', NurseShiftAssignmentView.as_view(), name='nurse-shift-api'),
]