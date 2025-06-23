from django.urls import path
from .views import EmployeePage, EmployeeUpdateView, EmployeeDeleteView, change_password, EmployeeCreateView

urlpatterns = [
    path('', EmployeePage.as_view(), name = 'employees'),
    path('<int:pk>/update/', EmployeeUpdateView.as_view(), name='employee_update'),
    path('<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee_delete'),
    path('change-password/', change_password, name='change_password'),
    path('add/', EmployeeCreateView.as_view(), name='employee_add'),

]