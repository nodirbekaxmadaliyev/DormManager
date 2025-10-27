import pandas as pd
from decimal import Decimal
from student.models import Student
from accounts.models import CustomUser
from payment.models import Payment

# === Sozlamalar ===
EXCEL_PATH = r"C:\Users\Nodirbek\Desktop\talabalar.xlsx"
ADDED_BY_USERNAME = "admin"  # o‘zgartir, agar boshqacha user bo‘lsa

# === Excelni o‘qish ===
df = pd.read_excel(EXCEL_PATH)
df = df.fillna("")

# === Qo‘shuvchi foydalanuvchini olish ===
added_by = CustomUser.objects.filter(username=ADDED_BY_USERNAME).first()

count = 0

for _, row in df.iterrows():
    try:
        first_name = str(row.get("Ismi", "")).strip()
        last_name = str(row.get("Familiyasi", "")).strip()
        phone_number = str(row.get("Telefon raqami", "")).strip()
        amount_value = str(row.get("To'lov summasi", "")).replace(",", "").strip()

        if not amount_value:
            print(f"⚠️ {first_name} {last_name} uchun to‘lov summasi yo‘q.")
            continue

        try:
            amount = Decimal(amount_value)
        except Exception:
            print(f"⚠️ Noto‘g‘ri summa: {amount_value}")
            continue

        # — Talabani topish
        student = Student.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            phone_number__icontains=phone_number[-4:]  # telefonning oxirgi 4 raqami bo‘yicha
        ).first()

        if not student:
            print(f"❌ Talaba topilmadi: {first_name} {last_name} ({phone_number})")
            continue

        # — To‘lov obyektini yaratish
        payment = Payment.objects.create(
            student=student,
            student_name=f"{first_name} {last_name}",
            amount=amount,
            added_by=added_by
        )

        count += 1
        print(f"✅ To‘lov qo‘shildi: {first_name} {last_name} — {amount} so‘m")

    except Exception as e:
        print(f"❌ Xatolik ({first_name} {last_name}): {e}")

print(f"\n✅ {count} ta to‘lov muvaffaqiyatli import qilindi.")
