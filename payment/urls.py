from django.urls import path
from .views import PaymentListView, PaymentCreateView, StudentSearchAPIView, DebtStatisticsView

urlpatterns = [
    path('', PaymentListView.as_view(), name='payments'),
    path('add/', PaymentCreateView.as_view(), name='payment_add'),
    path('api/student-search/', StudentSearchAPIView.as_view(), name='student_search_api'),
    path('statistics/', DebtStatisticsView.as_view(), name='debt_statistics'),
]