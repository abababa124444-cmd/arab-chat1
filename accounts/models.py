from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"


class OTP(models.Model):
    PURPOSE_SIGNUP = 'signup'
    PURPOSE_LOGIN = 'login'

    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, default=PURPOSE_SIGNUP)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"OTP {self.phone} {self.code} ({self.purpose})"


class Friendship(models.Model):
    """نموذج لإدارة العلاقات بين المستخدمين (أصدقاء/حظر)"""
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_BLOCKED = 'blocked'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'قيد الانتظار'),
        (STATUS_ACCEPTED, 'مقبول'),
        (STATUS_BLOCKED, 'محظور'),
    ]
    
    from_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='friendships_sent',
        verbose_name='من المستخدم'
    )
    to_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='friendships_received',
        verbose_name='إلى المستخدم'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=STATUS_PENDING,
        verbose_name='الحالة'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = (('from_user', 'to_user'),)
        ordering = ['-created_at']
        verbose_name = 'صداقة'
        verbose_name_plural = 'الصداقات'
    
    def __str__(self) -> str:
        return f"{self.from_user.profile.name if hasattr(self.from_user, 'profile') else self.from_user.username} -> {self.to_user.profile.name if hasattr(self.to_user, 'profile') else self.to_user.username} ({self.get_status_display()})"
    
    @classmethod
    def are_friends(cls, user1, user2):
        """تحقق من وجود صداقة مقبولة بين مستخدمين"""
        return cls.objects.filter(
            models.Q(from_user=user1, to_user=user2, status=cls.STATUS_ACCEPTED) |
            models.Q(from_user=user2, to_user=user1, status=cls.STATUS_ACCEPTED)
        ).exists()
    
    @classmethod
    def is_blocked(cls, user1, user2):
        """تحقق من حظر أحد المستخدمين للآخر"""
        return cls.objects.filter(
            models.Q(from_user=user1, to_user=user2, status=cls.STATUS_BLOCKED) |
            models.Q(from_user=user2, to_user=user1, status=cls.STATUS_BLOCKED)
        ).exists()
    
    @classmethod
    def get_friendship_status(cls, user1, user2):
        """الحصول على حالة العلاقة بين مستخدمين"""
        friendship = cls.objects.filter(
            models.Q(from_user=user1, to_user=user2) |
            models.Q(from_user=user2, to_user=user1)
        ).first()
        
        if not friendship:
            return None
        return friendship
