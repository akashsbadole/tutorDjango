import json
from django.http import StreamingHttpResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification

User = get_user_model()


def event_stream_generator(user):
    """Generator function for SSE events"""
    last_notification_id = 0
    
    # Get initial unread count
    unread_count = Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()
    
    # Send initial unread count
    yield f"data: {json.dumps({'type': 'unread_count', 'count': unread_count})}\n\n"
    
    while True:
        # Check for new notifications
        latest_notification = Notification.objects.filter(
            recipient=user,
            id__gt=last_notification_id
        ).order_by('-id').first()
        
        if latest_notification:
            last_notification_id = latest_notification.id
            notification_data = {
                'type': 'new_notification',
                'notification': {
                    'id': latest_notification.id,
                    'title': latest_notification.title,
                    'content': latest_notification.content,
                    'priority': latest_notification.priority,
                    'created_at': latest_notification.created_at.isoformat(),
                    'notification_type': latest_notification.notification_type if latest_notification.notification_type else None,
                }
            }
            yield f"data: {json.dumps(notification_data)}\n\n"
            
            # Update unread count
            unread_count = Notification.objects.filter(
                recipient=user,
                is_read=False
            ).count()
            yield f"data: {json.dumps({'type': 'unread_count', 'count': unread_count})}\n\n"
        
        # Check for read notifications
        read_notifications = Notification.objects.filter(
            recipient=user,
            is_read=True,
            read_at__gte=timezone.now() - timezone.timedelta(seconds=30)
        ).order_by('-read_at').first()
        
        if read_notifications:
            notification_data = {
                'type': 'notification_read',
                'notification_id': read_notifications.id
            }
            yield f"data: {json.dumps(notification_data)}\n\n"
            
            # Update unread count
            unread_count = Notification.objects.filter(
                recipient=user,
                is_read=False
            ).count()
            yield f"data: {json.dumps({'type': 'unread_count', 'count': unread_count})}\n\n"
        
        # Sleep for a short period to prevent excessive database queries
        import time
        time.sleep(2)


@login_required
@require_GET
def notification_sse(request):
    """Server-Sent Events endpoint for real-time notifications"""
    response = StreamingHttpResponse(
        (chunk.encode('utf-8') for chunk in event_stream_generator(request.user)),
        content_type='text/event-stream'
    )
    
    # Set headers for SSE
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


@login_required
@require_GET
def notification_count(request):
    """Get current notification count via AJAX"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return HttpResponse(
        json.dumps({'count': count}),
        content_type='application/json'
    )