"""
Hospital Information System - Authentication & Authorization Helpers
===================================================================

Author: Athul Gopan
Created: 2025
Module: Authentication and Permission Management

This module provides custom permission classes and authentication utilities
for role-based access control (RBAC) in the Hospital Information System.

Components:
1. Custom Permission Classes - Role-based access control for different user types
2. Menu Management Functions - Dynamic menu generation based on user permissions

Permission Classes Available:
    - IsDoctor: Restricts access to doctors only
    - IsNurse: Restricts access to nurses only
    - IsReceptionist: Restricts access to receptionists only
    - IsPharmacist: Restricts access to pharmacists only
    - IsAdminUser: Restricts access to administrators only
    - IsSuperAdmin: Restricts access to super administrators only

Usage Example:
    from utils.auth_helper import IsDoctor, IsNurse

    class PatientView(APIView):
        permission_classes = [IsDoctor | IsNurse]  # Allow doctors or nurses
"""

from rest_framework.permissions import BasePermission
from apps.data_hub.models import *

import logging

# Set up logging for authentication and permission tracking
logger = logging.getLogger(__name__)


# ============================================================================
# ROLE-BASED PERMISSION CLASSES
# ============================================================================

class IsDoctor(BasePermission):
    """
    Custom permission class to restrict access to users in the 'Doctor' group.

    This permission checks if the authenticated user belongs to the Doctor group
    in the Django auth system.

    Returns:
        bool: True if user is authenticated and is a doctor, False otherwise
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.groups.filter(name="Doctor").exists()
        )


class IsNurse(BasePermission):
    """
    Custom permission class to restrict access to users in the 'Nurse' group.

    This permission checks if the authenticated user belongs to the Nurse group
    in the Django auth system.

    Returns:
        bool: True if user is authenticated and is a nurse, False otherwise
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="Nurse").exists()
        )


class IsReceptionist(BasePermission):
    """
    Custom permission class to restrict access to users in the 'Receptionist' group.

    This permission checks if the authenticated user belongs to the Receptionist
    group in the Django auth system.

    Returns:
        bool: True if user is authenticated and is a receptionist, False otherwise
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="Receptionist").exists()
        )


class IsPharmacist(BasePermission):
    """
    Custom permission class to restrict access to users in the 'Pharmacist' group.

    This permission checks if the authenticated user belongs to the Pharmacist
    group in the Django auth system.

    Returns:
        bool: True if user is authenticated and is a pharmacist, False otherwise
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="Pharmacist").exists()
        )


class IsAdminUser(BasePermission):
    """
    Custom permission class to restrict access to users in the 'Administrator' group.

    This permission checks if the authenticated user belongs to the Administrator
    group in the Django auth system. This is different from Django's built-in
    is_superuser flag.

    Returns:
        bool: True if user is authenticated and is an administrator, False otherwise
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="Administrator").exists()
        )


class IsSuperAdmin(BasePermission):
    """
    Custom permission class to restrict access to users in the 'SuperAdministrator' group.

    Super administrators have the highest level of access in the system,
    typically used for system configuration and user management.

    Returns:
        bool: True if user is authenticated and is a super administrator, False otherwise
    """
    def has_permission(self, request, view):
        # Log super admin access attempts for security auditing
        logger.debug(f"SuperAdmin permission check for user: {request.user.username}")

        return (
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="SuperAdministrator").exists()
        )
    


# ============================================================================
# DYNAMIC MENU MANAGEMENT
# ============================================================================

def get_user_menu_items(user, user_groups):
    """
    Generate a hierarchical menu structure based on user permissions and roles.

    This function creates a dynamic navigation menu by:
    1. Fetching menu items accessible to the user's groups
    2. Building a parent-child hierarchy
    3. Including permission and group information for each menu
    4. Marking menu items as active/accessible based on user permissions

    Args:
        user (User): The Django User object for whom to generate the menu
        user_groups (QuerySet): QuerySet of Group objects the user belongs to

    Returns:
        list: A list of root menu items, each containing:
            - id: Menu item ID
            - name: Internal menu name
            - title: Display title
            - code: Unique menu code
            - redirect_url: URL to navigate to
            - icon: Icon identifier for frontend
            - menu_order: Display order
            - feature_code: Associated feature code
            - is_active: Whether menu is active and accessible
            - is_accessible: Explicit accessibility flag
            - groups: List of groups that can access this menu
            - children: List of child menu items (same structure)

    Example:
        user = request.user
        user_groups = user.groups.all()
        menu_structure = get_user_menu_items(user, user_groups)
    """
    # ========================================================================
    # STEP 1: Fetch menu items based on user permissions
    # ========================================================================
    if user.is_superuser:
        # Superuser has access to all menu items regardless of permissions
        all_menu_items = Menu.objects.filter().order_by('menu_order')
    else:
        # Get menu IDs that are accessible to any of the user's groups
        permitted_menu_ids = MenuPermissionMapper.objects.filter(
            auth_group_permission__in=user_groups,
            is_active=True
        ).values_list('menu_id', flat=True)

        # Fetch all accessible menu items
        all_menu_items = Menu.objects.filter(
            id__in=permitted_menu_ids,
            is_active=True
        ).order_by('menu_order')

    # ========================================================================
    # STEP 2: Initialize data structures for menu hierarchy
    # ========================================================================
    root_menus = []  # Top-level menu items
    menu_dict = {}   # Dictionary for quick menu lookup by ID

    # Convert user groups to a set of IDs for efficient lookup
    user_group_ids = set(user_groups.values_list('id', flat=True))

    # ========================================================================
    # STEP 3: First Pass - Create dictionary of all menu items with metadata
    # ========================================================================
    for menu in all_menu_items:
        # Fetch all group permissions associated with this menu item
        menu_groups = MenuPermissionMapper.objects.filter(
            menu=menu,
            is_active=True
        ).select_related('auth_group_permission')

        # Build list of groups that can access this menu
        groups_info = []
        # Superusers can access everything by default
        is_accessible = user.is_superuser

        for menu_group in menu_groups:
            if menu_group.auth_group_permission:
                # Add group information to the menu metadata
                group_info = {
                    'id': menu_group.auth_group_permission.id,
                    'name': menu_group.auth_group_permission.name,
                    'permission_id': menu_group.id
                }
                groups_info.append(group_info)

                # Check if current user belongs to this group
                if menu_group.auth_group_permission.id in user_group_ids:
                    is_accessible = True

        # Build complete menu item data structure
        menu_data = {
            'id': menu.id,
            'name': menu.name,
            'title': menu.title,
            'code': menu.code,
            'redirect_url': menu.redirect_url,
            'icon': menu.icon,
            'menu_order': menu.menu_order,
            'feature_code': menu.feature_code,
            # Menu is active only if both the menu itself is active AND user has access
            'is_active': menu.is_active and is_accessible,
            'is_accessible': is_accessible,  # Explicit accessibility flag for frontend
            'groups': groups_info,
            'children': []  # Will be populated in second pass
        }
        menu_dict[menu.id] = menu_data

    # ========================================================================
    # STEP 4: Second Pass - Build parent-child hierarchy
    # ========================================================================
    for menu in all_menu_items:
        menu_data = menu_dict[menu.id]

        if menu.parent_id is None:
            # This is a root-level menu item (no parent)
            root_menus.append(menu_data)
        elif menu.parent_id in menu_dict:
            # This is a child menu - add it to parent's children list
            menu_dict[menu.parent_id]['children'].append(menu_data)

    # ========================================================================
    # STEP 5: Sort menus by display order
    # ========================================================================
    # Sort root menus by their menu_order field
    root_menus.sort(key=lambda x: x['menu_order'])

    # Sort children of each menu item by their menu_order field
    for menu_data in menu_dict.values():
        menu_data['children'].sort(key=lambda x: x['menu_order'])

    return root_menus