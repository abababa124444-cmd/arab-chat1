from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('verify/', views.verify, name='verify'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('contacts/sync/', views.contacts_sync, name='contacts_sync'),
    
    # Users & Friends
    path('users/', views.users_list, name='users_list'),
    path('friends/', views.friends_list, name='friends_list'),
    
    # Friend Management
    path('friends/request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friends/accept/<int:friendship_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('friends/reject/<int:friendship_id>/', views.reject_friend_request, name='reject_friend_request'),
    path('friends/cancel/<int:friendship_id>/', views.cancel_friend_request, name='cancel_friend_request'),
    path('friends/remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    
    # Block Management
    path('block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/<int:user_id>/', views.unblock_user, name='unblock_user'),
]
