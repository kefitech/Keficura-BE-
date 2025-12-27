# from django.db import models
# from base_util.base import *
# from django.utils import timezone
# from django.contrib.auth.models import User
# from apps.data_hub.models import *

# class Nurse(Base):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)

#     # Personal Details
#     date_of_birth = models.DateField(null=True)
#     gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')], null=True)

#     # Contact Info
#     contact_number = models.CharField(max_length=15)
#     email = models.EmailField()
    
#     # Qualifications and experience
#     qualification = models.CharField(max_length=255, null=True)
#     experience_years = models.PositiveIntegerField(null=True)
#     profile_picture = models.ImageField(upload_to='nurses/', blank=True, null=True)

#     def __str__(self):
#         return f"Nurse {self.user.first_name} {self.user.last_name}"

# class NurseShiftAssignment(Base):
#     nurse = models.ForeignKey(Nurse, on_delete=models.CASCADE, related_name='shift_assignments')
#     department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='nurse_assignments')

#     day = models.DateField()  # Which day is this shift for?
    
#     shift_type = models.CharField(max_length=20, choices=[
#         ('MORNING', 'Morning'),
#         ('AFTERNOON', 'Afternoon'),
#         ('EVENING', 'Evening'),
#         ('NIGHT', 'Night'),
#         ('FULL_DAY', 'Full Day'),
#         ('CUSTOM', 'Custom'),
#     ], default='FULL_DAY')

#     start_time = models.TimeField(null=True, blank=True)
#     end_time = models.TimeField(null=True, blank=True)

#     room_number = models.CharField(max_length=50, blank=True, null=True)
    
#     class Meta:
#         unique_together = ('nurse', 'day', 'shift_type')
#         ordering = ['day', 'start_time']

#     def __str__(self):
#         return f"{self.nurse} - {self.department} - {self.day} ({self.shift_type})"


