from django.urls import path
from . import views
from . import sse

app_name = 'notifications'

urlpatterns = [
    # Notification list and detail views
    path('', views.NotificationListView.as_view(), name='list'),
    path('<uuid:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    
    # Notification preferences
    path('preferences/', views.NotificationPreferenceView.as_view(), name='preferences'),
    
    # AJAX actions for individual notifications
    path('<uuid:pk>/mark-read/', views.mark_notification_read, name='mark_read'),
    path('<uuid:pk>/mark-unread/', views.mark_notification_unread, name='mark_unread'),
    path('<uuid:pk>/delete/', views.delete_notification, name='delete'),
    
    # Bulk actions
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # API endpoints
    path('count/', views.notification_count, name='count'),
    path('recent/', views.recent_notifications, name='recent'),
    
    # Server-Sent Events for real-time notifications
    path('sse/', sse.notification_sse, name='sse'),
    
    # System notifications
    path('system/', views.SystemNotificationListView.as_view(), name='system_list'),
    
    # Push notification device management
    path('devices/register/', views.PushDeviceRegisterView.as_view(), name='device_register'),
    path('devices/', views.PushDeviceListView.as_view(), name='device_list'),
    path('devices/register-ajax/', views.register_push_device, name='register_device_ajax'),
    
    # System notification actions
    path('system/dismiss/', views.dismiss_system_notification, name='dismiss_system'),
    
    # Analytics
    path('analytics/', views.NotificationAnalyticsView.as_view(), name='analytics'),
    
    # Webhook endpoints
    path('webhook/', views.notification_webhook, name='webhook'),
    
    # Unsubscribe
    path('unsubscribe/', views.notification_unsubscribe, name='unsubscribe'),
    path('unsubscribe/success/', views.unsubscribe_success, name='unsubscribe_success'),
]