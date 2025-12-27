"""
Hospital Information System - Accounts Module Views
====================================================

Author: Athul Gopan
Created: 2025
Module: Authentication & User Management APIs

This module contains all API endpoints for:
1. User Profile Management
2. Authentication (Login)
3. Menu Mapping & Permissions
4. Admin Registration

API Structure:
    - All views inherit from APIView or ViewSet
    - Transactions are wrapped with @transaction.atomic
    - Error handling follows standardized response format
    - Permission classes are configured per view
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from utils.auth_helper import *
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from utils.auth_helper import *
from django.contrib.auth.models import User, Group
from django.db import transaction
from apps.accounts.serializers import *
from utils.email_helper import *
from apps.data_hub.models import *

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# USER PROFILE MANAGEMENT APIs
# ============================================================================

class UserViewSet(viewsets.ModelViewSet):
    """
    User Profile Management ViewSet

    Endpoints:
        GET /api/accounts/users/ - List all users
        POST /api/accounts/users/ - Create new user
        GET /api/accounts/users/{id}/ - Get user details
        PUT /api/accounts/users/{id}/ - Update user
        PATCH /api/accounts/users/{id}/ - Partial update user
        DELETE /api/accounts/users/{id}/ - Delete user
        GET /api/accounts/users/me/ - Get current user profile
        PUT /api/accounts/users/me/ - Update current user profile

    Features:
        - Full CRUD operations for users
        - Self-service profile management (/me endpoint)
        - Different serializers for create/update vs read operations
        - Admin-only access for user management
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserSerializer
        return UserProfileSerializer
    
    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
            
        # Update profile
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def create_user_profile(self, request):
        pass


# ============================================================================
# AUTHENTICATION APIs
# ============================================================================

class LoginView(APIView):
    """
    User Login API

    Endpoint:
        POST /api/accounts/login/ - User authentication

    Request Body:
        - username: User's username
        - password: User's password

    Features:
        - JWT token generation (access & refresh tokens)
        - User validation and authentication
        - Account status verification
        - Returns user profile and tokens
        - Public endpoint (no authentication required)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'User account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Get user's groups
        user_groups = user.groups.all()
        
        # Get menu items based on user's group permissions
        
        # Format response data
        response_data = {
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
            },
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


# ============================================================================
# MENU MAPPING APIs
# ============================================================================

class MenuMapping(APIView):
    """
    Menu Mapping & Permission Management API

    Endpoints:
        POST /api/accounts/menu/ - Get user menu items
        PATCH /api/accounts/menu/ - Update menu permission mapping

    Request Body (POST):
        - user_id: ID of the user

    Request Body (PATCH):
        - user_id: ID of the user making the update
        - menu_id: ID of the menu item
        - permision_id: ID of the permission mapping
        - group_id: ID of the user group
        - is_active: Active status (true/false)

    Features:
        - Retrieve menu items based on user group permissions
        - Update menu permission mappings
        - Validate user permissions before updates
        - Group-based access control
    """

    def post(self, request):
        data = request.data
        user_id = data['user_id']
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user_groups = user.groups.all()
        menu_items = get_user_menu_items(user, user_groups)
        response_data = {
            'menu': menu_items
        }
        return Response(response_data, status=status.HTTP_200_OK)
    def patch(self, request):
        
        data = request.data
        user_id = data.get('user_id')
        menu_id = data.get('menu_id')
        permission_id = data.get('permision_id')  # Note the typo in 'permision_id'
        group_id = data.get('group_id')
        is_active = data.get('is_active')
        
        # Validate data
        if not all([user_id, menu_id, permission_id, group_id]):
            return Response(
                {'error': 'Missing required fields'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists and has permission to update
        try:
            user = User.objects.get(id=user_id)
            if not user.is_superuser and not user.is_staff:
                return Response(
                    {'error': 'User does not have permission to update menu mappings'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if menu exists
        try:
            menu = Menu.objects.get(id=menu_id)
        except Menu.DoesNotExist:
            return Response(
                {'error': 'Menu not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if group exists
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {'error': 'Group not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update or create the menu permission mapping
        try:
            menu_permission = MenuPermissionMapper.objects.get(id=permission_id)
            
            # Ensure the permission matches the requested menu and group
            if menu_permission.menu.id != menu_id or menu_permission.auth_group_permission.id != group_id:
                return Response(
                    {'error': 'Permission ID does not match the specified menu and group'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update the active status
            menu_permission.is_active = is_active
            menu_permission.save()
            
            return Response(
                {
                    'message': 'Menu permission updated successfully',
                    'menu_permission': {
                        'id': menu_permission.id,
                        'menu_id': menu_permission.menu.id,
                        'group_id': menu_permission.auth_group_permission.id,
                        'is_active': menu_permission.is_active
                    }
                }, 
                status=status.HTTP_200_OK
            )
        
        except MenuPermissionMapper.DoesNotExist:
            return Response(
                {'error': 'Menu permission mapping not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# ADMIN REGISTRATION APIs
# ============================================================================

class Admin_registrationView(APIView):
    """
    Administrator Registration API

    Endpoints:
        POST /api/accounts/admin/ - Create new administrator with user account
        GET /api/accounts/admin/ - List all administrators

    Features:
        - Create user account and administrator profile simultaneously
        - Auto-assign to admin group (Group ID: 1)
        - Upload profile picture
        - Send credentials via email
        - Link to department and specialization
        - Validation for duplicate username/email
        - Super admin access only
    """
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def post(self, request):
        """
        Creates a new user and associated Admin profile
        """
        try:
            
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
                admin_group = Group.objects.get(id=1)
                user.groups.add(admin_group)
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
            
            admin_data = {
            'user': user.id,
            'date_of_birth': request.data.get('date_of_birth'),
            'gender': request.data.get('gender'),
            'phone_number': request.data.get('phone_number'),
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
            
            }
            if 'profile_picture' in request.FILES:
                admin_data['profile_picture'] = request.FILES['profile_picture']

            serializer = AdministratorSerializer(data=admin_data)
            if serializer.is_valid():
                admin = serializer.save()

                try:
                    send_doctor_credentials_email(
                    doctor=admin,
                    username=username,
                    password=password
                )                
                    response_data = {
                        "message": "Admin created successfully  credentials sent to the admin's email address  ", 
                    }

                except Exception as e:
                # print(f"Failed to send email: {str(e)}")
                    response_data = {
                        "message": "Admin profile created successfully, but failed to send email with credentials.",
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
                
        except Exception as e:
            logger.error(f"Error creating admin: {str(e)}")
            return Response(
                {"detail": f"Failed to create admin: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """API for getting all Admin"""
        try: 
            admin_details = Administrator.objects.select_related(
                'user'
            ).all()

            response_data = []

            for data in admin_details:
                admin_data = {
                    "admin_id" : data.id,
                    "admin_name":f"{data.user.first_name} {data.user.last_name}",
                    "is_activr" : data.is_active,

                }
                response_data . append(admin_data)
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Error fetching doctors: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        



    
    

