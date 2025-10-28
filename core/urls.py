from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('rooms/', views.room_list, name='room_list'),
    path('chat/', views.room_list, name='chat'),
    path('r/<str:slug>/', views.room_detail, name='room_detail'),
    path('api/r/<str:slug>/messages/', views.api_messages, name='api_messages'),
    path('connect/', views.connect, name='connect'),
    path('dm/', views.dm_list, name='dm_list'),
    path('dm/<int:user_id>/', views.dm_thread, name='dm_thread'),
]
