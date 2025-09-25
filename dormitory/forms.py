from django import forms
from .models import Room, Dormitory


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['dormitory', 'number', 'size']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if hasattr(user, 'director'):
                self.fields['dormitory'].queryset = Dormitory.objects.filter(director=user.director)
            else:
                self.fields['dormitory'].queryset = Dormitory.objects.filter(employees__user=user)

    def clean_number(self):
        number = self.cleaned_data.get("number")
        dormitory = self.cleaned_data.get("dormitory")
        if dormitory and number:
            if Room.objects.filter(dormitory=dormitory, number=number).exists():
                raise forms.ValidationError("Bu xona raqami allaqachon mavjud!")
        return number

