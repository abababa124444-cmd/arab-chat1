from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Friendship
from .serializers import (
    UserSerializer, 
    FriendshipSerializer,
    FriendshipCreateSerializer
)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet للمستخدمين - للقراءة فقط"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """الحصول على جميع المستخدمين ماعدا المستخدم الحالي"""
        return User.objects.filter(
            profile__isnull=False
        ).exclude(
            id=self.request.user.id
        ).select_related('profile')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """البحث عن مستخدمين بالاسم أو الهاتف"""
        query = request.GET.get('q', '').strip()
        
        if not query:
            return Response({'error': 'يجب توفير معامل البحث q'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = self.get_queryset().filter(
            Q(profile__name__icontains=query) | 
            Q(profile__phone__icontains=query)
        )[:20]  # حد أقصى 20 نتيجة
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def friends(self, request):
        """الحصول على قائمة الأصدقاء فقط"""
        # الأصدقاء المقبولين
        friends_sent = Friendship.objects.filter(
            from_user=request.user,
            status=Friendship.STATUS_ACCEPTED
        ).select_related('to_user__profile')
        
        friends_received = Friendship.objects.filter(
            to_user=request.user,
            status=Friendship.STATUS_ACCEPTED
        ).select_related('from_user__profile')
        
        # دمج القوائم
        friend_users = []
        for f in friends_sent:
            friend_users.append(f.to_user)
        for f in friends_received:
            friend_users.append(f.from_user)
        
        serializer = self.get_serializer(friend_users, many=True)
        return Response(serializer.data)


class FriendshipViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة العلاقات بين المستخدمين"""
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """الحصول على العلاقات المتعلقة بالمستخدم الحالي"""
        return Friendship.objects.filter(
            Q(from_user=self.request.user) | Q(to_user=self.request.user)
        ).select_related('from_user__profile', 'to_user__profile')
    
    @action(detail=False, methods=['post'])
    def send_request(self, request):
        """إرسال طلب صداقة"""
        serializer = FriendshipCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        to_user = get_object_or_404(User, id=user_id)
        
        # التحقق من عدم وجود علاقة سابقة
        existing = Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) |
            Q(from_user=to_user, to_user=request.user)
        ).first()
        
        if existing:
            if existing.status == Friendship.STATUS_BLOCKED:
                return Response(
                    {'error': 'لا يمكن إرسال طلب صداقة لهذا المستخدم'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing.status == Friendship.STATUS_ACCEPTED:
                return Response(
                    {'error': 'أنتما أصدقاء بالفعل'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'error': 'تم إرسال طلب الصداقة مسبقاً'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # إنشاء طلب الصداقة
        friendship = Friendship.objects.create(
            from_user=request.user,
            to_user=to_user,
            status=Friendship.STATUS_PENDING
        )
        
        result_serializer = FriendshipSerializer(friendship)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """قبول طلب صداقة"""
        friendship = get_object_or_404(
            Friendship,
            id=pk,
            to_user=request.user,
            status=Friendship.STATUS_PENDING
        )
        
        friendship.status = Friendship.STATUS_ACCEPTED
        friendship.save()
        
        serializer = self.get_serializer(friendship)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """رفض طلب صداقة"""
        friendship = get_object_or_404(
            Friendship,
            id=pk,
            to_user=request.user,
            status=Friendship.STATUS_PENDING
        )
        
        friendship.delete()
        return Response({'message': 'تم رفض طلب الصداقة'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """إلغاء طلب صداقة تم إرساله"""
        friendship = get_object_or_404(
            Friendship,
            id=pk,
            from_user=request.user,
            status=Friendship.STATUS_PENDING
        )
        
        friendship.delete()
        return Response({'message': 'تم إلغاء طلب الصداقة'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def remove(self, request):
        """إزالة صديق"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        
        other_user = get_object_or_404(User, id=user_id)
        
        friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=other_user) |
            Q(from_user=other_user, to_user=request.user),
            status=Friendship.STATUS_ACCEPTED
        ).first()
        
        if not friendship:
            return Response({'error': 'لم يتم العثور على صداقة'}, status=status.HTTP_404_NOT_FOUND)
        
        friendship.delete()
        return Response({'message': 'تم إزالة الصديق'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def block(self, request):
        """حظر مستخدم"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        
        to_user = get_object_or_404(User, id=user_id)
        
        if to_user == request.user:
            return Response({'error': 'لا يمكنك حظر نفسك'}, status=status.HTTP_400_BAD_REQUEST)
        
        # حذف أي علاقة سابقة
        Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) |
            Q(from_user=to_user, to_user=request.user)
        ).delete()
        
        # إنشاء علاقة حظر
        friendship = Friendship.objects.create(
            from_user=request.user,
            to_user=to_user,
            status=Friendship.STATUS_BLOCKED
        )
        
        serializer = self.get_serializer(friendship)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def unblock(self, request):
        """إلغاء حظر مستخدم"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        
        to_user = get_object_or_404(User, id=user_id)
        
        deleted_count, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=to_user,
            status=Friendship.STATUS_BLOCKED
        ).delete()
        
        if deleted_count == 0:
            return Response({'error': 'لم يتم العثور على حظر'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'message': 'تم إلغاء الحظر'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def pending_received(self, request):
        """الحصول على طلبات الصداقة المستلمة المعلقة"""
        friendships = Friendship.objects.filter(
            to_user=request.user,
            status=Friendship.STATUS_PENDING
        ).select_related('from_user__profile')
        
        serializer = self.get_serializer(friendships, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_sent(self, request):
        """الحصول على طلبات الصداقة المرسلة المعلقة"""
        friendships = Friendship.objects.filter(
            from_user=request.user,
            status=Friendship.STATUS_PENDING
        ).select_related('to_user__profile')
        
        serializer = self.get_serializer(friendships, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def blocked_users(self, request):
        """الحصول على قائمة المستخدمين المحظورين"""
        friendships = Friendship.objects.filter(
            from_user=request.user,
            status=Friendship.STATUS_BLOCKED
        ).select_related('to_user__profile')
        
        serializer = self.get_serializer(friendships, many=True)
        return Response(serializer.data)

