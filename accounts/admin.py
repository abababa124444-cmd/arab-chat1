from django.contrib import admin
from .models import Profile, OTP, Friendship


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "phone", "created_at")
    search_fields = ("name", "phone", "user__username")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "purpose", "is_used", "expires_at", "created_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone", "code")


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("from_user__profile__name", "to_user__profile__name")
    raw_id_fields = ("from_user", "to_user")
