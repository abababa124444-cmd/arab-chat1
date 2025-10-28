from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'rooms', api_views.RoomViewSet, basename='room')
router.register(r'direct-threads', api_views.DirectThreadViewSet, basename='direct-thread')

urlpatterns = [
    path('', include(router.urls)),
    path('rooms/search/', api_views.search_rooms, name='search_rooms'),
    path('rooms/<str:room_slug>/poll/', api_views.api_messages_poll, name='messages_poll'),
]

