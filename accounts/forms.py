from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django.contrib.auth.forms import UserChangeForm
from django import forms
from dormitory.models import Dormitory
from employee.models import Employee

class EmployeeCreateForm(forms.ModelForm):
    first_name = forms.CharField(label='Ism')
    last_name = forms.CharField(label='Familiya')
    dormitory = forms.ModelChoiceField(queryset=Dormitory.objects.none(), label="Yotoqxona")

    class Meta:
        model = CustomUser
        fields = ['phone_number', 'work_start', 'work_end', 'hire_date', 'photo', 'salary']

    def __init__(self, *args, **kwargs):
        # Qo‘shimcha argumentlarni xavfsiz olib tashlaymiz
        request = kwargs.pop('request', None)
        director = kwargs.pop('director', None)
        # Har ehtimolga qarshi boshqa noma’lum argumentlarni ham olib tashlaymiz
        kwargs = {k: v for k, v in kwargs.items() if k in super().__init__.__code__.co_varnames}

        super().__init__(*args, **kwargs)

        # Foydalanuvchini kontekstdan olish
        self.request = request

        if not request:
            self.fields['dormitory'].queryset = Dormitory.objects.none()
            return

        user = request.user

        # Agar foydalanuvchi direktor bo‘lsa
        if getattr(user, 'role', None) == 'Direktor':
            self.fields['dormitory'].queryset = Dormitory.objects.filter(director__user=user)

        # Agar foydalanuvchi xodim bo‘lsa
        elif getattr(user, 'role', None) == 'Xodim':
            try:
                employee = Employee.objects.get(user=user)
                self.fields['dormitory'].queryset = Dormitory.objects.filter(id=employee.dormitory.id)
                self.fields['dormitory'].initial = employee.dormitory
            except Employee.DoesNotExist:
                self.fields['dormitory'].queryset = Dormitory.objects.none()

        # Boshqa hollarda (masalan admin)
        else:
            self.fields['dormitory'].queryset = Dormitory.objects.all()


class CustomUserUpdateForm(UserChangeForm):
    password = None  # Parolni bu yerda ko'rsatmaymiz, alohida forma orqali o'zgartiriladi

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name',
            'work_start', 'work_end', 'phone_number',
            'hire_date', 'salary'
        ]
        widgets = {
            'work_start': forms.TimeInput(attrs={'type': 'time'}),
            'work_end': forms.TimeInput(attrs={'type': 'time'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Maydonlar uchun label va help textlarni sozlaymiz
        self.fields['work_start'].label = 'Ish boshlanish vaqti'
        self.fields['work_end'].label = 'Ish tugash vaqti'
        self.fields['phone_number'].label = 'Telefon raqami'
        self.fields['hire_date'].label = 'Ishga qabul qilingan sana'
        self.fields['salary'].label = 'Maosh'
        self.fields['salary'].help_text = "Hodimning maoshi (so'mda)"

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone_number',
            'role', 'work_start', 'work_end', 'hire_date', 'photo', 'salary'
        ]
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'work_start': forms.TimeInput(attrs={'type': 'time'}),
            'work_end': forms.TimeInput(attrs={'type': 'time'}),
        }

