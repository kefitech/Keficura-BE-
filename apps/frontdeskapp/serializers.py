from rest_framework import serializers
from apps.data_hub.models import * 
from django.contrib.auth.models import User


class FrontDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrontDeskStaff
        fields = '__all__'