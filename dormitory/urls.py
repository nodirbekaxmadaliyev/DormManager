from django.urls import path
from .views import (DormitorySelectView,
                    DormitoryDetailView,
                    DormitoryUpdateView,
                    RoomListView, RoomCreateView, RoomUpdateView,
                    RoomDetailView, RoomDeleteView)

urlpatterns = [
    path('', DormitorySelectView.as_view(), name='dormitories'),
    path('<int:pk>/', DormitoryDetailView.as_view(), name='dormitory_detail'),
    path('<int:pk>/edit/', DormitoryUpdateView.as_view(), name='dormitory_edit'),
    path('rooms/', RoomListView.as_view(), name='rooms'),
    path('rooms/add/', RoomCreateView.as_view(), name='room_add'),
    path('rooms/<int:pk>/', RoomDetailView.as_view(), name='room_detail'),
    path('rooms/<int:pk>/edit/', RoomUpdateView.as_view(), name='room_update'),
    path('rooms/<int:pk>/delete/', RoomDeleteView.as_view(), name='room_delete'),

]
