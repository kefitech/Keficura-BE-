# from django.db import models
# from base_util.base import *
# from django.contrib.auth.models import User


# class FrontDeskStaff(Base):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    
#     # Personal Details
#     date_of_birth = models.DateField(null=True, blank=True)
#     gender = models.CharField(max_length=10, 
#                             choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], 
#                             null=True, blank=True)

#     # Contact Info
#     contact_number = models.CharField(max_length=15)
#     emergency_contact = models.CharField(max_length=15, blank=True)
#     email = models.EmailField()

#     # Employment Details
#     employee_id = models.CharField(max_length=20, unique=True)
#     hire_date = models.DateField()
#     department = models.CharField(max_length=50,
#                                  choices=[
#                                      ('RECEPTION', 'Reception'),
#                                      ('BILLING', 'Billing'),
#                                      ('APPOINTMENT', 'Appointment Scheduling'),
#                                      ('PATIENT_SERVICES', 'Patient Services')
#                                  ],null=True)
#     employment_type = models.CharField(max_length=20,
#                                       choices=[
#                                           ('FULL', 'Full-time'),
#                                           ('PART', 'Part-time'),
#                                           ('CONTRACT', 'Contract')
#                                       ],
#                                       default='FULL')
    
#     # Administrative Fields
#     shift_schedule = models.CharField(max_length=100, 
#                                      help_text="E.g., Morning, Evening, Night")
#     # system_access_level = models.CharField(max_length=50,
#     #                                       choices=[
#     #                                           ('BASIC', 'Basic Access'),
#     #                                           ('BILLING', 'Billing Systems'),
#     #                                           ('RECORDS', 'Patient Records'),
#     #                                           ('FULL', 'Full Access')
#     #                                       ],
#     #                                       default='BASIC')
    
#     # Skills & Training
#     # languages = models.ManyToManyField('Language', blank=True)
#     # training_programs = models.TextField(blank=True, 
#     #                                    help_text="Completed training programs/certifications")
    
#     # Work-Specific Information
#     # workstation_number = models.CharField(max_length=10, blank=True)
#     # is_supervisor = models.BooleanField(default=False)
    
#     # Profile Management
#     profile_picture = models.ImageField(upload_to='front_desk_staff/', blank=True, null=True)
#     signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    
#     # Status
#     is_active = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"Front Desk Staff {self.user.get_full_name()} - {self.employee_id}"

#     class Meta:
#         ordering = ['user__last_name']
#         verbose_name = 'Front Desk Staff'
#         verbose_name_plural = 'Front Desk Staff'

# # class Language(models.Model):
# #     name = models.CharField(max_length=50)
# #     code = models.CharField(max_length=5)

# #     def __str__(self):
# #         return self.name





