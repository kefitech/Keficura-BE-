from rest_framework import serializers
from apps.data_hub.models import *
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username','first_name', 'last_name', 'email']
        read_only_fields = ['id']



class NurseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nurse
        fields = '__all__'


class NurseShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseShiftAssignment
        fields = '__all__'
        