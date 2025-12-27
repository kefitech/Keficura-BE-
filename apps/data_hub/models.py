"""
Hospital Information System - Centralized Data Models
=====================================================

Author: Athul Gopan
Created: 2025
Description: Unified data models for the Hospital Management System.
            All models consolidated in a single app for better maintainability
            and reduced circular dependencies.

This module contains all core models for:
- User Management (System Creators, Administrators, Doctors, Nurses, Staff)
- Hospital Infrastructure (Departments, Specializations, Schedules)
- Patient Management (Registration, Appointments)
- Medical Services (Consultations, Prescriptions, Lab Tests)
- Pharmacy Operations (Medications, Stock, Dispensing)
- Billing Systems (Patient Bills, Pharmacy Bills, Lab Bills)
- Menu and Permissions Management

Note: All models inherit from Base abstract model which provides:
      - Audit fields (created_by, created_on, updated_by, updated_on)
      - Status tracking (is_active)
      - Comments field for additional notes
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from base_util.base import *
from django.core.validators import RegexValidator
from django.contrib.auth.models import Permission, Group
from apps.data_hub.choices import *



# ============================================================================
# USER MANAGEMENT MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Models for system-level users and administrators
# ============================================================================

class SystemCreator(models.Model):
    """
    System Creator Model

    Represents the highest level of system access - the super administrator
    who has full control over the entire Hospital Information System.

    Usage:
        - Created during initial system setup
        - Has unrestricted access to all features
        - Can create and manage other administrators
        - Typically one per hospital system

    Fields:
        user: OneToOne relationship with Django User model
        is_superadmin: Boolean flag indicating superadmin status
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_superadmin = models.BooleanField(default=True)

    def __str__(self):
        return f"System Creator: {self.user.username}"
    



class Administrator(Base):
    """
    Administrator Model

    Manages hospital administrators who have elevated privileges for
    system configuration and user management.

    Usage:
        - Created by SystemCreator
        - Manages hospital operations and staff
        - Can configure departments, schedules, and permissions
        - Has access to reports and analytics

    Fields:
        user: OneToOne relationship with Django User
        profile_picture: Administrator's profile photo
        phone_number: Unique contact number
        gender: Gender identification
        date_of_birth: Birth date for age verification
        date_joined: Employment start date
        employee_id: Unique employee identifier
        home_address: Residential address details
        qualification: Educational qualifications
        experience_years: Years of administrative experience
        experience_certificate: Document upload for verification
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Personal details
    profile_picture = models.ImageField(upload_to='admin_profiles/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined = models.DateField(blank=True, null=True)

    # Work and role information
    employee_id = models.CharField(max_length=50, unique=True, blank=True)

    # Address Information
    home_address = models.TextField(null=True)
    home_city = models.CharField(max_length=100, null=True)
    home_state = models.CharField(max_length=100, blank=True, null=True)
    home_country = models.CharField(max_length=100, null=True)
    home_zip_code = models.CharField(max_length=20, null=True)

    # Professional credentials
    experience_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
    qualification = models.CharField(max_length=255, null=True)
    experience_years = models.PositiveIntegerField(null=True)

    def __str__(self):
        return f"Administrator: {self.user.username}"
    


# ============================================================================
# CORE HOSPITAL INFRASTRUCTURE MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Hospital structure, departments, and reusable status tracking
# ============================================================================

class Status(Base):
    """
    Universal Status Tracking Model

    A reusable status model for tracking various states across different
    modules of the hospital system.

    Usage:
        - Tracks status for appointments, billing, lab tests, etc.
        - Provides standardized status codes across the system
        - Categorized by module for easy filtering

    Fields:
        code: Unique status identifier (e.g., 'APPT_SCHEDULED')
        name: Human-readable status name
        description: Detailed explanation of the status
        category: Module category (Appointment, Billing, Lab, etc.)

    Example:
        Status(code='APPT_SCHEDULED', name='Scheduled', category='APPOINTMENT')
    """
    STATUS_CATEGORIES = [
        ('APPOINTMENT', 'Appointment'),
        ('BILLING', 'Billing'),
        ('LAB', 'Lab'),
        ('DISCHARGE', 'Discharge'),
        ('ADMISSION', 'Admission'),
        ('PRESCRIPTION', 'Prescription'),
        ('GENERIC', 'Generic'),
    ]
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=STATUS_CATEGORIES)

    class Meta:
        verbose_name_plural = "Statuses"
        unique_together = ('code', 'category')

    def __str__(self):
        return f"{self.name} ({self.category})"
    


class Department(Base):
    """
    Hospital Department Model

    Represents various departments within the hospital (e.g., Cardiology,
    Orthopedics, Emergency, Pediatrics).

    Usage:
        - Organizes doctors and specializations
        - Tracks physical location within hospital
        - Links to department head (Doctor)
        - Used for routing patients and appointments

    Fields:
        name: Department name (e.g., 'Cardiology')
        code: Short code for quick reference (e.g., 'CARD')
        description: Detailed department information
        head: Foreign key to Doctor who heads the department
        floor: Physical location (floor/wing)
        contact_number: Department contact phone
        email: Department email for inquiries
    """
    name = models.CharField(max_length=100, unique=True, null=True)
    code = models.CharField(max_length=10, unique=True, null=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
    floor = models.CharField(max_length=20, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"
    


class Specialization(Base):
    """
    Medical Specialization Model

    Represents specific medical specializations within departments.

    Usage:
        - Categorizes doctors by their expertise
        - Links to parent department
        - Used for appointment routing and doctor search

    Fields:
        name: Specialization name (e.g., 'Interventional Cardiology')
        code: Short identifier (e.g., 'INTCARD')
        description: Detailed description of specialization
        department: Parent department this specialization belongs to

    Example:
        Specialization(name='Interventional Cardiology', code='INTCARD',
                      department=cardiology_dept)
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, null=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='specializations', null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


# ============================================================================
# MEDICAL STAFF MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Doctor, Nurse, and medical staff management
# ============================================================================

class Doctor(Base):
    """
    Doctor Model

    Represents medical practitioners in the hospital system.

    Usage:
        - Manages doctor profiles and credentials
        - Links to specialization and department
        - Stores consultation fees
        - Handles scheduling through DoctorSchedule
        - Used for appointments and consultations

    Fields:
        user: OneToOne link to Django User (for authentication)
        date_of_birth: Doctor's birth date
        gender: Gender identification
        contact_number: Primary contact
        phone_number: Alternate contact
        email: Professional email
        home_address: Full residential address
        qualification: Medical degrees and certifications
        experience_years: Years of medical practice
        profile_picture: Doctor's photo for patient reference
        specialization: Medical specialization (ForeignKey)
        date_joined: Hospital joining date
        curriculum_vitae: CV document upload
        education_certificate: Degree certificates
        experience_certificate: Experience proof documents
        doctor_consultation_fee: Fee charged per consultation

    Related Models:
        - DoctorSchedule: Weekly availability schedule
        - Appointment: Patient appointments
        - DoctorConsultation: Medical consultations performed
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)

    # Personal Information
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=10, choices=[
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other')
    ], null=True)

    # Contact Information
    contact_number = models.CharField(max_length=15)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()

    # Home Address
    home_address = models.TextField(null=True)
    home_city = models.CharField(max_length=100, null=True)
    home_state = models.CharField(max_length=100, blank=True, null=True)
    home_country = models.CharField(max_length=100, null=True)
    home_zip_code = models.CharField(max_length=20, null=True)

    # Professional Information
    qualification = models.CharField(max_length=255, null=True)
    experience_years = models.PositiveIntegerField(null=True)
    profile_picture = models.ImageField(upload_to='doctors/', blank=True, null=True)
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True)
    date_joined = models.DateField(blank=True, null=True)

    # Documents
    curriculum_vitae = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
    education_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
    experience_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)

    # Payment information
    doctor_consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"
    



class DoctorSchedule(Base):
    """
    Doctor Schedule Model

    Manages weekly availability schedules for doctors.

    Usage:
        - Defines doctor's working hours for each day
        - Used by appointment system to check availability
        - Supports multiple shifts per day
        - Includes validity period for temporary schedules

    Fields:
        doctor: Foreign key to Doctor
        day_of_week: Day of the week (Monday-Sunday)
        shift_type: Type of shift (Morning/Afternoon/Evening/Night/Full Day)
        start_time: Shift start time
        end_time: Shift end time
        room_number: Assigned consultation room
        max_appointments: Maximum appointments allowed per shift
        valid_from: Schedule validity start date (optional)
        valid_to: Schedule validity end date (optional)

    Business Logic:
        - Unique constraint on (doctor, day_of_week, shift_type)
        - Used for preventing appointment conflicts
        - Supports temporary schedules via valid_from/valid_to
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=[
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ], null=True)

    shift_type = models.CharField(max_length=20, choices=[
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('EVENING', 'Evening'),
        ('NIGHT', 'Night'),
        ('FULL_DAY', 'Full Day'),
        ('CUSTOM', 'Custom'),
    ], default='CUSTOM', null=True)

    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    room_number = models.CharField(max_length=50, blank=True, null=True)
    max_appointments = models.PositiveIntegerField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('doctor', 'day_of_week', 'shift_type')
        ordering = ['doctor', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor} - {self.day_of_week} ({self.shift_type})"
    


# ============================================================================
# PATIENT AND APPOINTMENT MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Patient registration and appointment management
# ============================================================================

class Appointment(Base):
    """
    Appointment Model

    Core model for managing patient appointments with doctors.

    Usage:
        - Scheduled by front desk or patients
        - Tracks patient journey from scheduling to completion
        - Supports follow-up appointments
        - Integrated with billing and pharmacy workflows

    Fields:
        appointment_id: Unique appointment identifier
        patient: Foreign key to PatientRegistration
        doctor: Foreign key to Doctor
        appointment_date: Scheduled date
        appointment_time: Scheduled time
        visit_reason: Patient's reason for visit
        visit_status: Current status in the workflow
        consultation_room: Assigned room number
        parent_consultation: Link to previous consultation (for follow-ups)
        is_follow_up: Flag indicating if this is a follow-up appointment

    Workflow States:
        SCHEDULED → CHECKED_IN → IN_CONSULTATION → PRESCRIPTION_READY →
        AT_PHARMACY → DISPENSED → AT_BILLING → PAYMENT_COMPLETE → COMPLETED

    Related Models:
        - DoctorConsultation: Medical consultation details
        - PatientBill: Billing information
        - MedicationDispense: Pharmacy dispensing records
    """

    appointment_id = models.CharField(max_length=50, unique=True)
    patient = models.ForeignKey('PatientRegistration', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    visit_reason = models.TextField(null=True, blank=True)
    visit_status = models.CharField(max_length=30, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('FOLLOW_UP', 'Follow-up'),
        ('CHECKED_IN', 'Checked In'),
        ('IN_CONSULTATION', 'In Consultation'),
        ('PRESCRIPTION_READY', 'Prescription Ready'),
        ('AT_PHARMACY', 'At Pharmacy'),
        ('DISPENSED', 'Medications Dispensed'),
        ('AT_BILLING', 'At Billing'),
        ('PAYMENT_COMPLETE', 'Payment Complete'),
        ('COMPLETED', 'Completed'),
        ('CANCELED', 'Canceled'),
    ], default='SCHEDULED')

    consultation_room = models.CharField(max_length=20, null=True, blank=True)

    # Follow-up tracking
    parent_consultation = models.ForeignKey('DoctorConsultation', null=True, blank=True, on_delete=models.SET_NULL, related_name='follow_up_appointments')
    is_follow_up = models.BooleanField(default=False)

    class Meta:
        db_table = 'appointment'
        ordering = ['-appointment_date', '-appointment_time']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        indexes = [
            models.Index(fields=['appointment_id']),
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['appointment_date']),
            models.Index(fields=['visit_status']),
            models.Index(fields=['is_active', 'appointment_date']),
            models.Index(fields=['visit_status', 'appointment_date']),
            models.Index(fields=['is_active', 'appointment_date', 'visit_status']),
        ]

    def __str__(self):
        return f"{self.patient.first_name}'s appointment with Dr. {self.doctor.user.last_name} on {self.appointment_date}"



# ============================================================================
# SUPPORT STAFF MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Front desk, pharmacists, and administrative staff
# ============================================================================

class FrontDeskStaff(Base):
    """
    Front Desk Staff Model

    Manages reception and front desk staff who handle patient registration,
    appointments, and initial patient interactions.

    Usage:
        - Registers new patients
        - Schedules appointments
        - Manages patient check-in/check-out
        - Handles billing and payment collection
        - First point of contact for patients

    Fields:
        user: OneToOne link to Django User
        date_of_birth: Birth date
        gender: Gender identification
        contact_number: Primary contact
        emergency_contact: Emergency contact number
        email: Professional email
        employee_id: Unique staff identifier
        hire_date: Employment start date
        department: Department assignment (Reception/Billing/etc.)
        employment_type: Full-time, Part-time, or Contract
        shift_schedule: Work shift timings
        profile_picture: Staff photo
        signature: Digital signature for documents
        is_active: Employment status flag
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)

    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10,
                            choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')],
                            null=True, blank=True)

    # Contact Info
    contact_number = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=15, blank=True)
    email = models.EmailField()

    # Employment Details
    employee_id = models.CharField(max_length=20, unique=True)
    hire_date = models.DateField()
    department = models.CharField(max_length=50,
                                 choices=[
                                     ('RECEPTION', 'Reception'),
                                     ('BILLING', 'Billing'),
                                     ('APPOINTMENT', 'Appointment Scheduling'),
                                     ('PATIENT_SERVICES', 'Patient Services')
                                 ], null=True)
    employment_type = models.CharField(max_length=20,
                                      choices=[
                                          ('FULL', 'Full-time'),
                                          ('PART', 'Part-time'),
                                          ('CONTRACT', 'Contract')
                                      ],
                                      default='FULL')

    # Administrative Fields
    shift_schedule = models.CharField(max_length=100,
                                     help_text="E.g., Morning, Evening, Night")

    # Profile Management
    profile_picture = models.ImageField(upload_to='front_desk_staff/', blank=True, null=True)
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Front Desk Staff {self.user.get_full_name()} - {self.employee_id}"

    class Meta:
        ordering = ['user__last_name']
        verbose_name = 'FrontDeskStaff'
        verbose_name_plural = 'FrontDeskStaff'



# ============================================================================
# HOSPITAL CONFIGURATION MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Hospital profile and organizational settings
# ============================================================================

class Hospital(Base):
    """
    Hospital Model

    Stores hospital/organization profile and configuration details.

    Usage:
        - Central repository for hospital information
        - Used in reports, bills, and official documents
        - Manages licensing and accreditation details
        - Supports multi-hospital systems

    Fields:
        name: Official hospital name
        hospital_code: Unique hospital identifier
        street_address/city/state/postal_code/country: Physical address
        phone_number/email/website: Contact information
        hospital_type: Classification (General/Specialty/Clinic/Teaching)
        emergency_services: Boolean flag for ER availability
        license_number: Government license number
        accreditation: Accreditation details
        license_expiry_date: License validity date
        established_date: Hospital establishment date
        bed_capacity: Total bed capacity
        logo: Hospital logo for branding
    """
    # Basic Information
    name = models.CharField(max_length=255, unique=True)
    hospital_code = models.CharField(max_length=50, unique=True)
    
    # Address Information
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'"
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Hospital Metadata
    HOSPITAL_TYPES = (
        ('G', 'General'),
        ('S', 'Specialty'),
        ('C', 'Clinic'),
        ('T', 'Teaching'),
    )
    hospital_type = models.CharField(max_length=1, choices=HOSPITAL_TYPES)
    
    # OWNERSHIP_TYPES = (
    #     ('PUB', 'Public'),
    #     ('PVT', 'Private'),
    #     ('GOV', 'Government'),
    #     ('NGO', 'Non-profit'),
    # )
    # ownership = models.CharField(max_length=5, choices=OWNERSHIP_TYPES)
    
    # Services Information
    emergency_services = models.BooleanField(default=False)
    # specialties = models.ManyToManyField('Specialty', blank=True)
    
    # Licensing and Certification
    license_number = models.CharField(max_length=100, unique=True,null=True)
    accreditation = models.CharField(max_length=100, null=True)
    license_expiry_date = models.DateField()
    
    # Additional Information
    description = models.TextField(blank=True)
    established_date = models.DateField(null=True, blank=True)
    bed_capacity = models.PositiveIntegerField(null=True, blank=True)
    logo = models.ImageField(upload_to='hospital_logos/', blank=True)
    
    # Geo Location (requires GeoDjango)
    # location = models.PointField(null=True, blank=True)
    
    # Timestamps

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'


# ============================================================================
# MENU AND PERMISSIONS MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Dynamic menu system and role-based access control
# ============================================================================

class MenuType(Base):
    """
    Menu Type Model

    Categorizes menu items by type (e.g., Main Menu, User Menu, Admin Menu).

    Usage:
        - Organizes menu structure
        - Supports different menu contexts
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=500)

    class Meta:
        db_table = "menu_type"
        verbose_name = "MenuType"
        verbose_name_plural = "MenuTypes"

    def __str__(self):
        return self.name


class Menu(Base):
    """
    Menu Model

    Defines hierarchical navigation menu structure with role-based access.

    Usage:
        - Creates dynamic menu based on user permissions
        - Supports parent-child menu hierarchy
        - Links to features and URLs
        - Controls UI navigation access

    Fields:
        name: Menu item name
        title: Display title
        code: Unique menu identifier
        parent: Parent menu for hierarchical structure
        menu_type: Menu category
        redirect_url: Target URL/route
        icon: Icon class for UI display
        menu_order: Display order
        feature_code: Feature identifier for permission mapping
    """
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    menu_type = models.ForeignKey(MenuType, on_delete=models.CASCADE, null=True, blank=True)
    redirect_url = models.CharField(max_length=100)
    icon = models.CharField(max_length=100)
    menu_order = models.IntegerField()
    description = models.CharField(max_length=500)
    feature_code = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "menu"
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

    def __str__(self):
        return self.name


class MenuPermissionMapper(Base):
    """
    Menu Permission Mapper

    Maps menu items to user groups for role-based access control.

    Usage:
        - Controls which user groups can see which menus
        - Implements role-based menu visibility
    """
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    auth_group_permission = models.ForeignKey(
        Group, on_delete=models.CASCADE, null=True, blank=True
    )
    description = models.CharField(max_length=500)

    class Meta:
        db_table = "menu_permision"
        verbose_name = "Menu Permission"
        verbose_name_plural = "Menu Permissions"


# ============================================================================
# NURSING STAFF MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Nurse management and shift scheduling
# ============================================================================

class Nurse(Base):
    """
    Nurse Model

    Manages nursing staff profiles and qualifications.

    Usage:
        - Stores nurse credentials and contact information
        - Links to shift assignments via NurseShiftAssignment
        - Supports department-wise nurse allocation

    Fields:
        user: OneToOne link to Django User
        date_of_birth: Birth date
        gender: Gender identification
        contact_number: Primary contact
        email: Professional email
        qualification: Nursing qualifications and certifications
        experience_years: Years of nursing experience
        profile_picture: Nurse's photo
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)

    # Personal Details
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], null=True)

    # Contact Info
    contact_number = models.CharField(max_length=15)
    email = models.EmailField()

    # Qualifications and experience
    qualification = models.CharField(max_length=255, null=True)
    experience_years = models.PositiveIntegerField(null=True)
    profile_picture = models.ImageField(upload_to='nurses/', blank=True, null=True)

    def __str__(self):
        return f"Nurse {self.user.first_name} {self.user.last_name}"
    



class NurseShiftAssignment(Base):
    """
    Nurse Shift Assignment Model

    Manages daily shift assignments for nurses to departments.

    Usage:
        - Assigns nurses to specific departments and shifts
        - Tracks daily roster and nurse availability
        - Supports multiple shift types
        - Used for workload distribution

    Fields:
        nurse: Foreign key to Nurse
        department: Department assignment
        day: Specific date for this shift
        shift_type: Type of shift (Morning/Afternoon/Evening/Night)
        start_time: Shift start time
        end_time: Shift end time
        room_number: Assigned station/room

    Business Logic:
        - Prevents double-booking via unique_together constraint
        - Ordered by day and start time for roster view
    """
    nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='shift_assignments')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='nurse_assignments')

    day = models.DateField()

    shift_type = models.CharField(max_length=20, choices=[
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('EVENING', 'Evening'),
        ('NIGHT', 'Night'),
        ('FULL_DAY', 'Full Day'),
        ('CUSTOM', 'Custom'),
    ], default='FULL_DAY')

    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    room_number = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ('nurse', 'day', 'shift_type')
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.nurse} - {self.department} - {self.day} ({self.shift_type})"
    


class PatientRegistration(Base):
    """
    Patient Registration Model

    Central repository for patient demographic and contact information.

    Usage:
        - Registers new patients in the system
        - Stores demographic details and medical history
        - Links to appointments, consultations, and billing
        - Maintains emergency contact information

    Fields:
        patient_id: Unique patient identifier (auto-generated or manual)
        first_name/last_name: Patient name
        date_of_birth: Birth date for age calculation
        age: Calculated or manually entered age
        gender: Gender (Male/Female/Other)
        contact_number: Primary contact
        email: Email address
        address: Residential address
        allergies: Known allergies (important for prescriptions)
        emergency_contact: Emergency contact person details
        registration_date: Date of registration
        registration_type: Type of registration (OPD/IPD/Emergency)
        insurance_provider: Insurance company name
        insurance_number: Policy number

    Related Models:
        - Appointment: Patient appointments
        - DoctorConsultation: Medical consultations
        - PatientBill: Billing records
    """
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    patient_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField()
    age = models.IntegerField(null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, null=True)
    registration_date = models.DateField()
    registration_type = models.CharField(max_length=50, null=True)
    insurance_provider = models.CharField(max_length=100, null=True)
    insurance_number = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = 'patient_registration'
        ordering = ['-registration_date']
        verbose_name = 'Patient Registration'
        verbose_name_plural = 'Patient Registrations'
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['contact_number']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['registration_date']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"


# ============================================================================
# PHARMACY MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Medication management, stock control, and dispensing
# ============================================================================

class PharmacistStaff(Base):
    """
    Pharmacist Staff Model

    Manages pharmacist profiles and employment details.

    Usage:
        - Stores pharmacist credentials
        - Used for medication dispensing authorization
        - Links to pharmacy billing and stock management
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    
    # Personal Details
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10,
                            choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')],
                            null=True, blank=True)
 
    # Contact Info
    contact_number = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=15, blank=True)
    email = models.EmailField()
 
    # Employment Details
    employee_id = models.CharField(max_length=20, unique=True, null=True)
    hire_date = models.DateField()

    profile_picture = models.ImageField(upload_to='front_desk_staff/', blank=True, null=True)
    # signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Pharmacist {self.user.get_full_name()} - {self.employee_id}"

    class Meta:
        ordering = ['user__last_name']
        verbose_name = 'Pharmacist Staff'
        verbose_name_plural = 'Pharmacist Staff'


# ============================================================================
# PHARMACY PURCHASE & SUPPLIER MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Models for supplier management and purchase operations
# ============================================================================

class Supplier(Base):
    """
    Supplier Model

    Master table for all pharmacy suppliers/vendors who provide medications
    and medical supplies to the hospital pharmacy.

    Usage:
        - Maintains supplier catalog
        - Tracks supplier payment terms and credit limits
        - Links to purchase orders and GRNs
        - Stores tax and business information

    Fields:
        Basic Information:
            code: Auto-generated unique supplier code (SUP-0001)
            name: Supplier company name
            supplier_type: Type of supplier (MANUFACTURER, DISTRIBUTOR, etc.)
            contact_person: Contact person name

        Contact Information:
            phone: Primary contact number
            alternate_phone: Secondary contact number
            email: Email address
            address: Full address

        Tax & Business:
            gstin: GST Identification Number (15 chars)
            pan: PAN number (10 chars)
            drug_license_number: Drug license number

        Payment Terms:
            payment_type: Cash/Credit/Both
            credit_days: Credit period in days
            credit_limit: Maximum credit amount allowed

        Banking:
            bank_name: Supplier's bank name
            account_number: Account number
            ifsc_code: IFSC code

        Rating:
            rating: Supplier rating (1-5 stars)

    Example:
        supplier = Supplier.objects.create(
            code='SUP-0001',
            name='MediPharma Distributors',
            supplier_type='DISTRIBUTOR',
            phone='9876543210',
            payment_type='CREDIT',
            credit_days=30,
            credit_limit=500000.00
        )
    """

    # Basic Information
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Auto-generated unique supplier code (SUP-0001)"
    )
    name = models.CharField(
        max_length=200,
        help_text="Supplier company name"
    )
    supplier_type = models.CharField(
        max_length=20,
        choices=SUPPLIER_TYPE_CHOICES,
        default='DISTRIBUTOR',
        help_text="Type of supplier"
    )
    contact_person = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Contact person name"
    )

    # Contact Information
    phone = models.CharField(
        max_length=15,
        help_text="Primary contact number"
    )
    alternate_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        help_text="Secondary contact number"
    )
    email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email address"
    )
    address = models.TextField(
        help_text="Full address"
    )

    # Tax & Business Information
    gstin = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        unique=True,
        help_text="GST Identification Number (15 characters)"
    )
    pan = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="PAN number (10 characters)"
    )
    drug_license_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Drug license number"
    )

    # Payment Terms
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='CASH',
        help_text="Payment terms: Cash/Credit/Both"
    )
    credit_days = models.IntegerField(
        default=0,
        help_text="Credit period in days (0 = cash only)"
    )
    credit_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum credit amount allowed"
    )

    # Banking Information
    bank_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Supplier's bank name"
    )
    account_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Bank account number"
    )
    ifsc_code = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        help_text="IFSC code"
    )

    # Rating
    rating = models.IntegerField(
        choices=SUPPLIER_RATING_CHOICES,
        null=True,
        blank=True,
        help_text="Supplier rating (1-5 stars)"
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate supplier code if not provided
        """
        if not self.code:
            # Get the last supplier code
            last_supplier = Supplier.objects.all().order_by('id').last()
            if last_supplier and last_supplier.code:
                # Extract number from last code (SUP-0001 -> 1)
                try:
                    last_number = int(last_supplier.code.split('-')[1])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1

            # Generate new code
            self.code = f"SUP-{new_number:04d}"

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'supplier'
        ordering = ['-created_on']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]


class PurchaseOrder(Base):
    """
    Purchase Order Model

    Represents purchase orders created before receiving goods from suppliers.
    Optional step in the procurement workflow - can create GRN directly without PO.

    Usage:
        - Create PO when ordering medications from supplier
        - Track order status (PENDING, APPROVED, COMPLETED, CANCELLED)
        - Link to supplier for vendor management
        - Track expected delivery dates
        - Calculate total order value
        - Link to GRNs when goods are received

    Fields:
        po_number: Auto-generated unique PO number (PO-YYYYMMDD-XXXX)
        supplier: Foreign key to Supplier
        order_date: Date when order was created
        expected_delivery_date: Expected delivery date
        status: Order status (DRAFT, PENDING, APPROVED, PARTIAL, COMPLETED, CANCELLED)
        total_amount: Total order value
        notes: Additional notes about the order

    Business Rules:
        - PO number auto-generated: PO-20251201-0001
        - Status flow: DRAFT → PENDING → APPROVED → PARTIAL → COMPLETED
        - Can be cancelled at any time
        - Total amount calculated from linked GRNs
        - Status updates to PARTIAL when some items received
        - Status updates to COMPLETED when all items received

    Example:
        po = PurchaseOrder.objects.create(
            supplier=supplier_obj,
            order_date='2025-12-01',
            expected_delivery_date='2025-12-08',
            status='PENDING',
            notes='Urgent order'
        )
    """

    # Basic Information
    po_number = models.CharField(
        max_length=30,
        unique=True,
        help_text="Auto-generated PO number (PO-YYYYMMDD-XXXX)"
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        help_text="Supplier for this purchase order"
    )

    # Dates
    order_date = models.DateField(
        help_text="Date when order was created"
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected delivery date"
    )

    # Status & Amount
    status = models.CharField(
        max_length=20,
        choices=PURCHASE_ORDER_STATUS_CHOICES,
        default='PENDING',
        help_text="Order status"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total order value"
    )

    # Additional Information
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes about the order"
    )

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate PO number if not provided
        Format: PO-YYYYMMDD-XXXX
        """
        if not self.po_number:
            from datetime import date
            today = date.today()
            date_str = today.strftime('%Y%m%d')

            # Get last PO for today
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f'PO-{date_str}'
            ).order_by('po_number').last()

            if last_po and last_po.po_number:
                # Extract sequence number
                try:
                    last_seq = int(last_po.po_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (IndexError, ValueError):
                    new_seq = 1
            else:
                new_seq = 1

            # Generate PO number
            self.po_number = f"PO-{date_str}-{new_seq:04d}"

        super().save(*args, **kwargs)

    def get_received_amount(self):
        """
        Calculate total amount received from linked GRNs
        """
        from django.db.models import Sum
        try:
            total = self.purchase_entries.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            return total
        except AttributeError:
            # GRN functionality not implemented yet - purchase_entries relation doesn't exist
            return 0

    def update_status(self):
        """
        Update PO status based on linked GRNs
        - PARTIAL if some items received
        - COMPLETED if all items received (based on amount)
        """
        received_amount = self.get_received_amount()

        if received_amount == 0:
            # No GRNs yet
            if self.status not in ['DRAFT', 'PENDING', 'APPROVED', 'CANCELLED']:
                self.status = 'APPROVED'
        elif received_amount >= self.total_amount:
            # Fully received
            self.status = 'COMPLETED'
        else:
            # Partially received
            self.status = 'PARTIAL'

        self.save()

    class Meta:
        db_table = 'purchase_order'
        ordering = ['-order_date', '-created_on']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['supplier']),
            models.Index(fields=['order_date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
        ]


class PurchaseEntry(Base):
    """
    Purchase Entry (GRN - Goods Receipt Note) Model

    Represents actual received goods from suppliers.
    Main transaction record for procurement.

    Usage:
        - Create GRN when goods are received from supplier
        - Can be linked to PurchaseOrder (optional)
        - Contains multiple line items (PurchaseItem)
        - Auto-creates MedicationStock entries
        - Tracks payment status
        - Updates PurchaseOrder status when linked

    Fields:
        grn_number: Auto-generated unique GRN number (GRN-YYYYMMDD-XXXX)
        supplier: Foreign key to Supplier
        purchase_order: Foreign key to PurchaseOrder (optional)
        invoice_number: Supplier's invoice number
        invoice_date: Invoice date
        received_date: Date goods were received
        subtotal: Sum of all item amounts (before tax/discount)
        discount_amount: Total discount
        tax_amount: Total GST amount
        total_amount: Final payable amount
        payment_status: Payment status (PENDING, PAID, PARTIAL, OVERDUE)
        payment_mode: Payment method
        payment_date: When payment was made

    Business Rules:
        - GRN number auto-generated: GRN-20251201-0001
        - Must have at least one PurchaseItem
        - Totals calculated from items
        - Auto-creates MedicationStock on save
        - Updates PO status if linked

    Example:
        grn = PurchaseEntry.objects.create(
            supplier=supplier_obj,
            invoice_number='INV-2024-12345',
            invoice_date='2025-11-30',
            received_date='2025-12-01',
            payment_mode='CREDIT'
        )
    """

    # Basic Information
    grn_number = models.CharField(
        max_length=30,
        unique=True,
        help_text="Auto-generated GRN number (GRN-YYYYMMDD-XXXX)"
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.PROTECT,
        related_name='purchase_entries',
        help_text="Supplier from whom goods were received"
    )
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        related_name='purchase_entries',
        null=True,
        blank=True,
        help_text="Related purchase order (optional)"
    )

    # Invoice Details
    invoice_number = models.CharField(
        max_length=50,
        help_text="Supplier's invoice number"
    )
    invoice_date = models.DateField(
        help_text="Invoice date"
    )
    received_date = models.DateField(
        help_text="Date when goods were received"
    )

    # Amount Fields
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Subtotal (before tax and discount)"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total discount amount"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total GST amount"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Final total amount"
    )

    # Payment Information
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Payment status"
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        null=True,
        blank=True,
        help_text="Payment method"
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when payment was made"
    )

    # Additional Information
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes"
    )

    # Approval Workflow
    status = models.CharField(
        max_length=20,
        choices=GRN_STATUS_CHOICES,
        default='PENDING',
        help_text="GRN approval status"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='approved_grns',
        null=True,
        blank=True,
        help_text="Pharmacist who approved this GRN"
    )
    approved_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When GRN was approved"
    )
    stock_created = models.BooleanField(
        default=False,
        help_text="Whether stock entries have been created (happens on approval)"
    )

    def __str__(self):
        return f"{self.grn_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate GRN number if not provided
        Format: GRN-YYYYMMDD-XXXX
        """
        if not self.grn_number:
            from datetime import date
            today = date.today()
            date_str = today.strftime('%Y%m%d')

            # Get last GRN for today
            last_grn = PurchaseEntry.objects.filter(
                grn_number__startswith=f'GRN-{date_str}'
            ).order_by('grn_number').last()

            if last_grn and last_grn.grn_number:
                # Extract sequence number
                try:
                    last_seq = int(last_grn.grn_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (IndexError, ValueError):
                    new_seq = 1
            else:
                new_seq = 1

            # Generate GRN number
            self.grn_number = f"GRN-{date_str}-{new_seq:04d}"

        super().save(*args, **kwargs)

        # Update PO status if linked
        if self.purchase_order:
            self.purchase_order.update_status()

    def calculate_totals(self):
        """
        Calculate totals from all purchase items
        Should be called after items are added
        """
        from django.db.models import Sum
        from decimal import Decimal

        items_data = self.purchase_items.aggregate(
            subtotal=Sum(models.F('quantity') * models.F('purchase_price')),
            total_tax=Sum('tax_amount'),
            total_discount=Sum('discount_amount')
        )

        self.subtotal = items_data['subtotal'] or Decimal('0')
        self.tax_amount = items_data['total_tax'] or Decimal('0')
        # Discount at item level already included, but can have GRN level discount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save()

    class Meta:
        db_table = 'purchase_entry'
        ordering = ['-received_date', '-created_on']
        verbose_name = 'Purchase Entry (GRN)'
        verbose_name_plural = 'Purchase Entries (GRN)'
        indexes = [
            models.Index(fields=['grn_number']),
            models.Index(fields=['supplier']),
            models.Index(fields=['purchase_order']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['received_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['is_active']),
        ]


class PurchaseItem(models.Model):
    """
    Purchase Item Model

    Line items in a Purchase Entry (GRN).
    Each item represents one medication with specific batch.

    Usage:
        - Created as part of PurchaseEntry
        - Links to Medication
        - Contains pricing and tax details
        - Auto-calculates margin and tax
        - Creates MedicationStock entry

    Fields:
        purchase_entry: FK to PurchaseEntry
        medication: FK to Medication
        batch_number: Manufacturer's batch number
        expiry_date: Expiration date
        quantity: Quantity purchased
        free_quantity: Free quantity (bonus)
        packing: Packing details
        mrp: Maximum Retail Price
        purchase_price: Cost per unit
        ptr: Price to Retailer
        discount_percent: Discount percentage
        discount_amount: Discount amount
        cgst_percent: CGST percentage
        sgst_percent: SGST percentage
        igst_percent: IGST percentage
        tax_amount: Total tax amount
        total_amount: Item total
        margin_percent: Profit margin
        stock_entry: Link to created MedicationStock

    Calculations (Auto):
        margin_percent = ((MRP - purchase_price) / MRP) * 100
        tax_amount = (quantity * purchase_price) * (cgst% + sgst% + igst%) / 100
        total_amount = (quantity * purchase_price) + tax_amount - discount_amount
    """

    purchase_entry = models.ForeignKey(
        'PurchaseEntry',
        on_delete=models.CASCADE,
        related_name='purchase_items',
        help_text="Parent purchase entry"
    )
    medication = models.ForeignKey(
        'Medication',
        on_delete=models.PROTECT,
        related_name='purchase_items',
        help_text="Medication purchased"
    )

    # Batch Information
    batch_number = models.CharField(
        max_length=50,
        help_text="Manufacturer's batch number"
    )
    expiry_date = models.DateField(
        help_text="Expiration date"
    )

    # Quantity
    quantity = models.PositiveIntegerField(
        help_text="Quantity purchased (will be auto-calculated from pack_quantity × units_per_pack)"
    )
    free_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Free quantity (bonus)"
    )

    # NEW: Structured Packing Fields (MANDATORY)
    pack_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of packs/strips received (e.g., 50 strips)"
    )
    units_per_pack = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of units per pack (e.g., 15 tablets per strip)"
    )
    price_per_pack = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per pack/strip (e.g., ₹180 per strip)"
    )

    # Auto-calculated fields
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Calculated: price_per_pack ÷ units_per_pack"
    )
    total_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calculated: pack_quantity × units_per_pack (total tablets/units)"
    )

    # Old packing field (kept for backward compatibility)
    packing = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Legacy packing details - Auto-generated from structured fields"
    )

    # Pricing
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum Retail Price"
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Purchase cost per unit"
    )
    ptr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price to Retailer"
    )

    # Discount
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Discount percentage"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Discount amount"
    )

    # GST
    cgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="CGST percentage"
    )
    sgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="SGST percentage"
    )
    igst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="IGST percentage"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total tax amount"
    )

    # Totals
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Item total amount"
    )
    margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Profit margin percentage"
    )

    # Link to created stock
    stock_entry = models.ForeignKey(
        'MedicationStock',
        on_delete=models.SET_NULL,
        related_name='purchase_item_link',
        null=True,
        blank=True,
        help_text="Created medication stock entry"
    )

    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medication.name} - {self.batch_number}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-calculate amounts and packing values
        """
        from decimal import Decimal

        # NEW: Calculate packing values first
        if self.price_per_pack and self.units_per_pack:
            self.price_per_unit = Decimal(str(self.price_per_pack)) / Decimal(str(self.units_per_pack))

        if self.pack_quantity and self.units_per_pack:
            self.total_units = self.pack_quantity * self.units_per_pack
            # Auto-set quantity to total_units if not provided
            if not self.quantity:
                self.quantity = self.total_units

        # Auto-generate packing description for legacy field
        if self.pack_quantity and self.units_per_pack:
            self.packing = f"{self.pack_quantity} packs × {self.units_per_pack} units = {self.total_units} total units"

        # NEW: If price_per_pack is provided, calculate purchase_price as price_per_unit
        if self.price_per_unit and not self.purchase_price:
            self.purchase_price = self.price_per_unit

        # Ensure all fields are Decimal type
        self.quantity = int(self.quantity) if self.quantity else 0
        self.purchase_price = Decimal(str(self.purchase_price)) if self.purchase_price else Decimal('0')
        self.mrp = Decimal(str(self.mrp)) if self.mrp else Decimal('0')
        self.discount_percent = Decimal(str(self.discount_percent)) if self.discount_percent else Decimal('0')
        self.discount_amount = Decimal(str(self.discount_amount)) if self.discount_amount else Decimal('0')
        self.cgst_percent = Decimal(str(self.cgst_percent)) if self.cgst_percent else Decimal('0')
        self.sgst_percent = Decimal(str(self.sgst_percent)) if self.sgst_percent else Decimal('0')
        self.igst_percent = Decimal(str(self.igst_percent)) if self.igst_percent else Decimal('0')

        # Calculate discount amount if percentage given
        if self.discount_percent > 0 and self.discount_amount == 0:
            base_amount = Decimal(str(self.quantity)) * self.purchase_price
            self.discount_amount = (base_amount * self.discount_percent) / Decimal('100')

        # Calculate tax amount
        gst_total = self.cgst_percent + self.sgst_percent + self.igst_percent
        taxable_amount = (Decimal(str(self.quantity)) * self.purchase_price) - self.discount_amount
        self.tax_amount = (taxable_amount * gst_total) / Decimal('100')

        # Calculate total amount
        self.total_amount = taxable_amount + self.tax_amount

        # Calculate margin percentage
        if self.mrp > 0:
            self.margin_percent = ((self.mrp - self.purchase_price) / self.mrp) * Decimal('100')

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'purchase_item'
        ordering = ['id']
        verbose_name = 'Purchase Item'
        verbose_name_plural = 'Purchase Items'
        indexes = [
            models.Index(fields=['purchase_entry']),
            models.Index(fields=['medication']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['expiry_date']),
        ]


# ============================================================================
# SUPPLIER RETURN (PURCHASE RETURN) MODELS
# ============================================================================

class SupplierReturn(Base):
    """
    Supplier Return Model (Purchase Return to Supplier)

    Represents medicines/items returned from pharmacy back to suppliers.
    Used for damaged goods, expired items, wrong deliveries, or excess stock.

    Usage:
        - Create return when medicines need to be sent back to supplier
        - Link to original Purchase Entry (GRN) if applicable
        - Track credit notes from supplier
        - Manage approval workflow
        - Adjust stock when items are returned

    Fields:
        return_number: Auto-generated unique return number (SRN-YYYYMMDD-XXXX)
        purchase_entry: Foreign key to PurchaseEntry (optional - may not have GRN)
        supplier: Foreign key to Supplier
        return_date: Date when return is initiated
        reason: Reason category for return
        status: Return status (workflow)
        credit_note_number: Supplier's credit note reference
        credit_note_date: When supplier issued credit note
        credit_note_amount: Amount supplier will credit
        subtotal: Sum before tax
        tax_amount: Total GST being returned
        total_amount: Final return value
        notes: Additional details

    Business Rules:
        - Return number auto-generated: SRN-20251202-0001
        - Status flow: PENDING → APPROVED → SHIPPED → COMPLETED / REJECTED
        - Stock reduced when return is created
        - Credit note tracked for accounts reconciliation
        - Can return items without original GRN (for old stock)

    Example:
        supplier_return = SupplierReturn.objects.create(
            supplier=supplier_obj,
            purchase_entry=grn_obj,  # optional
            return_date='2025-12-02',
            reason='DAMAGED',
            status='PENDING'
        )
    """

    # Basic Information
    return_number = models.CharField(
        max_length=30,
        unique=True,
        help_text="Auto-generated return number (SRN-YYYYMMDD-XXXX)"
    )
    purchase_entry = models.ForeignKey(
        'PurchaseEntry',
        on_delete=models.SET_NULL,
        related_name='supplier_returns',
        null=True,
        blank=True,
        help_text="Original GRN (optional)"
    )
    supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.PROTECT,
        related_name='supplier_returns',
        help_text="Supplier to whom items are being returned"
    )

    # Dates
    return_date = models.DateField(
        help_text="Date when return is initiated"
    )

    # Return Details
    reason = models.CharField(
        max_length=20,
        choices=PURCHASE_RETURN_REASON_CHOICES,
        help_text="Reason for return"
    )
    status = models.CharField(
        max_length=20,
        choices=PURCHASE_RETURN_STATUS_CHOICES,
        default='PENDING',
        help_text="Return status"
    )

    # Credit Note Details
    credit_note_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Supplier's credit note number"
    )
    credit_note_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of supplier's credit note"
    )
    credit_note_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount credited by supplier (may differ from total_amount)"
    )

    # Amount Fields
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Subtotal (before tax)"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total GST amount being returned"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total return value"
    )

    # Additional Information
    notes = models.TextField(
        null=True,
        blank=True,
        help_text="Additional notes about the return"
    )

    # Workflow tracking
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='approved_supplier_returns',
        null=True,
        blank=True,
        help_text="Who approved this return"
    )
    approved_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When return was approved"
    )
    shipped_date = models.DateField(
        null=True,
        blank=True,
        help_text="When items were shipped back to supplier"
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
        help_text="When supplier accepted and issued credit note"
    )
    stock_adjusted = models.BooleanField(
        default=False,
        help_text="Whether stock has been adjusted (happens on approval)"
    )

    def __str__(self):
        return f"{self.return_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate return number if not provided
        Format: SRN-YYYYMMDD-XXXX
        """
        if not self.return_number:
            from datetime import date
            today = date.today()
            date_str = today.strftime('%Y%m%d')

            # Get last return for today
            last_return = SupplierReturn.objects.filter(
                return_number__startswith=f'SRN-{date_str}'
            ).order_by('return_number').last()

            if last_return and last_return.return_number:
                # Extract sequence number
                try:
                    last_seq = int(last_return.return_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (IndexError, ValueError):
                    new_seq = 1
            else:
                new_seq = 1

            # Generate return number
            self.return_number = f"SRN-{date_str}-{new_seq:04d}"

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """
        Calculate totals from all return items
        """
        from django.db.models import Sum

        totals = self.return_items.aggregate(
            subtotal=Sum('total_amount'),
            tax_total=Sum('tax_amount')
        )

        self.total_amount = totals['subtotal'] or 0
        self.tax_amount = totals['tax_total'] or 0
        # Subtotal = total - tax
        self.subtotal = self.total_amount - self.tax_amount

        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

    def adjust_stock(self):
        """
        Adjust stock for returned items

        Logic:
        - For DAMAGED/EXPIRED: Increase damaged_quantity (written off)
        - For GOOD condition: Increase returned_quantity (track supplier returns)

        Note: We don't reduce received_quantity because that represents
        what we originally received. We track returns separately.

        This should only be called ONCE when the return is approved.
        """
        # Prevent double adjustment
        if self.stock_adjusted:
            return

        for item in self.return_items.all():
            if item.stock_entry:
                stock = item.stock_entry

                if item.condition == 'DAMAGED' or item.condition == 'EXPIRED':
                    # Write off as damaged
                    stock.damaged_quantity += item.quantity_returned
                else:
                    # Track as returned to supplier (reduces available stock)
                    stock.returned_quantity += item.quantity_returned

                stock.save()

        # Mark as adjusted
        self.stock_adjusted = True
        self.save(update_fields=['stock_adjusted'])

    class Meta:
        db_table = 'supplier_return'
        ordering = ['-return_date', '-created_on']
        verbose_name = 'Supplier Return'
        verbose_name_plural = 'Supplier Returns'
        indexes = [
            models.Index(fields=['return_number']),
            models.Index(fields=['supplier']),
            models.Index(fields=['purchase_entry']),
            models.Index(fields=['return_date']),
            models.Index(fields=['status']),
            models.Index(fields=['reason']),
        ]


class SupplierReturnItem(models.Model):
    """
    Supplier Return Item Model

    Represents individual items/medicines being returned to supplier.
    Line items within a SupplierReturn.

    Usage:
        - Created when adding items to a supplier return
        - Links to original purchase item if available
        - Tracks batch, quantity, and pricing details
        - Calculates refund amounts

    Fields:
        supplier_return: Foreign key to SupplierReturn
        purchase_item: Foreign key to PurchaseItem (optional)
        medication: Foreign key to Medication
        stock_entry: Foreign key to MedicationStock
        batch_number: Batch being returned
        expiry_date: Expiry date of batch
        quantity_returned: How many units being returned
        unit_price: Original purchase price per unit
        tax_amount: GST amount on this item
        total_amount: Total value of return for this item
        condition: Physical condition of items
        reason_detail: Specific reason for this item

    Business Rules:
        - Can link to original PurchaseItem if available
        - Must specify medication and batch
        - Quantity must be positive
        - Amounts auto-calculated based on original purchase price

    Example:
        item = SupplierReturnItem.objects.create(
            supplier_return=return_obj,
            medication=med_obj,
            stock_entry=stock_obj,
            quantity_returned=50,
            unit_price=6.00,
            condition='DAMAGED'
        )
    """

    # Basic Information
    supplier_return = models.ForeignKey(
        SupplierReturn,
        on_delete=models.CASCADE,
        related_name='return_items',
        help_text="Parent return"
    )
    purchase_item = models.ForeignKey(
        'PurchaseItem',
        on_delete=models.SET_NULL,
        related_name='supplier_return_items',
        null=True,
        blank=True,
        help_text="Original purchase item (if available)"
    )
    medication = models.ForeignKey(
        'Medication',
        on_delete=models.PROTECT,
        help_text="Medication being returned"
    )
    stock_entry = models.ForeignKey(
        'MedicationStock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Stock entry being returned from"
    )

    # Batch Details
    batch_number = models.CharField(
        max_length=100,
        help_text="Batch number being returned"
    )
    expiry_date = models.DateField(
        help_text="Expiry date of batch"
    )

    # Quantity and Pricing
    quantity_returned = models.PositiveIntegerField(
        help_text="Quantity being returned"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original purchase price per unit"
    )

    # GST Details (from original purchase)
    cgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="CGST percentage"
    )
    sgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="SGST percentage"
    )
    igst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="IGST percentage"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total GST amount"
    )

    # Calculated Fields
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total return value for this item"
    )

    # Condition and Reason
    condition = models.CharField(
        max_length=20,
        choices=ITEM_CONDITION_CHOICES,
        help_text="Physical condition of items"
    )
    reason_detail = models.TextField(
        null=True,
        blank=True,
        help_text="Specific reason for returning this item"
    )

    # Timestamps
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.medication.name} - {self.batch_number} ({self.quantity_returned} units)"

    def save(self, *args, **kwargs):
        """
        Override save to auto-calculate amounts
        """
        from decimal import Decimal

        # Ensure all fields are Decimal type
        self.quantity_returned = int(self.quantity_returned) if self.quantity_returned else 0
        self.unit_price = Decimal(str(self.unit_price)) if self.unit_price else Decimal('0')
        self.cgst_percent = Decimal(str(self.cgst_percent)) if self.cgst_percent else Decimal('0')
        self.sgst_percent = Decimal(str(self.sgst_percent)) if self.sgst_percent else Decimal('0')
        self.igst_percent = Decimal(str(self.igst_percent)) if self.igst_percent else Decimal('0')

        # Calculate base amount
        base_amount = Decimal(str(self.quantity_returned)) * self.unit_price

        # Calculate tax amount
        gst_total = self.cgst_percent + self.sgst_percent + self.igst_percent
        self.tax_amount = (base_amount * gst_total) / Decimal('100')

        # Calculate total amount
        self.total_amount = base_amount + self.tax_amount

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'supplier_return_item'
        ordering = ['id']
        verbose_name = 'Supplier Return Item'
        verbose_name_plural = 'Supplier Return Items'
        indexes = [
            models.Index(fields=['supplier_return']),
            models.Index(fields=['medication']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['expiry_date']),
        ]


class Medication(Base):
    """
    Medication Master Model - ENHANCED

    Master list of all medications available in the hospital pharmacy.

    Usage:
        - Maintains medication catalog
        - Used in prescriptions and stock management
        - Links to stock entries and dispensing records
        - Stores reorder configuration

    Fields:
        name: Generic/brand name of medication
        description: Medication details and uses
        dosage_form: Form (tablet, capsule, syrup, injection)
        strength: Medication strength (e.g., '500mg', '10ml')

        NEW FIELDS:
        generic_name: Generic name of the medication
        brand_name: Brand/commercial name
        therapeutic_category: Category (Antibiotic, Analgesic, etc.)
        base_unit: Default unit for this medication
        default_reorder_level: Default minimum stock level
        default_reorder_quantity: Default reorder quantity
        requires_prescription: Whether prescription is mandatory
        is_refrigerated: Cold chain requirement
    """
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    dosage_form = models.CharField(max_length=100)
    strength = models.CharField(max_length=50)

    # NEW: Additional medication details
    # generic_name = models.CharField(max_length=200, null=True, blank=True, help_text="Generic name")
    # brand_name = models.CharField(max_length=200, null=True, blank=True, help_text="Brand name")
    # therapeutic_category = models.CharField(max_length=100, null=True, blank=True,
    #                                        help_text="e.g., Antibiotic, Analgesic")

    # NEW: Unit configuration
    # base_unit = models.ForeignKey('MedicationUnit', on_delete=models.SET_NULL, null=True, blank=True,
                                #   related_name='medications', help_text="Default unit (Tablet, ML, etc.)")

    # NEW: Reorder defaults
    # default_reorder_level = models.PositiveIntegerField(default=50, help_text="Default minimum stock level")
    # default_reorder_quantity = models.PositiveIntegerField(default=100, help_text="Default reorder quantity")

    # NEW: Flags
    # requires_prescription = models.BooleanField(default=True, help_text="Requires doctor's prescription")
    # is_refrigerated = models.BooleanField(default=False, help_text="Requires cold storage")
    # is_controlled_substance = models.BooleanField(default=False, help_text="Narcotic/controlled drug")

    class Meta:
        db_table = 'medication'
        ordering = ['name']
        verbose_name = 'Medication'
        verbose_name_plural = 'Medications'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['dosage_form']),
        ]

    def __str__(self):
        return f"{self.name} {self.strength} ({self.dosage_form})"

    def get_total_stock(self):
        """Get total stock across all batches"""
        return sum(stock.quantity for stock in self.stock_entries.filter(is_active=True))

    def get_available_stock(self):
        """Get available stock (non-expired batches)"""
        from datetime import datetime
        return sum(stock.quantity for stock in self.stock_entries.filter(
            is_active=True,
            expiry_date__gte=datetime.now().date()
        ))


# ============================================================================
# MEDICAL CONSULTATION MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Doctor consultations, prescriptions, and medical records
# ============================================================================

class DoctorConsultation(Base):
    """
    Doctor Consultation Model

    Records medical consultations performed by doctors.

    Usage:
        - Stores diagnosis and treatment plan
        - Links prescriptions to appointments
        - Tracks recommended tests
        - Supports follow-up scheduling

    Fields:
        appointment: Foreign key to Appointment
        diagnosis: Doctor's diagnosis
        recommended_tests: JSON array of lab tests recommended
        doctor_notes: Additional notes from doctor
        follow_up_date: Next appointment date if required
        prescribed_medicines: ManyToMany to Medication via PrescribedMedicine

    Related Models:
        - PrescribedMedicine: Detailed prescription information
        - PatientBill: Billing for consultation
    """
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='consultations')
    diagnosis = models.TextField()
    recommended_tests = models.JSONField(default=list, blank=True)
    doctor_notes = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    prescribed_medicines = models.ManyToManyField(Medication, through='PrescribedMedicine')

    class Meta:
        db_table = 'doctor_consultation'
        ordering = ['-created_on']
        verbose_name = 'Doctor Consultation'
        verbose_name_plural = 'Doctor Consultations'
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['created_on']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Consultation for {self.appointment.patient.first_name} on {self.appointment.appointment_date}"


class PrescribedMedicine(Base):
    """
    Prescribed Medicine Model

    Through model for DoctorConsultation and Medication relationship.
    Stores detailed prescription instructions.

    Usage:
        - Links consultation to prescribed medications
        - Stores dosage, frequency, and duration
        - Used by pharmacy for dispensing

    Fields:
        consultation: Foreign key to DoctorConsultation
        medicine: Foreign key to Medication
        dosage: Dosage instruction (e.g., '1 tablet')
        frequency: How often (e.g., 'Twice daily')
        duration: Treatment duration (e.g., '7 days')
        quantity: Total quantity to dispense
        instructions: Special instructions for patient
    """
    consultation = models.ForeignKey(DoctorConsultation, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medication, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    instructions = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'prescribed_medicine'
        ordering = ['id']
        verbose_name = 'Prescribed Medicine'
        verbose_name_plural = 'Prescribed Medicines'
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['medicine']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.medicine.name} for {self.consultation.appointment.patient.first_name}"


class MedicationStock(Base):
    """
    Medication Stock Model - ENHANCED

    Manages pharmacy inventory with batch-wise tracking.

    Usage:
        - Tracks medication inventory by batch
        - Manages expiry dates for stock rotation
        - Stores pricing information
        - Links to dispensing records
        - Tracks opening stock, received, sold, and balance quantities

    Fields:
        medication: Foreign key to Medication
        batch_number: Manufacturer batch number
        quantity: Current available quantity in stock
        expiry_date: Expiration date
        received_date: Stock received date
        purchase_price: Procurement cost
        selling_price: Retail price
        supplier: Supplier name (kept for backward compatibility)
        supplier_fk: Foreign key to Supplier model (NEW)
        manufacturer: Manufacturer name

        NEW FIELDS:
        opening_quantity: Opening stock quantity
        received_quantity: Total quantity received
        sold_quantity: Total quantity sold
        returned_quantity: Total quantity returned
        damaged_quantity: Total quantity damaged
        adjusted_quantity: Total adjustments (+/-)
        grn: Link to GRN that created this stock

    Business Logic:
        - Track FIFO/FEFO for stock rotation
        - Alert on low stock or near-expiry items
        - Formula: current_quantity = opening + received - sold - returned - damaged + adjusted
    """
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='stock_entries')
    batch_number = models.CharField(max_length=100)

    # Current quantity
    quantity = models.PositiveIntegerField()

    # NEW: Detailed quantity tracking
    opening_quantity = models.PositiveIntegerField(default=0, help_text="Opening stock")
    received_quantity = models.PositiveIntegerField(default=0, help_text="Total received")
    sold_quantity = models.PositiveIntegerField(default=0, help_text="Total sold")
    returned_quantity = models.PositiveIntegerField(default=0, help_text="Total returned to supplier")
    damaged_quantity = models.PositiveIntegerField(default=0, help_text="Total damaged/written off")
    adjusted_quantity = models.IntegerField(default=0, help_text="Adjustments (+/-)")

    # NEW: Department-wise allocation
    pharmacy_quantity = models.PositiveIntegerField(default=0, help_text="Quantity allocated to main pharmacy")
    home_care_quantity = models.PositiveIntegerField(default=0, help_text="Quantity allocated to home care")
    casualty_quantity = models.PositiveIntegerField(default=0, help_text="Quantity allocated to casualty/emergency")

    # Dates
    expiry_date = models.DateField()
    received_date = models.DateField()

    # Pricing
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum Retail Price")

    # Supplier info (keeping old field for backward compatibility)
    supplier = models.CharField(max_length=200)

    manufacturer = models.CharField(max_length=200, default='Medi power')

    # NEW: Link to Purchase Entry (GRN)
    # IMPORTANT: These are required fields for proper traceability
    # Every stock entry MUST come from a purchase entry (GRN)
    purchase_entry = models.ForeignKey(
        'PurchaseEntry',
        on_delete=models.PROTECT,  # Prevent deletion of GRN if stock exists
        related_name='stock_entries',
        null=False,  # Required field - ensures traceability
        blank=False,  # Required field - ensures traceability
        help_text="Source purchase entry (GRN) - Required for full audit trail"
    )
    purchase_item = models.ForeignKey(
        'PurchaseItem',
        on_delete=models.PROTECT,  # Prevent deletion of purchase item if stock exists
        related_name='stock_created',
        null=False,  # Required field - ensures traceability
        blank=False,  # Required field - ensures traceability
        help_text="Source purchase item - Required for batch tracking and supplier returns"
    )

    # NEW: Additional Pricing Fields
    ptr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price to Retailer"
    )

    # NEW: Stock Location
    rack_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Physical rack/shelf location (e.g., A-12-03)"
    )

    # NEW: Packing and Free Quantity
    free_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Free quantity received with this batch"
    )

    # NEW: Structured Packing Fields (MANDATORY)
    pack_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of packs/strips received (e.g., 50 strips)"
    )
    units_per_pack = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of units per pack (e.g., 15 tablets per strip)"
    )
    price_per_pack = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price per pack/strip (e.g., ₹180 per strip)"
    )

    # Auto-calculated fields
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Calculated: price_per_pack ÷ units_per_pack"
    )
    total_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calculated: pack_quantity × units_per_pack (total tablets/units)"
    )

    # Old packing field (kept for backward compatibility, now optional)
    packing = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Legacy packing details - Auto-generated from structured fields"
    )

    # NEW: GST Fields
    cgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="CGST percentage"
    )
    sgst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="SGST percentage"
    )
    igst_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="IGST percentage"
    )
    margin_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Profit margin percentage"
    )

    # NEW: Alert flags (auto-calculated)
    is_near_expiry = models.BooleanField(default=False, help_text="Expiring within 3 months")
    is_expired = models.BooleanField(default=False, help_text="Already expired")
    is_low_stock = models.BooleanField(default=False, help_text="Below reorder level")
    is_out_of_stock = models.BooleanField(default=False, help_text="Stock is completely out (quantity = 0)")

    # Verification/Approval Status
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this stock has been verified/approved by pharmacist. Unverified stock cannot be dispensed."
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='verified_stocks',
        null=True,
        blank=True,
        help_text="Pharmacist who verified this stock entry"
    )
    verified_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this stock was verified"
    )

    def __str__(self):
        return f"{self.medication.name} - Batch {self.batch_number} (Expires {self.expiry_date})"

    def calculate_packing_values(self):
        """
        Calculate packing-related values:
        - price_per_unit = price_per_pack ÷ units_per_pack
        - total_units = pack_quantity × units_per_pack
        - Auto-generate packing description
        """
        from decimal import Decimal

        if self.price_per_pack and self.units_per_pack:
            self.price_per_unit = Decimal(str(self.price_per_pack)) / Decimal(str(self.units_per_pack))

        if self.pack_quantity and self.units_per_pack:
            self.total_units = self.pack_quantity * self.units_per_pack

        # Auto-generate packing description for legacy field
        if self.pack_quantity and self.units_per_pack:
            self.packing = f"{self.pack_quantity} packs × {self.units_per_pack} units = {self.total_units} total units"

    def save(self, *args, **kwargs):
        """Override save to auto-calculate packing values"""
        self.calculate_packing_values()
        super().save(*args, **kwargs)

    def get_current_stock(self):
        """Calculate current stock based on all transactions"""
        return (self.opening_quantity + self.received_quantity -
                self.sold_quantity - self.returned_quantity -
                self.damaged_quantity + self.adjusted_quantity)

    def days_to_expiry(self):
        """Calculate days until expiry"""
        from datetime import datetime
        delta = self.expiry_date - datetime.now().date()
        return delta.days

    def check_expiry_status(self):
        """Update expiry status flags"""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        three_months = today + timedelta(days=90)

        self.is_expired = self.expiry_date < today
        self.is_near_expiry = today <= self.expiry_date <= three_months

    def get_expiration_status(self):
        """Get human-readable expiration status"""
        if self.is_expired:
            return "EXPIRED"
        elif self.is_near_expiry:
            return "NEAR_EXPIRY"
        else:
            return "VALID"

    def get_unallocated_quantity(self):
        """Calculate unallocated quantity"""
        allocated = self.pharmacy_quantity + self.home_care_quantity + self.casualty_quantity
        return max(0, self.quantity - allocated)

    def get_allocated_total(self):
        """Get total allocated quantity across all departments"""
        return self.pharmacy_quantity + self.home_care_quantity + self.casualty_quantity

    class Meta:
        db_table = 'medication_stock'
        ordering = ['expiry_date', 'batch_number']
        verbose_name = 'Medication Stock'
        verbose_name_plural = 'Medication Stocks'
        indexes = [
            models.Index(fields=['medication', 'expiry_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['is_active']),
            models.Index(fields=['medication', 'is_active']),
            models.Index(fields=['is_active', 'expiry_date']),
            models.Index(fields=['is_expired']),
            models.Index(fields=['is_near_expiry']),
            models.Index(fields=['is_out_of_stock']),
        ]

    def save(self, *args, **kwargs):
        # Auto-update expiry flags
        self.check_expiry_status()

        # Auto-update out-of-stock flag
        self.is_out_of_stock = (self.quantity == 0)

        super().save(*args, **kwargs)


class StockTransfer(Base):
    """
    Stock Transfer Model - Department-wise Stock Movement

    Tracks inter-department transfers of medication stock.
    Allows borrowing/transferring stock between Pharmacy, Home Care, and Casualty departments.

    Usage:
        - Transfer stock from one department to another
        - Track borrowing when a department runs low
        - Maintain audit trail of all stock movements
        - Return borrowed stock to original department

    Fields:
        stock_entry: Foreign key to MedicationStock (which batch)
        from_department: Source department (PHARMACY, HOME_CARE, CASUALTY)
        to_department: Destination department (PHARMACY, HOME_CARE, CASUALTY)
        quantity_transferred: Number of units transferred
        reason: Why transfer was needed
        transferred_by: User who authorized the transfer
        transfer_date: When transfer occurred
        status: Transfer status (PENDING, COMPLETED, CANCELLED)

    Business Logic:
        - Cannot transfer more than available in source department
        - Updates source department quantity (decrease)
        - Updates destination department quantity (increase)
        - Total stock quantity remains unchanged (internal movement)
        - Full audit trail maintained
    """

    DEPARTMENT_CHOICES = [
        ('PHARMACY', 'Main Pharmacy'),
        ('HOME_CARE', 'Home Care'),
        ('CASUALTY', 'Casualty/Emergency'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    stock_entry = models.ForeignKey(
        MedicationStock,
        on_delete=models.PROTECT,
        related_name='transfers',
        help_text="Stock batch being transferred"
    )

    from_department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        help_text="Source department"
    )

    to_department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        help_text="Destination department"
    )

    quantity_transferred = models.PositiveIntegerField(
        help_text="Number of units transferred"
    )

    reason = models.TextField(
        help_text="Reason for transfer (e.g., 'Home care stock low')"
    )

    transferred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_transfers',
        help_text="User who authorized the transfer"
    )

    transfer_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When transfer was created"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='COMPLETED',
        help_text="Transfer status"
    )

    class Meta:
        db_table = 'stock_transfer'
        ordering = ['-transfer_date']
        verbose_name = 'Stock Transfer'
        verbose_name_plural = 'Stock Transfers'
        indexes = [
            models.Index(fields=['stock_entry']),
            models.Index(fields=['from_department']),
            models.Index(fields=['to_department']),
            models.Index(fields=['transfer_date']),
            models.Index(fields=['status']),
            models.Index(fields=['transferred_by']),
        ]

    def __str__(self):
        return f"{self.from_department} → {self.to_department}: {self.quantity_transferred} units ({self.stock_entry.medication.name})"

    def clean(self):
        """Validate transfer"""
        from django.core.exceptions import ValidationError

        # Cannot transfer to same department
        if self.from_department == self.to_department:
            raise ValidationError("Cannot transfer to the same department")

        # Check if source department has enough quantity
        stock = self.stock_entry
        if self.from_department == 'PHARMACY':
            available = stock.pharmacy_quantity
        elif self.from_department == 'HOME_CARE':
            available = stock.home_care_quantity
        elif self.from_department == 'CASUALTY':
            available = stock.casualty_quantity
        else:
            available = 0

        if self.quantity_transferred > available:
            raise ValidationError(
                f"Insufficient quantity in {self.from_department}. "
                f"Available: {available}, Requested: {self.quantity_transferred}"
            )

    def process_transfer(self):
        """Execute the stock transfer"""
        from django.db import transaction

        with transaction.atomic():
            stock = self.stock_entry
            qty = self.quantity_transferred

            # Decrease from source department
            if self.from_department == 'PHARMACY':
                stock.pharmacy_quantity -= qty
            elif self.from_department == 'HOME_CARE':
                stock.home_care_quantity -= qty
            elif self.from_department == 'CASUALTY':
                stock.casualty_quantity -= qty

            # Increase in destination department
            if self.to_department == 'PHARMACY':
                stock.pharmacy_quantity += qty
            elif self.to_department == 'HOME_CARE':
                stock.home_care_quantity += qty
            elif self.to_department == 'CASUALTY':
                stock.casualty_quantity += qty

            stock.save()

            # Mark transfer as completed
            self.status = 'COMPLETED'
            self.save(update_fields=['status'])


class MedicationDispense(Base):
    """
    Medication Dispense Model

    Records medication dispensing transactions from pharmacy.

    Usage:
        - Tracks medications given to patients
        - Links prescription to stock deduction
        - Records who dispensed the medication
        - Used for inventory management

    Fields:
        prescribed_medicine: Foreign key to PrescribedMedicine
        stock_entry: Foreign key to MedicationStock (batch tracking)
        quantity_dispensed: Quantity given to patient
        dispensed_date: Date and time of dispensing
        dispensed_by: Pharmacist who dispensed (User FK)
    """
    prescribed_medicine = models.ForeignKey(PrescribedMedicine, on_delete=models.CASCADE)
    stock_entry = models.ForeignKey(MedicationStock, on_delete=models.CASCADE)
    quantity_dispensed = models.PositiveIntegerField()
    dispensed_date = models.DateTimeField(auto_now_add=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'medication_dispense'
        ordering = ['-dispensed_date']
        verbose_name = 'Medication Dispense'
        verbose_name_plural = 'Medication Dispenses'
        indexes = [
            models.Index(fields=['prescribed_medicine']),
            models.Index(fields=['stock_entry']),
            models.Index(fields=['dispensed_date']),
            models.Index(fields=['dispensed_by']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.quantity_dispensed} of {self.stock_entry.medication.name} to {self.prescribed_medicine.consultation.appointment.patient.first_name}"



# ============================================================================
# ADVANCED PHARMACY MANAGEMENT MODELS
# ============================================================================
# Author: Enhanced Pharmacy Module
# Purpose: Purchase Orders, GRN, Unit Conversion, Stock Returns, Expiry Management
# ============================================================================


class PatientMedicineReturn(Base):
    """
    Patient Medicine Return - Simplified Workflow

    Direct refund process by pharmacist without approval workflow.
    Supports returns from both PatientBill (consultation-based) and PharmacyBilling (OTC sales).

    Workflow: Create Return → Process Refund → Auto Stock Adjustment
    """
    return_number = models.CharField(max_length=50, unique=True, editable=False)
    patient = models.ForeignKey(PatientRegistration, on_delete=models.PROTECT, related_name='medicine_returns', null=True, blank=True)

    # Link to either patient bill (prescription-based) OR pharmacy bill (OTC sales)
    # One of these must be provided
    patient_bill = models.ForeignKey('PatientBill', on_delete=models.PROTECT, related_name='medicine_returns', null=True, blank=True)
    pharmacy_bill = models.ForeignKey('PharmacyBilling', on_delete=models.PROTECT, related_name='medicine_returns', null=True, blank=True)

    # Return tracking
    return_date = models.DateField(auto_now_add=True)
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Refund method
    refund_method = models.CharField(max_length=20, choices=[
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('ORIGINAL_MODE', 'Original Payment Mode'),
    ], default='CASH')

    # Simplified status - just refunded or not
    is_refunded = models.BooleanField(default=False)

    # Processing details
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_medicine_returns')
    processed_date = models.DateTimeField(null=True, blank=True)

    # Stock adjustment tracking
    stock_adjusted = models.BooleanField(default=False)

    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Reason for return or additional notes")

    class Meta:
        ordering = ['-return_date', '-id']
        verbose_name = 'Patient Medicine Return'
        verbose_name_plural = 'Patient Medicine Returns'
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(patient_bill__isnull=False, pharmacy_bill__isnull=True) |
                    models.Q(patient_bill__isnull=True, pharmacy_bill__isnull=False)
                ),
                name='either_patient_bill_or_pharmacy_bill'
            )
        ]

    def __str__(self):
        if self.patient:
            return f"{self.return_number} - {self.patient.first_name} {self.patient.last_name}"
        return f"{self.return_number}"

    def clean(self):
        """Validate that exactly one bill type is provided"""
        from django.core.exceptions import ValidationError

        if not self.patient_bill and not self.pharmacy_bill:
            raise ValidationError("Either patient_bill or pharmacy_bill must be provided")

        if self.patient_bill and self.pharmacy_bill:
            raise ValidationError("Cannot have both patient_bill and pharmacy_bill")

    def save(self, *args, **kwargs):
        # Auto-generate return number
        if not self.return_number:
            last_return = PatientMedicineReturn.objects.order_by('-id').first()
            if last_return and last_return.return_number:
                try:
                    last_num = int(last_return.return_number.split('-')[1])
                    self.return_number = f"PRET-{last_num + 1:06d}"
                except:
                    self.return_number = "PRET-000001"
            else:
                self.return_number = "PRET-000001"

        # Auto-calculate total refund from items
        if self.pk:
            self.total_refund_amount = sum(item.refund_amount for item in self.items.all())

        super().save(*args, **kwargs)

    def process_stock_adjustment(self):
        """
        Adjust stock for all returned items based on their condition.
        Called after refund is processed.
        """
        from django.db import transaction

        if self.stock_adjusted:
            return  # Already adjusted

        with transaction.atomic():
            for item in self.items.all():
                stock = item.stock_entry
                qty = item.quantity_returned

                if item.condition == 'UNOPENED':
                    # Can resell - add back to available stock
                    stock.adjusted_quantity += qty
                    # Only decrease sold_quantity if it's greater than the return quantity
                    if stock.sold_quantity >= qty:
                        stock.sold_quantity -= qty
                elif item.condition in ['OPENED', 'DAMAGED']:
                    # Cannot resell - mark as damaged
                    stock.damaged_quantity += qty
                    # Only decrease sold_quantity if it's greater than the return quantity
                    if stock.sold_quantity >= qty:
                        stock.sold_quantity -= qty

                stock.save()

            self.stock_adjusted = True
            self.save(update_fields=['stock_adjusted'])


class PatientMedicineReturnItem(Base):
    """
    Patient Medicine Return Line Items

    Tracks individual medications being returned with their condition
    and determines if they can be restocked or should be written off.
    """
    patient_return = models.ForeignKey(PatientMedicineReturn, on_delete=models.CASCADE, related_name='items')

    # Medication details
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT, help_text="Medication being returned")
    stock_entry = models.ForeignKey(MedicationStock, on_delete=models.PROTECT, help_text="Original stock batch")

    # Batch tracking for verification
    batch_number = models.CharField(max_length=100, help_text="Batch number from original package")
    expiry_date = models.DateField(help_text="Expiry date from original package")

    # Quantities
    quantity_returned = models.PositiveIntegerField(help_text="Quantity being returned")

    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit from original bill")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False, help_text="Auto-calculated refund")

    # Condition assessment
    condition = models.CharField(max_length=20, choices=[
        ('UNOPENED', 'Unopened/Sealed - Can Resell'),
        ('OPENED', 'Opened - Cannot Resell'),
        ('DAMAGED', 'Damaged - Write Off'),
    ], help_text="Physical condition of returned medicine")

    # Restock decision
    can_restock = models.BooleanField(default=False, editable=False, help_text="Auto-determined based on condition")

    class Meta:
        verbose_name = 'Medicine Return Item'
        verbose_name_plural = 'Medicine Return Items'

    def __str__(self):
        return f"{self.medication.name} ({self.medication.strength}) - {self.quantity_returned} units"

    def save(self, *args, **kwargs):
        # Auto-calculate refund amount
        self.refund_amount = self.quantity_returned * self.unit_price

        # Auto-determine restock eligibility based on condition
        if self.condition == 'UNOPENED':
            self.can_restock = True
        elif self.condition in ['OPENED', 'DAMAGED']:
            self.can_restock = False

        # Auto-populate batch info from stock entry if not provided
        if not self.batch_number and self.stock_entry:
            self.batch_number = self.stock_entry.batch_number
        if not self.expiry_date and self.stock_entry:
            self.expiry_date = self.stock_entry.expiry_date

        super().save(*args, **kwargs)


class MedicationReorderConfig(Base):
    """
    Reorder Level Configuration for each medication
    """
    medication = models.OneToOneField(Medication, on_delete=models.CASCADE, related_name='reorder_config')
    reorder_level = models.PositiveIntegerField(default=50)
    reorder_quantity = models.PositiveIntegerField(default=100)
    max_stock_level = models.PositiveIntegerField(default=500)
    lead_time_days = models.PositiveIntegerField(default=7)
    is_auto_reorder = models.BooleanField(default=False)
    # preferred_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.medication.name} - Reorder at {self.reorder_level}"


class ExpiryAlertLog(Base):
    """
    Expiry Alert Log - Tracks alerts sent for near-expiry medications
    """
    stock_entry = models.ForeignKey(MedicationStock, on_delete=models.CASCADE, related_name='expiry_alerts')
    alert_type = models.CharField(max_length=20, choices=[
        ('EXPIRED', 'Already Expired'),
        ('CRITICAL', 'Expiring in 30 days'),
        ('WARNING', 'Expiring in 3 months'),
        ('INFO', 'Expiring in 6 months'),
    ])
    expiry_date = models.DateField()
    alert_sent_date = models.DateTimeField(auto_now_add=True)
    alert_recipients = models.JSONField(default=list)
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['expiry_date', '-alert_sent_date']

    def __str__(self):
        return f"{self.alert_type} - {self.stock_entry.medication.name} (Expires: {self.expiry_date})"


# ============================================================================
# BILLING MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Patient billing, pharmacy billing, and payment management
# ============================================================================

class PatientBill(Base):
    """
    Patient Bill Model

    Generates consolidated bills for patient consultations and medications.

    Usage:
        - Creates final bill after consultation and pharmacy
        - Combines consultation fees and medicine costs
        - Stores patient and doctor information for records
        - Tracks payment status
        - Generates bill receipts

    Fields:
        bill_number: Unique bill identifier (auto-generated)
        patient_name: Patient name (denormalized for reports)
        doctor_name: Doctor name (denormalized for reports)
        consultation: Foreign key to DoctorConsultation
        appointment: Foreign key to Appointment
        bill_date: Bill generation timestamp
        appointment_date/time: Appointment details
        consultation_fee: Doctor's consultation charge
        total_medicine_cost: Total medicine charges
        total_bill_amount: Grand total (auto-calculated)
        medicine_items: JSON array of medicine line items
        payment_status: Payment status (Pending/Paid/Cancelled)
        payment_type: Payment method (Cash/Card/UPI/Other)

    Business Logic:
        - Auto-generates bill_number on save
        - Auto-calculates total_bill_amount
    """
    bill_number = models.CharField(max_length=50, unique=True)

    # Patient and Doctor Information
    patient_name = models.CharField(max_length=255)
    doctor_name = models.CharField(max_length=255)
    
    # Original References (for database integrity)
    consultation = models.OneToOneField(DoctorConsultation, on_delete=models.PROTECT)
    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT)
    
    # Date Information
    bill_date = models.DateTimeField(auto_now_add=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    
    # Amount Information
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_medicine_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_bill_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Store medicine items as JSON
    medicine_items = models.JSONField(default=list)
    
    # Payment Status
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
        ('OTHER', 'Other')
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='CASH')
    
    class Meta:
        db_table = 'patient_bill'
        ordering = ['-bill_date']
        verbose_name = 'Patient Bill'
        verbose_name_plural = 'Patient Bills'
        indexes = [
            models.Index(fields=['bill_number']),
            models.Index(fields=['appointment']),
            models.Index(fields=['consultation']),
            models.Index(fields=['bill_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_status', 'bill_date']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_on']),
        ]

    def __str__(self):
        return f"Bill #{self.bill_number} - {self.patient_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate bill number if not provided
        if not self.bill_number:
            last_bill = PatientBill.objects.order_by('-id').first()
            if last_bill:
                last_id = int(last_bill.bill_number.split('-')[1])
                self.bill_number = f"BILL-{last_id + 1:06d}"
            else:
                self.bill_number = "BILL-000001"
        
        # Ensure total bill amount is correct
        self.total_bill_amount = self.consultation_fee + self.total_medicine_cost
        
        super().save(*args, **kwargs)


class Pharmacy_Medication(Base):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    stock_entry = models.ForeignKey(MedicationStock, on_delete=models.CASCADE)
    diagnosis = models.TextField()
    dispensed_date = models.DateTimeField(auto_now_add=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True ,related_name='dispensed_medications')
    quantity_dispensed = models.PositiveIntegerField()
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)


class PharmacyBilling(Base):
    bill_number = models.CharField(max_length=20, unique=True)
    patient_name = models.CharField(max_length=100)
    bill_date = models.DateField(null=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pharmacy_billing')
    age = models.PositiveIntegerField(null=True)
    gender = models.CharField(max_length=10,null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    payment_type = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash'),
            ('CARD', 'Card'),
            ('UPI', 'UPI'),
            ('OTHER', 'Other')
        ],
        default='CASH'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    items = models.JSONField(default=list, null=True)
    others = models.JSONField(default=list, null=True)

    class Meta:
        db_table = 'pharmacy_billing'
        ordering = ['-bill_date', '-created_on']
        verbose_name = 'Pharmacy Billing'
        verbose_name_plural = 'Pharmacy Billings'
        indexes = [
            models.Index(fields=['bill_number']),
            models.Index(fields=['bill_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_status', 'bill_date']),
            models.Index(fields=['dispensed_by']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_on']),
        ]


class PharmacyBillingItem(Base):
    billing = models.ForeignKey(PharmacyBilling, related_name='items_set', on_delete=models.CASCADE)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    stock_entry = models.ForeignKey(MedicationStock, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,null=True)


# ============================================================================
# LABORATORY MODELS
# ============================================================================
# Author: Athul Gopan
# Purpose: Lab test management, billing, and hierarchical test catalog
# ============================================================================

class LabBilling(Base):
    bill_number = models.CharField(max_length=20, unique=True)
    patient_name = models.CharField(max_length=100)
    bill_date = models.DateField(null=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='Lab_billing')
    age = models.PositiveIntegerField(null=True)
    gender = models.CharField(max_length=10,null=True)
    discount = models.DecimalField(null=True,max_digits=10, decimal_places=2, default=0.00)
 
    payment_type = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash'),
            ('CARD', 'Card'),
            ('UPI', 'UPI'),
            ('OTHER', 'Other')
        ],
        default='CASH'
    )
 
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PAID', 'Paid'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING'
    )
 
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    items = models.JSONField(default=list, null=True)


class LabDepartment(Base):
    """
    Lab Department Model

    Represents laboratory departments (e.g., Hematology, Biochemistry).

    Usage:
        - Organizes lab tests by department
        - Stores department-level pricing
        - Links to test categories
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    rate = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


class TestCategory(models.Model):
    """
    Test Category Model

    Hierarchical categorization of lab tests.

    Usage:
        - Groups related tests (e.g., CBC, Lipid Profile)
        - Supports parent-child hierarchy
        - Links to department and parameters

    Fields:
        department: Parent lab department
        name: Category name
        code: Unique category code
        description: Category details
        parent: Parent category for hierarchical structure

    Example:
        Hematology > CBC > Hemoglobin
    """
    department = models.ForeignKey(LabDepartment, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name='subcategories', null=True, blank=True)

    class Meta:
        unique_together = ['department', 'name']

    def __str__(self):
        return f"{self.department.name} - {self.name}" if not self.parent else f"{self.parent.name} > {self.name}"


class TestParameter(models.Model):
    """
    Test Parameter Model

    Individual test components within a category.

    Usage:
        - Defines specific test parameters (e.g., Hemoglobin, WBC)
        - Stores normal value ranges via ReferenceRange
        - Supports both quantitative and qualitative tests

    Fields:
        category: Parent test category
        name: Parameter name
        code: Parameter code
        unit: Measurement unit (e.g., 'g/dL', 'cells/μL')
        is_qualitative: Boolean for qualitative tests
        normal_values: JSON storage for reference ranges
        sequence_order: Display order in reports
        is_active: Activation status
    """
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    unit = models.CharField(max_length=50, blank=True)
    is_qualitative = models.BooleanField(default=False)
    normal_values = models.JSONField(blank=True, null=True)
    sequence_order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['category', 'code']
        ordering = ['sequence_order', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ReferenceRange(models.Model):
    """
    Reference Range Model

    Defines normal value ranges for test parameters by age/gender.

    Usage:
        - Stores reference ranges for different demographics
        - Supports age and gender-specific ranges
        - Used for flagging abnormal results

    Fields:
        parameter: Foreign key to TestParameter
        gender: Gender category (Male/Female/Other/All)
        age_min/age_max: Age range applicability
        min_val/max_val: Normal value range
        note: Additional notes

    Example:
        Hemoglobin | Male | 18-65yrs : 13.5 - 17.5 g/dL
    """
    parameter = models.ForeignKey(TestParameter, on_delete=models.CASCADE, related_name='reference_ranges')
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
    age_min = models.PositiveIntegerField(blank=True, null=True)
    age_max = models.PositiveIntegerField(blank=True, null=True)
    min_val = models.FloatField()
    max_val = models.FloatField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['age_min']

    def __str__(self):
        return f"{self.parameter.name} | {self.gender or 'All'} | {self.age_min or 0}-{self.age_max or '∞'}yrs : {self.min_val} - {self.max_val} {self.parameter.unit}"


class LabTestOrder(Base):
    """
    Lab Test Order Model - External Lab Management

    Purpose:
        Manages lab test orders sent to external laboratories.
        Tracks order lifecycle from creation to result delivery.
        Supports partial payment workflow for real-world scenarios.

    Workflow:
        1. Patient comes (with/without appointment)
        2. Select tests from TestCategory
        3. Collect payment (full/partial/advance)
        4. Send samples to external lab
        5. Upload PDF results when received
        6. Complete order and deliver to patient

    Fields:
        patient: Link to patient (required)
        appointment: Link to appointment (nullable for walk-ins)
        order_number: Auto-generated unique order ID
        selected_tests: JSON array of selected test details
        external_lab_name: Name of external laboratory
        external_reference_number: Lab's reference number
        status: Order status (ORDERED/SENT/RECEIVED/COMPLETED/CANCELLED)
        total_amount: Total bill amount
        paid_amount: Total amount paid so far
        balance_amount: Remaining amount to be paid
        discount: Discount applied
        payment_status: Payment status (UNPAID/PARTIALLY_PAID/PAID/REFUNDED)
        date_ordered: Order creation date
        date_sent: Date sent to external lab
        date_received: Date results received
        special_instructions: Additional notes for lab

    Related Models:
        - PatientRegistration (Many-to-One)
        - Appointment (Many-to-One, nullable)
        - LabPaymentTransaction (One-to-Many via 'payments')
        - LabTestResult (One-to-Many via 'results')

    Example:
        # Walk-in patient with partial payment
        order = LabTestOrder.objects.create(
            patient=patient,
            appointment=None,  # Walk-in
            selected_tests=[{"id": 1, "name": "CBC", "price": 500}],
            total_amount=500,
            paid_amount=200,  # Advance payment
            balance_amount=300,
            payment_status='PARTIALLY_PAID',
            status='ORDERED'
        )
    """
    # Patient & Appointment Tracking
    patient = models.ForeignKey(
        'PatientRegistration',
        on_delete=models.CASCADE,
        related_name='lab_orders',
        help_text="Patient for whom tests are ordered"
    )
    appointment = models.ForeignKey(
        'Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lab_orders',
        help_text="Related appointment (null for walk-in patients)"
    )

    # Order Details
    order_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique order number (e.g., LAB-2025-0001)"
    )
    lab_departments = models.ManyToManyField(
        'LabDepartment',
        related_name='lab_orders',
        help_text="Lab departments/test categories ordered (e.g., Hematology, Biochemistry)"
    )
    selected_tests = models.JSONField(
        default=list,
        help_text="Array of selected test details for quick display: [{id, name, category, price}, ...]"
    )

    # External Lab Tracking
    external_lab_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Name of external laboratory (e.g., 'Path Lab', 'Dr. Lal PathLabs')"
    )
    external_reference_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Reference number provided by external lab"
    )

    # Order Status
    status = models.CharField(
        max_length=20,
        choices=LAB_ORDER_STATUS_CHOICES,
        default='ORDERED',
        help_text="Current status of the lab order"
    )

    # Payment Tracking (supports partial payments)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total bill amount before discount"
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total amount paid so far (sum of all transactions)"
    )
    balance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Remaining amount to be paid (total - paid - discount)"
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Discount amount applied"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=LAB_PAYMENT_STATUS_CHOICES,
        default='UNPAID',
        help_text="Payment status (supports partial payments)"
    )

    # Date Tracking
    date_ordered = models.DateField(
        auto_now_add=True,
        help_text="Date when order was created"
    )
    date_sent = models.DateField(
        null=True,
        blank=True,
        help_text="Date when samples were sent to external lab"
    )
    date_received = models.DateField(
        null=True,
        blank=True,
        help_text="Date when results were received from external lab"
    )

    # Additional Information
    special_instructions = models.TextField(
        blank=True,
        help_text="Special instructions or notes for the lab"
    )

    class Meta:
        ordering = ['-date_ordered', '-created_on']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['patient', 'date_ordered']),
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['date_ordered']),
        ]
        verbose_name = "Lab Test Order"
        verbose_name_plural = "Lab Test Orders"

    def __str__(self):
        return f"{self.order_number} - {self.patient.first_name} {self.patient.last_name} ({self.status})"

    def save(self, *args, **kwargs):
        """Auto-generate order number if not provided"""
        if not self.order_number:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            last_order = LabTestOrder.objects.filter(
                order_number__startswith=f'LAB-{date_str}'
            ).order_by('-order_number').first()

            if last_order:
                last_seq = int(last_order.order_number.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1

            self.order_number = f'LAB-{date_str}-{new_seq:04d}'

        # Auto-calculate balance amount
        self.balance_amount = self.total_amount - self.paid_amount - self.discount

        super().save(*args, **kwargs)


class LabPaymentTransaction(Base):
    """
    Lab Payment Transaction Model

    Purpose:
        Tracks individual payment transactions for lab test orders.
        Supports multiple payments for a single order (partial payments).

    Usage:
        - Record each payment made by patient
        - Support multiple payment methods per order
        - Generate receipt for each transaction
        - Maintain audit trail of all payments

    Fields:
        lab_order: Parent lab test order
        transaction_id: Auto-generated unique transaction ID
        amount: Payment amount
        payment_type: Payment method (CASH/CARD/UPI/etc.)
        payment_date: Transaction date (auto-set)
        received_by: Staff who received payment
        receipt_number: Receipt number (optional)
        notes: Additional notes

    Related Models:
        - LabTestOrder (Many-to-One)
        - User (Many-to-One for received_by)

    Example:
        # First payment (advance)
        LabPaymentTransaction.objects.create(
            lab_order=order,
            amount=200,
            payment_type='CASH',
            received_by=user
        )

        # Second payment (remaining)
        LabPaymentTransaction.objects.create(
            lab_order=order,
            amount=300,
            payment_type='UPI',
            received_by=user
        )
    """
    # Order Link
    lab_order = models.ForeignKey(
        'LabTestOrder',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Related lab test order"
    )

    # Transaction Details
    transaction_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique transaction ID"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        help_text="Payment method (CASH/CARD/UPI/etc.)"
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time of payment"
    )

    # Staff Tracking
    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lab_payments_received',
        help_text="Staff member who received the payment"
    )

    # Receipt Information
    receipt_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Receipt number (if generated)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the transaction"
    )

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['lab_order', 'payment_date']),
            models.Index(fields=['payment_date']),
        ]
        verbose_name = "Lab Payment Transaction"
        verbose_name_plural = "Lab Payment Transactions"

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount} ({self.payment_type})"

    def save(self, *args, **kwargs):
        """Auto-generate transaction ID if not provided"""
        if not self.transaction_id:
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d%H%M%S')
            self.transaction_id = f'TXN-{date_str}-{self.lab_order.order_number.split("-")[-1]}'

        super().save(*args, **kwargs)


class LabTestResult(Base):
    """
    Lab Test Result Model - PDF Storage

    Purpose:
        Stores PDF reports received from external laboratories.
        Links results to patient and lab order.
        Maintains document metadata and audit trail.

    Usage:
        - Upload PDF reports from external labs
        - Store multiple results per order (if needed)
        - Track who uploaded and when
        - Retrieve patient lab history

    Fields:
        lab_order: Related lab test order
        patient: Patient (denormalized for quick access)
        report_pdf: PDF file upload
        report_date: Date of the lab report
        uploaded_by: User who uploaded the PDF
        uploaded_on: Upload timestamp (auto-set)
        file_name: Original filename
        file_size: File size in bytes
        notes: Additional notes about the report

    Related Models:
        - LabTestOrder (Many-to-One)
        - PatientRegistration (Many-to-One)
        - User (Many-to-One for uploaded_by)

    File Storage:
        PDFs stored at: media/lab_reports/YYYY/MM/filename.pdf
        Organized by year and month for better management

    Example:
        result = LabTestResult.objects.create(
            lab_order=order,
            patient=order.patient,
            report_pdf=pdf_file,
            report_date='2025-12-14',
            uploaded_by=user,
            file_name='CBC_Report_Patient123.pdf',
            notes='All parameters normal'
        )
    """
    # Order and Patient Link
    lab_order = models.ForeignKey(
        'LabTestOrder',
        on_delete=models.CASCADE,
        related_name='results',
        help_text="Related lab test order"
    )
    patient = models.ForeignKey(
        'PatientRegistration',
        on_delete=models.CASCADE,
        related_name='lab_results',
        help_text="Patient (denormalized for quick queries)"
    )

    # PDF File Storage
    report_pdf = models.FileField(
        upload_to='lab_reports/%Y/%m/',
        help_text="PDF report file (organized by year/month)"
    )

    # Report Details
    report_date = models.DateField(
        help_text="Date mentioned on the lab report"
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lab_results_uploaded',
        help_text="User who uploaded the report"
    )
    uploaded_on = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time of upload"
    )

    # File Metadata
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes"
    )

    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or observations about the report"
    )

    class Meta:
        ordering = ['-report_date', '-uploaded_on']
        indexes = [
            models.Index(fields=['patient', 'report_date']),
            models.Index(fields=['lab_order']),
            models.Index(fields=['uploaded_on']),
        ]
        verbose_name = "Lab Test Result"
        verbose_name_plural = "Lab Test Results"

    def __str__(self):
        return f"{self.lab_order.order_number} - {self.file_name} ({self.report_date})"

    def save(self, *args, **kwargs):
        """Extract file metadata before saving"""
        if self.report_pdf and not self.file_size:
            self.file_size = self.report_pdf.size
            if not self.file_name:
                self.file_name = self.report_pdf.name

        super().save(*args, **kwargs)