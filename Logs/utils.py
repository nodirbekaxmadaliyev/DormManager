# logs/utils.py
import pytz
import requests
from datetime import datetime
from requests.auth import HTTPDigestAuth
from accounts.models import CustomUser
from student.models import Student
from dormitory.models import Dormitory

def process_logs(dormitory: Dormitory, last_time=None):
    tz = pytz.timezone("Asia/Tashkent")
    now = datetime.now(tz)
    start_time = (last_time or (now.replace(second=0, microsecond=0)))
    end_time = now.replace(second=0, microsecond=0)

    start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%S+05:00")
    end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%S+05:00")

    devices = dormitory.devices.all()

    for device in devices:
        try:
            url = f"http://{device.ipaddress}/ISAPI/AccessControl/AcsEvent?format=json"
            payload = {
                "AcsEventCond": {
                    "searchID": "100001",
                    "searchResultPosition": 0,
                    "maxResults": 20,
                    "major": 5,
                    "minor": 75,
                    "startTime": start_iso,
                    "endTime": end_iso,
                    "picEnable": True,
                    "timeReverseOrder": True
                }
            }

            response = requests.post(url, json=payload, auth=HTTPDigestAuth(device.username, device.password), timeout=10)

            if response.status_code != 200:
                continue

            data = response.json()
            info_list = data.get("AcsEvent", {}).get("InfoList", [])

            for entry in info_list:
                employee_no = int(entry.get("employeeNoString", "0") or 0)

                if employee_no < 10000:
                    try:
                        user = CustomUser.objects.get(pk=employee_no)
                        user.is_in_dormitory = device.entrance
                        user.save(update_fields=["is_in_dormitory"])
                    except CustomUser.DoesNotExist:
                        continue
                else:
                    try:
                        student = Student.objects.get(pk=employee_no)
                        student.is_in_dormitory = device.entrance
                        student.save(update_fields=["is_in_dormitory"])
                    except Student.DoesNotExist:
                        continue
        except Exception as e:
            print("❌ Qurilmadan log olishda xatolik:", str(e))

    return end_time  # Keyingi chaqiriqda shundan boshlab olish uchun
