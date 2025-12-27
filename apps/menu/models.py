# from django.db import models
# from base_util.base import *
# from django.contrib.auth.models import Permission ,Group

# class MenuType(Base):
#     name = models.CharField(max_length=100)
#     code = models.CharField(max_length=50, unique=True)
#     description = models.CharField(max_length=500)

#     class Meta:
#         db_table = "menu_type"

# class Menu(Base):
#     name = models.CharField(max_length=100)
#     title = models.CharField(max_length=100)
#     code = models.CharField(max_length=50, unique=True)
#     parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
#     menu_type = models.ForeignKey(MenuType, on_delete=models.CASCADE, null=True, blank=True)
#     redirect_url = models.CharField(max_length=100)
#     icon = models.CharField(max_length=100)
#     menu_order = models.IntegerField()
#     description = models.CharField(max_length=500)
#     # Add this new field:
#     feature_code = models.CharField(max_length=50, null=True, blank=True)

#     class Meta:
#         db_table = "menu"


# class MenuPermissionMapper(Base):
#     menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
#     auth_group_permission = models.ForeignKey(
#         Group, on_delete=models.CASCADE, null=True, blank=True
#     )
#     description = models.CharField(max_length=500)

#     class Meta:
#         db_table = "menu_permision"




