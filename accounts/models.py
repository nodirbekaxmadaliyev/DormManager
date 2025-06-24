from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
import os
from django.utils.text import slugify
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ValidationError
import re

# Create your models here.

class AutoIncrementField(models.PositiveIntegerField):
    def __init__(self, start_from=10, *args, **kwargs):
        self.start_from = start_from
        kwargs['editable'] = False
        kwargs['primary_key'] = True
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if not getattr(model_instance, self.attname):
            # Barcha mavjud ID larni olish
            existing_ids = list(model_instance.__class__.objects.values_list(
                self.attname, flat=True).order_by(self.attname))

            # Agar hech qanday ID bo'lmasa, start_from dan boshlash
            if not existing_ids:
                setattr(model_instance, self.attname, self.start_from)
                return super().pre_save(model_instance, add)

            # Bo'sh joylarni tekshirish
            full_range = set(range(self.start_from, existing_ids[-1] + 2))
            existing_set = set(existing_ids)
            gaps = full_range - existing_set

            # Agar bo'sh joylar bo'lsa, ulardan eng kichigini olish
            if gaps:
                setattr(model_instance, self.attname, min(gaps))
            else:
                # Bo'sh joy yo'q bo'lsa, eng yuqori ID + 1
                setattr(model_instance, self.attname, existing_ids[-1] + 1)

        return super().pre_save(model_instance, add)

def staff_photo_upload_path(instance, filename):
    """Hodim suratlari uchun upload pathini generatsiya qilish"""
    ext = filename.split('.')[-1]

    first_name_slug = slugify(instance.first_name) if instance.first_name else 'noname'
    last_name_slug = slugify(instance.last_name) if instance.last_name else 'nosurname'

    new_filename = f"{instance.pk}_{first_name_slug}_{last_name_slug}.{ext}"

    return os.path.join('staff', new_filename)

class CustomUser(AbstractUser):
    id = AutoIncrementField(start_from=1)
    ROLE_CHOICES = [
        ('director', 'Direktor'),
        ('employee', 'Xodim'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='other',
        verbose_name='Lavozim'
    )

    work_start = models.TimeField(
        verbose_name='Ish boshlanish vaqti',
        null=True,
        blank=True
    )

    work_end = models.TimeField(
        verbose_name='Ish tugash vaqti',
        null=True,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefon raqami'
    )

    hire_date = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Ishga qabul qilingan sana'
    )

    photo = models.ImageField(
        upload_to=staff_photo_upload_path,
        blank=False,
        null=False,
        verbose_name='Hodim surati'
    )

    salary = models.PositiveIntegerField(
        verbose_name='Maosh',
        null=True,
        blank=True,
        help_text="Hodimning maoshi (so'mda)"
    )
    is_in_dormitory = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new:
            clean_first_name = re.sub(r'[^a-zA-Z0-9]', '', self.first_name.lower() if self.first_name else 'noname')
            clean_last_name = re.sub(r'[^a-zA-Z0-9]', '', self.last_name.lower() if self.last_name else 'nosurname')
            self.username = f"{clean_first_name}.{clean_last_name}"
            self.set_password("12345678")

        super().save(*args, **kwargs)  # Bu yerda pk yaratiladi

        # Usernamega pk ni qo‘shish (faqat yangi foydalanuvchi uchun)
        if is_new:
            self.username = f"{self.pk}_{self.username}"
            super().save(update_fields=['username'])

    def clean(self):
        super().clean()
        if self.password and len(self.password) < 8:
            raise ValidationError(
                _('Parol kamida 4 ta belgidan iborat bo\'lishi kerak'),
                code='Parol juda qisqa'
            )

@receiver(pre_delete, sender=CustomUser)
def delete_user_photo(sender, instance, **kwargs):
    """Hodim o'chirilganda uning suratini ham o'chiramiz"""
    if instance.photo:
        if os.path.isfile(instance.photo.path):
            os.remove(instance.photo.path)

class Director(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    

    def clean(self):
        if self.user.role != 'director':
            raise ValidationError("Faqat direktor roliga ega foydalanuvchini bog'lashingiz mumkin.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()} (Direktor)"