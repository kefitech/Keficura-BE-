# from django.db import models
# from base_util.base import *
# from apps.appointments.models import Appointment
# from django.contrib.auth.models import User


# class PharmacistStaff(Base):
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
#     employee_id = models.CharField(max_length=20, unique=True, null=True)
#     hire_date = models.DateField()

#     profile_picture = models.ImageField(upload_to='front_desk_staff/', blank=True, null=True)
#     # signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    
#     # Status
#     is_active = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"Front Desk Staff {self.user.get_full_name()} - {self.employee_id}"
 
#     class Meta:
#         ordering = ['user__last_name']
#         verbose_name = 'Front Desk Staff'
#         verbose_name_plural = 'Front Desk Staff'



# class Medication(Base):
#     name = models.CharField(max_length=200)
#     description = models.TextField(null=True,blank=True)
#     dosage_form = models.CharField(max_length=100)  # e.g., tablet, capsule, syrup
#     strength = models.CharField(max_length=50)

#     def __str__(self):
#         return f"{self.name} {self.strength} ({self.dosage_form})"


# class DoctorConsultation(Base):
#     appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='consultations')
#     diagnosis = models.TextField()
#     recommended_tests = models.JSONField(default=list, blank=True)  
#     doctor_notes = models.TextField(blank=True, null=True)
#     follow_up_date = models.DateField(blank=True, null=True)
#     prescribed_medicines = models.ManyToManyField(Medication, through='PrescribedMedicine')

#     def __str__(self):
#         return f"Consultation for {self.appointment.patient.first_name} on {self.appointment.appointment_date}"

# class PrescribedMedicine(Base):
#     consultation = models.ForeignKey(DoctorConsultation, on_delete=models.CASCADE)
#     medicine = models.ForeignKey(Medication, on_delete=models.CASCADE)    
#     dosage = models.CharField(max_length=100)
#     frequency = models.CharField(max_length=100)
#     duration = models.CharField(max_length=100)
#     quantity = models.PositiveIntegerField()
#     instructions = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.medicine.name} for {self.consultation.appointment.patient.first_name}"



# class MedicationStock(Base):
#     medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='stock_entries')
#     batch_number = models.CharField(max_length=100)
#     quantity = models.PositiveIntegerField()
#     expiry_date = models.DateField()
#     received_date = models.DateField()
#     purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
#     selling_price = models.DecimalField(max_digits=10, decimal_places=2)
#     supplier = models.CharField(max_length=200)
#     manufacturer = models.CharField(max_length=200, default='Medi power')

#     def __str__(self):
#         return f"{self.medication.name} - Batch {self.batch_number} (Expires {self.expiry_date})"
    

# class MedicationDispense(Base):
#     prescribed_medicine = models.ForeignKey(PrescribedMedicine, on_delete=models.CASCADE)
#     stock_entry = models.ForeignKey(MedicationStock, on_delete=models.CASCADE)
#     quantity_dispensed = models.PositiveIntegerField()
#     dispensed_date = models.DateTimeField(auto_now_add=True)
#     dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

#     def __str__(self):
#         return f"{self.quantity_dispensed} of {self.stock_entry.medication.name} to {self.prescribed_medicine.consultation.appointment.patient.first_name}"


# class PatientBill(Base):
#     bill_number = models.CharField(max_length=50, unique=True)
    
#     # Patient and Doctor Information
#     patient_name = models.CharField(max_length=255)
#     doctor_name = models.CharField(max_length=255)
    
#     # Original References (for database integrity)
#     consultation = models.OneToOneField(DoctorConsultation, on_delete=models.PROTECT)
#     appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT)
    
#     # Date Information
#     bill_date = models.DateTimeField(auto_now_add=True)
#     appointment_date = models.DateField()
#     appointment_time = models.TimeField()
    
#     # Amount Information
#     consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
#     total_medicine_cost = models.DecimalField(max_digits=10, decimal_places=2)
#     total_bill_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
#     # Store medicine items as JSON
#     medicine_items = models.JSONField(default=list)
    
#     # Payment Status
#     PAYMENT_STATUS_CHOICES = [
#         ('PENDING', 'Pending'),
#         ('PAID', 'Paid'),
#         ('CANCELLED', 'Cancelled'),
#     ]

#     PAYMENT_TYPE_CHOICES = [
#         ('CASH', 'Cash'),
#         ('CARD', 'Card'),
#         ('UPI', 'UPI'),
#         ('OTHER', 'Other')
#     ]
#     payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
#     payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='CASH')
    
#     class Meta:
#         ordering = ['-bill_date']
    
#     def __str__(self):
#         return f"Bill #{self.bill_number} - {self.patient_name}"
    
#     def save(self, *args, **kwargs):
#         # Auto-generate bill number if not provided
#         if not self.bill_number:
#             last_bill = PatientBill.objects.order_by('-id').first()
#             if last_bill:
#                 last_id = int(last_bill.bill_number.split('-')[1])
#                 self.bill_number = f"BILL-{last_id + 1:06d}"
#             else:
#                 self.bill_number = "BILL-000001"
        
#         # Ensure total bill amount is correct
#         self.total_bill_amount = self.consultation_fee + self.total_medicine_cost
        
#         super().save(*args, **kwargs)
        
        

# class Pharmacy_Medication(Base):
#     appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
#     medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
#     stock_entry = models.ForeignKey(MedicationStock, on_delete=models.CASCADE)
#     diagnosis = models.TextField()
#     dispensed_date = models.DateTimeField(auto_now_add=True)
#     dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True ,related_name='dispensed_medications')
#     quantity_dispensed = models.PositiveIntegerField()
#     dosage = models.CharField(max_length=100)
#     frequency = models.CharField(max_length=100)
#     duration = models.CharField(max_length=100)





# class PharmacyBilling(Base):
#     bill_number = models.CharField(max_length=20, unique=True)
#     patient_name = models.CharField(max_length=100)
#     bill_date = models.DateField(null=True)
#     dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pharmacy_billing')
#     age = models.PositiveIntegerField(null=True)
#     gender = models.CharField(max_length=10,null=True)
#     discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

#     payment_type = models.CharField(
#         max_length=20,
#         choices=[
#             ('CASH', 'Cash'),
#             ('CARD', 'Card'),
#             ('UPI', 'UPI'),
#             ('OTHER', 'Other')
#         ],
#         default='CASH'
#     )

#     payment_status = models.CharField(
#         max_length=20,
#         choices=[
#             ('PENDING', 'Pending'),
#             ('PAID', 'Paid'),
#             ('CANCELLED', 'Cancelled'),
#         ],
#         default='PENDING'
#     )

#     amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     items = models.JSONField(default=list, null=True)
#     others = models.JSONField(default=list, null=True)
    
# class PharmacyBillingItem(Base):
#     billing = models.ForeignKey(PharmacyBilling, related_name='items_set', on_delete=models.CASCADE)
#     medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
#     stock_entry = models.ForeignKey(MedicationStock, on_delete=models.SET_NULL, null=True)
#     quantity = models.IntegerField()
#     unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,null=True)


# class LabBilling(Base):
#     bill_number = models.CharField(max_length=20, unique=True)
#     patient_name = models.CharField(max_length=100)
#     bill_date = models.DateField(null=True)
#     dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='Lab_billing')
#     age = models.PositiveIntegerField(null=True)
#     gender = models.CharField(max_length=10,null=True)
#     discount = models.DecimalField(null=True,max_digits=10, decimal_places=2, default=0.00)
 
#     payment_type = models.CharField(
#         max_length=20,
#         choices=[
#             ('CASH', 'Cash'),
#             ('CARD', 'Card'),
#             ('UPI', 'UPI'),
#             ('OTHER', 'Other')
#         ],
#         default='CASH'
#     )
 
#     payment_status = models.CharField(
#         max_length=20,
#         choices=[
#             ('PENDING', 'Pending'),
#             ('PAID', 'Paid'),
#             ('CANCELLED', 'Cancelled'),
#         ],
#         default='PENDING'
#     )
 
#     amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
#     items = models.JSONField(default=list, null=True)

    

# class LabDepartment(Base):
#     """Lab departments like Hematology, Biochemistry, Urology"""
#     name = models.CharField(max_length=100, unique=True)
#     code = models.CharField(max_length=10, unique=True)
#     description = models.TextField(blank=True)
#     rate = models.PositiveIntegerField(blank=True , null=True)
    
#     def __str__(self):
#         return self.name
    

# class TestCategory(models.Model):
#     """Test Categories, e.g. Hematology, CBC, Lipid Profile."""
#     department = models.ForeignKey(LabDepartment, on_delete=models.CASCADE, related_name='categories')
#     name = models.CharField(max_length=150)
#     code = models.CharField(max_length=20, unique=True)
#     description = models.TextField(blank=True)
#     parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name='subcategories', null=True, blank=True)

#     class Meta:
#         unique_together = ['department', 'name']

#     def __str__(self):
#         return f"{self.department.name} - {self.name}" if not self.parent else f"{self.parent.name} > {self.name}"
  

    
# class TestParameter(models.Model):
#     """Individual test components, e.g. Hemoglobin, WBC."""
#     category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='parameters')
#     name = models.CharField(max_length=150)
#     code = models.CharField(max_length=20)
#     unit = models.CharField(max_length=50, blank=True) 
#     is_qualitative = models.BooleanField(default=False)
#     normal_values = models.JSONField(blank=True, null=True)  
#     sequence_order = models.PositiveIntegerField(default=1)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         unique_together = ['category', 'code']
#         ordering = ['sequence_order', 'name']

#     def __str__(self):
#         return f"{self.category.name} - {self.name}"


# class ReferenceRange(models.Model):
#     """Reference range for a particular test parameter and age/gender group."""
#     parameter = models.ForeignKey(TestParameter, on_delete=models.CASCADE, related_name='reference_ranges')
#     gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
#     age_min = models.PositiveIntegerField(blank=True, null=True)
#     age_max = models.PositiveIntegerField(blank=True, null=True)
#     min_val = models.FloatField()
#     max_val = models.FloatField()
#     note = models.TextField(blank=True)

#     class Meta:
#         ordering = ['age_min']

#     def __str__(self):
#         return f"{self.parameter.name} | {self.gender or 'All'} | {self.age_min or 0}-{self.age_max or '∞'}yrs : {self.min_val} - {self.max_val} {self.parameter.unit}"


# class DentalConsultation(Base):
#     """Dental consultation with dental-specific fields"""
#     appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='dental_consultations')

#     # Dental-specific fields
#     chief_complaint = models.TextField()
#     tooth_number = models.CharField(max_length=50, blank=True, null=True)  # Can be multiple teeth
#     dental_procedure = models.CharField(max_length=200, blank=True, null=True)

#     # Examination findings
#     gum_condition = models.TextField(blank=True, null=True)
#     oral_hygiene_status = models.CharField(max_length=100, blank=True, null=True)
#     dental_chart_data = models.JSONField(default=dict, blank=True)  # For storing tooth chart

#     # Diagnosis and Treatment
#     diagnosis = models.TextField()
#     treatment_plan = models.TextField(blank=True, null=True)

#     # Additional notes
#     x_ray_notes = models.TextField(blank=True, null=True)
#     recommended_tests = models.JSONField(default=list, blank=True)
#     dentist_notes = models.TextField(blank=True, null=True)

#     # Follow-up
#     follow_up_date = models.DateField(blank=True, null=True)

#     # Medicines (many-to-many through PrescribedMedicine)
#     prescribed_medicines = models.ManyToManyField(Medication, through='DentalPrescribedMedicine')

#     def __str__(self):
#         return f"Dental Consultation for {self.appointment.patient.first_name} on {self.appointment.appointment_date}"


# class DentalPrescribedMedicine(Base):
#     """Medicines prescribed during dental consultation"""
#     consultation = models.ForeignKey(DentalConsultation, on_delete=models.CASCADE)
#     medicine = models.ForeignKey(Medication, on_delete=models.CASCADE)
#     dosage = models.CharField(max_length=100)
#     frequency = models.CharField(max_length=100)
#     duration = models.CharField(max_length=100)
#     quantity = models.PositiveIntegerField()
#     instructions = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.medicine.name} for {self.consultation.appointment.patient.first_name}"


