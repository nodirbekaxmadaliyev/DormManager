from django.urls import path
from .views import DormitorySelectView, DormitoryDetailView, DormitoryUpdateView

urlpatterns = [
    path('', DormitorySelectView.as_view(), name='dormitories'),
    path('<int:pk>/', DormitoryDetailView.as_view(), name='dormitory_detail'),
    path('<int:pk>/edit/', DormitoryUpdateView.as_view(), name='dormitory_edit'),
]
