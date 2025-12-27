# from django.db import models
# from django.utils import timezone
# from apps.patients.models import *
# from apps.accounts.models import *
# from base_util.base import *
# # -------------------------------------------------Doctor Model------------------------------------------

# '''re usable status table for  front desk  discharge'''

# class Status(Base):
#     STATUS_CATEGORIES = [
#         ('APPOINTMENT', 'Appointment'),
#         ('BILLING', 'Billing'),
#         ('LAB', 'Lab'),
#         ('DISCHARGE', 'Discharge'),
#         ('ADMISSION', 'Admission'),
#         ('PRESCRIPTION', 'Prescription'),
#         ('GENERIC', 'Generic'),
#     ]
#     code = models.CharField(max_length=50, unique=True)  
#     name = models.CharField(max_length=100)              
#     description = models.TextField(blank=True, null=True)
#     category = models.CharField(max_length=50, choices=STATUS_CATEGORIES)

#     class Meta:
#         verbose_name_plural = "Statuses"
#         unique_together = ('code', 'category')

#     def __str__(self):
#         return f"{self.name} ({self.category})"
    
# class Department(Base):
#     name = models.CharField(max_length=100, unique=True,null=True)
#     code = models.CharField(max_length=10, unique=True,null=True)  
#     description = models.TextField(blank=True)
#     head = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
#     floor = models.CharField(max_length=20, blank=True, null=True)  # Physical location
#     contact_number = models.CharField(max_length=15, blank=True,null=True)
#     email = models.EmailField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.name} ({self.code})"

# class Specialization(Base):
#     name = models.CharField(max_length=100, unique=True)
#     code = models.CharField(max_length=10, unique=True,null=True)  
#     description = models.TextField(blank=True)
#     department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='specializations',null=True)  # Link it!
    
#     def __str__(self):
#         return f"{self.name} ({self.code})"

# class Doctor(Base):
#     user = models.OneToOneField(User, on_delete=models.CASCADE,null=True)

#     # Personal Information
#     date_of_birth = models.DateField(null=True)
#     gender = models.CharField(max_length=10, choices=[
#         ('MALE', 'Male'),
#         ('FEMALE', 'Female'),
#         ('OTHER', 'Other')
#     ],null=True)

#     # Contact Information
#     contact_number = models.CharField(max_length=15)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)
#     email = models.EmailField()


#     # Home Town Address
#     home_address = models.TextField(null=True)
#     home_city = models.CharField(max_length=100,null=True)
#     home_state = models.CharField(max_length=100, blank=True, null=True)
#     home_country = models.CharField(max_length=100,null=True)
#     home_zip_code = models.CharField(max_length=20,null=True)

#     # Professional Information
#     qualification = models.CharField(max_length=255, null=True)
#     experience_years = models.PositiveIntegerField(null=True)
#     profile_picture = models.ImageField(upload_to='doctors/', blank=True, null=True)
#     specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True)
#     date_joined = models.DateField(blank=True, null=True)

#     # Documents
#     curriculum_vitae = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
#     education_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
#     experience_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)

#     # payment information
#     doctor_consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)


#     def __str__(self):
#         return f"Dr. {self.user.first_name} {self.user.last_name}"


# class DoctorSchedule(Base):
#     doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
#     day_of_week = models.CharField(max_length=10, choices=[
#         ('MONDAY', 'Monday'),
#         ('TUESDAY', 'Tuesday'),
#         ('WEDNESDAY', 'Wednesday'),
#         ('THURSDAY', 'Thursday'),
#         ('FRIDAY', 'Friday'),
#         ('SATURDAY', 'Saturday'),
#         ('SUNDAY', 'Sunday'),
#     ],null=True)

#     shift_type = models.CharField(max_length=20, choices=[
#         ('MORNING', 'Morning'),
#         ('AFTERNOON', 'Afternoon'),
#         ('EVENING', 'Evening'),
#         ('NIGHT', 'Night'),
#         ('FULL_DAY', 'Full Day'),
#         ('CUSTOM', 'Custom'),
#     ], default='CUSTOM',null=True)

#     start_time = models.TimeField(null=True)
#     end_time = models.TimeField(null=True)
#     room_number = models.CharField(max_length=50, blank=True, null=True)  # If assigned to a consultation room
#     max_appointments = models.PositiveIntegerField(null=True, blank=True)  # limit per shift/day
#     valid_from = models.DateField(null=True, blank=True)  # Schedule start validity
#     valid_to = models.DateField(null=True, blank=True)    # Schedule end validity
    
#     class Meta:
#         unique_together = ('doctor', 'day_of_week', 'shift_type')
#         ordering = ['doctor', 'day_of_week', 'start_time']

#     def __str__(self):
#         return f"{self.doctor} - {self.day_of_week} ({self.shift_type})"
    

# #---------------------------------------- Doctor Section  ---------------------------------------------- 
# # --------------------------------------- Appointment Section ------------------------------------------ 
# class Appointment(Base):
    
#     appointment_id = models.CharField(max_length=50, unique=True)
#     patient = models.ForeignKey(PatientRegistration, on_delete=models.CASCADE, related_name='appointments')
#     doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
#     appointment_date = models.DateField()
#     appointment_time = models.TimeField()
#     visit_reason = models.TextField(null=True, blank=True)
#     visit_status = models.CharField(max_length=30, choices=[
#         ('SCHEDULED', 'Scheduled'),
#         ('FOLLOW_UP', 'Follow-up'),
#         ('CHECKED_IN', 'Checked In'),
#         ('IN_CONSULTATION', 'In Consultation'),
#         ('PRESCRIPTION_READY', 'Prescription Ready'),
#         ('AT_PHARMACY', 'At Pharmacy'),
#         ('DISPENSED', 'Medications Dispensed'),
#         ('AT_BILLING', 'At Billing'),
#         ('PAYMENT_COMPLETE', 'Payment Complete'),
#         ('COMPLETED', 'Completed'),
#         ('CANCELED', 'Canceled'),
#     ], default='SCHEDULED')

#     consultation_room = models.CharField(max_length=20, null=True, blank=True)

#     # Follow-up tracking fields
#     parent_consultation = models.ForeignKey('pharmacy.DoctorConsultation', null=True, blank=True, on_delete=models.SET_NULL, related_name='follow_up_appointments')
#     is_follow_up = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.patient.first_name}'s appointment with Dr. {self.doctor.user.last_name} on {self.appointment_date}"
    

# #--------------------------------------------------------------------------------------------------------

# #=========================================================================================================#
# #                                            DOCTOR CONSULTATION                                          #
# #=========================================================================================================#




