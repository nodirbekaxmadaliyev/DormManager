from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import transaction
from django.utils.timezone import now
import time
import re

from dormitory.models import Device
from accounts.models import CustomUser
from student.models import Student


events = []  # Oxirgi eventlarni saqlash

# Eventlarni va ularning qayta ishlanganligini kuzatish uchun
processed_events = {}


@csrf_exempt
def hikvision_event(request):
    global events, processed_events

    if request.method == "POST":
        try:
            content_type = request.META.get('CONTENT_TYPE', '')
            event_json = None

            # Multipart/form-data ni qayta ishlash
            if 'multipart/form-data' in content_type:
                raw_data = request.body

                # Boundary ni topish
                boundary_match = re.search(r'boundary=(.*)$', content_type)
                if boundary_match:
                    boundary = boundary_match.group(1).encode()

                    # Partlarni ajratish
                    parts = raw_data.split(b'--' + boundary)

                    for part in parts:
                        if b'Content-Type: application/json' in part:
                            # JSON qismini ajratish
                            json_sections = part.split(b'\r\n\r\n', 1)
                            if len(json_sections) > 1:
                                json_part = json_sections[1]
                                json_part = json_part.rstrip(b'\r\n--')

                                try:
                                    event_json = json.loads(json_part.decode('utf-8'))
                                    break
                                except json.JSONDecodeError:
                                    continue

                    if event_json is None:
                        return HttpResponse("OK", content_type="text/plain")

            # Agar multipart bo'lmasa, to'g'ridan-to'g'ri JSON deb harakat qilamiz
            if event_json is None:
                try:
                    event_json = json.loads(request.body.decode('utf-8'))
                except json.JSONDecodeError:
                    return HttpResponse("OK", content_type="text/plain")

            # Eventni identifikatsiya qilish
            event_id = event_json.get("eventId") or event_json.get("dateTime") or str(hash(str(event_json)))

            # Agar bu event allaqachon qayta ishlangan bo'lsa, darhol 200 OK qaytaramiz
            if event_id in processed_events:
                return HttpResponse("OK", content_type="text/plain")

            # JSON ma'lumotlarini tekshirish
            access_event = event_json.get("AccessControllerEvent", {})
            emp_no_str = access_event.get("employeeNoString")
            ip = event_json.get("ipAddress")

            # Agar employeeNoString bo'lmasa, bu eventni o'tkazib yuboramiz
            if not emp_no_str:
                return HttpResponse("OK", content_type="text/plain")

            if not ip:
                processed_events[event_id] = now()
                return HttpResponse("OK", content_type="text/plain")

            try:
                emp_no = int(emp_no_str)
            except ValueError:
                processed_events[event_id] = now()
                return HttpResponse("OK", content_type="text/plain")

            try:
                device = Device.objects.get(ipaddress=ip)
            except Device.DoesNotExist:
                processed_events[event_id] = now()
                return HttpResponse("OK", content_type="text/plain")

            in_dorm = True if device.entrance else False

            with transaction.atomic():
                if emp_no < 10000:
                    # Xodim
                    try:
                        user = CustomUser.objects.get(pk=emp_no)
                        user.is_in_dormitory = in_dorm
                        user.save(update_fields=["is_in_dormitory"])
                        print(f"[EMPLOYEE] {user.username} is_in_dormitory -> {in_dorm}")

                    except CustomUser.DoesNotExist:
                        print(f"Xodim {emp_no} topilmadi")

                else:
                    # Talaba
                    try:
                        student = Student.objects.get(pk=emp_no)
                        student.is_in_dormitory = in_dorm
                        student.save(update_fields=["is_in_dormitory"])

                        print(f"[STUDENT] {student.first_name} {student.last_name} is_in_dormitory -> {in_dorm}")

                    except Student.DoesNotExist:
                        print(f"Talaba {emp_no} topilmadi")

            # Eventni qayta ishlanganlar ro'yxatiga qo'shamiz
            processed_events[event_id] = now()

            # Eventni saqlash
            event_html = f"<div style='margin:10px;padding:10px;border:1px solid #ccc;'><pre style='white-space:pre-wrap;font-size:12px;'>{json.dumps(event_json, indent=2, ensure_ascii=False)}</pre></div>"
            events.append(event_html)
            if len(events) > 20:
                events = events[-20:]

            # Eski eventlarni tozalash (1 soatdan oldingi)
            current_time = now()
            for event_id_key in list(processed_events.keys()):
                if (current_time - processed_events[event_id_key]).total_seconds() > 3600:
                    del processed_events[event_id_key]

            return HttpResponse("OK", content_type="text/plain")

        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")
            return HttpResponse("OK", content_type="text/plain")

    # GET so'rovi uchun - jonli kuzatish sahifasi
    html = """
    <html>
    <head>
    <meta charset='utf-8'>
    <title>Hikvision Events</title>
    <style>
    .event-block { 
        margin: 10px; 
        padding: 10px; 
        border: 1px solid #ccc; 
        border-radius: 5px;
        background-color: #f9f9f9;
    }
    .event-data {
        white-space: pre-wrap;
        font-size: 12px;
        font-family: monospace;
    }
    </style>
    </head>
    <body>
    <h2>Oxirgi Hikvision Eventlar (jonli)</h2>
    <div id="events">""" + "".join(reversed(events)) + """</div>

    <script>
    var evtSource = new EventSource("/stream/");
    evtSource.onmessage = function(e) {
        var div = document.getElementById("events");
        div.innerHTML = e.data + div.innerHTML;
    };
    </script>
    </body>
    </html>
    """
    return HttpResponse(html)


def stream_events(request):
    response = StreamingHttpResponse(stream_events_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


def stream_events_generator():
    while True:
        if events:
            event_data = events[-1]
            yield f"data: {event_data}\n\n"
            events.clear()
        else:
            yield ":keep-alive\n\n"

        time.sleep(1)