import pytz

from dormitory.models import Dormitory
import os
import urllib3
import requests
from requests.auth import HTTPDigestAuth
from accounts.models import CustomUser
from student.models import Student
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime

def add_user_to_devices(dormitory: Dormitory, employee_id: str, full_name: str, image_path: str) -> tuple[bool, str | None]:
    """Barcha qurilmalarga foydalanuvchini (ism+familiya+id) va rasmni yuklash.
    Xatolik bo‘lsa: (False, xatolik_sababi), muvaffaqiyatli bo‘lsa: (True, None)
    """

    devices = dormitory.devices.all()

    for device in devices:
        base_url = f"http://{device.ipaddress}"
        username = device.username
        password = device.password

        # 1. Foydalanuvchini qo‘shish
        user_payload = {
            "UserInfo": {
                "employeeNo": employee_id,
                "name": full_name,
                "userType": "normal",
                "Valid": {
                    "enable": True,
                    "beginTime": "2024-01-01T00:00:00",
                    "endTime": "2030-12-31T23:59:59"
                },
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "userVerifyMode": "face",
                "maxOpenDoorTime": 10,
                "userGroup": 1,
                "localUIRight": False,
                "userPassword": "",
                "passwordType": "normal",
                "openDoorType": {
                    "doorType": "local"
                }
            }
        }

        try:
            auth = HTTPDigestAuth(username, password)
            headers = {"Content-Type": "application/json"}
            user_url = f"{base_url}/ISAPI/AccessControl/UserInfo/Record?format=json"
            user_response = requests.post(user_url, auth=auth, json=user_payload, headers=headers, verify=False)

            if user_response.status_code != 200:
                reason = f"[{device.ipaddress}] Foydalanuvchi qo‘shilmadi: {user_response.text}"
                print("❌", reason)
                return False, reason

            # 2. Yuz rasm yuklash
            if not os.path.exists(image_path):
                reason = f"Surat topilmadi: {image_path}"
                print("❌", reason)
                return False, reason

            face_url = f"{base_url}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
            files = {
                "FaceDataRecord": (
                    None,
                    f'{{"faceLibType":"blackFD","FDID":"1","FPID":"{employee_id}"}}',
                    "application/json"
                ),
                "img": (
                    os.path.basename(image_path),
                    open(image_path, "rb"),
                    "image/jpeg"
                )
            }

            face_response = requests.post(face_url, auth=auth, files=files, verify=False)
            if face_response.status_code != 200:
                reason = f"[{device.ipaddress}] Surat yuklanmadi: {face_response.text}"
                print("❌", reason)
                return False, reason

            print(f"[{device.ipaddress}] ✅ Foydalanuvchi va surat yuklandi.")

        except Exception as e:
            reason = f"[{device.ipaddress}] Istisno yuz berdi: {str(e)}"
            print("❌", reason)
            return False, reason

    return True, None

def delete_user_from_devices(dormitory: Dormitory, employee_id: str) -> tuple[bool, str | None]:

    devices = dormitory.devices.all()

    for device in devices:
        base_url = f"http://{device.ipaddress}"
        username = device.username
        password = device.password
        auth = HTTPDigestAuth(username, password)

        delete_url = f"{base_url}/ISAPI/AccessControl/UserInfo/Delete?format=json"
        payload = {
            "UserInfoDelCond": {
                "EmployeeNoList": [{"employeeNo": employee_id}]
            }
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.put(delete_url, auth=auth, json=payload, headers=headers, verify=False)
            if response.status_code == 200:
                print(f"[{device.ipaddress}] ✅ Foydalanuvchi (ID: {employee_id}) o‘chirildi.")
            else:
                reason = f"[{device.ipaddress}] ❌ O‘chirishda xatolik: {response.status_code} - {response.text}"
                print(reason)
                return False, reason

        except Exception as e:
            reason = f"[{device.ipaddress}] ❌ Istisno yuz berdi: {str(e)}"
            print(reason)
            return False, reason

    return True, None

def update_user_on_devices(dormitory: Dormitory, employee_id: str, name: str) -> tuple[bool, str | None]:

    urllib3.disable_warnings()

    devices = dormitory.devices.all()

    for device in devices:
        base_url = f"http://{device.ipaddress}"
        auth = HTTPDigestAuth(device.username, device.password)

        update_url = f"{base_url}/ISAPI/AccessControl/UserInfo/Modify?format=json"
        payload = {
            "UserInfo": {
                "employeeNo": employee_id,
                "name": name,
                "userType": "normal",
                "Valid": {
                    "enable": True,
                    "beginTime": "2025-01-01T00:00:00",
                    "endTime": "2030-12-31T23:59:59",
                    "timeType": "local"
                },
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "gender": "unknown",
                "localUIRight": False,
                "maxOpenDoorTime": 100,
                "userVerifyMode": "face",
                "password": ""
            }
        }

        try:
            response = requests.put(update_url, auth=auth, json=payload, headers={"Content-Type": "application/json"},
                                    verify=False)
            if response.status_code == 200:
                print(f"[{device.ipaddress}] ✅ Yangilandi: {employee_id} ({name})")
            else:
                return False, f"[{device.ipaddress}] ❌ Xato: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"[{device.ipaddress}] ❌ Istisno: {str(e)}"

    return True, None

def getLogs(dormitory: Dormitory, start_time_str, end_time_str):
    tz = pytz.timezone("Asia/Tashkent")
    try:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("Sanani formatda kiriting: YYYY-MM-DD HH:MM")
    devices = dormitory.devices.all()
    start_time = tz.localize(start_time)
    end_time = tz.localize(end_time)

    start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%S+05:00")
    end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%S+05:00")

    errors = []
    all_logs = []

    for device in devices:
        device_ip = device.ipaddress
        username = device.username
        password = device.password
        entrance = device.entrance

        url = f"http://{device_ip}/ISAPI/AccessControl/AcsEvent?format=json"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        search_position = 0
        max_results = 20  # qurilma imkoniyatiga qarab o'zgartiring

        while True:
            payload = {
                "AcsEventCond": {
                    "searchID": "100001",
                    "searchResultPosition": search_position,
                    "maxResults": max_results,
                    "major": 5,
                    "minor": 75,
                    "startTime": start_iso,
                    "endTime": end_iso,
                    "picEnable": True,
                    "timeReverseOrder": True
                }
            }

            try:
                response = requests.post(url, json=payload, headers=headers,
                                         auth=HTTPDigestAuth(username, password), timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    events = data.get("AcsEvent", {})
                    info_list = events.get("InfoList", [])

                    if not info_list:
                        # Loglar qolmadi, siklni to'xtatamiz
                        break

                    for entry in info_list:
                        raw_time = entry.get("time")
                        try:
                            dt = datetime.fromisoformat(raw_time)
                            formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            formatted_time = raw_time

                        employee_no_str = entry.get("employeeNoString")
                        try:
                            employee_no_int = int(employee_no_str)
                        except (ValueError, TypeError):
                            employee_no_int = 0

                        # Hodim yoki talaba borligini tekshirish
                        if employee_no_int < 10000:
                            exists = CustomUser.objects.filter(pk=employee_no_int).exists()
                        else:
                            exists = Student.objects.filter(pk=employee_no_int).exists()

                        log_entry = {
                            "employeeNo": employee_no_int,
                            "name": entry.get("name"),
                            "time": formatted_time,
                            "status": "Kirish" if entrance else "Chiqish",
                            "exists": exists,
                        }
                        all_logs.append(log_entry)

                    # Agar qaytgan eventlar soni max_results dan kam bo'lsa, tugatamiz
                    if len(info_list) < max_results:
                        break

                    # Keyingi sahifaga o'tamiz
                    search_position += max_results

                else:
                    errors.append(f"{device_ip} — So‘rov xatosi: {response.status_code}")
                    break

            except Exception as e:
                errors.append(f"{device_ip} — Xatolik: {str(e)}")
                break

    all_logs.sort(key=lambda x: x["time"], reverse=True)

    return all_logs, errors,
