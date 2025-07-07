from django.db import models
from accounts.models import Director
# Create your models here.
class Dormitory(models.Model):
    director = models.ForeignKey(Director, on_delete=models.CASCADE, related_name='dormitories')
    name = models.CharField(max_length=300, blank=False)
    address = models.CharField(max_length=300, blank=False)
    monthly_payment = models.PositiveIntegerField(default=0, verbose_name="Oylik to‘lov miqdori (so'm)")
    default_monthly_payment = models.PositiveIntegerField(
        default=1,
        help_text="Shartnomaga asosan boshlang‘ich oylik to‘lov (so‘mda)"
    )
    last_update_time = models.DateTimeField(blank=True, null=True)
    def __str__(self):
        return self.name

class Device(models.Model):
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name='devices')
    ipaddress = models.CharField(max_length=25, blank=False)
    username = models.CharField(max_length=100, blank=False)
    password = models.CharField(max_length=100, blank=False)
    entrance = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.pk} -> {self.dormitory.name} -> {self.entrance}"

class Room(models.Model):
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE, related_name='rooms')
    number = models.CharField(max_length=5)
    size = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.dormitory.name} - {self.number} (sig‘im: {self.size})"

