# from django.db import models
# from django.contrib.auth.models import User



# class Report(models.Model):
#     REPORT_TYPE_CHOICES = [
#         ('PATIENT_CENSUS', 'Patient Census'),
#         ('BILLING_SUMMARY', 'Billing Summary'),
#         ('DOCTOR_PERFORMANCE', 'Doctor Performance'),
#         ('PHARMACY_INVENTORY', 'Pharmacy Inventory'),
#         ('BED_OCCUPANCY', 'Bed Occupancy'),
#         ('APPOINTMENT_STATISTICS', 'Appointment Statistics'),
#         ('REVENUE_ANALYSIS', 'Revenue Analysis'),
#         ('CUSTOM', 'Custom Report'),
#     ]
    
#     report_id = models.CharField(max_length=50, unique=True)
#     title = models.CharField(max_length=200)
#     report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
#     description = models.TextField(blank=True, null=True)
#     parameters = models.JSONField(blank=True, null=True)
#     generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_reports')
#     created_at = models.DateTimeField(auto_now_add=True)
#     data = models.JSONField(blank=True, null=True)
    
#     def __str__(self):
#         return f"{self.title} ({self.report_type}) - {self.created_at.strftime('%Y-%m-%d')}"