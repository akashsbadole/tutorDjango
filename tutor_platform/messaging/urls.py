from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'messaging'

urlpatterns = [
    # Message URLs
    path('', login_required(views.MessageListView.as_view()), name='message_list'),
    path('conversation/<int:pk>/', login_required(views.MessageDetailView.as_view()), name='detail'),
    path('conversation/create/', login_required(views.MessageCreateView.as_view()), name='create'),
    
    # Online Class URLs
    path('online-class/create/', login_required(views.OnlineClassCreateView.as_view()), name='online_class_create'),
    path('online-class/<int:pk>/', login_required(views.OnlineClassDetailView.as_view()), name='online_class_detail'),
    
    # Communication Preferences
    path('preferences/', login_required(views.CommunicationPreferencesView.as_view()), name='preferences'),
    
    # File Sharing URLs
    path('files/create/', login_required(views.SharedFileCreateView.as_view()), name='shared_file_create'),
    path('files/<int:pk>/', login_required(views.SharedFileDetailView.as_view()), name='shared_file_detail'),
    path('files/<int:pk>/download/', login_required(views.download_shared_file), name='download_shared_file'),
    
    # User Blocking URLs
    path('block-user/', login_required(views.BlockUserView.as_view()), name='block_user'),
    path('blocked-users/', login_required(views.BlockedUsersListView.as_view()), name='blocked_users'),
    path('unblock/<int:pk>/', login_required(views.unblock_user), name='unblock_user'),
    
    # Message Actions
    path('message/<int:pk>/delete/', login_required(views.delete_message), name='delete_message'),
    path('message/<int:pk>/edit/', login_required(views.edit_message), name='edit_message'),
    
    # Online Class Actions
    path('online-class/<int:pk>/join/', login_required(views.join_online_class), name='join_online_class'),
    path('online-class/<int:pk>/leave/', login_required(views.leave_online_class), name='leave_online_class'),
    
    # Class Schedule, Recording, Resource, and Analytics URLs
    path('schedule/<int:schedule_id>/', login_required(views.ClassScheduleView.as_view()), name='class_schedule'),
    path('recording/<int:recording_id>/', login_required(views.ClassRecordingView.as_view()), name='class_recording'),
    path('resource/<int:resource_id>/', login_required(views.ClassResourceView.as_view()), name='class_resource'),
    path('analytics/<int:pk>/', login_required(views.ClassAnalyticsView.as_view()), name='class_analytics'),
    
    # Class Recording and Resource Creation URLs
    path('online-class/<int:class_id>/recording/create/', login_required(views.ClassRecordingCreateView.as_view()), name='class_recording_create'),
    path('online-class/<int:class_id>/resource/create/', login_required(views.ClassResourceCreateView.as_view()), name='class_resource_create'),
    
    # Masked Email URLs
    path('masked-email/<int:pk>/', login_required(views.masked_email_info), name='masked_email_info'),
    path('masked-email/create/<int:award_id>/', login_required(views.create_masked_email), name='create_masked_email'),
]