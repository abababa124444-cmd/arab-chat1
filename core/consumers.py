import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from .models import Room, Message, DirectThread, DirectMessage


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket Consumer for Room-based chat"""
    
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = f'chat_{self.room_slug}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            content = data.get('content', '')
            author_name = data.get('author_name', 'Anonymous')
            
            # Save message to database
            room = await sync_to_async(Room.objects.get)(slug=self.room_slug)
            message = await sync_to_async(Message.objects.create)(
                room=room,
                author_name=author_name,
                content=content
            )
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'data': {
                        'id': message.id,
                        'author_name': message.author_name,
                        'content': message.content,
                        'created_at': message.created_at.isoformat(),
                    }
                }
            )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['data']))


class DirectMessageConsumer(AsyncWebsocketConsumer):
    """WebSocket Consumer for Direct Messages (1-on-1)"""
    
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.current_user = self.scope['user']
        
        # Determine thread ID
        user = await sync_to_async(User.objects.get)(id=self.user_id)
        
        u1, u2 = (self.current_user, user) if self.current_user.id <= user.id else (user, self.current_user)
        
        thread = await sync_to_async(DirectThread.objects.get)(
            user1=u1,
            user2=u2
        )
        
        self.thread_id = thread.id
        self.group_name = f'dm_{self.thread_id}'
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'dm_message':
            content = data.get('content', '')
            
            # Save to database
            thread = await sync_to_async(DirectThread.objects.get)(id=self.thread_id)
            message = await sync_to_async(DirectMessage.objects.create)(
                thread=thread,
                author=self.current_user,
                content=content
            )
            
            # Send to group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'dm_message',
                    'data': {
                        'id': message.id,
                        'author': self.current_user.username,
                        'author_name': self.current_user.profile.name if hasattr(self.current_user, 'profile') else self.current_user.username,
                        'content': message.content,
                        'created_at': message.created_at.isoformat(),
                    }
                }
            )
    
    async def dm_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event['data']))

