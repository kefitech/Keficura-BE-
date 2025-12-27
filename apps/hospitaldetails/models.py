# from django.db import models
# from base_util.base import *
# from apps.menu.models import Menu
# from django.core.validators import RegexValidator

# class Hospital(Base):
#     # Basic Information
#     name = models.CharField(max_length=255, unique=True)
#     hospital_code = models.CharField(max_length=50, unique=True)
    
#     # Address Information
#     street_address = models.CharField(max_length=255)
#     city = models.CharField(max_length=100)
#     state = models.CharField(max_length=100)
#     postal_code = models.CharField(max_length=20)
#     country = models.CharField(max_length=100, default='India')
    
#     # Contact Information
#     phone_regex = RegexValidator(
#         regex=r'^\+?1?\d{9,15}$',
#         message="Phone number must be entered in the format: '+999999999'"
#     )
#     phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
#     email = models.EmailField(blank=True)
#     website = models.URLField(blank=True)
    
#     # Hospital Metadata
#     HOSPITAL_TYPES = (
#         ('G', 'General'),
#         ('S', 'Specialty'),
#         ('C', 'Clinic'),
#         ('T', 'Teaching'),
#     )
#     hospital_type = models.CharField(max_length=1, choices=HOSPITAL_TYPES)
    
#     # OWNERSHIP_TYPES = (
#     #     ('PUB', 'Public'),
#     #     ('PVT', 'Private'),
#     #     ('GOV', 'Government'),
#     #     ('NGO', 'Non-profit'),
#     # )
#     # ownership = models.CharField(max_length=5, choices=OWNERSHIP_TYPES)
    
#     # Services Information
#     emergency_services = models.BooleanField(default=False)
#     # specialties = models.ManyToManyField('Specialty', blank=True)
    
#     # Licensing and Certification
#     license_number = models.CharField(max_length=100, unique=True,null=True)
#     accreditation = models.CharField(max_length=100, null=True)
#     license_expiry_date = models.DateField()
    
#     # Additional Information
#     description = models.TextField(blank=True)
#     established_date = models.DateField(null=True, blank=True)
#     bed_capacity = models.PositiveIntegerField(null=True, blank=True)
#     logo = models.ImageField(upload_to='hospital_logos/', blank=True)
    
#     # Geo Location (requires GeoDjango)
#     # location = models.PointField(null=True, blank=True)
    
#     # Timestamps

#     def __str__(self):
#         return self.name

#     class Meta:
#         ordering = ['name']
#         verbose_name = 'Hospital'
#         verbose_name_plural = 'Hospitals'



# # class Specialty(models.Model):
# #     name = models.CharField(max_length=100)
# #     code = models.CharField(max_length=10)
# #     description = models.TextField(blank=True)

# #     def __str__(self):
# #         return self.name





    






