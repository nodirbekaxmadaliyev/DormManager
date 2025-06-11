from django.db import models
from accounts.models import Director
# Create your models here.
class Dormitory(models.Model):
    director = models.ForeignKey(Director, on_delete=models.CASCADE, related_name='dormitories')
    name = models.CharField(max_length=300, blank=False)
    address = models.CharField(max_length=300, blank=False)

    def __str__(self):
        return self.name

class Device(models.Model):
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name='devices')
    ipaddress = models.GenericIPAddressField(blank=False)
    username = models.CharField(max_length=100, blank=False)
    password = models.CharField(max_length=100, blank=False)
    entrance = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.pk} -> {self.dormitory.name} -> {self.entrance}"