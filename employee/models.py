from django.db import models
from accounts.models import CustomUser
from dormitory.models import Dormitory
# Create your models here.
class Employee(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='employee')
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, null=True, blank=True, related_name='employees')
    def __str__(self):
        return f"Xodim -> {self.user.get_full_name()}"