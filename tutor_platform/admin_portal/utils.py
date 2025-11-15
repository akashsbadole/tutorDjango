"""
Django Tutor Platform Admin Portal Utilities

This module contains utility functions for the admin portal including
data export, permission checking, and system monitoring.
"""

import json
import csv
import os
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models import Count, Sum, Avg, Q
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

# Import models
from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Award, Session
from messaging.models import Conversation, Message
from notifications.models import Notification
from paymentsdetails.models import Payment, EscrowAccount, Payout, Transaction
from .models import AdminProfile, AdminActivityLog


def log_admin_activity(admin, action_type, action_description, ip_address=None, 
                       user_agent=None, content_type=None, object_id=None, 
                       additional_data=None):
    """
    Log admin activity for audit trail
    
    Args:
        admin: User object who performed the action
        action_type: Type of action (CREATE, UPDATE, DELETE, etc.)
        action_description: Description of the action
        ip_address: IP address of the admin
        user_agent: User agent string
        content_type: ContentType of the object acted upon
        object_id: ID of the object acted upon
        additional_data: Additional data as dictionary
    """
    AdminActivityLog.objects.create(
        admin=admin,
        action_type=action_type,
        action_description=action_description,
        content_type=content_type,
        object_id=object_id,
        ip_address=ip_address,
        user_agent=user_agent,
        additional_data=additional_data or {}
    )


def check_permission(user, permission):
    """
    Check if user has a specific admin permission
    
    Args:
        user: User object to check
        permission: Permission string to check
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    # Check if user is superuser
    if user.is_superuser:
        return True
    
    # Check if user has admin profile
    if not hasattr(user, 'admin_profile'):
        return False
    
    # Check if user is super admin
    if user.admin_profile.is_super_admin:
        return True
    
    # Check role-based permission
    if user.admin_profile.role:
        return user.admin_profile.role.has_permission(permission)
    
    return False


def get_dashboard_stats():
    """
    Get dashboard statistics for admin portal
    
    Returns:
        dict: Dictionary containing dashboard statistics
    """
    # Cache the stats for 5 minutes to improve performance
    cache_key = 'admin_dashboard_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # User statistics
        stats = {
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'tutors': TutorProfile.objects.count(),
                'students': StudentProfile.objects.count(),
                'new_today': User.objects.filter(
                    date_joined__date=now().date()
                ).count(),
                'active_today': User.objects.filter(
                    last_login__date=now().date()
                ).count(),
            },
            'requirements': {
                'total': Requirement.objects.count(),
                'open': Requirement.objects.filter(status='OPEN').count(),
                'in_progress': Requirement.objects.filter(status='IN_PROGRESS').count(),
                'completed': Requirement.objects.filter(status='COMPLETED').count(),
                'new_today': Requirement.objects.filter(
                    created_at__date=now().date()
                ).count(),
            },
            'sessions': {
                'total': Session.objects.count(),
                'scheduled': Session.objects.filter(status='SCHEDULED').count(),
                'completed': Session.objects.filter(status='COMPLETED').count(),
                'upcoming': Session.objects.filter(
                    status='SCHEDULED',
                    scheduled_start__gte=now()
                ).count(),
                'today': Session.objects.filter(
                    scheduled_start__date=now().date()
                ).count(),
            },
            'payments': {
                'total': Payment.objects.count(),
                'completed': Payment.objects.filter(status='COMPLETED').count(),
                'pending': Payment.objects.filter(status='PENDING').count(),
                'failed': Payment.objects.filter(status='FAILED').count(),
                'total_amount': Payment.objects.filter(
                    status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'today_amount': Payment.objects.filter(
                    status='COMPLETED',
                    created_at__date=now().date()
                ).aggregate(total=Sum('amount'))['total'] or 0,
            },
            'communications': {
                'conversations': Conversation.objects.count(),
                'messages': Message.objects.count(),
                'messages_today': Message.objects.filter(
                    created_at__date=now().date()
                ).count(),
                'active_conversations': Conversation.objects.filter(
                    updated_at__gte=now() - timedelta(days=1)
                ).count(),
            },
            'notifications': {
                'total': Notification.objects.count(),
                'unread': Notification.objects.filter(is_read=False).count(),
                'sent_today': Notification.objects.filter(
                    created_at__date=now().date()
                ).count(),
            },
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
    
    return stats


def get_system_health():
    """
    Get system health information
    
    Returns:
        dict: Dictionary containing system health information
    """
    # Cache system health for 1 minute
    cache_key = 'admin_system_health'
    health = cache.get(cache_key)
    
    if health is None:
        health = {
            'database': {
                'status': 'healthy',  # Could be enhanced with actual DB health checks
                'connections': 'normal',
            },
            'storage': {
                'status': 'healthy',
                'usage': 'normal',  # Could check actual disk usage
            },
            'cache': {
                'status': 'healthy' if cache.get('health_check') else 'warning',
                'backend': 'Redis' if hasattr(cache, 'client') else 'Database',
            },
            'performance': {
                'response_time': 'good',  # Could measure actual response times
                'load': 'normal',
            },
            'services': {
                'email': 'healthy',  # Could check email service status
                'payments': 'healthy',  # Could check payment gateway status
            },
            'security': {
                'failed_logins': get_recent_failed_logins(),
                'active_sessions': AdminSession.objects.filter(
                    is_active=True,
                    expires_at__gt=now()
                ).count(),
            },
        }
        
        # Cache for 1 minute
        cache.set(cache_key, health, 60)
    
    return health


def get_recent_failed_logins(hours=24):
    """
    Get count of recent failed login attempts
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        int: Count of failed login attempts
    """
    # This would need to be implemented based on your login tracking
    # For now, return a placeholder
    return 0


def export_data_to_csv(export_type, filters=None):
    """
    Export data to CSV file
    
    Args:
        export_type: Type of data to export
        filters: Dictionary of filters to apply
        
    Returns:
        str: Path to the generated CSV file
    """
    filters = filters or {}
    timestamp = now().strftime('%Y%m%d_%H%M%S')
    filename = f"export_{export_type.lower()}_{timestamp}.csv"
    file_path = os.path.join(settings.MEDIA_ROOT, 'exports', filename)
    
    # Create exports directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    if export_type == 'USERS':
        queryset = get_filtered_users(filters)
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'is_active', 'date_joined', 'last_login']
        
    elif export_type == 'REQUIREMENTS':
        queryset = get_filtered_requirements(filters)
        fields = ['id', 'title', 'description', 'status', 'budget', 
                 'created_at', 'student__username']
        
    elif export_type == 'PAYMENTS':
        queryset = get_filtered_payments(filters)
        fields = ['id', 'amount', 'status', 'payment_method', 
                 'created_at', 'student__username', 'tutor__username']
        
    elif export_type == 'MESSAGES':
        queryset = get_filtered_messages(filters)
        fields = ['id', 'content', 'created_at', 'sender__username', 
                 'conversation__id']
        
    elif export_type == 'NOTIFICATIONS':
        queryset = get_filtered_notifications(filters)
        fields = ['id', 'title', 'message', 'is_read', 'created_at', 
                 'recipient__username']
        
    else:
        raise ValueError(f"Unsupported export type: {export_type}")
    
    # Write CSV file
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([field.replace('__', '.') for field in fields])
        
        # Write data rows
        for obj in queryset:
            row = []
            for field in fields:
                if '__' in field:
                    # Handle related fields
                    parts = field.split('__')
                    value = obj
                    for part in parts:
                        try:
                            value = getattr(value, part)
                        except AttributeError:
                            value = None
                            break
                else:
                    value = getattr(obj, field, None)
                
                # Format datetime objects
                if value is not None and hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif value is None:
                    value = ''
                
                row.append(value)
            writer.writerow(row)
    
    return file_path


def get_filtered_users(filters):
    """Get filtered user queryset for export"""
    queryset = User.objects.select_related('admin_profile')
    
    if filters.get('search'):
        search = filters['search']
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if filters.get('user_type') == 'tutor':
        queryset = queryset.filter(tutorprofile__isnull=False)
    elif filters.get('user_type') == 'student':
        queryset = queryset.filter(studentprofile__isnull=False)
    elif filters.get('user_type') == 'admin':
        queryset = queryset.filter(admin_profile__isnull=False)
    
    if filters.get('status') == 'active':
        queryset = queryset.filter(is_active=True)
    elif filters.get('status') == 'inactive':
        queryset = queryset.filter(is_active=False)
    
    if filters.get('date_from'):
        queryset = queryset.filter(date_joined__date__gte=filters['date_from'])
    
    if filters.get('date_to'):
        queryset = queryset.filter(date_joined__date__lte=filters['date_to'])
    
    return queryset


def get_filtered_requirements(filters):
    """Get filtered requirement queryset for export"""
    queryset = Requirement.objects.select_related('student')
    
    if filters.get('search'):
        search = filters['search']
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    if filters.get('status'):
        queryset = queryset.filter(status=filters['status'])
    
    if filters.get('subject'):
        queryset = queryset.filter(subject__icontains=filters['subject'])
    
    if filters.get('budget_min'):
        queryset = queryset.filter(budget__gte=filters['budget_min'])
    
    if filters.get('budget_max'):
        queryset = queryset.filter(budget__lte=filters['budget_max'])
    
    if filters.get('date_from'):
        queryset = queryset.filter(created_at__date__gte=filters['date_from'])
    
    if filters.get('date_to'):
        queryset = queryset.filter(created_at__date__lte=filters['date_to'])
    
    return queryset


def get_filtered_payments(filters):
    """Get filtered payment queryset for export"""
    queryset = Payment.objects.select_related('student', 'tutor')
    
    if filters.get('search'):
        search = filters['search']
        queryset = queryset.filter(
            Q(transaction_id__icontains=search) |
            Q(student__username__icontains=search) |
            Q(tutor__username__icontains=search)
        )
    
    if filters.get('status'):
        queryset = queryset.filter(status=filters['status'])
    
    if filters.get('payment_method'):
        queryset = queryset.filter(payment_method=filters['payment_method'])
    
    if filters.get('amount_min'):
        queryset = queryset.filter(amount__gte=filters['amount_min'])
    
    if filters.get('amount_max'):
        queryset = queryset.filter(amount__lte=filters['amount_max'])
    
    if filters.get('date_from'):
        queryset = queryset.filter(created_at__date__gte=filters['date_from'])
    
    if filters.get('date_to'):
        queryset = queryset.filter(created_at__date__lte=filters['date_to'])
    
    return queryset


def get_filtered_messages(filters):
    """Get filtered message queryset for export"""
    queryset = Message.objects.select_related('sender', 'conversation')
    
    if filters.get('search'):
        search = filters['search']
        queryset = queryset.filter(
            Q(content__icontains=search) |
            Q(sender__username__icontains=search)
        )
    
    if filters.get('date_from'):
        queryset = queryset.filter(created_at__date__gte=filters['date_from'])
    
    if filters.get('date_to'):
        queryset = queryset.filter(created_at__date__lte=filters['date_to'])
    
    if filters.get('has_attachments'):
        queryset = queryset.filter(attachments__isnull=False).distinct()
    
    return queryset


def get_filtered_notifications(filters):
    """Get filtered notification queryset for export"""
    queryset = Notification.objects.select_related('recipient')
    
    if filters.get('date_from'):
        queryset = queryset.filter(created_at__date__gte=filters['date_from'])
    
    if filters.get('date_to'):
        queryset = queryset.filter(created_at__date__lte=filters['date_to'])
    
    if filters.get('is_read') is not None:
        queryset = queryset.filter(is_read=filters['is_read'])
    
    return queryset


def bulk_update_users(user_ids, action, admin_user):
    """
    Perform bulk updates on users
    
    Args:
        user_ids: List of user IDs to update
        action: Action to perform ('activate', 'deactivate', 'delete')
        admin_user: Admin user performing the action
        
    Returns:
        tuple: (success_count, error_message)
    """
    try:
        users = User.objects.filter(id__in=user_ids)
        count = 0
        
        if action == 'activate':
            count = users.update(is_active=True)
            action_description = f"Activated {count} users"
        elif action == 'deactivate':
            count = users.update(is_active=False)
            action_description = f"Deactivated {count} users"
        elif action == 'delete':
            # Soft delete by setting is_active=False
            count = users.update(is_active=False)
            action_description = f"Soft deleted {count} users"
        else:
            return 0, "Invalid action"
        
        # Log the action
        log_admin_activity(
            admin=admin_user,
            action_type='BULK_ACTION',
            action_description=action_description,
            additional_data={'action': action, 'user_ids': user_ids}
        )
        
        return count, None
        
    except Exception as e:
        return 0, str(e)


def generate_system_report():
    """
    Generate comprehensive system report
    
    Returns:
        dict: Dictionary containing system report data
    """
    report = {
        'generated_at': now().isoformat(),
        'users': {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'tutors': TutorProfile.objects.count(),
            'students': StudentProfile.objects.count(),
            'new_this_month': User.objects.filter(
                date_joined__gte=now() - timedelta(days=30)
            ).count(),
        },
        'requirements': {
            'total': Requirement.objects.count(),
            'open': Requirement.objects.filter(status='OPEN').count(),
            'in_progress': Requirement.objects.filter(status='IN_PROGRESS').count(),
            'completed': Requirement.objects.filter(status='COMPLETED').count(),
            'new_this_month': Requirement.objects.filter(
                created_at__gte=now() - timedelta(days=30)
            ).count(),
        },
        'sessions': {
            'total': Session.objects.count(),
            'completed': Session.objects.filter(status='COMPLETED').count(),
            'upcoming': Session.objects.filter(
                status='SCHEDULED',
                scheduled_start__gte=now()
            ).count(),
            'this_month': Session.objects.filter(
                scheduled_start__gte=now() - timedelta(days=30),
                scheduled_start__lte=now()
            ).count(),
        },
        'payments': {
            'total': Payment.objects.count(),
            'completed': Payment.objects.filter(status='COMPLETED').count(),
            'total_revenue': Payment.objects.filter(
                status='COMPLETED'
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'this_month_revenue': Payment.objects.filter(
                status='COMPLETED',
                created_at__gte=now() - timedelta(days=30)
            ).aggregate(total=Sum('amount'))['total'] or 0,
        },
        'communications': {
            'total_conversations': Conversation.objects.count(),
            'total_messages': Message.objects.count(),
            'messages_this_month': Message.objects.filter(
                created_at__gte=now() - timedelta(days=30)
            ).count(),
        },
    }
    
    return report


# Import AdminSession for get_system_health function
from .models import AdminSession