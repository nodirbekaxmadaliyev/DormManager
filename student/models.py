from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os
from dormitory.models import Dormitory


class AutoIncrementField(models.PositiveIntegerField):
    def __init__(self, start_from=10000, *args, **kwargs):
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

def student_image_upload_to(instance, filename):
    # Fayl kengaytmasini olish
    ext = filename.split('.')[-1]

    room = instance.room.replace('/', '_')
    last_name = instance.last_name.replace(' ', '_')
    first_name = instance.first_name.replace(' ', '_')

    # Yangi fayl nomi
    new_filename = f"{room}_{last_name}_{first_name}.{ext}"

    return os.path.join('residents/', new_filename)

class Student(models.Model):
    id = AutoIncrementField(start_from=10000)
    dormitory = models.ForeignKey(Dormitory, models.CASCADE, related_name='students')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    faculty = models.CharField(max_length=100)
    room = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=20)
    is_in_dormitory = models.BooleanField(default=True)
    parent_full_name = models.CharField(max_length=100)
    parent_login = models.CharField(max_length=150, unique=True, editable=False)
    parent_password = models.CharField(max_length=20, editable=True)
    image = models.ImageField(upload_to=student_image_upload_to, null=True, blank=True)
    contract_number = models.CharField(max_length=50, null=True, blank=True)
    contract_date = models.DateField(null=True, blank=True)
    arrival_time = models.DateField(null=True, blank=True)
    checkout_time = models.DateField(null=True, blank=True)
    total_payment = models.PositiveIntegerField(null=True, blank=True, default=0)

    def save(self, *args, **kwargs):
        # Agar rasm yangilansa, eski faylni o'chirish
        if self.pk:  # Model yangilanayotganligini tekshirish
            old_student = Student.objects.get(pk=self.pk)
            if old_student.image and old_student.image != self.image:
                if os.path.isfile(old_student.image.path):
                    os.remove(old_student.image.path)

        # Parent login va passwordni generatsiya qilish
        self.parent_login = f"{self.first_name.lower()}.{self.last_name.lower()}_{self.room}"
        self.parent_password = '12345678'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.room}) {self.first_name} {self.last_name} "


@receiver(post_delete, sender=Student)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
