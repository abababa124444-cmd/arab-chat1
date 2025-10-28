from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Friendship


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer لمعلومات الملف الشخصي"""
    
    class Meta:
        model = Profile
        fields = ['name', 'phone', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer للمستخدمين مع معلومات الملف الشخصي"""
    profile = ProfileSerializer(read_only=True)
    is_friend = serializers.SerializerMethodField()
    friendship_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'profile', 'is_friend', 'friendship_status']
    
    def get_is_friend(self, obj):
        """تحقق إذا كان المستخدم صديق"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj:
            return Friendship.are_friends(request.user, obj)
        return False
    
    def get_friendship_status(self, obj):
        """الحصول على حالة الصداقة"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj:
            friendship = Friendship.get_friendship_status(request.user, obj)
            if friendship:
                return {
                    'status': friendship.status,
                    'from_me': friendship.from_user == request.user,
                    'created_at': friendship.created_at.isoformat()
                }
        return None


class UserMinimalSerializer(serializers.ModelSerializer):
    """Serializer مبسط للمستخدمين (لقوائم الأصدقاء)"""
    name = serializers.CharField(source='profile.name', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'phone']


class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer لعلاقات الصداقة"""
    from_user = UserMinimalSerializer(read_only=True)
    to_user = UserMinimalSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'from_user', 'to_user', 'status', 'status_display', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FriendshipCreateSerializer(serializers.Serializer):
    """Serializer لإنشاء طلب صداقة"""
    user_id = serializers.IntegerField()
    
    def validate_user_id(self, value):
        """التحقق من صحة معرف المستخدم"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("المستخدم غير موجود")
        
        request = self.context.get('request')
        if request and request.user.id == value:
            raise serializers.ValidationError("لا يمكنك إضافة نفسك كصديق")
        
        return value

