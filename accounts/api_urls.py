from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import UserViewSet, FriendshipViewSet

app_name = 'accounts_api'

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'friendships', FriendshipViewSet, basename='friendship')

urlpatterns = [
    path('', include(router.urls)),
]

