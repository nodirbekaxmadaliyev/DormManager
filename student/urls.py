from django.urls import path
from .views import StudentListView, StudentDetailView, StudentUpdateView, StudentDeleteView, StudentCreateView, load_rooms_ajax

urlpatterns = [
    path('', StudentListView.as_view(), name='students'),
    path('<int:pk>/', StudentDetailView.as_view(), name='student_detail'),
    path('<int:pk>/edit/', StudentUpdateView.as_view(), name='student_update'),
    path('<int:pk>/delete/', StudentDeleteView.as_view(), name='student_delete'),
    path('add/', StudentCreateView.as_view(), name='student_add'),
    path('ajax/load-rooms/', load_rooms_ajax, name='ajax_load_rooms'),
]