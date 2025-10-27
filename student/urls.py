from django.urls import path
from .views import StudentListView, StudentDetailView, StudentUpdateView, StudentDeleteView, StudentCreateView, load_rooms_ajax, toggle_block, DeleteAllStudentsView, AddStudentsToDevicesView, StudentDeleteFromModel

urlpatterns = [
    path('', StudentListView.as_view(), name='students'),
    path('<int:pk>/', StudentDetailView.as_view(), name='student_detail'),
    path('<int:pk>/toggle-block/', toggle_block, name='toggle_block'),
    path('<int:pk>/edit/', StudentUpdateView.as_view(), name='student_update'),
    path('<int:pk>/delete/', StudentDeleteView.as_view(), name='student_delete'),
    path('<int:pk>/deleteFromModel/', StudentDeleteFromModel.as_view(), name='student_delete_from_model'),
    path('add/', StudentCreateView.as_view(), name='student_add'),
    path('ajax/load-rooms/', load_rooms_ajax, name='ajax_load_rooms'),
    path("students/delete_all/", DeleteAllStudentsView.as_view(), name="students_delete_all"),
    path('students/add-to-devices/', AddStudentsToDevicesView.as_view(), name='add_students_to_devices'),

]