from django import forms
from .models import Student, Dormitory, Room

class StudentCreateForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'faculty', 'dormitory', 'room',
            'phone_number', 'is_in_dormitory', 'image',
            'contract_number', 'contract_date',
            'arrival_time', 'checkout_time',
            'parent_full_name'
        ]
        labels = {
            'first_name': "Ism",
            'last_name': "Familiya",
            'dormitory': "Yotoqxona",
            'room': "Xona",
            'phone_number': "Telefon raqami",
            'parent_full_name': "Ota-ona F.I.Sh.",
            'image': "Rasm",
            'faculty': "Fakultet",
            'is_in_dormitory': "Yotoqxonada yashayapti",
            'arrival_time': "Kelgan sana",
            'checkout_time': "Ketadigan sana",
            'contract_number': "Shartnoma raqami",
            'contract_date': "Shartnoma sanasi",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Foydalanuvchiga qarab yotoqxona filterlash
        if user:
            if hasattr(user, 'director'):
                self.fields['dormitory'].queryset = Dormitory.objects.filter(director__user=user)
            elif hasattr(user, 'employee'):
                self.fields['dormitory'].queryset = Dormitory.objects.filter(pk=user.employee.dormitory.pk)
            else:
                self.fields['dormitory'].queryset = Dormitory.objects.none()

        # Xonalarni faqat dormitory tanlangandan keyin ko‘rsatish
        self.fields['room'].queryset = Room.objects.none()
        if 'dormitory' in self.data:
            try:
                dormitory_id = int(self.data.get('dormitory'))
                self.fields['room'].queryset = Room.objects.filter(dormitory_id=dormitory_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['room'].queryset = self.instance.dormitory.rooms.all()
