from django.db import models
from django.conf import settings

class Base(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_set",null=True)
    created_on = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s_updatedby_set", blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    comments = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    # password_last_changed = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True