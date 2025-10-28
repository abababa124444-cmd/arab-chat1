from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<slug:slug>/', consumers.ChatConsumer.as_asgi(), name='chat_websocket'),
    path('ws/dm/<int:user_id>/', consumers.DirectMessageConsumer.as_asgi(), name='dm_websocket'),
]

