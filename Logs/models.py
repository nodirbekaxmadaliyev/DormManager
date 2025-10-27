from django.db import models

class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

    @staticmethod
    def get(key, default=None):
        try:
            return SystemConfig.objects.get(key=key).value
        except SystemConfig.DoesNotExist:
            return default

    @staticmethod
    def set(key, value):
        obj, created = SystemConfig.objects.get_or_create(key=key)
        obj.value = value
        obj.save()
