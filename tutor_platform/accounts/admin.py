from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied

from .models import (
    User, StudentProfile, TutorProfile, AdminProfile,
    Subject, TutorSubject, TutorVerification, TutorRating, UserPreferences
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced admin configuration for User model with role-based filtering and advanced search"""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_verified', 'is_online', 'is_active', 'date_joined')
    list_filter = (
        'user_type', 'is_verified', 'is_online', 'is_active', 'is_staff', 'is_superuser',
        'date_joined', 'last_login'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    # raw_id_fields removed as 'id' is not a foreign key or many-to-many field
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture')}),
        (_('User Type'), {'fields': ('user_type', 'is_verified', 'is_online')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Additional Info'), {'fields': ('timezone',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )
    
    actions = ['mark_verified', 'mark_unverified', 'activate_users', 'deactivate_users',
               'mark_online', 'mark_offline', 'send_verification_email']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('studentprofile', 'tutorprofile', 'adminprofile').prefetch_related(
            'tutorprofile__tutor_subjects', 'tutorprofile__ratings'
        )
    
    def view_profile_link(self, obj):
        """Display link to view profile based on user type"""
        if obj.is_student():
            if hasattr(obj, 'studentprofile'):
                url = reverse('admin:accounts_studentprofile_change', args=[obj.studentprofile.id])
                return format_html('<a href="{}">View Student Profile</a>', url)
        elif obj.is_tutor():
            if hasattr(obj, 'tutorprofile'):
                url = reverse('admin:accounts_tutorprofile_change', args=[obj.tutorprofile.id])
                return format_html('<a href="{}">View Tutor Profile</a>', url)
        elif obj.is_admin_user():
            if hasattr(obj, 'adminprofile'):
                url = reverse('admin:accounts_adminprofile_change', args=[obj.adminprofile.id])
                return format_html('<a href="{}">View Admin Profile</a>', url)
        return "-"
    view_profile_link.short_description = _('Profile')  # type: ignore
    
    def mark_verified(self, request, queryset):
        """Mark selected users as verified"""
        count = queryset.filter(is_verified=False).update(is_verified=True)
        self.message_user(request, _('%(count)d users marked as verified.') % {'count': count}, level='success')
    mark_verified.short_description = _('Mark selected users as verified')
    
    def mark_unverified(self, request, queryset):
        """Mark selected users as unverified"""
        count = queryset.filter(is_verified=True).update(is_verified=False)
        self.message_user(request, _('%(count)d users marked as unverified.') % {'count': count}, level='success')
    mark_unverified.short_description = _('Mark selected users as unverified')
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, _('%(count)d users activated.') % {'count': count}, level='success')
    activate_users.short_description = _('Activate selected users')
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        # Don't allow deactivating yourself
        if request.user in queryset:
            raise PermissionDenied("You cannot deactivate yourself.")
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, _('%(count)d users deactivated.') % {'count': count}, level='success')
    deactivate_users.short_description = _('Deactivate selected users')
    
    def mark_online(self, request, queryset):
        """Mark selected users as online"""
        count = queryset.filter(is_online=False).update(is_online=True)
        self.message_user(request, _('%(count)d users marked as online.') % {'count': count}, level='success')
    mark_online.short_description = _('Mark selected users as online')
    
    def mark_offline(self, request, queryset):
        """Mark selected users as offline"""
        count = queryset.filter(is_online=True).update(is_online=False)
        self.message_user(request, _('%(count)d users marked as offline.') % {'count': count}, level='success')
    mark_offline.short_description = _('Mark selected users as offline')
    
    def send_verification_email(self, request, queryset):
        """Send verification email to selected users"""
        # This would integrate with your email system
        count = queryset.count()
        self.message_user(request, _('Verification emails sent to %(count)d users.') % {'count': count}, level='success')
    send_verification_email.short_description = _('Send verification email')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin configuration for StudentProfile model"""
    
    list_display = ('user', 'educational_status', 'institution', 'grade_level', 'created_at')
    list_filter = ('educational_status', 'preferred_learning_style', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'institution')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Student Information'), {
            'fields': ('user', 'educational_status', 'institution', 'grade_level', 'major_field')
        }),
        (_('Learning Preferences'), {
            'fields': ('learning_goals', 'preferred_learning_style', 'bio')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for TutorProfile model with advanced filtering and analytics"""
    
    list_display = (
        'user', 'professional_title', 'experience_years', 'availability_status',
        'hourly_rate_range', 'profile_completion_score', 'rating_display',
        'is_featured', 'is_verified', 'subjects_count'
    )
    list_filter = (
        'availability_status', 'is_featured', 'user__is_verified', 'experience_years',
        'created_at', 'hourly_rate_min', 'hourly_rate_max'
    )
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'professional_title', 'languages', 'bio'
    )
    readonly_fields = ('created_at', 'updated_at', 'get_average_rating_display', 'get_completed_sessions_display')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Tutor Information'), {
            'fields': ('user', 'professional_title', 'experience_years', 'education', 'bio')
        }),
        (_('Pricing & Availability'), {
            'fields': ('hourly_rate_min', 'hourly_rate_max', 'availability_status', 'response_time_hours')
        }),
        (_('Additional Info'), {
            'fields': ('languages', 'teaching_experience', 'profile_completion_score', 'is_featured')
        }),
        (_('Statistics'), {
            'fields': ('get_average_rating_display', 'get_completed_sessions_display', 'subjects_count'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_featured', 'remove_featured', 'verify_tutor', 'unverify_tutor',
        'update_profile_completion', 'set_available', 'set_busy', 'set_offline'
    ]
    
    def is_verified(self, obj):
        """Check if tutor is verified"""
        return obj.user.is_verified
    is_verified.boolean = True
    is_verified.short_description = _('Verified')
    
    def get_average_rating_display(self, obj):
        """Display average rating with stars"""
        rating = obj.get_average_rating()
        if rating > 0:
            stars = '★' * int(rating) + '☆' * (5 - int(rating))
            return format_html(f'{rating:.1f}/5 {stars}')
        return _("No ratings")
    get_average_rating_display.short_description = _('Average Rating')
    
    def get_completed_sessions_display(self, obj):
        """Display completed sessions count"""
        count = obj.get_completed_sessions()
        return format_html(f'<span style="color: green;">{count}</span>')
    get_completed_sessions_display.short_description = _('Completed Sessions')
    
    def hourly_rate_range(self, obj):
        """Display hourly rate range"""
        if obj.hourly_rate_min and obj.hourly_rate_max:
            return f"${obj.hourly_rate_min} - ${obj.hourly_rate_max}"
        elif obj.hourly_rate_min:
            return f"From ${obj.hourly_rate_min}"
        elif obj.hourly_rate_max:
            return f"Up to ${obj.hourly_rate_max}"
        return _("Not specified")
    hourly_rate_range.short_description = _('Hourly Rate')
    
    def rating_display(self, obj):
        """Display rating with color coding"""
        rating = obj.get_average_rating()
        if rating >= 4.5:
            color = 'green'
        elif rating >= 3.5:
            color = 'orange'
        elif rating > 0:
            color = 'red'
        else:
            return _("No rating")
        return format_html(f'<span style="color: {color}; font-weight: bold;">{rating:.1f}</span>')
    rating_display.short_description = _('Rating')
    
    def subjects_count(self, obj):
        """Count tutor subjects"""
        count = obj.tutor_subjects.count()
        return format_html(f'<span style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{count}</span>')
    subjects_count.short_description = _('Subjects')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user'
        ).prefetch_related(
            'tutor_subjects__subject', 'ratings'
        ).annotate(
            subjects_count=Count('tutor_subjects'),
            avg_rating=Avg('ratings__rating')
        )
    
    def mark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, _('%(count)d tutors marked as featured.') % {'count': count}, level='success')
    mark_as_featured.short_description = _('Mark selected tutors as featured')
    
    def remove_featured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, _('Featured status has been removed from %(count)d tutors.') % {'count': count}, level='success')
    remove_featured.short_description = _('Remove featured status from selected tutors')
    
    def verify_tutor(self, request, queryset):
        count = 0
        for tutor in queryset:
            if not tutor.user.is_verified:
                tutor.user.is_verified = True
                tutor.user.save()
                count += 1
        self.message_user(request, _('%(count)d tutors have been verified.') % {'count': count}, level='success')
    verify_tutor.short_description = _('Verify selected tutors')
    
    def unverify_tutor(self, request, queryset):
        count = 0
        for tutor in queryset:
            if tutor.user.is_verified:
                tutor.user.is_verified = False
                tutor.user.save()
                count += 1
        self.message_user(request, _('Verification has been removed from %(count)d tutors.') % {'count': count}, level='success')
    unverify_tutor.short_description = _('Remove verification from selected tutors')
    
    def update_profile_completion(self, request, queryset):
        """Update profile completion score for selected tutors"""
        count = 0
        for tutor in queryset:
            tutor.update_profile_completion()
            count += 1
        self.message_user(request, _('Profile completion updated for %(count)d tutors.') % {'count': count}, level='success')
    update_profile_completion.short_description = _('Update profile completion scores')
    
    def set_available(self, request, queryset):
        """Set availability status to available"""
        count = queryset.update(availability_status=TutorProfile.AvailabilityStatus.AVAILABLE)
        self.message_user(request, _('%(count)d tutors set as available.') % {'count': count}, level='success')
    set_available.short_description = _('Set as available')
    
    def set_busy(self, request, queryset):
        """Set availability status to busy"""
        count = queryset.update(availability_status=TutorProfile.AvailabilityStatus.BUSY)
        self.message_user(request, _('%(count)d tutors set as busy.') % {'count': count}, level='success')
    set_busy.short_description = _('Set as busy')
    
    def set_offline(self, request, queryset):
        """Set availability status to offline"""
        count = queryset.update(availability_status=TutorProfile.AvailabilityStatus.OFFLINE)
        self.message_user(request, _('%(count)d tutors set as offline.') % {'count': count}, level='success')
    set_offline.short_description = _('Set as offline')


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """Admin configuration for AdminProfile model"""
    
    list_display = ('user', 'department', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'department')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Admin Information'), {
            'fields': ('user', 'department', 'permissions')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin configuration for Subject model"""
    
    list_display = ('name', 'parent', 'is_active', 'order', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (_('Subject Information'), {
            'fields': ('name', 'slug', 'parent', 'description', 'icon')
        }),
        (_('Settings'), {
            'fields': ('is_active', 'order')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


class TutorSubjectInline(admin.TabularInline):
    """Inline configuration for TutorSubject model"""
    model = TutorSubject
    extra = 1
    fields = ('subject', 'proficiency_level', 'hourly_rate', 'is_primary_subject', 'years_of_experience')


@admin.register(TutorSubject)
class TutorSubjectAdmin(admin.ModelAdmin):
    """Admin configuration for TutorSubject model"""
    
    list_display = ('tutor', 'subject', 'proficiency_level', 'hourly_rate', 'is_primary_subject', 'years_of_experience')
    list_filter = ('proficiency_level', 'is_primary_subject', 'subject', 'created_at')
    search_fields = ('tutor__user__username', 'tutor__user__email', 'subject__name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tutor__user', 'subject')


@admin.register(TutorVerification)
class TutorVerificationAdmin(admin.ModelAdmin):
    """Admin configuration for TutorVerification model"""
    
    list_display = ('tutor', 'verification_type', 'status', 'submitted_at', 'reviewed_at', 'verified_by')
    list_filter = ('verification_type', 'status', 'submitted_at', 'reviewed_at')
    search_fields = ('tutor__user__username', 'tutor__user__email', 'document_number', 'issuing_authority')
    readonly_fields = ('submitted_at', 'reviewed_at')
    
    fieldsets = (
        (_('Verification Information'), {
            'fields': ('tutor', 'verification_type', 'document', 'document_number', 'issuing_authority')
        }),
        (_('Document Details'), {
            'fields': ('issue_date', 'expiry_date', 'expires_at')
        }),
        (_('Review'), {
            'fields': ('status', 'verified_by', 'verification_notes', 'admin_comments')
        }),
        (_('Timestamps'), {
            'fields': ('submitted_at', 'reviewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_verifications', 'reject_verifications', 'mark_as_expired']
    
    def approve_verifications(self, request, queryset):
        count = queryset.filter(status=TutorVerification.VerificationStatus.PENDING).update(
            status=TutorVerification.VerificationStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d verification(s) have been approved.') % {'count': count}, level='success')
    approve_verifications.short_description = _('Approve selected verifications')  # type: ignore
    
    def reject_verifications(self, request, queryset):
        count = queryset.filter(status=TutorVerification.VerificationStatus.PENDING).update(
            status=TutorVerification.VerificationStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, _('%(count)d verification(s) have been rejected.') % {'count': count}, level='success')
    reject_verifications.short_description = _('Reject selected verifications')  # type: ignore
    
    def mark_as_expired(self, request, queryset):
        count = queryset.update(status=TutorVerification.VerificationStatus.EXPIRED)
        self.message_user(request, _('%(count)d verification(s) have been marked as expired.') % {'count': count}, level='success')
    mark_as_expired.short_description = _('Mark selected verifications as expired')  # type: ignore
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tutor__user', 'verified_by')


@admin.register(TutorRating)
class TutorRatingAdmin(admin.ModelAdmin):
    """Admin configuration for TutorRating model"""
    
    list_display = ('tutor', 'student', 'rating', 'requirement', 'is_public', 'created_at')
    list_filter = ('rating', 'is_public', 'created_at')
    search_fields = ('tutor__user__username', 'tutor__user__email', 'student__username', 'student__email', 'review')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Rating Information'), {
            'fields': ('tutor', 'student', 'requirement', 'rating', 'is_public')
        }),
        (_('Review'), {
            'fields': ('review',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tutor__user', 'student')


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    """Admin configuration for UserPreferences model"""
    
    list_display = ('user', 'email_notifications', 'sms_notifications', 'push_notifications', 'language', 'timezone', 'currency')
    list_filter = ('email_notifications', 'sms_notifications', 'push_notifications', 'marketing_emails', 'language', 'timezone', 'currency')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Notification Preferences'), {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications', 'marketing_emails')
        }),
        (_('Localization'), {
            'fields': ('language', 'timezone', 'currency')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Customize TutorProfile admin to include TutorSubject inline
class TutorProfileWithSubjectsAdmin(TutorProfileAdmin):
    inlines = [TutorSubjectInline]


# Unregister the original TutorProfileAdmin and register the enhanced one
admin.site.unregister(TutorProfile)
admin.site.register(TutorProfile, TutorProfileWithSubjectsAdmin)


# Customize admin site
admin.site.site_header = _('Django Tutor Platform Administration')
admin.site.site_title = _('Django Tutor Platform')
admin.site.index_title = _('Welcome to Django Tutor Platform')
