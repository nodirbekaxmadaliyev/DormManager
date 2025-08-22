from django import forms
from .models import Expense
from dormitory.models import Dormitory

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["dormitory", "amount", "note"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, "role") and user.role == "employee":
            # hodim uchun dormitory maydonini yashirish
            self.fields.pop("dormitory")
        elif user and hasattr(user, "role") and user.role == "director":
            # direktor uchun faqat o‘ziga bog‘langan yotoxonalarni ko‘rsatish
            self.fields["dormitory"].queryset = Dormitory.objects.filter(director=user)
