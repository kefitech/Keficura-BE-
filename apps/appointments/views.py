"""
Hospital Information System - Appointments Module Views
========================================================

Author: Athul Gopan
Created: 2025
Module: Appointments & Doctor Management APIs

This module contains all API endpoints for:
1. Department Management
2. Specialization Management
3. Doctor Management
4. Doctor Schedule Management
5. Appointment Management
6. Doctor Appointment Views
7. Appointment History & Consultation

API Structure:
    - All views inherit from APIView
    - Transactions are wrapped with @transaction.atomic
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework import viewsets, permissions
from apps.data_hub.models import *
from .serializers import *
from django.utils import timezone
from django.contrib.auth.models import User, Group
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from django.db import transaction
from utils.auth_helper import *
from django.db.models import Q
from utils.email_helper import *
from utils.auth_unique_id import *
from django.core.exceptions import ValidationError
from collections import defaultdict
from datetime import datetime, timedelta
import pytz
from django.db.models import Case, When, Value, IntegerField


# ============================================================================
# DEPARTMENT MANAGEMENT APIs
# ============================================================================

class CreateDepartment(APIView):
    """
    Department Management API

    Endpoints:
        POST /api/appointments/add-department/ - Create new department
        GET /api/appointments/add-department/ - List all departments

    Features:
        - Create hospital departments
        - Retrieve all departments list
        - Validation for department data
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            data = request.data

            serializer = Department_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                response_data = {"message": "Department created successfully"}
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except KeyError as e:
            error_message = f"Missing required field: {str(e)}"
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Get all departments"""
        try:
            department_list = Department.objects.all()
            serializer = Department_serializer(department_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve departments: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# SPECIALIZATION MANAGEMENT APIs
# ============================================================================

class CreateSpecialization(APIView):
    """
    Specialization Management API

    Endpoints:
        POST /api/appointments/add-specialization/ - Create new specialization
        GET /api/appointments/add-specialization/ - List all specializations

    Features:
        - Create medical specializations
        - Link specializations to departments
        - Retrieve all specializations list
        - Validation for specialization data
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            data = request.data
            
            serializer = Specialization_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                response_data = {"message": "Specialization created successfully"}
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except KeyError as e:
            error_message = f"Missing required field: {str(e)}"
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self,request):
        """get all specializations"""
        try:
            specialization_list = Specialization.objects.all()
            serializer = Specialization_serializer(specialization_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": f"Failed to retrieve departments: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# DOCTOR MANAGEMENT APIs
# ============================================================================

class CreateDoctorView(APIView):
    """
    Doctor Management API

    Endpoints:
        POST /api/appointments/add-doctor/ - Create new doctor with user account
        GET /api/appointments/add-doctor/ - List all doctors

    Features:
        - Create user account and doctor profile simultaneously
        - Auto-assign to doctor group
        - Upload profile picture and certificates
        - Send credentials via email
        - Link doctor to department and specialization
        - Validation for duplicate username/email
    """
    permission_classes = [IsAdminUser]  
    
    @transaction.atomic
    def post(self, request):
        """
        Creates a new user and associated doctor profile
        """
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        
        if not username or not email or not password:
            return Response(
                {"detail": "Username, email and password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Username already exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email already exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )            
            doctor_group = Group.objects.get(id=2)
            user.groups.add(doctor_group)
            user.save()
            
        except Group.DoesNotExist:
            user.delete()
            return Response(
                {"detail": "Doctor group with ID 2 does not exist"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"Failed to create user: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        doctor_data = {
            'user': user.id,
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),

            'contact_number': request.data.get('contact_number'),
            'phone_number': request.data.get('phone_number'),
            'email': email,

            'home_address': request.data.get('home_address'),
            'home_city': request.data.get('home_city'),
            'home_state': request.data.get('home_state'),
            'home_country': request.data.get('home_country'),
            'home_zip_code': request.data.get('home_zip_code'),

            'qualification': request.data.get('qualification'),
            'experience_years': request.data.get('experience_years'),
            'specialization': request.data.get('specialization'),
            'department': request.data.get('department'),
            'date_joined': request.data.get('date_joined'),
            'doctor_consultation_fee': request.data.get('doctor_consultation_fee'),
            
        }
        
        # If profile picture was included
        if 'profile_picture' in request.FILES:
            doctor_data['profile_picture'] = request.FILES['profile_picture']

        if 'curriculum_vitae' in request.FILES:
            doctor_data['curriculum_vitae'] = request.FILES['curriculum_vitae']

        if 'education_certificate' in request.FILES:
            doctor_data['education_certificate'] = request.FILES['education_certificate']

        if 'experience_certificate' in request.FILES:
            doctor_data['experience_certificate'] = request.FILES['experience_certificate']
        
        
        serializer = DoctorSerializer(data=doctor_data)
        if serializer.is_valid():
            doctor = serializer.save()  
            
            try:
                send_doctor_credentials_email(
                    doctor=doctor,
                    username=username,
                    password=password
                )                
                response_data = {
                    "message": "Doctor profile created successfully. Credentials have been sent to the doctor's email."
                }
                
            except Exception as e:
                # print(f"Failed to send email: {str(e)}")
                response_data = {
                    "message": "Doctor profile created successfully, but failed to send email with credentials.",
                    "warning": "Please provide the doctor with their credentials manually.",
                    "credentials": {
                        "username": username,
                        "password": password
                    }
                }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            user.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        


    def get(self, request):
        """API for getting all doctors"""
        try:
            Doctor_details = Doctor.objects.select_related(
                'user',
                'specialization',
                'specialization__department',
            ).all()
            response_data = []

            for doctor in Doctor_details:
                doctor_data = {
                    "doctor_id" : doctor.id,
                    "doctor_name" : f"{doctor.user.first_name} {doctor.user.last_name}",
                    "specialization": doctor.specialization.name,
                    "department": doctor.specialization.department.name,
                    "is_active": doctor.is_active,
                }
                response_data.append(doctor_data)
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"detail": f"Error fetching doctors: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# DOCTOR SCHEDULE APIs
# ============================================================================

class DoctorSchedulesViewSet(APIView):
    """
    Doctor Schedule Management API

    Endpoints:
        POST /api/appointments/doctor-schedule/ - Create doctor schedule(s)
        GET /api/appointments/doctor-schedule/ - Get all doctor schedules

    Features:
        - Bulk schedule creation support
        - Set working days, shift types, and time slots
        - Configure room numbers and max appointments
        - Define validity period for schedules
        - Retrieve complete schedule with doctor and department details
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
            """API for creating doctor schedules (supports bulk creation)"""
            try:
                
                is_bulk = isinstance(request.data, list)
                
                if is_bulk:

                    serializer = DoctorScheduleSerializer(data=request.data, many=True)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(
                            {"message": f"Successfully created {len(serializer.validated_data)} schedules"},
                            status=status.HTTP_201_CREATED
                        )
                else:
                    
                    serializer = DoctorScheduleSerializer(data=request.data)
                    if serializer.is_valid():
                        serializer.save()
                        return Response(
                            {"message": "Successfully scheduled the doctor"},
                            status=status.HTTP_201_CREATED
                        )
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                return Response(
                    {"detail": f"An error occurred while scheduling: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            

    def get(self, request):
        """API for getting Doctor Schedule with details:
        Returns:
        - name of the doctor
        - department
        - specialisation
        - schedule details
        """
        try:
            doctors = Doctor.objects.select_related(
                'user',
                'specialization',
                'specialization__department'  
            ).prefetch_related(
                'schedules'  
            ).all()
            
            response_data = []
            for doctor in doctors:
                
                schedules = []
                for schedule in doctor.schedules.all():
                    schedules.append({
                        'day': schedule.day_of_week,
                        'shift_type': schedule.shift_type,
                        'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                        'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                        'room_number': schedule.room_number,
                        'max_appointments': schedule.max_appointments,
                        'valid_from': schedule.valid_from,
                        'valid_to': schedule.valid_to
                    })
                
                doctor_data = {
                    'doctor_id': doctor.id,
                    'doctor_name': f"Dr. {doctor.user.first_name} {doctor.user.last_name}",
                    'specialization': {
                        'specialization_id': doctor.specialization.id if doctor.specialization else None,
                        'name': doctor.specialization.name if doctor.specialization else None,
                        'code': doctor.specialization.code if doctor.specialization else None,
                        'department': doctor.specialization.department.name if doctor.specialization and doctor.specialization.department else None,
                        'departmennt_id': doctor.specialization.department.id if doctor.specialization and doctor.specialization.department else None
                    },
                    'schedules': schedules
                }
                response_data.append(doctor_data)
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error fetching doctor schedules: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Note: DoctorDepartmentViewset is part of DOCTOR MANAGEMENT section

class DoctorDepartmentViewset(APIView):
    """
    Doctor-Department Listing API

    Endpoint:
        GET /api/appointments/doctor-department/ - Get doctors grouped by department

    Features:
        - Retrieve doctors organized by department
        - Show doctor name, ID, and active status
        - Includes specialization and department information
    """
    # permission_classes = [IsReceptionist]

    def get(self, request):
        try:
            doctor_details = Doctor.objects.select_related(
                'user',
                'specialization',
                'specialization__department',
            ).all()

            department_data = defaultdict(list)

            for doctor in doctor_details:
                doctor_data = {
                    "doctor_id": doctor.id,
                    "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}",
                    "is_active": doctor.is_active,
                }
                department_name = doctor.specialization.department.name
                department_data[department_name].append(doctor_data)

            return Response(dict(department_data), status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Error fetching doctors: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



# ============================================================================
# APPOINTMENT MANAGEMENT APIs
# ============================================================================

class TodayPatientAppointment(APIView):
    """
    Daily Appointment View API

    Endpoint:
        GET /api/appointments/daily-appointment-view/ - Get appointments with date filtering

    Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)

    Features:
        - Filter appointments by date ranges
        - Track follow-up appointments
        - Show parent consultation information
        - Prioritize scheduled appointments
        - Include patient details and appointment status
    """
    # permission_classes = [IsReceptionist]

    def get_follow_up_context(self, appointment):
        # print("trueeeeeeee")
        # print(appointment,"siuiuiiiuiu")
        """Get follow-up context for an appointment."""
        context = {
            "is_follow_up": appointment.is_follow_up,
            "follow_up_indicator": "🔄" if appointment.is_follow_up else "",
            "patient_phone": appointment.patient.contact_number,
        }

        # If this is a follow-up appointment, add parent consultation info
        if appointment.is_follow_up and appointment.parent_consultation:
            context.update({
                "parent_consultation_id": appointment.parent_consultation.id,
                "parent_diagnosis": appointment.parent_consultation.diagnosis,
                "parent_appointment_date": appointment.parent_consultation.appointment.appointment_date,
                "follow_up_reason": f"Follow-up for: {appointment.parent_consultation.diagnosis}"
            })

        # Check if this appointment has any scheduled follow-ups

        consultations = DoctorConsultation.objects.filter(appointment=appointment)
        if consultations.exists():
            consultation = consultations.first()
            if consultation.follow_up_date:
                context.update({
                    "has_follow_up_scheduled": True,
                    "next_follow_up_date": consultation.follow_up_date,
                    "follow_up_note": f"Next follow-up: {consultation.follow_up_date}"
                })
            else:
                context.update({
                    "has_follow_up_scheduled": False,
                    "next_follow_up_date": None,
                    "follow_up_note": ""
                })

        return context

    def get(self, request, *args, **kwargs):
        """Retrieve appointments with date filtering

        Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)
        """
        try:
            india_tz = pytz.timezone('Asia/Kolkata')
            today = datetime.now(india_tz).date()

            # Get filter parameters
            filter_type = request.query_params.get('filter_type', 'today').lower()
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')

            # Calculate date range based on filter_type
            if filter_type == 'today':
                start_date = today
                end_date = today
            elif filter_type == 'week':
                start_date = today - timedelta(days=today.weekday())  # Monday of current week
                end_date = start_date + timedelta(days=6)  # Sunday
            elif filter_type == 'month':
                start_date = today.replace(day=1)  # First day of current month
                next_month = start_date.replace(day=28) + timedelta(days=4)
                end_date = next_month - timedelta(days=next_month.day)  # Last day of current month
            elif filter_type == 'custom':
                if not from_date or not to_date:
                    return Response({
                        "status": "error",
                        "message": "from_date and to_date are required for custom filter"
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(to_date, '%Y-%m-%d').date()

                    if start_date > end_date:
                        return Response({
                            "status": "error",
                            "message": "from_date cannot be after to_date"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "status": "error",
                    "message": "Invalid filter_type. Use 'today', 'week', 'month', or 'custom'"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Filter appointments by date range
            appointments = Appointment.objects.filter(
                appointment_date__gte=start_date,
                appointment_date__lte=end_date,created_by=request.user
            ).select_related(
                'patient', 'doctor', 'doctor__user', 'doctor__specialization',
                'parent_consultation', 'parent_consultation__appointment'
            ).annotate(
                scheduled_priority=Case(
                    When(visit_status="Scheduled", then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            ).order_by('appointment_date', 'scheduled_priority', 'appointment_time')

            # Add follow-up information to each appointment
            appointment_data = []
            for appointment in appointments:
                serializer = AppointmentSerializer(appointment)
                appointment_info = serializer.data

                # Add follow-up context
                follow_up_context = self.get_follow_up_context(appointment)
                appointment_info.update(follow_up_context)

                appointment_data.append(appointment_info)

            return Response(appointment_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to fetch appointments: {str(e)}")
            return Response({
                "status": "error",
                "message": "Error fetching appointments"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientAppointmentView(APIView):
    """
    Patient Appointment Management API

    Endpoints:
        POST /api/appointments/patient-appointment/ - Create new appointment
        GET /api/appointments/patient-appointment/ - Get filtered appointments

    Query Parameters (GET):
        - patient_id: Filter by patient ID
        - doctor_id: Filter by doctor ID
        - date: Filter by specific date

    Features:
        - Create patient appointments with auto-generated ID
        - Automatic follow-up detection and linking
        - Filter appointments by patient, doctor, or date
        - Link to parent consultations for follow-ups
        - Track follow-up appointments
    """
    # permission_classes = [IsReceptionist]

    def get_queryset(self, request):
        """Helper to filter appointments based on query parameters."""
        appointments = Appointment.objects.filter(created_by=request.user)
        
        patient_id = request.query_params.get('patient_id')
        doctor_id = request.query_params.get('doctor_id')
        date = request.query_params.get('date')
 
        if patient_id:
            appointments = appointments.filter(patient__patient_id=patient_id)
        if doctor_id:
            appointments = appointments.filter(doctor__doctor_id=doctor_id)
        if date:
            appointments = appointments.filter(appointment_date=date)
 
        return appointments
 
    def get(self, request, *args, **kwargs):
        """Retrieve filtered appointment list."""
        try:
            appointments = self.get_queryset(request)
            serializer = AppointmentSerializer(appointments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to fetch appointments: {str(e)}")
            return Response({
                "status": "error",
                "message": "Error fetching appointments"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    def create_appointment(self, validated_data):
        """Handles appointment creation with a new ID."""
        validated_data['appointment_id'] = get_next_appointment_id()
        return Appointment.objects.create(**validated_data)

    def check_follow_up_appointment(self, appointment):
        """Check if this appointment matches any follow-up dates from previous consultations."""


        # Look for consultations with follow_up_date matching this appointment's date
        matching_consultations = DoctorConsultation.objects.filter(
            appointment__patient=appointment.patient,
            appointment__doctor=appointment.doctor,
            follow_up_date=appointment.appointment_date
        ).select_related('appointment')

        if matching_consultations.exists():
            # Get the most recent consultation that matches
            latest_consultation = matching_consultations.order_by('-created_on').first()

            # Update this appointment as a follow-up
            appointment.parent_consultation = latest_consultation
            appointment.is_follow_up = True
            appointment.save()

            return {
                "is_follow_up": True,
                "parent_consultation_id": latest_consultation.id,
                "parent_appointment_id": latest_consultation.appointment.id,
                "original_diagnosis": latest_consultation.diagnosis,
                "follow_up_for_date": latest_consultation.appointment.appointment_date
            }

        return None
 
    def post(self, request, *args, **kwargs):
        """Create a new appointment entry."""
        try:
            with transaction.atomic():
                appointment_data = request.data.copy()
                appointment_data['appointment_id'] = get_next_appointment_id()
 
                serializer = AppointmentSerializer(data=appointment_data)
                serializer.is_valid(raise_exception=True)
                appointment = serializer.save(created_by=request.user)

                # Check if this appointment matches any follow-up dates
                follow_up_info = self.check_follow_up_appointment(appointment)

                response_data = serializer.data
                if follow_up_info:
                    response_data.update(follow_up_info)

                return Response({
                    "status": "success",
                    "appointment_id": response_data['appointment_id'],
                    "data": response_data
                }, status=status.HTTP_201_CREATED)
 
        except serializers.ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            return Response({
                "status": "error",
                "message": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
 
        except Exception as e:
            logger.error(f"Appointment creation failed: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to create appointment"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AppointmentStatusView(APIView):
    """
    Appointment Status Update API

    Endpoint:
        PATCH /api/appointments/update-appoointment-status/ - Update appointment status/reschedule

    Request Body:
        - appointment_id: ID of the appointment
        - status: New status (optional)
        - date: New appointment date for rescheduling (optional)
        - time: New appointment time for rescheduling (optional)

    Features:
        - Update appointment status
        - Reschedule appointments
        - Prevent modification of completed appointments
        - Support partial updates
    """
    # permission_classes = [IsAdminUser]

    def patch(self, request, *args, **kwargs):
        """Update appointment status and/or reschedule"""
        try:
            appointment_id = request.data.get('appointment_id')
            new_status = request.data.get('status')
            
            # Check if this is a reschedule request (has date and time)
            new_date = request.data.get('date')
            new_time = request.data.get('time')
            
            # Debug log to check what's being received
            print(f"Received data: appointment_id={appointment_id}, status={new_status}, date={new_date}, time={new_time}")
            
            appointment = Appointment.objects.get(appointment_id=appointment_id)
            
            # If completed, don't allow changes
            if appointment.visit_status == 'COMPLETED':
                return Response({
                    "status": "error",
                    "message": "Completed appointments cannot be modified"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status if provided
            if new_status:
                appointment.visit_status = new_status
            
            # Update date and time if provided (reschedule)
            if new_date:
                appointment.appointment_date = new_date
            if new_time:
                appointment.appointment_time = new_time
                
            # Save changes
            appointment.save()
            
            # Log post-save values
            print(f"After save: appointment_date={appointment.appointment_date}, appointment_time={appointment.appointment_time}")
            
            response_data = {
                "status": "success",
                "new_status": appointment.visit_status
            }
            
            # Add reschedule info to response if applicable
            if new_date or new_time:
                response_data["rescheduled"] = True
                response_data["new_date"] = str(appointment.appointment_date)
                response_data["new_time"] = str(appointment.appointment_time)
                
            return Response(response_data)
                   
        except Appointment.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Appointment not found"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error updating appointment: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# DOCTOR APPOINTMENT VIEWS APIs
# ============================================================================

class DoctorAppointmentView(APIView):
    """
    Doctor-Specific Appointment View API

    Endpoint:
        GET /api/appointments/doctor-appointment-view/ - Get appointments for logged-in doctor

    Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)

    Features:
        - View appointments for the logged-in doctor
        - Filter by date ranges (today, week, month, custom)
        - Show only relevant statuses (CHECKED_IN, IN_CONSULTATION, etc.)
        - Indicate if appointments can be edited
        - Mark past, present, and future appointments
        - Include patient demographics
    """
    # permission_classes = [IsAdminUser]

    def get(self, request):
        """Get appointments for the specified doctor with date filtering

        Query Parameters:
        - filter_type: 'today', 'week', 'month', 'custom' (default: 'today')
        - from_date: Start date for custom range (YYYY-MM-DD)
        - to_date: End date for custom range (YYYY-MM-DD)
        """

        try:
            doctor_id = request.user.doctor.id
            print(doctor_id, "testttt")

            try:
                doctor = Doctor.objects.get(id=doctor_id)
            except Doctor.DoesNotExist:
                return Response({
                    "status": "error",
                    "message": "Doctor not found"
                }, status=status.HTTP_404_NOT_FOUND)

            india_tz = pytz.timezone('Asia/Kolkata')
            today = datetime.now(india_tz).date()

            # Get filter parameters
            filter_type = request.query_params.get('filter_type', 'today').lower()
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')

            # Calculate date range based on filter_type
            if filter_type == 'today':
                start_date = today
                end_date = today
            elif filter_type == 'week':
                start_date = today - timedelta(days=today.weekday())  # Monday of current week
                end_date = start_date + timedelta(days=6)  # Sunday
            elif filter_type == 'month':
                start_date = today.replace(day=1)  # First day of current month
                next_month = start_date.replace(day=28) + timedelta(days=4)
                end_date = next_month - timedelta(days=next_month.day)  # Last day of current month
            elif filter_type == 'custom':
                if not from_date or not to_date:
                    return Response({
                        "status": "error",
                        "message": "from_date and to_date are required for custom filter"
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(to_date, '%Y-%m-%d').date()

                    if start_date > end_date:
                        return Response({
                            "status": "error",
                            "message": "from_date cannot be after to_date"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "status": "error",
                    "message": "Invalid filter_type. Use 'today', 'week', 'month', or 'custom'"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Filter appointments by date range
            appointments = Appointment.objects.select_related('patient').filter(
                visit_status__in=['CHECKED_IN', 'IN_CONSULTATION', 'SCHEDULED', 'FOLLOW_UP','PRESCRIPTION_READY','DISPENSED','PAYMENT_COMPLETE'],
                doctor=doctor,
                appointment_date__gte=start_date,
                appointment_date__lte=end_date
            ).order_by('-appointment_date', 'appointment_time')
            
            if not appointments.exists():
                return Response({
                    "status": "success",
                    "message": "No Appointments Found"
                }, status=status.HTTP_200_OK)

            for appointment in appointments:
                print(appointment.patient.first_name, "appointment")

            appointment_data = []
            for appt in appointments:
                # Determine if appointment can be edited
                can_edit = appt.visit_status in ['PRESCRIPTION_READY', 'DISPENSED', 'PAYMENT_COMPLETE']
                
                appointment_data.append({
                    "appointment_id": appt.id,
                    "appointment_date": appt.appointment_date.strftime("%d-%m-%Y"),
                    "appointment_time": appt.appointment_time.strftime("%H:%M"),
                    "visit_status": appt.visit_status,
                    "visit_reason": appt.visit_reason,
                    "patient_name": appt.patient.first_name + " " + appt.patient.last_name,
                    "patient_gender": appt.patient.gender,
                    "patient_age": appt.patient.age,
                    "patient_id": appt.patient.patient_id,
                    "p_id": appt.patient.id,
                    "is_today": appt.appointment_date == today,
                    "is_past": appt.appointment_date < today,
                    "is_future": appt.appointment_date > today,
                    "can_edit": can_edit  # ADD THIS FLAG
                })

            return Response({
                "status": "success",
                "current_date": today.strftime("%d-%m-%Y"),
                "total_appointments": len(appointment_data),
                "appointments": appointment_data
            })

        except Exception as e:
            logger.error(f"Appointment fetch error: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to retrieve appointments"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# APPOINTMENT HISTORY & CONSULTATION APIs
# ============================================================================

class PharmacyAppointmentsView(APIView):
    """
    Pharmacy Appointments View API

    Endpoint:
        GET /api/appointments/appointment-history/ - Get pharmacy-relevant appointments

    Query Parameters:
        - visit_status: Filter by specific status (PRESCRIPTION_READY, DISPENSED, PAYMENT_COMPLETE)
        - date: Specific date (YYYY-MM-DD)
        - from_date: Start date for range (YYYY-MM-DD)
        - to_date: End date for range (YYYY-MM-DD)

    Features:
        - Filter appointments by pharmacy-relevant statuses
        - Date range filtering (today, specific date, date range)
        - Include patient and doctor information
        - Show appointment details for dispensing workflow
    """

    def get(self, request):
        try:
            # Get query parameters
            visit_status = request.query_params.get('visit_status')
            date = request.query_params.get('date')
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')

            # Build base query
            india_tz = pytz.timezone('Asia/Kolkata')

            # Filter by allowed statuses
            allowed_statuses = ['PRESCRIPTION_READY', 'DISPENSED', 'PAYMENT_COMPLETE']

            if visit_status:
                # Single status filter
                if visit_status not in allowed_statuses:
                    return Response({
                        "status": "error",
                        "message": f"Invalid status. Allowed: {', '.join(allowed_statuses)}"
                    }, status=status.HTTP_400_BAD_REQUEST)

                appointments = Appointment.objects.filter(visit_status=visit_status)
            else:
                # All allowed statuses
                appointments = Appointment.objects.filter(visit_status__in=allowed_statuses)

            # Date filtering
            if date:
                # Specific date
                try:
                    filter_date = datetime.strptime(date, '%Y-%m-%d').date()
                    appointments = appointments.filter(appointment_date=filter_date)
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)

            elif from_date and to_date:
                # Date range
                try:
                    start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                    end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
                    appointments = appointments.filter(
                        appointment_date__gte=start_date,
                        appointment_date__lte=end_date
                    )
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)

            elif from_date:
                # From date only
                try:
                    start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                    appointments = appointments.filter(appointment_date__gte=start_date)
                except ValueError:
                    return Response({
                        "status": "error",
                        "message": "Invalid date format. Use YYYY-MM-DD"
                    }, status=status.HTTP_400_BAD_REQUEST)

            else:
                # Default to today if no date filter
                today = datetime.now(india_tz).date()
                appointments = appointments.filter(appointment_date=today,created_by=request.user)

            # Select related data and order
            appointments = appointments.select_related(
                'patient', 'doctor', 'doctor__user'
            ).order_by('-appointment_date', 'appointment_time')

            if not appointments.exists():
                return Response({
                    "status": "success",
                    "message": "No appointments found",
                    "data": []
                }, status=status.HTTP_200_OK)

            # Format response
            appointment_data = []
            for appt in appointments:
                appointment_data.append({
                    "appointment_id": appt.id,
                    "appointment_date": appt.appointment_date,
                    "appointment_time": appt.appointment_time.strftime("%H:%M") if appt.appointment_time else None,
                    "visit_status": appt.visit_status,
                    "patient_id": appt.patient.patient_id,
                    "p_id": appt.patient.id,
                    "patient_name": f"{appt.patient.first_name} {appt.patient.last_name}",
                    "patient_age": appt.patient.age,
                    "patient_gender": appt.patient.gender,
                    "patient_contact": appt.patient.contact_number,
                    "doctor_name": f"Dr. {appt.doctor.user.first_name} {appt.doctor.user.last_name}"
                })

            return Response({
                "status": "success",
                "total": len(appointment_data),
                "data": appointment_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Pharmacy appointments fetch error: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientConsultationHistoryView(APIView):
    """
    Patient Consultation History API

    Endpoint:
        GET /api/appointments/patient-consultation-history/ - Search and get patient consultation history

    Query Parameters:
        - patient_id: Search by patient ID
        - patient_name: Search by patient name (first or last)
        - phone_number: Search by phone number

    Features:
        - Multi-parameter search (patient ID, name, phone)
        - Complete consultation history for matched patients
        - Include prescribed medicines for each consultation
        - Show diagnosis, doctor notes, and recommended tests
        - Track follow-up dates and appointments
        - Return patient demographics
    """

    def get(self, request):
        try:
            # Get search parameters
            patient_id = request.query_params.get('patient_id')
            patient_name = request.query_params.get('patient_name')
            phone_number = request.query_params.get('phone_number')

            # At least one search parameter is required
            if not patient_id and not patient_name and not phone_number:
                return Response({
                    "status": "error",
                    "message": "Please provide at least one search parameter: patient_id, patient_name, or phone_number"
                }, status=status.HTTP_400_BAD_REQUEST)

        

            patient_query = Q()

            if patient_id:
                patient_query &= Q(patient_id__icontains=patient_id)

            if patient_name:
                # Search in both first and last name
                patient_query &= (Q(first_name__icontains=patient_name) | Q(last_name__icontains=patient_name))

            if phone_number:
                patient_query &= Q(contact_number__icontains=phone_number)

            # Find patients matching criteria
            patients = PatientRegistration.objects.filter(patient_query)

            if not patients.exists():
                return Response({
                    "status": "success",
                    "message": "No patients found matching the search criteria",
                    "data": []
                }, status=status.HTTP_200_OK)

            # Get consultation history for all matching patients
            results = []
            for patient in patients:
                # Get all appointments for this patient
                patient_appointments = Appointment.objects.filter(patient=patient,created_by = request.user)

                # Get all consultations
                consultations = DoctorConsultation.objects.filter(
                    appointment__in=patient_appointments
                ).select_related(
                    'appointment', 'appointment__doctor', 'appointment__doctor__user'
                ).prefetch_related(
                    'prescribedmedicine_set__medicine'
                ).order_by('-created_on')

                # Format consultation history
                consultation_history = []
                for consultation in consultations:
                    # Get prescribed medicines
                    prescribed_medicines = []
                    for prescribed in consultation.prescribedmedicine_set.all():
                        prescribed_medicines.append({
                            "medicine_name": prescribed.medicine.name,
                            "dosage": prescribed.dosage,
                            "frequency": prescribed.frequency,
                            "duration": prescribed.duration,
                            "quantity": prescribed.quantity,
                            "instructions": prescribed.instructions
                        })

                    consultation_history.append({
                        "consultation_id": consultation.id,
                        "appointment_id": consultation.appointment.id,
                        "appointment_date": consultation.appointment.appointment_date,
                        "doctor_name": f"Dr. {consultation.appointment.doctor.user.first_name} {consultation.appointment.doctor.user.last_name}",
                        "diagnosis": consultation.diagnosis,
                        "doctor_notes": consultation.doctor_notes,
                        "recommended_tests": consultation.recommended_tests,
                        "follow_up_date": consultation.follow_up_date,
                        "prescribed_medicines": prescribed_medicines,
                        "consultation_date": consultation.created_on.date()
                    })

                results.append({
                    "patient_info": {
                        "patient_id": patient.patient_id,
                        "p_id": patient.id,
                        "name": f"{patient.first_name} {patient.last_name}",
                        "age": patient.age,
                        "gender": patient.gender,
                        "contact_number": patient.contact_number,
                        "email": patient.email
                    },
                    "total_consultations": consultations.count(),
                    "consultation_history": consultation_history
                })

            return Response({
                "status": "success",
                "total_patients": len(results),
                "data": results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Patient history search error: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


