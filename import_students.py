import os
import pandas as pd
from django.core.files import File
from dormitory.models import Dormitory, Room
from student.models import Student

# === Sozlamalar ===
EXCEL_PATH = r"C:\Users\Nodirbek\Desktop\talabalar.xlsx"
IMAGES_DIR = r"C:\Users\Nodirbek\Desktop\PythonProject\hikvision_faces203"

# === Excelni o‘qish ===
df = pd.read_excel(EXCEL_PATH)
df = df.fillna("")

count = 0

# TTJ obyektini olish (faqat bitta TTJ ishlatilmoqda)
TTJ = Dormitory.objects.filter(name__iexact="TTJ").first()
if not TTJ:
    raise Exception("❌ 'TTJ' nomli yotoqxona topilmadi. Avval uni bazaga qo‘shing.")

for _, row in df.iterrows():
    try:
        student_id = str(row.get("Student ID", "")).strip()
        first_name = str(row.get("Ismi", "")).strip()
        last_name = str(row.get("Familiyasi", "")).strip()
        faculty = str(row.get("Fakulteti", "")).strip()
        room_number = str(row.get("room__number", "")).strip()
        phone_number = str(row.get("Telefon raqami", "")).strip()
        parent_full_name = str(row.get("Ota-onasi", "")).strip()
        is_in_dormitory = str(row.get("Yotoqxonada", "")).strip().lower() in ["ha", "true", "1"]
        arrival_time = row.get("Kelgan sana") or None
        checkout_time = row.get("Ketadigan sana") or None

        # — Xona topish yoki yaratish
        room = None
        if room_number:
            room = Room.objects.filter(number__iexact=room_number, dormitory=TTJ).first()
            if not room:
                room = Room.objects.create(
                    dormitory=TTJ,
                    number=room_number,
                    size=6
                )
                print(f"🏠 Yangi xona yaratildi: {room_number} (sig‘imi: 6)")
        else:
            print("⚠️ Xona raqami kiritilmagan, talabaga xona bog‘lanmaydi.")

        # — Talaba obyektini yaratish
        student = Student(
            dormitory=TTJ,
            room=room,
            first_name=first_name,
            last_name=last_name,
            faculty=faculty,
            phone_number=phone_number,
            parent_full_name=parent_full_name,
            is_in_dormitory=is_in_dormitory,
            arrival_time=arrival_time,
            checkout_time=checkout_time,
        )

        # — Rasmni faqat Student ID orqali (boshlanishi bo‘yicha) qidirish
        found_image = None
        if student_id:
            for file_name in os.listdir(IMAGES_DIR):
                if file_name.lower().startswith(f"{student_id}_"):
                    found_image = os.path.join(IMAGES_DIR, file_name)
                    break

        if found_image:
            with open(found_image, "rb") as f:
                student.image.save(os.path.basename(found_image), File(f), save=False)
        else:
            print(f"⚠️ Rasm topilmadi: {student_id}")

        # — Saqlash
        student.save()
        count += 1
        print(f"✅ Talaba qo‘shildi: {first_name} {last_name}")

    except Exception as e:
        print(f"❌ Xatolik ({first_name} {last_name}): {e}")

print(f"\n✅ {count} ta talaba muvaffaqiyatli import qilindi.")
