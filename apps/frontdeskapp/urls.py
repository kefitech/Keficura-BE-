from django.urls import path
from .views import *

urlpatterns = [
    # ============================================================================
    # FRONT DESK PROFILE URLs
    # ============================================================================
    path('frontdesk_profile/', FrontdeskProfileView.as_view(), name='frontdesk_profile'),
]