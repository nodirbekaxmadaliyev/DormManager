from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from config import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('employees/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('students/', include('student.urls')),
    path('logs/', include('Logs.urls')),
    path('payment/', include('payment.urls')),
    path('dormitory/', include('dormitory.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)