"""
Hospital Information System - Main URL Configuration
====================================================

Author: Athul Gopan
Created: 2025
Project: Hospital Management System

This module contains the root URL routing configuration for the entire
Hospital Information System. All API endpoints are prefixed with 'api/'
and are organized by functional modules.

URL Structure:
    /admin/                 - Django admin interface
    /api/auth/             - Authentication & authorization
    /api/patients/         - Patient management
    /api/appointments/     - Appointment scheduling
    /api/nurse/            - Nurse management
    /api/front-desk/       - Front desk operations
    /api/pharmacy/         - Pharmacy & medication management

Planned/Future Modules (currently commented):
    /api/outpatient/       - Outpatient services
    /api/inpatient/        - Inpatient services
    /api/emergency/        - Emergency department
    /api/billing/          - Billing & invoicing
    /api/reports/          - Reports & analytics
    /api/discharge/        - Patient discharge management

For more information on Django URL configuration:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ============================================================================
# MAIN URL PATTERNS
# ============================================================================

urlpatterns = [
    # --------------------------------------------------------------------
    # Django Admin Interface
    # --------------------------------------------------------------------
    path('admin/', admin.site.urls),

    # --------------------------------------------------------------------
    # Core API Endpoints (Active Modules)
    # --------------------------------------------------------------------
    # Authentication and user management
    path('api/auth/', include('apps.accounts.urls')),

    # Patient registration and management
    path('api/patients/', include('apps.patients.urls')),

    # Appointment scheduling and management
    path('api/appointments/', include('apps.appointments.urls')),

    # Nurse profile and operations management
    path('api/nurse/', include('apps.nurse.urls')),

    # Front desk operations and patient check-in
    path('api/front-desk/', include('apps.frontdeskapp.urls')),

    # Pharmacy and medication management
    path('api/pharmacy/', include('apps.pharmacy.urls')),

    # --------------------------------------------------------------------
    # Future/Planned API Endpoints (Currently Disabled)
    # --------------------------------------------------------------------
    # Outpatient services and consultations
    # path('api/outpatient/', include('apps.outpatient.urls')),

    # Inpatient ward management
    # path('api/inpatient/', include('apps.inpatient.urls')),

    # Emergency department operations
    # path('api/emergency/', include('apps.emergency.urls')),

    # Billing, invoicing, and payment processing
    # path('api/billing/', include('apps.billing.urls')),

    # Reports, analytics, and statistics
    # path('api/reports/', include('apps.reports.urls')),

    # Patient discharge processing
    # path('api/discharge/', include('apps.discharge.urls')),
]

# ============================================================================
# MEDIA FILES CONFIGURATION
# ============================================================================
# Serve uploaded media files (profile pictures, documents, etc.) in development
# In production, these should be served by a web server (nginx/Apache) or CDN
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



    