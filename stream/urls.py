from django.urls import path
from .views import hikvision_event

urlpatterns = [
    path('', hikvision_event),      # Hikvision POST ham GET sahifa ham shu
]
