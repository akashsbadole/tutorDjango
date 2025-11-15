from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, CreateView, FormView, TemplateView
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import (
    Notification, NotificationPreference, NotificationTemplate,
    PushDevice, SystemNotification, NotificationDelivery,
    NotificationDigest, NotificationAnalytics, SystemNotificationDismissal
)
from .forms import (
    NotificationPreferenceForm, NotificationSearchForm,
    BulkNotificationForm, PushNotificationForm
)
from .utils import (
    create_notification, get_unread_count, get_recent_notifications,
    mark_all_as_read, cleanup_expired_notifications
)


class NotificationListView(LoginRequiredMixin, ListView):
    """List all notifications for the current user"""
    
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter notifications for current user"""
        queryset = Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender', 'content_type')
        
        # Filter by read status
        read_status = self.request.GET.get('read')
        if read_status == 'read':
            queryset = queryset.filter(is_read=True)
        elif read_status == 'unread':
            queryset = queryset.filter(is_read=False)
        
        # Filter by type
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by priority
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context"""
        context = super().get_context_data(**kwargs)
        
        # Add counts
        context['unread_count'] = Notification.objects.filter(
            recipient=self.request.user,
            is_read=False
        ).count()
        
        context['total_count'] = Notification.objects.filter(
            recipient=self.request.user
        ).count()
        
        # Add filter options
        context['current_filters'] = {
            'read': self.request.GET.get('read', ''),
            'type': self.request.GET.get('type', ''),
            'priority': self.request.GET.get('priority', ''),
        }
        
        context['notification_types'] = Notification.Type.choices
        context['priority_levels'] = Notification.Priority.choices
        
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """View notification details"""
    
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        """Only show notifications for current user"""
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('sender', 'content_type')
    
    def get_object(self, queryset=None):
        """Mark notification as read when viewed"""
        obj = super().get_object(queryset)
        if not obj.is_read:
            obj.mark_as_read()
        return obj


class NotificationPreferenceView(LoginRequiredMixin, UpdateView):
    """Update notification preferences"""
    
    model = NotificationPreference
    template_name = 'notifications/preferences.html'
    success_url = reverse_lazy('notifications:preferences')
    fields = [
        'email_enabled', 'push_enabled', 'in_app_enabled',
        'email_message', 'email_proposal', 'email_award',
        'email_session', 'email_review', 'email_payment', 'email_system',
        'push_message', 'push_proposal', 'push_award',
        'push_session', 'push_review', 'push_payment', 'push_system',
        'in_app_message', 'in_app_proposal', 'in_app_award',
        'in_app_session', 'in_app_review', 'in_app_payment', 'in_app_system',
        'email_frequency', 'quiet_hours_enabled', 'quiet_hours_start',
        'quiet_hours_end', 'quiet_hours_timezone', 'auto_delete_read',
        'auto_delete_days'
    ]
    
    def get_object(self, queryset=None):
        """Get or create notification preferences for user"""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def form_valid(self, form):
        """Add success message"""
        messages.success(self.request, 'Notification preferences updated successfully.')
        return super().form_valid(form)


@login_required
@require_POST
def mark_notification_read(request, pk):
    """Mark a notification as read via AJAX"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    
    notification.mark_as_read()
    
    return JsonResponse({
        'success': True,
        'is_read': notification.is_read,
        'read_at': notification.read_at.isoformat() if notification.read_at else None
    })


@login_required
@require_POST
def mark_notification_unread(request, pk):
    """Mark a notification as unread via AJAX"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    
    notification.mark_as_unread()
    
    return JsonResponse({
        'success': True,
        'is_read': notification.is_read
    })


@login_required
@require_POST
def delete_notification(request, pk):
    """Delete a notification via AJAX"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    
    notification.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Notification deleted successfully.'
    })


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return JsonResponse({
        'success': True,
        'message': 'All notifications marked as read.'
    })


@login_required
def notification_count(request):
    """Get unread notification count via AJAX"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'count': count
    })


@login_required
def recent_notifications(request):
    """Get recent notifications for header dropdown via AJAX"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-created_at')[:5]
    
    data = []
    for notification in notifications:
        item = {
            'id': str(notification.id),
            'title': notification.title,
            'content': notification.content[:100] + '...' if len(notification.content) > 100 else notification.content,
            'type': notification.notification_type,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
        }
        
        if notification.sender:
            item['sender'] = {
                'name': notification.sender.get_full_name(),
                'username': notification.sender.username
            }
        
        data.append(item)
    
    return JsonResponse({
        'notifications': data
    })


class SystemNotificationListView(LoginRequiredMixin, ListView):
    """List system-wide notifications"""
    
    model = SystemNotification
    template_name = 'notifications/system_notification_list.html'
    context_object_name = 'system_notifications'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter system notifications for current user"""
        queryset = SystemNotification.objects.filter(is_active=True)
        
        # Filter by target audience
        if hasattr(self.request.user, 'user_type'):
            if self.request.user.user_type == 'STUDENT':
                queryset = queryset.filter(
                    Q(target_audience=SystemNotification.TargetAudience.ALL) |
                    Q(target_audience=SystemNotification.TargetAudience.STUDENTS)
                )
            elif self.request.user.user_type == 'TUTOR':
                queryset = queryset.filter(
                    Q(target_audience=SystemNotification.TargetAudience.ALL) |
                    Q(target_audience=SystemNotification.TargetAudience.TUTORS)
                )
            elif self.request.user.is_staff or self.request.user.is_superuser:
                queryset = queryset.filter(
                    Q(target_audience=SystemNotification.TargetAudience.ALL) |
                    Q(target_audience=SystemNotification.TargetAudience.ADMINS)
                )
            else:
                queryset = queryset.filter(target_audience=SystemNotification.TargetAudience.ALL)
        else:
            # If no user type, show all
            queryset = queryset.filter(target_audience=SystemNotification.TargetAudience.ALL)
        
        # Exclude dismissed notifications
        dismissed_ids = SystemNotificationDismissal.objects.filter(
            user=self.request.user
        ).values_list('system_notification_id', flat=True)
        
        return queryset.exclude(id__in=dismissed_ids).order_by('-created_at')


class PushDeviceRegisterView(LoginRequiredMixin, FormView):
    """Register a push notification device"""
    
    template_name = 'notifications/push_device_register.html'
    form_class = PushNotificationForm
    success_url = reverse_lazy('notifications:device_list')
    
    def form_valid(self, form):
        """Register the device"""
        device = form.save(commit=False)
        device.user = self.request.user
        device.save()
        
        messages.success(
            self.request,
            'Device registered successfully for push notifications.'
        )
        return super().form_valid(form)


class PushDeviceListView(LoginRequiredMixin, ListView):
    """List user's push notification devices"""
    
    model = PushDevice
    template_name = 'notifications/push_device_list.html'
    context_object_name = 'devices'
    paginate_by = 20
    
    def get_queryset(self):
        """Get devices for current user"""
        return PushDevice.objects.filter(
            user=self.request.user
        ).order_by('-last_used_at', '-created_at')


class NotificationAnalyticsView(LoginRequiredMixin, TemplateView):
    """Show notification analytics for the current user"""
    
    template_name = 'notifications/analytics.html'
    
    def get_context_data(self, **kwargs):
        """Add analytics data to context"""
        context = super().get_context_data(**kwargs)
        
        # Get user's notification statistics
        stats = Notification.objects.filter(
            recipient=self.request.user
        ).aggregate(
            total=Count('id'),
            read=Count('id', filter=Q(is_read=True)),
            unread=Count('id', filter=Q(is_read=False)),
            email_sent=Count('id', filter=Q(email_sent=True)),
            push_sent=Count('id', filter=Q(push_sent=True))
        )
        
        # Get statistics by type
        type_stats = Notification.objects.filter(
            recipient=self.request.user
        ).values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get recent activity
        recent_notifications = Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')[:10]
        
        context.update({
            'stats': stats,
            'type_stats': type_stats,
            'recent_notifications': recent_notifications,
        })
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
def notification_webhook(request):
    """Handle webhook notifications from external services"""
    try:
        data = json.loads(request.body)
        
        # Process webhook data based on type
        webhook_type = data.get('type')
        
        if webhook_type == 'email_delivery':
            # Handle email delivery status update
            message_id = data.get('message_id')
            status = data.get('status')
            timestamp = data.get('timestamp')
            
            try:
                delivery = NotificationDelivery.objects.get(
                    recipient_address=message_id,
                    channel='EMAIL'
                )
                
                if status == 'delivered':
                    delivery.mark_as_delivered()
                elif status == 'bounced':
                    delivery.status = NotificationDelivery.Status.BOUNCED
                    delivery.failed_at = timezone.now()
                    delivery.failure_reason = data.get('reason', 'Email bounced')
                    delivery.save()
                
                return JsonResponse({'status': 'success'})
                
            except NotificationDelivery.DoesNotExist:
                return JsonResponse(
                    {'status': 'error', 'message': 'Delivery record not found'},
                    status=400
                )
        
        elif webhook_type == 'push_delivery':
            # Handle push notification delivery status
            message_id = data.get('message_id')
            status = data.get('status')
            
            try:
                delivery = NotificationDelivery.objects.get(
                    recipient_address=message_id,
                    channel='PUSH'
                )
                
                if status == 'delivered':
                    delivery.mark_as_delivered()
                elif status == 'failed':
                    delivery.status = NotificationDelivery.Status.FAILED
                    delivery.failed_at = timezone.now()
                    delivery.failure_reason = data.get('reason', 'Push notification failed')
                    delivery.save()
                
                return JsonResponse({'status': 'success'})
                
            except NotificationDelivery.DoesNotExist:
                return JsonResponse(
                    {'status': 'error', 'message': 'Delivery record not found'},
                    status=400
                )
        
        else:
            return JsonResponse(
                {'status': 'error', 'message': 'Unknown webhook type'},
                status=400
            )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=500
        )


@login_required
@require_POST
def register_push_device(request):
    """Register a push device via AJAX"""
    try:
        data = json.loads(request.body)
        
        device_token = data.get('device_token')
        device_type = data.get('device_type', 'WEB')
        device_id = data.get('device_id')
        app_version = data.get('app_version')
        os_version = data.get('os_version')
        
        if not device_token:
            return JsonResponse(
                {'status': 'error', 'message': 'Device token is required'},
                status=400
            )
        
        # Check if device already exists
        device, created = PushDevice.objects.update_or_create(
            user=request.user,
            device_token=device_token,
            defaults={
                'device_type': device_type,
                'device_id': device_id,
                'app_version': app_version,
                'os_version': os_version,
                'is_active': True,
                'last_used_at': timezone.now()
            }
        )
        
        if not created:
            # Update existing device
            device.device_type = device_type
            device.device_id = device_id
            device.app_version = app_version
            device.os_version = os_version
            device.is_active = True
            device.last_used_at = timezone.now()
            device.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Device registered successfully',
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=500
        )


@login_required
@require_POST
def dismiss_system_notification(request):
    """Dismiss a system notification"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        
        if not notification_id:
            return JsonResponse(
                {'status': 'error', 'message': 'Notification ID is required'},
                status=400
            )
        
        try:
            notification = SystemNotification.objects.get(id=notification_id)
            
            # Create dismissal record
            SystemNotificationDismissal.objects.get_or_create(
                system_notification=notification,
                user=request.user
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Notification dismissed'
            })
            
        except SystemNotification.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Notification not found'},
                status=404
            )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid JSON'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=500
        )


@login_required
def notification_unsubscribe(request):
    """Handle notification unsubscribe requests"""
    if request.method == 'GET':
        # Show unsubscribe confirmation page
        token = request.GET.get('token')
        email = request.GET.get('email')
        
        return render(request, 'notifications/unsubscribe.html', {
            'token': token,
            'email': email
        })
    
    elif request.method == 'POST':
        try:
            # Process unsubscribe request
            token = request.POST.get('token')
            email = request.POST.get('email')
            
            # Here you would validate the token and update preferences
            # For now, we'll just show a success message
            
            messages.success(
                request,
                'You have been unsubscribed from notifications.'
            )
            
            return redirect('notifications:unsubscribe_success')
            
        except Exception as e:
            messages.error(
                request,
                f'Error processing unsubscribe request: {str(e)}'
            )
            
    return redirect('home')


def unsubscribe_success(request):
    """Show unsubscribe success page"""
    return render(request, 'notifications/unsubscribe_success.html')
