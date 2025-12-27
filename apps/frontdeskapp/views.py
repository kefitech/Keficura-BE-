"""
Hospital Information System - Front Desk Module Views
======================================================

Author: Athul Gopan
Created: 2025
Module: Front Desk Management APIs

This module contains all API endpoints for:
1. Front Desk Profile Management

API Structure:
    - All views inherit from APIView
    - Transactions are wrapped with @transaction.atomic
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from django.shortcuts import render
from django.contrib.auth.models import User, Group
from rest_framework.response import Response
from utils.auth_helper import *
from utils.email_helper import *
from apps.data_hub.models import *
from .serializers import *
from rest_framework.views import APIView
from django.db import transaction
from rest_framework import viewsets, status, permissions


# ============================================================================
# FRONT DESK PROFILE APIs
# ============================================================================

class FrontdeskProfileView(APIView):
    """
    API view to create a new user and Front desk profile simultaneously

    Endpoint: POST /api/frontdesk/profile/
    Permission: Admin users only

    This view handles the complete onboarding process for front desk staff:
    1. Creates Django User account
    2. Assigns to front desk group
    3. Creates FrontDesk profile with additional details
    4. Sends welcome email with credentials
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        """
        Creates a new user and associated Front desk profile

        Request Body:
            - username (required): Unique username for login
            - email (required): Email address for communication
            - password (required): Initial password
            - first_name (optional): Staff first name
            - last_name (optional): Staff last name
            - date_of_birth (optional): Date of birth
            - gender (optional): Gender
            - hire_date (optional): Employment start date
            - contact_number (optional): Phone number
            - employee_id (optional): Unique employee identifier
            - shift_schedule (optional): Work shift information
            - profile_picture (optional): Profile image file

        Returns:
            201: Profile created successfully with confirmation message
            400: Validation errors or duplicate username/email
        """
        # ====================================================================
        # STEP 1: Extract and validate required fields
        # ====================================================================
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        # Validate required fields presence
        if not username or not email or not password:
            return Response(
                {"detail": "Username, email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for duplicate username
        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Username already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check for duplicate email
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ====================================================================
        # STEP 2: Create Django User and assign to front desk group
        # ====================================================================
        try:
            # Create base user account
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
               )

            # Assign user to front desk group (ID: 4)
            front_desk_group = Group.objects.get(id=4)
            user.groups.add(front_desk_group)
            user.save()

        except Group.DoesNotExist:
            # Rollback user creation if group doesn't exist
            user.delete()
            return Response(
                {"detail": "Front desk group with ID 4 does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Handle any other user creation errors
            return Response(
                {"detail": f"Failed to create user: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ====================================================================
        # STEP 3: Prepare front desk profile data
        # ====================================================================
        front_desk_data = {
            'user': user.id,
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),
            'hire_date': request.data.get('hire_date'),
            'contact_number': request.data.get('contact_number'),
            'email': email,
            'employee_id': request.data.get('employee_id'),
            'shift_schedule': request.data.get('shift_schedule'),

            # Address fields - currently not in use
            # 'home_address': request.data.get('home_address'),
            # 'home_city': request.data.get('home_city'),
            # 'home_state': request.data.get('home_state'),
            # 'home_country': request.data.get('home_country'),
            # 'home_zip_code': request.data.get('home_zip_code'),
        }

        # Add profile picture if provided
        if 'profile_picture' in request.FILES:
            front_desk_data['profile_picture'] = request.FILES['profile_picture']

        # ====================================================================
        # STEP 4: Create front desk profile using serializer
        # ====================================================================
        serializer = FrontDeskSerializer(data=front_desk_data)
        if serializer.is_valid():
            # Save the front desk profile
            front_desk = serializer.save()

            # ================================================================
            # STEP 5: Send welcome email with credentials
            # ================================================================
            try:
                # Note: Async email delivery with Celery is commented out
                # send_doctor_credentials_email.delay(
                #     email=user.email,
                #     first_name=user.first_name,
                #     last_name=user.last_name,
                #     username=username,
                #     password=password
                # )

                # Synchronous email sending
                # TODO: Replace with front_desk specific email template
                send_doctor_credentials_email(
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=username,
                    password=password
                )

                # Success response when email is sent
                response_data = {
                    "message": "Front desk profile created successfully. Credentials have been sent to their email."
                }

            except Exception as e:
                # Email failed but profile was created successfully
                # Provide credentials in response for manual delivery
                response_data = {
                    "message": "Front desk profile created successfully, but failed to send email with credentials.",
                    "warning": "Please provide the front desk staff with their credentials manually.",
                    "credentials": {
                        "username": username,
                        "password": password
                    }
                }

            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            # Profile validation failed - rollback user creation
            user.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






        
