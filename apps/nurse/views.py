"""
Hospital Information System - Nurse Module Views
=================================================

Author: Athul Gopan
Created: 2025
Module: Nurse Management APIs

This module contains all API endpoints for:
1. Nurse Profile Management
2. Nurse Shift Assignment

API Structure:
    - All views inherit from APIView
    - Transactions are wrapped with @transaction.atomic
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from django.shortcuts import render
from apps.data_hub.models import *
from .serializers import *
from rest_framework.views import APIView
from django.db import transaction
from rest_framework import viewsets, status, permissions
from django.contrib.auth.models import User, Group
from rest_framework.response import Response
from utils.auth_helper import *
from utils.email_helper import *


# ============================================================================
# NURSE MANAGEMENT APIs
# ============================================================================

class CreateNurseView(APIView):
    """
    API view to create a new user and Nurse profile simultaneously
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
            
            nurse_group = Group.objects.get(id=3)
            user.groups.add(nurse_group)
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
        
        # Create doctor profile with the new user
        nurse_data = {
            'user': user.id,
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),

            'contact_number': request.data.get('contact_number'),
            'email': email,

            # 'home_address': request.data.get('home_address'),
            # 'home_city': request.data.get('home_city'),
            # 'home_state': request.data.get('home_state'),
            # 'home_country': request.data.get('home_country'),
            # 'home_zip_code': request.data.get('home_zip_code'),

            'qualification': request.data.get('qualification'),
            'experience_years': request.data.get('experience_years'),
        }
        
        # If profile picture was included
        if 'profile_picture' in request.FILES:
            nurse_data['profile_picture'] = request.FILES['profile_picture']
        
        serializer = NurseSerializer(data=nurse_data)
        if serializer.is_valid():
            nurse = serializer.save()  
            
            try:
                # send_doctor_credentials_email.delay(
                #     email=user.email,
                #     first_name=user.first_name,
                #     last_name=user.last_name,
                #     username=username,
                #     password=password
                # )       
                send_doctor_credentials_email(
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=username,
                    password=password
                )           
                response_data = {
                    "message": "Nurse profile created successfully. Credentials have been sent to their respective email."
                }

            except Exception as e:
                print(f"Failed to send email: {str(e)}")
                response_data = {
                    "message": "Nurse profile created successfully, but failed to send email with credentials.",
                    "warning": "Please provide the Nurse with their credentials manually.",
                    "credentials": {
                        "username": username,
                        "password": password
                    }
                }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            user.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get (self, request):
        try:
            Nurse_details = Nurse.objects.select_related(
                'user',
            ).all()
            response_data = []

            for nurse in Nurse_details:
                nurse_data = {
                    "nurse_id" : nurse.id,
                    "nurse_name" : f"{nurse.user.first_name} {nurse.user.last_name}",
                    "is_active": nurse.is_active,
                }
                response_data.append(nurse_data)
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"detail": f"Error fetching doctors: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# NURSE SHIFT ASSIGNMENT APIs
# ============================================================================

class NurseShiftAssignmentView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        """
        Assigns a nurse to a shift
        """
        try:
            serializer = NurseShiftSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"detail": "Invalid data", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            
            assignment = serializer.save()
            
            return Response(
                {
                    "detail": "Nurse assigned to shift successfully",
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"detail": f"Error assigning nurse to shift: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
