# from django.db import models
# from django.utils import timezone
# from django.contrib.auth.models import User
# from base_util.base import *

# class PatientRegistration(Base):
#     GENDER_CHOICES = [
#         ('M', 'Male'),
#         ('F', 'Female'),
#         ('O', 'Other'),
#     ]    
#     patient_id = models.CharField(max_length=50, unique=True)
#     first_name = models.CharField(max_length=100,null=True,blank=True)
#     last_name = models.CharField(max_length=100,null=True,blank=True)
#     date_of_birth = models.DateField()
#     age = models.IntegerField(null=True)
#     gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
#     contact_number = models.CharField(max_length=15)
#     email = models.EmailField(blank=True, null=True)
#     address = models.TextField(blank=True, null=True)
#     allergies = models.TextField(blank=True, null=True)
#     emergency_contact = models.CharField(max_length=100,null=True)
#     registration_date = models.DateField()
#     registration_type = models.CharField(max_length=50,null=True)
#     insurance_provider = models.CharField(max_length=100,null=True)
#     insurance_number = models.CharField(max_length=50,null=True)
   
    
    
#     def __str__(self):
#         return f"{self.first_name} {self.last_name} ({self.patient_id})"








