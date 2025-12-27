from rest_framework import serializers
from apps.data_hub.models import *

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientRegistration
        fields = '__all__'

