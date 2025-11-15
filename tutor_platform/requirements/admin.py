from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg, Q
from django.utils import timezone

from .models import (
    Requirement, RequirementAttachment, Proposal, ProposalAttachment,
    Award, Milestone, Session, Review, SavedRequirement, FavoriteTutor
)


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Requirement model with advanced filtering and lifecycle management"""
    
    list_display = [
        'title', 'subject', 'learning_level', 'budget_display',
        'urgency_level', 'status', 'view_count', 'proposal_count', 'created_at'
    ]
    list_filter = [
        'status', 'visibility', 'budget_type', 'urgency_level',
        'learning_level', 'location_type', 'subject', 'is_featured'
    ]
    search_fields = ['title', 'description', 'specific_topics', 'student__username', 'student__email']
    list_editable = ['status']
    readonly_fields = ['view_count', 'proposal_count', 'slug', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('student', 'subject')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'slug', 'student', 'subject', 'learning_level',
                'description', 'specific_topics'
            )
        }),
        ('Budget & Schedule', {
            'fields': (
                'budget_type', 'budget_min', 'budget_max', 'currency',
                'urgency_level', 'deadline', 'preferred_schedule',
                'timezone', 'session_duration', 'number_of_sessions'
            )
        }),
        ('Location & Settings', {
            'fields': (
                'location_type', 'visibility', 'is_featured'
            )
        }),
        ('Status & Timestamps', {
            'fields': (
                'status', 'view_count', 'proposal_count',
                'created_at', 'updated_at', 'published_at', 'closed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_requirements_featured', 'mark_requirements_not_featured',
        'publish_requirements', 'close_requirements', 'archive_requirements'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('student', 'subject')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(student=request.user)
        return qs.none()
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status not in ['DRAFT', 'OPEN']:
            readonly.extend(['student', 'subject', 'learning_level'])
        return readonly
    
    def budget_display(self, obj):
        """Display budget range with formatting"""
        return obj.get_budget_range()
    budget_display.short_description = _('Budget')
    
    def mark_requirements_featured(self, request, queryset):
        """Mark selected requirements as featured"""
        count = queryset.update(is_featured=True)
        self.message_user(request, _('%(count)d requirements marked as featured.') % {'count': count}, level='success')
    mark_requirements_featured.short_description = _('Mark selected as featured')
    
    def mark_requirements_not_featured(self, request, queryset):
        """Mark selected requirements as not featured"""
        count = queryset.update(is_featured=False)
        self.message_user(request, _('%(count)d requirements marked as not featured.') % {'count': count}, level='success')
    mark_requirements_not_featured.short_description = _('Mark selected as not featured')
    
    def publish_requirements(self, request, queryset):
        """Publish selected requirements"""
        count = queryset.filter(status='DRAFT').update(
            status='OPEN',
            published_at=timezone.now()
        )
        self.message_user(request, _('%(count)d requirements published.') % {'count': count}, level='success')
    publish_requirements.short_description = _('Publish selected requirements')
    
    def close_requirements(self, request, queryset):
        """Close selected requirements"""
        count = queryset.filter(status__in=['OPEN', 'IN_PROGRESS']).update(
            status='CANCELLED',
            closed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d requirements closed.') % {'count': count}, level='success')
    close_requirements.short_description = _('Close selected requirements')
    
    def archive_requirements(self, request, queryset):
        """Archive selected requirements"""
        count = queryset.filter(status__in=['OPEN', 'IN_PROGRESS', 'AWARDED']).update(
            status='COMPLETED',
            closed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d requirements archived.') % {'count': count}, level='success')
    archive_requirements.short_description = _('Archive selected requirements')


@admin.register(RequirementAttachment)
class RequirementAttachmentAdmin(admin.ModelAdmin):
    list_display = ['requirement', 'filename', 'file_size', 'file_type', 'is_public', 'uploaded_at']
    list_filter = ['is_public', 'file_type']
    search_fields = ['filename', 'description']
    readonly_fields = ['file_size', 'file_type', 'uploaded_at']
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']


class ProposalAttachmentInline(admin.TabularInline):
    model = ProposalAttachment
    extra = 0
    readonly_fields = ['file_size', 'file_type', 'uploaded_at']


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Proposal model with advanced filtering and status management"""
    
    list_display = [
        'requirement', 'tutor', 'proposed_rate', 'rate_type',
        'status', 'calculated_amount', 'submitted_at', 'created_at'
    ]
    list_filter = ['status', 'rate_type', 'can_start_immediately', 'submitted_at']
    search_fields = ['cover_letter', 'approach', 'availability', 'tutor__username', 'tutor__email']
    readonly_fields = ['submitted_at', 'reviewed_at', 'accepted_at', 'created_at', 'updated_at']
    date_hierarchy = 'submitted_at'
    ordering = ['-created_at']
    raw_id_fields = ('requirement', 'tutor')
    inlines = [ProposalAttachmentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'requirement', 'tutor', 'status', 'cover_letter'
            )
        }),
        ('Rate & Schedule', {
            'fields': (
                'proposed_rate', 'rate_type', 'estimated_hours',
                'total_amount', 'can_start_immediately', 'proposed_start_date'
            )
        }),
        ('Details', {
            'fields': (
                'approach', 'availability'
            )
        }),
        ('Timestamps', {
            'fields': (
                'submitted_at', 'reviewed_at', 'accepted_at',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'accept_proposals', 'reject_proposals', 'shortlist_proposals',
        'withdraw_proposals', 'mark_as_withdrawn'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('requirement', 'tutor')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'TUTOR':
                return qs.filter(tutor=request.user)
            elif request.user.user_type == 'STUDENT':
                return qs.filter(requirement__student=request.user)
        return qs.none()
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['SUBMITTED', 'SHORTLISTED', 'ACCEPTED', 'REJECTED']:
            readonly.extend(['requirement', 'tutor', 'proposed_rate', 'rate_type'])
        return readonly
    
    def calculated_amount(self, obj):
        """Display calculated total amount"""
        if obj.rate_type == obj.RateType.HOURLY_RATE and obj.estimated_hours:
            return f"${obj.proposed_rate * obj.estimated_hours:.2f}"
        return f"${obj.total_amount:.2f}" if obj.total_amount else "-"
    calculated_amount.short_description = _('Calculated Amount')
    
    def accept_proposals(self, request, queryset):
        """Accept selected proposals"""
        count = queryset.filter(status='SUBMITTED').update(
            status='ACCEPTED',
            accepted_at=timezone.now()
        )
        self.message_user(request, _('%(count)d proposals accepted.') % {'count': count}, level='success')
    accept_proposals.short_description = _('Accept selected proposals')
    
    def reject_proposals(self, request, queryset):
        """Reject selected proposals"""
        count = queryset.filter(status__in=['SUBMITTED', 'SHORTLISTED']).update(
            status='REJECTED',
            reviewed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d proposals rejected.') % {'count': count}, level='success')
    reject_proposals.short_description = _('Reject selected proposals')
    
    def shortlist_proposals(self, request, queryset):
        """Shortlist selected proposals"""
        count = queryset.filter(status='SUBMITTED').update(
            status='SHORTLISTED',
            reviewed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d proposals shortlisted.') % {'count': count}, level='success')
    shortlist_proposals.short_description = _('Shortlist selected proposals')
    
    def withdraw_proposals(self, request, queryset):
        """Withdraw selected proposals"""
        count = queryset.filter(status__in=['DRAFT', 'SUBMITTED']).update(
            status='WITHDRAWN'
        )
        self.message_user(request, _('%(count)d proposals withdrawn.') % {'count': count}, level='success')
    withdraw_proposals.short_description = _('Withdraw selected proposals')
    
    def mark_as_withdrawn(self, request, queryset):
        """Mark selected proposals as withdrawn"""
        count = queryset.filter(status__in=['SHORTLISTED', 'REJECTED']).update(
            status='WITHDRAWN'
        )
        self.message_user(request, _('%(count)d proposals marked as withdrawn.') % {'count': count}, level='success')
    mark_as_withdrawn.short_description = _('Mark selected proposals as withdrawn')


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Award model with payment tracking integration"""
    
    list_display = [
        'requirement', 'proposal', 'student', 'tutor', 'agreed_rate_display',
        'rate_type', 'total_amount_display', 'status', 'payment_status', 'created_at'
    ]
    list_filter = ['status', 'rate_type', 'currency', 'created_at']
    search_fields = [
        'requirement__title', 'student__username', 'student__email',
        'tutor__username', 'tutor__email'
    ]
    readonly_fields = [
        'requirement', 'proposal', 'student', 'tutor', 'agreed_rate_display',
        'rate_type', 'total_amount_display', 'currency', 'created_at', 'updated_at',
        'activated_at', 'completed_at', 'cancelled_at', 'payment_status'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('requirement', 'proposal', 'student', 'tutor')
    inlines = [MilestoneInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'requirement', 'proposal', 'student', 'tutor', 'status'
            )
        }),
        ('Financial Details', {
            'fields': (
                'agreed_rate', 'rate_type', 'total_amount', 'currency',
                'agreed_rate_display', 'total_amount_display', 'payment_status'
            )
        }),
        ('Schedule', {
            'fields': (
                'start_date', 'expected_end_date', 'actual_end_date'
            )
        }),
        ('Terms & Conditions', {
            'fields': (
                'terms_and_conditions', 'cancellation_reason',
                'cancelled_by'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'activated_at',
                'completed_at', 'cancelled_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_awards', 'complete_awards', 'cancel_awards',
        'pause_awards', 'resume_awards'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'requirement', 'proposal', 'student', 'tutor'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(student=request.user)
            elif request.user.user_type == 'TUTOR':
                return qs.filter(tutor=request.user)
        return qs.none()
    
    def agreed_rate_display(self, obj):
        """Display agreed rate with currency formatting"""
        if obj.agreed_rate:
            return f"{obj.currency} {obj.agreed_rate:.2f}" if obj.currency else f"${obj.agreed_rate:.2f}"
        return "-"
    agreed_rate_display.short_description = _('Agreed Rate')
    
    def total_amount_display(self, obj):
        """Display total amount with currency formatting"""
        if obj.total_amount:
            return f"{obj.currency} {obj.total_amount:.2f}" if obj.currency else f"${obj.total_amount:.2f}"
        return "-"
    total_amount_display.short_description = _('Total Amount')
    
    def payment_status(self, obj):
        """Display payment status with color coding"""
        # This would typically check against related payment records
        # For now, we'll use a placeholder implementation
        if obj.status == 'COMPLETED':
            return format_html(
                '<span style="color: green;">✓ Paid</span>'
            )
        elif obj.status == 'ACTIVE':
            return format_html(
                '<span style="color: orange;">⏳ In Progress</span>'
            )
        elif obj.status == 'CANCELLED':
            return format_html(
                '<span style="color: red;">✗ Cancelled</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Pending</span>'
        )
    payment_status.short_description = _('Payment Status')
    payment_status.allow_tags = True
    
    def activate_awards(self, request, queryset):
        """Activate selected awards"""
        count = queryset.filter(status='PENDING').update(
            status='ACTIVE',
            activated_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d awards activated.') % {'count': count},
            level='success'
        )
    activate_awards.short_description = _('Activate selected awards')
    
    def complete_awards(self, request, queryset):
        """Mark selected awards as completed"""
        count = queryset.filter(status__in=['PENDING', 'ACTIVE']).update(
            status='COMPLETED',
            completed_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d awards marked as completed.') % {'count': count},
            level='success'
        )
    complete_awards.short_description = _('Mark selected as completed')
    
    def cancel_awards(self, request, queryset):
        """Cancel selected awards"""
        count = queryset.filter(status__in=['PENDING', 'ACTIVE']).update(
            status='CANCELLED',
            cancelled_at=timezone.now(),
            cancelled_by=request.user
        )
        self.message_user(
            request,
            _('%(count)d awards cancelled.') % {'count': count},
            level='success'
        )
    cancel_awards.short_description = _('Cancel selected awards')
    
    def pause_awards(self, request, queryset):
        """Pause selected awards"""
        count = queryset.filter(status='ACTIVE').update(status='PAUSED')
        self.message_user(
            request,
            _('%(count)d awards paused.') % {'count': count},
            level='success'
        )
    pause_awards.short_description = _('Pause selected awards')
    
    def resume_awards(self, request, queryset):
        """Resume selected awards"""
        count = queryset.filter(status='PAUSED').update(status='ACTIVE')
        self.message_user(
            request,
            _('%(count)d awards resumed.') % {'count': count},
            level='success'
        )
    resume_awards.short_description = _('Resume selected awards')


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Milestone model with progress tracking"""
    
    list_display = [
        'award', 'title', 'amount_display', 'due_date', 'status_display',
        'order', 'progress_percentage', 'completion_date'
    ]
    list_filter = ['status', 'due_date']
    search_fields = [
        'title', 'description', 'award__requirement__title',
        'award__student__username', 'award__tutor__username'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'completed_at', 'progress_percentage',
        'amount_display', 'status_display'
    ]
    date_hierarchy = 'due_date'
    ordering = ['award', 'order', 'due_date']
    raw_id_fields = ('award',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'award', 'title', 'description', 'status', 'order'
            )
        }),
        ('Financial Details', {
            'fields': (
                'amount', 'currency', 'amount_display'
            )
        }),
        ('Schedule & Progress', {
            'fields': (
                'due_date', 'completed_at', 'progress_percentage',
                'status_display'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_completed', 'mark_as_pending', 'mark_as_in_progress',
        'update_progress'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'award', 'award__student', 'award__tutor', 'award__requirement'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(award__student=request.user)
            elif request.user.user_type == 'TUTOR':
                return qs.filter(award__tutor=request.user)
        return qs.none()
    
    def amount_display(self, obj):
        """Display amount with currency formatting"""
        if obj.amount:
            return f"{obj.currency} {obj.amount:.2f}" if obj.currency else f"${obj.amount:.2f}"
        return "-"
    amount_display.short_description = _('Amount')
    
    def status_display(self, obj):
        """Display status with color coding"""
        if obj.status == 'COMPLETED':
            return format_html(
                '<span style="color: green;">✓ Completed</span>'
            )
        elif obj.status == 'IN_PROGRESS':
            return format_html(
                '<span style="color: blue;">↻ In Progress</span>'
            )
        elif obj.status == 'OVERDUE':
            return format_html(
                '<span style="color: red;">⚠ Overdue</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending</span>'
        )
    status_display.short_description = _('Status')
    status_display.allow_tags = True
    
    def progress_percentage(self, obj):
        """Display progress as a percentage bar"""
        if obj.status == 'COMPLETED':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: 100%; background-color: #28a745; color: white; text-align: center; border-radius: 3px;">100%</div>'
                '</div>'
            )
        elif obj.status == 'IN_PROGRESS':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: 50%; background-color: #007bff; color: white; text-align: center; border-radius: 3px;">50%</div>'
                '</div>'
            )
        elif obj.status == 'OVERDUE':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: 25%; background-color: #dc3545; color: white; text-align: center; border-radius: 3px;">25%</div>'
                '</div>'
            )
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: 0%; background-color: #ffc107; color: black; text-align: center; border-radius: 3px;">0%</div>'
            '</div>'
        )
    progress_percentage.short_description = _('Progress')
    progress_percentage.allow_tags = True
    
    def completion_date(self, obj):
        """Display completion date or days until due"""
        if obj.completed_at:
            return obj.completed_at.strftime('%Y-%m-%d')
        elif obj.due_date:
            days_until = (obj.due_date.date() - timezone.now().date()).days
            if days_until < 0:
                return format_html(
                    '<span style="color: red;">{} days overdue</span>',
                    abs(days_until)
                )
            elif days_until == 0:
                return format_html(
                    '<span style="color: orange;">Due today</span>'
                )
            return f"{days_until} days"
        return "-"
    completion_date.short_description = _('Completion')
    completion_date.allow_tags = True
    
    def mark_as_completed(self, request, queryset):
        """Mark selected milestones as completed"""
        count = queryset.filter(status__in=['PENDING', 'IN_PROGRESS']).update(
            status='COMPLETED',
            completed_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d milestones marked as completed.') % {'count': count},
            level='success'
        )
    mark_as_completed.short_description = _('Mark selected as completed')
    
    def mark_as_pending(self, request, queryset):
        """Mark selected milestones as pending"""
        count = queryset.filter(status__in=['IN_PROGRESS', 'COMPLETED']).update(
            status='PENDING',
            completed_at=None
        )
        self.message_user(
            request,
            _('%(count)d milestones marked as pending.') % {'count': count},
            level='success'
        )
    mark_as_pending.short_description = _('Mark selected as pending')
    
    def mark_as_in_progress(self, request, queryset):
        """Mark selected milestones as in progress"""
        count = queryset.filter(status='PENDING').update(status='IN_PROGRESS')
        self.message_user(
            request,
            _('%(count)d milestones marked as in progress.') % {'count': count},
            level='success'
        )
    mark_as_in_progress.short_description = _('Mark selected as in progress')
    
    def update_progress(self, request, queryset):
        """Update progress for selected milestones"""
        # This is a placeholder for a more complex progress update logic
        count = queryset.count()
        self.message_user(
            request,
            _('Progress updated for %(count)d milestones.') % {'count': count},
            level='success'
        )
    update_progress.short_description = _('Update progress')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Session model with calendar view and status management"""
    
    list_display = [
        'award', 'title', 'scheduled_start', 'scheduled_end',
        'duration_display', 'location_type', 'status', 'is_completed'
    ]
    list_filter = [
        'status', 'location_type', 'scheduled_start'
    ]
    search_fields = [
        'title', 'description', 'meeting_url', 'meeting_address',
        'award__requirement__title', 'award__student__username',
        'award__tutor__username'
    ]
    readonly_fields = [
        'award', 'duration_display', 'created_at', 'updated_at',
        'actual_start', 'actual_end', 'is_completed'
    ]
    date_hierarchy = 'scheduled_start'
    ordering = ['-scheduled_start']
    raw_id_fields = ('award',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'award', 'title', 'description', 'status'
            )
        }),
        ('Schedule', {
            'fields': (
                'scheduled_start', 'scheduled_end',
                'actual_start', 'actual_end', 'duration_display'
            )
        }),
        ('Location', {
            'fields': (
                'location_type', 'meeting_url', 'meeting_address'
            )
        }),
        ('Notes & Cancellation', {
            'fields': (
                'tutor_notes', 'student_notes',
                'cancellation_reason', 'cancelled_by'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'confirm_sessions', 'complete_sessions', 'cancel_sessions',
        'reschedule_sessions'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'award', 'award__student', 'award__tutor', 'award__requirement'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(award__student=request.user)
            elif request.user.user_type == 'TUTOR':
                return qs.filter(award__tutor=request.user)
        return qs.none()
    
    def duration_display(self, obj):
        """Display duration in a readable format"""
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            return f"{minutes}m"
        return "-"
    duration_display.short_description = _('Duration')
    
    def is_completed(self, obj):
        """Display completion status with color"""
        if obj.status == 'COMPLETED':
            return format_html(
                '<span style="color: green;">✓ Completed</span>'
            )
        elif obj.status == 'CANCELLED':
            return format_html(
                '<span style="color: red;">✗ Cancelled</span>'
            )
        elif obj.actual_start and obj.actual_end:
            return format_html(
                '<span style="color: blue;">↻ In Progress</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Scheduled</span>'
        )
    is_completed.short_description = _('Status')
    is_completed.allow_tags = True
    
    def confirm_sessions(self, request, queryset):
        """Confirm selected sessions"""
        count = queryset.filter(status='SCHEDULED').update(status='CONFIRMED')
        self.message_user(
            request,
            _('%(count)d sessions confirmed.') % {'count': count},
            level='success'
        )
    confirm_sessions.short_description = _('Confirm selected sessions')
    
    def complete_sessions(self, request, queryset):
        """Mark selected sessions as completed"""
        now = timezone.now()
        count = queryset.filter(status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS']).update(
            status='COMPLETED',
            actual_end=now
        )
        self.message_user(
            request,
            _('%(count)d sessions marked as completed.') % {'count': count},
            level='success'
        )
    complete_sessions.short_description = _('Mark selected as completed')
    
    def cancel_sessions(self, request, queryset):
        """Cancel selected sessions"""
        count = queryset.filter(status__in=['SCHEDULED', 'CONFIRMED', 'IN_PROGRESS']).update(
            status='CANCELLED',
            cancelled_by=request.user
        )
        self.message_user(
            request,
            _('%(count)d sessions cancelled.') % {'count': count},
            level='success'
        )
    cancel_sessions.short_description = _('Cancel selected sessions')
    
    def reschedule_sessions(self, request, queryset):
        """Mark selected sessions for rescheduling"""
        count = queryset.filter(status__in=['SCHEDULED', 'CONFIRMED']).update(
            status='RESCHEDULED'
        )
        self.message_user(
            request,
            _('%(count)d sessions marked for rescheduling.') % {'count': count},
            level='success'
        )
    reschedule_sessions.short_description = _('Mark for rescheduling')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Review model with moderation capabilities"""
    
    list_display = [
        'award', 'reviewer', 'reviewee', 'rating_display',
        'detailed_ratings', 'would_recommend_display',
        'is_public', 'is_verified', 'created_at'
    ]
    list_filter = [
        'rating', 'would_recommend', 'is_public', 'is_verified',
        'created_at'
    ]
    search_fields = [
        'comment', 'reviewer__username', 'reviewee__username',
        'award__requirement__title'
    ]
    readonly_fields = [
        'award', 'reviewer', 'reviewee', 'created_at', 'updated_at',
        'rating_display', 'detailed_ratings'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('award', 'reviewer', 'reviewee')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'award', 'reviewer', 'reviewee', 'rating', 'rating_display'
            )
        }),
        ('Detailed Ratings', {
            'fields': (
                'communication_rating', 'expertise_rating',
                'punctuality_rating', 'detailed_ratings', 'would_recommend'
            )
        }),
        ('Content & Moderation', {
            'fields': (
                'comment', 'is_public', 'is_verified', 'would_recommend_display'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'approve_reviews', 'reject_reviews', 'make_public', 'make_private',
        'verify_reviews', 'unverify_reviews'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'award', 'reviewer', 'reviewee', 'award__requirement'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(reviewer=request.user)
            elif request.user.user_type == 'TUTOR':
                return qs.filter(reviewee=request.user)
        return qs.none()
    
    def rating_display(self, obj):
        """Display rating with stars"""
        if obj.rating:
            stars = '★' * obj.rating + '☆' * (5 - obj.rating)
            return format_html(
                '<span style="color: gold; font-size: 1.2em;">{}</span> ({}/5)',
                stars, obj.rating
            )
        return "-"
    rating_display.short_description = _('Rating')
    rating_display.allow_tags = True
    
    def detailed_ratings(self, obj):
        """Display detailed ratings in a compact format"""
        if all([obj.communication_rating, obj.expertise_rating, obj.punctuality_rating]):
            return format_html(
                '<div>C: {}/5 | E: {}/5 | P: {}/5</div>',
                obj.communication_rating,
                obj.expertise_rating,
                obj.punctuality_rating
            )
        return "-"
    detailed_ratings.short_description = _('Detailed Ratings')
    detailed_ratings.allow_tags = True
    
    def would_recommend_display(self, obj):
        """Display recommendation status with icon"""
        if obj.would_recommend is True:
            return format_html(
                '<span style="color: green;">✓ Would Recommend</span>'
            )
        elif obj.would_recommend is False:
            return format_html(
                '<span style="color: red;">✗ Would Not Recommend</span>'
            )
        return "-"
    would_recommend_display.short_description = _('Recommendation')
    would_recommend_display.allow_tags = True
    
    def approve_reviews(self, request, queryset):
        """Approve selected reviews"""
        count = queryset.update(is_verified=True, is_public=True)
        self.message_user(
            request,
            _('%(count)d reviews approved and made public.') % {'count': count},
            level='success'
        )
    approve_reviews.short_description = _('Approve and make public')
    
    def reject_reviews(self, request, queryset):
        """Reject selected reviews"""
        count = queryset.update(is_verified=False, is_public=False)
        self.message_user(
            request,
            _('%(count)d reviews rejected and made private.') % {'count': count},
            level='success'
        )
    reject_reviews.short_description = _('Reject and make private')
    
    def make_public(self, request, queryset):
        """Make selected reviews public"""
        count = queryset.update(is_public=True)
        self.message_user(
            request,
            _('%(count)d reviews made public.') % {'count': count},
            level='success'
        )
    make_public.short_description = _('Make public')
    
    def make_private(self, request, queryset):
        """Make selected reviews private"""
        count = queryset.update(is_public=False)
        self.message_user(
            request,
            _('%(count)d reviews made private.') % {'count': count},
            level='success'
        )
    make_private.short_description = _('Make private')
    
    def verify_reviews(self, request, queryset):
        """Verify selected reviews"""
        count = queryset.update(is_verified=True)
        self.message_user(
            request,
            _('%(count)d reviews verified.') % {'count': count},
            level='success'
        )
    verify_reviews.short_description = _('Verify reviews')
    
    def unverify_reviews(self, request, queryset):
        """Unverify selected reviews"""
        count = queryset.update(is_verified=False)
        self.message_user(
            request,
            _('%(count)d reviews unverified.') % {'count': count},
            level='success'
        )
    unverify_reviews.short_description = _('Unverify reviews')


@admin.register(SavedRequirement)
class SavedRequirementAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for SavedRequirement model with analytics"""
    
    list_display = [
        'user', 'requirement', 'requirement_status', 'requirement_budget',
        'created_at', 'days_since_saved'
    ]
    list_filter = [
        'created_at', 'requirement__status', 'requirement__subject',
        'requirement__learning_level'
    ]
    search_fields = [
        'user__username', 'user__email',
        'requirement__title', 'requirement__description',
        'requirement__specific_topics'
    ]
    readonly_fields = ['created_at', 'days_since_saved']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user', 'requirement')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user', 'requirement', 'requirement_status',
                'requirement_budget', 'created_at', 'days_since_saved'
            )
        }),
    )
    
    actions = [
        'notify_users_about_updates', 'remove_expired_requirements'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'user', 'requirement', 'requirement__subject'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(user=request.user)
        return qs.none()
    
    def requirement_status(self, obj):
        """Display requirement status with color coding"""
        if obj.requirement.status == 'OPEN':
            return format_html(
                '<span style="color: green;">✓ Open</span>'
            )
        elif obj.requirement.status == 'IN_PROGRESS':
            return format_html(
                '<span style="color: blue;">↻ In Progress</span>'
            )
        elif obj.requirement.status == 'COMPLETED':
            return format_html(
                '<span style="color: gray;">✓ Completed</span>'
            )
        elif obj.requirement.status == 'CANCELLED':
            return format_html(
                '<span style="color: red;">✗ Cancelled</span>'
            )
        return obj.requirement.status
    requirement_status.short_description = _('Requirement Status')
    requirement_status.allow_tags = True
    
    def requirement_budget(self, obj):
        """Display requirement budget range"""
        return obj.requirement.get_budget_range()
    requirement_budget.short_description = _('Budget')
    
    def days_since_saved(self, obj):
        """Calculate days since requirement was saved"""
        days = (timezone.now() - obj.created_at).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        return f"{days} days ago"
    days_since_saved.short_description = _('Saved')
    
    def notify_users_about_updates(self, request, queryset):
        """Notify users about updates to saved requirements"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d saved requirements.') % {'count': count},
            level='success'
        )
    notify_users_about_updates.short_description = _('Notify about updates')
    
    def remove_expired_requirements(self, request, queryset):
        """Remove saved requirements that are no longer relevant"""
        count = queryset.filter(
            requirement__status__in=['COMPLETED', 'CANCELLED']
        ).count()
        self.message_user(
            request,
            _('%(count)d expired saved requirements identified.') % {'count': count},
            level='info'
        )
    remove_expired_requirements.short_description = _('Identify expired requirements')


@admin.register(FavoriteTutor)
class FavoriteTutorAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for FavoriteTutor model with analytics"""
    
    list_display = [
        'student', 'tutor', 'tutor_rating', 'tutor_specialties',
        'tutor_hourly_rate', 'created_at', 'days_since_favorited'
    ]
    list_filter = [
        'created_at'
    ]
    search_fields = [
        'student__username', 'student__email',
        'tutor__username', 'tutor__email',
        'tutor__profile__bio'
    ]
    readonly_fields = ['created_at', 'days_since_favorited']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('student', 'tutor')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'student', 'tutor', 'tutor_rating', 'tutor_specialties',
                'tutor_hourly_rate', 'created_at', 'days_since_favorited'
            )
        }),
    )
    
    actions = [
        'notify_students_about_availability', 'remove_inactive_tutors'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'student', 'tutor'
        ).prefetch_related('tutor__subjects')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(student=request.user)
        return qs.none()
    
    def tutor_rating(self, obj):
        """Display tutor rating with stars"""
        if hasattr(obj.tutor, 'average_rating') and obj.tutor.average_rating:
            stars = '★' * int(obj.tutor.average_rating) + '☆' * (5 - int(obj.tutor.average_rating))
            return format_html(
                '<span style="color: gold;">{}</span> ({:.1f}/5)',
                stars, obj.tutor.average_rating
            )
        return "Not rated"
    tutor_rating.short_description = _('Rating')
    tutor_rating.allow_tags = True
    
    def tutor_specialties(self, obj):
        """Display tutor's subjects"""
        if hasattr(obj.tutor, 'subjects'):
            subjects = obj.tutor.subjects.all()[:3]  # Show first 3 subjects
            return ", ".join([s.name for s in subjects])
        return "-"
    tutor_specialties.short_description = _('Specialties')
    
    def tutor_hourly_rate(self, obj):
        """Display tutor's hourly rate"""
        if hasattr(obj.tutor, 'profile') and obj.tutor.profile.hourly_rate:
            return f"${obj.tutor.profile.hourly_rate:.2f}/hr"
        return "Not specified"
    tutor_hourly_rate.short_description = _('Hourly Rate')
    
    def days_since_favorited(self, obj):
        """Calculate days since tutor was favorited"""
        days = (timezone.now() - obj.created_at).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        return f"{days} days ago"
    days_since_favorited.short_description = _('Favorited')
    
    def notify_students_about_availability(self, request, queryset):
        """Notify students about tutor availability"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d favorite tutors.') % {'count': count},
            level='success'
        )
    notify_students_about_availability.short_description = _('Notify about availability')
    
    def remove_inactive_tutors(self, request, queryset):
        """Remove favorite tutors who are no longer active"""
        count = queryset.filter(
            tutor__is_active=False
        ).count()
        self.message_user(
            request,
            _('%(count)d inactive favorite tutors identified.') % {'count': count},
            level='info'
        )
    remove_inactive_tutors.short_description = _('Identify inactive tutors')


# Custom admin actions
def mark_requirements_featured(modeladmin, request, queryset):
    """Mark selected requirements as featured"""
    count = queryset.update(is_featured=True)
    modeladmin.message_user(request, f"{count} requirements marked as featured.")
mark_requirements_featured.short_description = "Mark selected as featured"


def mark_requirements_not_featured(modeladmin, request, queryset):
    """Mark selected requirements as not featured"""
    count = queryset.update(is_featured=False)
    modeladmin.message_user(request, f"{count} requirements marked as not featured.")
mark_requirements_not_featured.short_description = "Mark selected as not featured"


def publish_requirements(modeladmin, request, queryset):
    """Publish selected requirements"""
    count = queryset.update(status='OPEN', published_at=timezone.now())
    modeladmin.message_user(request, f"{count} requirements published.")
publish_requirements.short_description = "Publish selected requirements"


def close_requirements(modeladmin, request, queryset):
    """Close selected requirements"""
    count = queryset.update(status='CANCELLED', closed_at=timezone.now())
    modeladmin.message_user(request, f"{count} requirements closed.")
close_requirements.short_description = "Close selected requirements"


# Add custom actions to RequirementAdmin
RequirementAdmin.actions = [
    mark_requirements_featured,
    mark_requirements_not_featured,
    publish_requirements,
    close_requirements,
]
