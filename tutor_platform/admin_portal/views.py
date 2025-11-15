"""
Django Tutor Platform Admin Portal Views

This module contains views for the admin portal including dashboard,
user management, and system monitoring.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now, timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.conf import settings
import json
import csv
from datetime import datetime, date
from collections import defaultdict

# Import models from other apps
from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Award, Session
from messaging.models import Conversation, Message
from notifications.models import Notification
from paymentsdetails.models import Payment, EscrowAccount, Payout, Transaction

# Import admin portal models
from .models import (
    AdminProfile, AdminActivityLog, SystemSetting, 
    AdminSession, DataExport, AdminRole
)
from .forms import AdminProfileForm, SystemSettingForm, BulkActionForm
from .utils import (
    get_dashboard_stats, log_admin_activity, export_data_to_csv,
    get_system_health, check_permission
)


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Main admin dashboard view"""
    
    template_name = 'admin_portal/dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has admin profile
        if not hasattr(request.user, 'admin_profile'):
            messages.error(request, _("You don't have admin privileges."))
            return redirect('admin_portal:access_denied')
        
        # Log admin access
        log_admin_activity(
            admin=request.user,
            action_type='VIEW',
            action_description=_('Accessed admin dashboard'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dashboard statistics
        context.update(get_dashboard_stats())
        
        # Get recent activities
        context['recent_activities'] = AdminActivityLog.objects.select_related(
            'admin'
        ).order_by('-timestamp')[:10]
        
        # Get system health
        context['system_health'] = get_system_health()
        
        # Get active sessions
        context['active_sessions'] = AdminSession.objects.filter(
            is_active=True,
            expires_at__gt=now()
        ).select_related('admin').count()
        
        return context


class UserManagementView(LoginRequiredMixin, ListView):
    """User management dashboard view"""
    
    model = User
    template_name = 'admin_portal/user_management.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'user_management'):
            messages.error(request, _("You don't have permission to access user management."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = User.objects.select_related('admin_profile').all()
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        user_type = self.request.GET.get('user_type')
        if user_type == 'tutor':
            queryset = queryset.filter(tutorprofile__isnull=False)
        elif user_type == 'student':
            queryset = queryset.filter(studentprofile__isnull=False)
        elif user_type == 'admin':
            queryset = queryset.filter(admin_profile__isnull=False)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user statistics
        context['user_stats'] = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'tutors': TutorProfile.objects.count(),
            'students': StudentProfile.objects.count(),
            'admins': AdminProfile.objects.count(),
        }
        
        # Add filter parameters to context
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'user_type': self.request.GET.get('user_type', ''),
            'status': self.request.GET.get('status', ''),
        }
        
        return context


class RequirementManagementView(LoginRequiredMixin, ListView):
    """Requirement management dashboard view"""
    
    model = Requirement
    template_name = 'admin_portal/requirement_management.html'
    context_object_name = 'requirements'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'requirement_management'):
            messages.error(request, _("You don't have permission to access requirement management."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Requirement.objects.select_related('student').prefetch_related('proposals')
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(student__username__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        subject = self.request.GET.get('subject')
        if subject:
            queryset = queryset.filter(subject=subject)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get requirement statistics
        context['requirement_stats'] = {
            'total_requirements': Requirement.objects.count(),
            'open_requirements': Requirement.objects.filter(status='OPEN').count(),
            'in_progress': Requirement.objects.filter(status='IN_PROGRESS').count(),
            'completed': Requirement.objects.filter(status='COMPLETED').count(),
            'cancelled': Requirement.objects.filter(status='CANCELLED').count(),
            'total_proposals': Proposal.objects.count(),
            'pending_proposals': Proposal.objects.filter(status='PENDING').count(),
        }
        
        # Add filter parameters to context
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'subject': self.request.GET.get('subject', ''),
        }
        
        return context


class PaymentEscrowView(LoginRequiredMixin, TemplateView):
    """Payment and escrow management dashboard view"""
    
    template_name = 'admin_portal/payment_escrow.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'payment_management'):
            messages.error(request, _("You don't have permission to access payment management."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get payment statistics
        context['payment_stats'] = {
            'total_payments': Payment.objects.count(),
            'completed_payments': Payment.objects.filter(status='COMPLETED').count(),
            'pending_payments': Payment.objects.filter(status='PENDING').count(),
            'failed_payments': Payment.objects.filter(status='FAILED').count(),
            'total_amount': Payment.objects.filter(status='COMPLETED').aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'total_escrow': EscrowAccount.objects.aggregate(
                total=Sum('balance')
            )['total'] or 0,
            'pending_payouts': Payout.objects.filter(status='PENDING').count(),
        }
        
        # Get recent payments
        context['recent_payments'] = Payment.objects.select_related(
            'student', 'tutor'
        ).order_by('-created_at')[:10]
        
        # Get pending payouts
        context['pending_payouts_list'] = Payout.objects.filter(
            status='PENDING'
        ).select_related('tutor').order_by('-created_at')[:10]
        
        return context


class CommunicationMonitoringView(LoginRequiredMixin, ListView):
    """Communication monitoring dashboard view"""
    
    model = Message
    template_name = 'admin_portal/communication_monitoring.html'
    context_object_name = 'messages'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'communication_monitoring'):
            messages.error(request, _("You don't have permission to access communication monitoring."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Message.objects.select_related(
            'sender', 'conversation'
        ).order_by('-created_at')
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) |
                Q(sender__username__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get communication statistics
        context['communication_stats'] = {
            'total_conversations': Conversation.objects.count(),
            'total_messages': Message.objects.count(),
            'messages_today': Message.objects.filter(
                created_at__date=now().date()
            ).count(),
            'messages_this_week': Message.objects.filter(
                created_at__gte=now() - timedelta(days=7)
            ).count(),
            'active_conversations': Conversation.objects.filter(
                updated_at__gte=now() - timedelta(days=1)
            ).count(),
        }
        
        # Add filter parameters to context
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        }
        
        return context


class SystemAnalyticsView(LoginRequiredMixin, TemplateView):
    """System health and analytics dashboard view"""
    
    template_name = 'admin_portal/system_analytics.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'system_analytics'):
            messages.error(request, _("You don't have permission to access system analytics."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get system health
        context['system_health'] = get_system_health()
        
        # Get user activity over time (last 30 days)
        context['user_activity'] = []
        for i in range(30):
            date = now().date() - timedelta(days=i)
            context['user_activity'].append({
                'date': date.isoformat(),
                'new_users': User.objects.filter(date_joined__date=date).count(),
                'active_users': User.objects.filter(
                    last_login__date=date
                ).count(),
            })
        context['user_activity'].reverse()
        
        # Get payment trends (last 30 days)
        context['payment_trends'] = []
        for i in range(30):
            date = now().date() - timedelta(days=i)
            context['payment_trends'].append({
                'date': date.isoformat(),
                'payments': Payment.objects.filter(
                    created_at__date=date,
                    status='COMPLETED'
                ).count(),
                'amount': Payment.objects.filter(
                    created_at__date=date,
                    status='COMPLETED'
                ).aggregate(total=Sum('amount'))['total'] or 0,
            })
        context['payment_trends'].reverse()
        
        # Get platform statistics
        context['platform_stats'] = {
            'total_users': User.objects.count(),
            'total_requirements': Requirement.objects.count(),
            'total_sessions': Session.objects.count(),
            'total_payments': Payment.objects.count(),
            'total_messages': Message.objects.count(),
            'total_notifications': Notification.objects.count(),
        }
        
        return context


class DataExportView(LoginRequiredMixin, FormView):
    """Data export view"""
    
    template_name = 'admin_portal/data_export.html'
    form_class = BulkActionForm
    success_url = reverse_lazy('admin_portal:data_export')
    
    def dispatch(self, request, *args, **kwargs):
        if not check_permission(request.user, 'data_export'):
            messages.error(request, _("You don't have permission to export data."))
            return redirect('admin_portal:access_denied')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        export_type = form.cleaned_data['export_type']
        filters = form.cleaned_data.get('filters', {})
        
        # Create export record
        export_record = DataExport.objects.create(
            admin=self.request.user,
            export_type=export_type,
            filters=filters,
            expires_at=now() + timedelta(days=7)
        )
        
        # Process export in background (simplified for this example)
        try:
            file_path = export_data_to_csv(export_type, filters)
            export_record.file_path = file_path
            export_record.status = 'COMPLETED'
            export_record.completed_at = now()
            export_record.save()
            
            messages.success(
                self.request, 
                f"Export completed successfully. File will be available for 7 days."
            )
        except Exception as e:
            export_record.status = 'FAILED'
            export_record.error_message = str(e)
            export_record.save()
            
            messages.error(
                self.request, 
                f"Export failed: {str(e)}"
            )
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get recent exports
        context['recent_exports'] = DataExport.objects.filter(
            admin=self.request.user
        ).order_by('-created_at')[:10]
        
        return context


class AccessDeniedView(TemplateView):
    """Access denied view"""
    
    template_name = 'admin_portal/access_denied.html'


@login_required
def bulk_user_action(request):
    """Handle bulk user actions"""
    if not check_permission(request.user, 'user_management'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    action = request.POST.get('action')
    user_ids = request.POST.getlist('user_ids')
    
    if not action or not user_ids:
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
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
            # Soft delete by setting is_active=False and adding a flag
            count = users.update(is_active=False)
            action_description = f"Deleted {count} users"
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Log admin activity
        log_admin_activity(
            admin=request.user,
            action_type='BULK_ACTION',
            action_description=action_description,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            additional_data={'action': action, 'user_ids': user_ids}
        )
        
        return JsonResponse({
            'success': True,
            'message': f"{action_description}",
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_chart_data(request):
    """Get chart data for dashboard"""
    if not check_permission(request.user, 'dashboard'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    chart_type = request.GET.get('type')
    period = request.GET.get('period', '7d')
    
    try:
        if chart_type == 'user_growth':
            data = get_user_growth_data(period)
        elif chart_type == 'payment_trends':
            data = get_payment_trends_data(period)
        elif chart_type == 'activity_stats':
            data = get_activity_stats_data(period)
        else:
            return JsonResponse({'error': 'Invalid chart type'}, status=400)
        
        return JsonResponse({'data': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions for chart data
def get_user_growth_data(period):
    """Get user growth data for charts"""
    days = 30 if period == '30d' else 7 if period == '7d' else 1
    data = []
    
    for i in range(days):
        date = now().date() - timedelta(days=i)
        data.append({
            'date': date.isoformat(),
            'users': User.objects.filter(date_joined__date=date).count(),
        })
    
    return list(reversed(data))


def get_payment_trends_data(period):
    """Get payment trends data for charts"""
    days = 30 if period == '30d' else 7 if period == '7d' else 1
    data = []
    
    for i in range(days):
        date = now().date() - timedelta(days=i)
        payments = Payment.objects.filter(
            created_at__date=date,
            status='COMPLETED'
        )
        data.append({
            'date': date.isoformat(),
            'count': payments.count(),
            'amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
        })
    
    return list(reversed(data))


def get_activity_stats_data(period):
    """Get activity statistics data for charts"""
    days = 30 if period == '30d' else 7 if period == '7d' else 1
    data = []
    
    for i in range(days):
        date = now().date() - timedelta(days=i)
        data.append({
            'date': date.isoformat(),
            'messages': Message.objects.filter(created_at__date=date).count(),
            'requirements': Requirement.objects.filter(created_at__date=date).count(),
            'sessions': Session.objects.filter(created_at__date=date).count(),
        })
    
    return list(reversed(data))