from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import base64, re, json
from django.db import transaction

from dormitory.models import Device
from employee.models import Employee
from accounts.models import CustomUser
from student.models import Student


events = []        # Oxirgi eventlarni saqlash
listeners = []     # SSE ulangan brauzerlar


@csrf_exempt
def hikvision_event(request):
    global events

    if request.method == "POST":
        raw = request.body
        parts = re.split(b"--MIME_boundary", raw)
        html_parts = []
        event_json = None

        for part in parts:
            if not part.strip():
                continue

            if b"Content-Type: image/jpeg" in part:
                # Rasmni base64 ga o‘tkazamiz
                jpeg_data = part.split(b"\r\n\r\n", 1)[1].rstrip(b"--\r\n")
                b64 = base64.b64encode(jpeg_data).decode()
                html_parts.append(f"<img src='data:image/jpeg;base64,{b64}' style='max-width:300px;'><br>")
            elif b"Content-Type: application/json" in part:
                # JSON qism
                try:
                    json_str = part.split(b"\r\n\r\n", 1)[1].rstrip(b"--\r\n").decode()
                    event_json = json.loads(json_str)
                    html_parts.append(f"<pre style='white-space:pre-wrap;font-size:12px;'>{json.dumps(event_json, indent=2, ensure_ascii=False)}</pre>")
                except Exception as e:
                    html_parts.append(f"<pre style='color:red;'>JSON xatosi: {e}</pre>")

        # Agar JSON bo‘lsa, Employee va Student uchun ishlov beramiz
        if event_json:
            emp_no_str = event_json.get("AccessControllerEvent", {}).get("employeeNoString")
            ip = event_json.get("ipAddress")

            if emp_no_str and ip:
                try:
                    emp_no = int(emp_no_str)
                except ValueError:
                    emp_no = None

                try:
                    device = Device.objects.get(ipaddress=ip)
                except Device.DoesNotExist:
                    device = None

                if emp_no and device:
                    in_dorm = True if device.entrance else False
                    with transaction.atomic():
                        if emp_no < 10000:
                            # Xodim
                            try:
                                user = CustomUser.objects.get(pk=emp_no)
                                user.is_in_dormitory = in_dorm
                                user.save(update_fields=["is_in_dormitory"])
                                print(f"[EMPLOYEE] {user.username} is_in_dormitory -> {in_dorm}")
                            except Employee.DoesNotExist:
                                print(f"Employee {emp_no} topilmadi")
                        else:
                            # Student
                            try:
                                student = Student.objects.get(pk=emp_no)
                                student.is_in_dormitory = in_dorm
                                student.save(update_fields=["is_in_dormitory"])
                                print(f"[STUDENT] {student.first_name} {student.last_name} is_in_dormitory -> {in_dorm}")
                            except Student.DoesNotExist:
                                print(f"Student {emp_no} topilmadi")

        # Front uchun blok
        block_html = (
            "<div style='margin:10px;padding:10px;border:1px solid #ccc;'>"
            + "".join(html_parts) +
            "</div>"
        )
        events.append(block_html)
        if len(events) > 20:
            events = events[-20:]

        print("=== Hikvision multipart event qabul qilindi ===")
        return HttpResponse("OK", content_type="text/plain")

    # GET bo'lsa — jonli kuzatish sahifasi
    html = """
    <html>
    <head>
    <meta charset='utf-8'>
    <title>Hikvision Events</title>
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
    # SSE orqali jonli ulanish
    def event_stream():
        resp = StreamingHttpResponse(content_type='text/event-stream')
        listeners.append(resp)
        return resp
    return event_stream()
