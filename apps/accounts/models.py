# from django.db import models
# from django.contrib.auth.models import User
# from django.utils.translation import gettext_lazy as _
# from base_util.base import *


# class SystemCreator(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     is_superadmin = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"System Creator: {self.user.username}"
    
# from django.db import models
# from django.contrib.auth.models import User
# from django.utils.translation import gettext_lazy as _
# from base_util.base import *


# class SystemCreator(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     is_superadmin = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"System Creator: {self.user.username}"
    


# class Administrator(Base):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)

#     # Personal details
#     profile_picture = models.ImageField(upload_to='admin_profiles/', null=True, blank=True)
#     phone_number = models.CharField(max_length=15, unique=True)
#     gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
#     date_of_birth = models.DateField(null=True, blank=True)
#     date_joined = models.DateField(blank=True, null=True)

#     # Work and role information
#     # designation = models.CharField(max_length=100, default='System Administrator')
#     # department = models.CharField(max_length=100, null=True, blank=True)
#     employee_id = models.CharField(max_length=50, unique=True, blank=True)


#     home_address = models.TextField(null=True)
#     home_city = models.CharField(max_length=100,null=True)
#     home_state = models.CharField(max_length=100, blank=True, null=True)
#     home_country = models.CharField(max_length=100,null=True)
#     home_zip_code = models.CharField(max_length=20,null=True)

#     experience_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
#     qualification = models.CharField(max_length=255, null=True)
#     experience_years = models.PositiveIntegerField(null=True)

#     # Professional Information

#     # Access control and status

#     # Optional Enterprise-level fields
#     # multi_hospital_access = models.BooleanField(default=False)
#     # timezone = models.CharField(max_length=50, default='UTC')
#     # language_preference = models.CharField(max_length=20, default='en')

#     def __str__(self):
#         return f"Administrator: {self.user.username}"
    
    

# class Administrator(Base):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)

#     # Personal details
#     profile_picture = models.ImageField(upload_to='admin_profiles/', null=True, blank=True)
#     phone_number = models.CharField(max_length=15, unique=True)
#     gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
#     date_of_birth = models.DateField(null=True, blank=True)
#     date_joined = models.DateField(blank=True, null=True)

#     # Work and role information
#     # designation = models.CharField(max_length=100, default='System Administrator')
#     # department = models.CharField(max_length=100, null=True, blank=True)
#     employee_id = models.CharField(max_length=50, unique=True, blank=True)


#     home_address = models.TextField(null=True)
#     home_city = models.CharField(max_length=100,null=True)
#     home_state = models.CharField(max_length=100, blank=True, null=True)
#     home_country = models.CharField(max_length=100,null=True)
#     home_zip_code = models.CharField(max_length=20,null=True)

#     experience_certificate = models.FileField(upload_to='doctor_documents/', blank=True, null=True)
#     qualification = models.CharField(max_length=255, null=True)
#     experience_years = models.PositiveIntegerField(null=True)

#     # Professional Information

#     # Access control and status

#     # Optional Enterprise-level fields
#     # multi_hospital_access = models.BooleanField(default=False)
#     # timezone = models.CharField(max_length=50, default='UTC')
#     # language_preference = models.CharField(max_length=20, default='en')

#     def __str__(self):
#         return f"Administrator: {self.user.username}"
    
    