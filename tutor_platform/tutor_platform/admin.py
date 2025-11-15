"""
Django Tutor Platform Admin Site Customization

This module provides customizations for the Django admin interface,
including site branding, navigation, and dashboard enhancements.
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.utils.timezone import now, timedelta

# Import models
from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Award, Session
from messaging.models import Conversation, Message
from notifications.models import Notification
from paymentsdetails.models import Payment, EscrowAccount, Payout


class TutorPlatformAdminSite(AdminSite):
    """Custom admin site for Django Tutor Platform"""
    
    site_header = _("Django Tutor Platform")
    site_title = _("Django Tutor Platform Admin")
    index_title = _("Dashboard")
    site_url = "/"
    
    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all installed apps that have been
        registered in this site.
        """
        app_dict = self._build_app_dict(request)
        
        # Sort the apps alphabetically by their verbose_name
        app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
        
        # Reorder apps to put the most important ones first
        priority_order = [
            'accounts', 'requirements', 'paymentsdetails', 
            'messaging', 'notifications', 'auth'
        ]
        
        # Create a new ordered list
        ordered_app_list = []
        
        # Add apps in priority order
        for app_name in priority_order:
            for app in app_list:
                if app['app_label'] == app_name:
                    ordered_app_list.append(app)
                    break
        
        # Add any remaining apps
        for app in app_list:
            if app not in ordered_app_list:
                ordered_app_list.append(app)
        
        return ordered_app_list
    
    def index(self, request, extra_context=None):
        """Custom admin dashboard with statistics"""
        extra_context = extra_context or {}
        
        # Calculate dashboard statistics
        stats = {}
        
        # User statistics
        stats['total_users'] = User.objects.count()
        stats['total_tutors'] = TutorProfile.objects.count()
        stats['total_students'] = StudentProfile.objects.count()
        stats['active_users'] = User.objects.filter(
            last_login__gte=now() - timedelta(days=30)
        ).count()
        
        # Requirements statistics
        stats['total_requirements'] = Requirement.objects.count()
        stats['open_requirements'] = Requirement.objects.filter(
            status='OPEN'
        ).count()
        stats['total_proposals'] = Proposal.objects.count()
        stats['pending_proposals'] = Proposal.objects.filter(
            status='PENDING'
        ).count()
        
        # Session statistics
        stats['total_sessions'] = Session.objects.count()
        stats['upcoming_sessions'] = Session.objects.filter(
            status='SCHEDULED',
            scheduled_start__gte=now()
        ).count()
        
        # Payment statistics
        stats['total_payments'] = Payment.objects.count()
        stats['completed_payments'] = Payment.objects.filter(
            status='COMPLETED'
        ).count()
        stats['pending_payouts'] = Payout.objects.filter(
            status='PENDING'
        ).count()
        
        # Messaging statistics
        stats['total_conversations'] = Conversation.objects.count()
        stats['total_messages'] = Message.objects.count()
        stats['recent_messages'] = Message.objects.filter(
            created_at__gte=now() - timedelta(days=7)
        ).count()
        
        # Notification statistics
        stats['total_notifications'] = Notification.objects.count()
        stats['unread_notifications'] = Notification.objects.filter(
            is_read=False
        ).count()
        
        extra_context['stats'] = stats
        
        return super().index(request, extra_context)


# Create custom admin site instance
admin_site = TutorPlatformAdminSite(name='tutor_platform_admin')


# Import admin classes
from accounts.admin import UserAdmin, StudentProfileAdmin, TutorProfileAdmin
from requirements.admin import RequirementAdmin, ProposalAdmin, AwardAdmin, SessionAdmin
from messaging.admin import ConversationAdmin, MessageAdmin
from notifications.admin import NotificationAdmin
from paymentsdetails.admin import PaymentAdmin, EscrowAccountAdmin, PayoutAdmin

# Register all models with the custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(StudentProfile, StudentProfileAdmin)
admin_site.register(TutorProfile, TutorProfileAdmin)

admin_site.register(Requirement, RequirementAdmin)
admin_site.register(Proposal, ProposalAdmin)
admin_site.register(Award, AwardAdmin)
admin_site.register(Session, SessionAdmin)

admin_site.register(Conversation, ConversationAdmin)
admin_site.register(Message, MessageAdmin)

admin_site.register(Notification, NotificationAdmin)

admin_site.register(Payment, PaymentAdmin)
admin_site.register(EscrowAccount, EscrowAccountAdmin)
admin_site.register(Payout, PayoutAdmin)


# Customize the default admin site as well
admin.site.site_header = _("Django Tutor Platform")
admin.site.site_title = _("Django Tutor Platform Admin")
admin.site.index_title = _("Dashboard")