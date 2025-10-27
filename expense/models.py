from django.db import models
from django.conf import settings
from dormitory.models import Dormitory

class Expense(models.Model):
    dormitory = models.ForeignKey(
        Dormitory,
        on_delete=models.CASCADE,
        related_name="expenses"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # employee o‘chirilsa, chiqim qoladi
        null=True,
        blank=True,
        related_name="expenses"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} - {self.note[:30]}"
