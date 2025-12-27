"""
Hospital Information System - Patients Module Views
====================================================

Author: Athul Gopan
Created: 2025
Module: Patient Management APIs

This module contains all API endpoints for:
1. Patient Registration
2. Patient Search & Retrieval

API Structure:
    - All views inherit from APIView
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import viewsets, permissions
from apps.data_hub.models import *
from .serializers import PatientSerializer
from utils.auth_helper import *
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.views import APIView
from utils.auth_unique_id import *


# ============================================================================
# PATIENT REGISTRATION APIs
# ============================================================================

class PatientRegistrationView(APIView):
    # permission_classes = [IsReceptionist]

    def post(self, request, *args, **kwargs):
        """
        Handles patient registration
        """
        try:
            patient_id = get_next_patient_id()
            print(patient_id,"idddddddddddddddddd") 
            
            patient_data = {
                **request.data,
                "patient_id": patient_id
            }
            serializer = PatientSerializer(data=patient_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(created_by=request.user)
            
            return Response(
                {
                    "status": "success",
                    "patient_id": patient_id,
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# PATIENT SEARCH APIs
# ============================================================================

class PatientSearchView(APIView):
    """
    Patient Search API - Autocomplete/Search-as-you-type

    Endpoint:
        POST /api/patients/patient-search/

    Features:
        - Real-time search as user types phone number
        - Partial match (starts with) for autocomplete
        - Minimum 3 digits required for search
        - Limited to 10 results for performance
        - Returns patient details with last 3 appointments
        - Includes insurance and contact information
    """
    # permission_classes = [IsReceptionist]
    def post(self, request):
        try:
            contact_number = request.data.get('patient_phone_number', '').strip()

            if not contact_number:
                return Response(
                    {"error": "Patient phone number is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Minimum length validation for better search results
            if len(contact_number) < 3:
                return Response(
                    {"error": "Please enter at least 3 digits to search"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Partial match search (starts with) - for autocomplete
            patients = PatientRegistration.objects.filter(
                contact_number__startswith=contact_number
            )[:10]  # Limit to 10 results for performance

            if not patients.exists():
                return Response(
                    {
                        "count": 0,
                        "results": [],
                        "message": f"No patients found with phone number starting with '{contact_number}'"
                    },
                    status=status.HTTP_200_OK  # Return 200 with empty results instead of 404
                )
            results = []
            for patient in patients:
                appointments = Appointment.objects.filter(
                    patient=patient
                ).order_by('-appointment_date', '-appointment_time')[:3]                
                patient_data = {
                    "patient_id": patient.id,
                    "name": f"{patient.first_name} {patient.last_name}",
                    "date_of_birth": patient.date_of_birth,
                    "age": patient.age,
                    "gender": patient.get_gender_display(),
                    "address": patient.address,
                    "contact_number": patient.contact_number,
                    "email": patient.email,
                    "allergies": patient.allergies,
                    "emergency_contact": patient.emergency_contact,
                    "registration_date": patient.registration_date,
                    "insurance_details": {
                        "provider": patient.insurance_provider,
                        "number": patient.insurance_number
                    }
                }                
                appointment_data = []
                for appointment in appointments:
                    appointment_data.append({
                        "appointment_id": appointment.appointment_id,
                        "doctor": f"Dr. {appointment.doctor.user.first_name}",
                        "date": appointment.appointment_date,
                        "time": appointment.appointment_time,
                        "reason": appointment.visit_reason,
                        "status": appointment.visit_status,
                        "room": appointment.consultation_room
                    })
                results.append({
                    "patient": patient_data,
                    "recent_appointments": appointment_data
                })
            response_data = {
                "count": len(results),
                "results": results
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )