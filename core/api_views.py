from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Room, Message, DirectThread, DirectMessage
from .serializers import (
    RoomSerializer, MessageSerializer,
    DirectThreadSerializer, DirectMessageSerializer
)


class RoomViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Chat Rooms"""
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def messages(self, request, slug=None):
        """Get all messages for a specific room"""
        room = self.get_object()
        messages = room.messages.all()[:200]  # Last 200 messages
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def send_message(self, request, slug=None):
        """Send a message to a room"""
        room = self.get_object()
        author_name = request.user.profile.name if hasattr(request.user, 'profile') else request.user.username
        content = request.data.get('content', '')
        
        if not content:
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = Message.objects.create(
            room=room,
            author_name=author_name,
            content=content
        )
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DirectThreadViewSet(viewsets.ModelViewSet):
    """ViewSet for Direct Message Threads"""
    serializer_class = DirectThreadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get only threads where the current user is a participant"""
        user = self.request.user
        return DirectThread.objects.filter(
            Q(user1=user) | Q(user2=user)
        ).distinct()
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a specific thread"""
        thread = self.get_object()
        messages = thread.messages.all()[:500]
        serializer = DirectMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a direct thread"""
        thread = self.get_object()
        content = request.data.get('content', '')
        
        if not content:
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = DirectMessage.objects.create(
            thread=thread,
            author=request.user,
            content=content
        )
        serializer = DirectMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """Get or create a direct thread with another user"""
        other_user_id = request.data.get('user_id')
        
        if not other_user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth.models import User
        other_user = get_object_or_404(User, id=other_user_id)
        
        # Ensure consistent ordering
        u1, u2 = (request.user, other_user) if request.user.id <= other_user.id else (other_user, request.user)
        
        thread, created = DirectThread.objects.get_or_create(user1=u1, user2=u2)
        serializer = self.get_serializer(thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
def api_messages_poll(request, room_slug):
    """Get new messages since a specific message ID (for polling)"""
    room = get_object_or_404(Room, slug=room_slug)
    after_id = int(request.GET.get('after', 0))
    
    messages = room.messages.filter(id__gt=after_id)
    serializer = MessageSerializer(messages, many=True)
    
    return Response({
        'messages': serializer.data,
        'count': messages.count()
    })


@api_view(['GET'])
def search_rooms(request):
    """Search for rooms by name"""
    query = request.GET.get('q', '')
    
    if query:
        rooms = Room.objects.filter(name__icontains=query)[:20]
    else:
        rooms = Room.objects.all()[:20]
    
    serializer = RoomSerializer(rooms, many=True)
    return Response(serializer.data)

