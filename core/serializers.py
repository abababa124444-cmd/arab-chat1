from rest_framework import serializers
from .models import Room, Message, DirectThread, DirectMessage
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'date_joined']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Room Messages"""
    class Meta:
        model = Message
        fields = ['id', 'room', 'author_name', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class RoomSerializer(serializers.ModelSerializer):
    """Serializer for Room model"""
    messages_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'slug', 'created_at', 'messages_count', 'last_message']
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_messages_count(self, obj):
        """Get count of messages in this room"""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """Get last message in this room"""
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'id': last_msg.id,
                'author': last_msg.author_name,
                'content': last_msg.content[:50],  # First 50 chars
                'created_at': last_msg.created_at
            }
        return None


class DirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for Direct Messages"""
    author_info = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessage
        fields = ['id', 'thread', 'author', 'author_info', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_author_info(self, obj):
        """Get author profile information"""
        if hasattr(obj.author, 'profile'):
            return {
                'name': obj.author.profile.name,
                'phone': obj.author.profile.phone,
            }
        return {'name': obj.author.username}


class DirectThreadSerializer(serializers.ModelSerializer):
    """Serializer for Direct Thread"""
    user1_info = serializers.SerializerMethodField()
    user2_info = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectThread
        fields = ['id', 'user1', 'user2', 'user1_info', 'user2_info', 
                 'last_message', 'unread_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_user1_info(self, obj):
        if hasattr(obj.user1, 'profile'):
            return {
                'name': obj.user1.profile.name,
                'phone': obj.user1.profile.phone,
            }
        return {'name': obj.user1.username}
    
    def get_user2_info(self, obj):
        if hasattr(obj.user2, 'profile'):
            return {
                'name': obj.user2.profile.name,
                'phone': obj.user2.profile.phone,
            }
        return {'name': obj.user2.username}
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:50],
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        # TODO: Implement unread messages count
        return 0

