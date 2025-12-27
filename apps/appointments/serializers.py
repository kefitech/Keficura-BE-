from rest_framework import serializers
from apps.data_hub.models import *
from apps.patients.serializers import PatientSerializer
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username','first_name', 'last_name', 'email']
        read_only_fields = ['id']


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = '__all__'  

class Department_serializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class Specialization_serializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = '__all__'

class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = '__all__'
        

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    class Meta:
        model = Appointment
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by']
        # fields = '__all__'
        extra_kwargs = {
            'visit_status': {'read_only': True}  # Status should be updated via separate endpoint
        }

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        return f"Dr.{obj.doctor.user.first_name} {obj.doctor.user.last_name}"

    # def validate(self, data):
    #     """Check for existing appointments at same time with same doctor"""
    #     existing = Appointment.objects.filter(
    #         doctor=data['doctor'],
    #         appointment_date=data['appointment_date'],
    #         appointment_time=data['appointment_time']
    #     ).exists()
        
        if existing:
            raise serializers.ValidationError("Doctor already has an appointment at this time")
        return data

 
