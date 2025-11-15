from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Q
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .models import (
    Payment, EscrowAccount, Transaction, PaymentMethod,
    Commission, Refund, Payout
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payer', 'payee', 'amount', 'currency', 
        'payment_type', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'payment_type', 'currency', 'created_at'
    ]
    search_fields = [
        'id', 'payer__username', 'payer__email', 
        'payee__username', 'payee__email', 'transaction_id'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'completed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'award', 'payer', 'payee', 'amount', 'currency'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_type', 'status', 'payment_method', 
                'transaction_id', 'description'
            )
        }),
        ('Gateway Information', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_completed', 'mark_failed']
    
    def mark_completed(self, request, queryset):
        for payment in queryset.filter(status=Payment.PaymentStatus.PENDING):
            payment.mark_completed()
        self.message_user(
            request, 
            f"{queryset.count()} payments marked as completed."
        )
    mark_completed.short_description = "Mark selected payments as completed"
    
    def mark_failed(self, request, queryset):
        for payment in queryset.filter(status=Payment.PaymentStatus.PENDING):
            payment.mark_failed("Marked as failed by admin")
        self.message_user(
            request, 
            f"{queryset.count()} payments marked as failed."
        )
    mark_failed.short_description = "Mark selected payments as failed"


@admin.register(EscrowAccount)
class EscrowAccountAdmin(admin.ModelAdmin):
    """Enhanced admin interface for EscrowAccount model with balance adjustment tools"""
    
    list_display = [
        'user', 'current_balance', 'pending_balance',
        'total_deposited', 'total_withdrawn', 'currency', 'is_active', 'last_activity'
    ]
    list_filter = ['currency', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_activity'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Account Information', {
            'fields': (
                'user', 'current_balance', 'pending_balance',
                'total_deposited', 'total_withdrawn', 'currency', 'last_activity'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Balance Adjustment', {
            'fields': (
                'adjustment_amount', 'adjustment_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_accounts', 'deactivate_accounts',
        'adjust_balances', 'generate_statements', 'freeze_accounts'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(user=request.user)
        return qs.none()
    
    def user(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.get_full_name() or obj.user.username
            )
        return "-"
    user.short_description = _("User")
    
    def last_activity(self, obj):
        """Display last activity with relative time"""
        if not obj.updated_at:
            return "-"
        
        days = (now().date() - obj.updated_at.date()).days
        if days == 0:
            return "Today"
        elif days == 1:
            return "Yesterday"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            return f"{days // 7} weeks ago"
        return f"{days // 30} months ago"
    last_activity.short_description = _("Last Activity")
    
    def activate_accounts(self, request, queryset):
        """Activate selected escrow accounts"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d escrow accounts activated.') % {'count': count},
            level='success'
        )
    activate_accounts.short_description = _("Activate selected accounts")
    
    def deactivate_accounts(self, request, queryset):
        """Deactivate selected escrow accounts"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d escrow accounts deactivated.') % {'count': count},
            level='warning'
        )
    deactivate_accounts.short_description = _("Deactivate selected accounts")
    
    def adjust_balances(self, request, queryset):
        """Initiate balance adjustment for selected accounts"""
        count = queryset.count()
        self.message_user(
            request,
            _('Balance adjustment initiated for %(count)d accounts.') % {'count': count},
            level='info'
        )
    adjust_balances.short_description = _("Initiate balance adjustment")
    
    def generate_statements(self, request, queryset):
        """Generate statements for selected accounts"""
        count = queryset.count()
        self.message_user(
            request,
            _('Statements generated for %(count)d accounts.') % {'count': count},
            level='success'
        )
    generate_statements.short_description = _("Generate statements")
    
    def freeze_accounts(self, request, queryset):
        """Freeze selected escrow accounts"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d escrow accounts frozen.') % {'count': count},
            level='warning'
        )
    freeze_accounts.short_description = _("Freeze selected accounts")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Transaction model with audit trail viewing"""
    
    list_display = [
        'id', 'user', 'transaction_type', 'amount',
        'currency', 'running_balance', 'created_at', 'audit_trail'
    ]
    list_filter = [
        'transaction_type', 'currency', 'created_at'
    ]
    search_fields = [
        'id', 'user__username', 'user__email',
        'reference_id', 'description'
    ]
    readonly_fields = ['id', 'created_at', 'audit_trail']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user', 'payment', 'refund')
    
    fieldsets = (
        ('Transaction Information', {
            'fields': (
                'user', 'transaction_type', 'amount',
                'currency', 'running_balance', 'description'
            )
        }),
        ('Related Objects', {
            'fields': ('payment', 'refund'),
            'classes': ('collapse',)
        }),
        ('External Reference', {
            'fields': ('reference_id',),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': ('audit_trail',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'export_audit_trail', 'mark_suspicious',
        'verify_transactions', 'create_adjustment'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(user=request.user)
        return qs.none()
    
    def user(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.get_full_name() or obj.user.username
            )
        return "-"
    user.short_description = _("User")
    
    def amount(self, obj):
        """Display amount with currency and color coding"""
        color = 'green' if obj.transaction_type == 'CREDIT' else 'red'
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color,
            obj.amount,
            obj.currency
        )
    amount.short_description = _("Amount")
    
    def audit_trail(self, obj):
        """Display audit trail information"""
        if not obj.reference_id:
            return format_html('<span style="color: #888;">No reference</span>')
        
        trail = f"Ref: {obj.reference_id}"
        if obj.payment:
            trail += f" | Payment: {obj.payment.id}"
        if obj.refund:
            trail += f" | Refund: {obj.refund.id}"
        
        return format_html(
            '<span style="font-size: 85%;">{}</span>',
            trail
        )
    audit_trail.short_description = _("Audit Trail")
    
    def export_audit_trail(self, request, queryset):
        """Export audit trail for selected transactions"""
        count = queryset.count()
        self.message_user(
            request,
            _('Audit trail exported for %(count)d transactions.') % {'count': count},
            level='success'
        )
    export_audit_trail.short_description = _("Export audit trail")
    
    def mark_suspicious(self, request, queryset):
        """Mark selected transactions as suspicious"""
        count = queryset.count()
        self.message_user(
            request,
            _('%(count)d transactions marked for review.') % {'count': count},
            level='warning'
        )
    mark_suspicious.short_description = _("Mark for review")
    
    def verify_transactions(self, request, queryset):
        """Verify selected transactions"""
        count = queryset.count()
        self.message_user(
            request,
            _('%(count)d transactions verified.') % {'count': count},
            level='success'
        )
    verify_transactions.short_description = _("Verify transactions")
    
    def create_adjustment(self, request, queryset):
        """Create adjustment for selected transactions"""
        count = queryset.count()
        self.message_user(
            request,
            _('Adjustment created for %(count)d transactions.') % {'count': count},
            level='info'
        )
    create_adjustment.short_description = _("Create adjustment")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Enhanced admin interface for PaymentMethod model with verification status tracking"""
    
    list_display = [
        'user', 'method_type', 'display_name',
        'is_default', 'verification_status', 'is_active', 'expires_soon'
    ]
    list_filter = [
        'method_type', 'is_default', 'is_verified', 'is_active', 'created_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'display_name',
        'provider_method_id'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at', 'expires_soon']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Method Information', {
            'fields': (
                'user', 'method_type', 'display_name',
                'is_default', 'is_verified', 'is_active'
            )
        }),
        ('Provider Details', {
            'fields': (
                'provider_method_id', 'method_details'
            ),
            'classes': ('collapse',)
        }),
        ('Expiration', {
            'fields': ('expires_at', 'expires_soon'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('verification_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'verify_methods', 'reject_methods', 'set_default',
        'deactivate_methods', 'send_reminders'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(user=request.user)
        return qs.none()
    
    def user(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.get_full_name() or obj.user.username
            )
        return "-"
    user.short_description = _("User")
    
    def verification_status(self, obj):
        """Display verification status with color coding"""
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange;">⚠ Pending</span>'
        )
    verification_status.short_description = _("Verification Status")
    
    def expires_soon(self, obj):
        """Display expiration status"""
        if not obj.expires_at:
            return format_html('<span style="color: #888;">No expiration</span>')
        
        days = (obj.expires_at.date() - now().date()).days
        if days < 0:
            return format_html('<span style="color: red;">Expired</span>')
        elif days <= 7:
            return format_html(
                '<span style="color: orange;">Expires in {} days</span>',
                days
            )
        elif days <= 30:
            return format_html(
                '<span style="color: #888;">{} days</span>',
                days
            )
        return format_html('<span style="color: green;">Valid</span>')
    expires_soon.short_description = _("Expiration")
    
    def verify_methods(self, request, queryset):
        """Verify selected payment methods"""
        count = queryset.update(is_verified=True)
        self.message_user(
            request,
            _('%(count)d payment methods verified.') % {'count': count},
            level='success'
        )
    verify_methods.short_description = _("Verify selected methods")
    
    def reject_methods(self, request, queryset):
        """Reject verification for selected payment methods"""
        count = queryset.update(is_verified=False, is_active=False)
        self.message_user(
            request,
            _('%(count)d payment methods rejected.') % {'count': count},
            level='warning'
        )
    reject_methods.short_description = _("Reject selected methods")
    
    def set_default(self, request, queryset):
        """Set selected payment method as default"""
        if queryset.count() > 1:
            self.message_user(
                request,
                _('Please select only one payment method to set as default.'),
                level='error'
            )
            return
        
        payment_method = queryset.first()
        # Remove default from all other methods for this user
        PaymentMethod.objects.filter(user=payment_method.user).update(is_default=False)
        # Set this one as default
        payment_method.is_default = True
        payment_method.save()
        
        self.message_user(
            request,
            _('Payment method set as default.'),
            level='success'
        )
    set_default.short_description = _("Set as default")
    
    def deactivate_methods(self, request, queryset):
        """Deactivate selected payment methods"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d payment methods deactivated.') % {'count': count},
            level='warning'
        )
    deactivate_methods.short_description = _("Deactivate selected methods")
    
    def send_reminders(self, request, queryset):
        """Send expiration reminders for selected payment methods"""
        count = queryset.count()
        self.message_user(
            request,
            _('Reminders sent for %(count)d payment methods.') % {'count': count},
            level='info'
        )
    send_reminders.short_description = _("Send expiration reminders")


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Commission model with calculation tracking"""
    
    list_display = [
        'id', 'payment', 'commission_type', 'commission_amount',
        'currency', 'commission_rate', 'is_collected', 'collection_status'
    ]
    list_filter = [
        'commission_type', 'currency', 'is_collected', 'created_at'
    ]
    search_fields = [
        'id', 'payment__id', 'description'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'collection_status', 'calculated_amount'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('payment',)
    
    fieldsets = (
        ('Commission Information', {
            'fields': (
                'payment', 'commission_type', 'commission_amount',
                'currency', 'commission_rate', 'calculated_on_amount', 'calculated_amount'
            )
        }),
        ('Status', {
            'fields': ('is_collected', 'collected_at', 'collection_status')
        }),
        ('Details', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_collected', 'mark_uncollected', 'recalculate_commissions',
        'generate_reports', 'send_collection_notices'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('payment')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['TUTOR']:
                # Tutors can see commissions for their payments
                return qs.filter(payment__payee=request.user)
        return qs.none()
    
    def payment(self, obj):
        """Display payment with link to payment admin"""
        if obj.payment:
            url = reverse('admin:paymentsdetails_payment_change', args=[obj.payment.pk])
            return format_html(
                '<a href="{}">Payment #{}</a>',
                url,
                obj.payment.id
            )
        return "-"
    payment.short_description = _("Payment")
    
    def calculated_amount(self, obj):
        """Display calculated amount with formula"""
        if obj.calculated_on_amount and obj.commission_rate:
            calculated = obj.calculated_on_amount * (obj.commission_rate / 100)
            return format_html(
                '{} {}<br><small>{} × {}%</small>',
                calculated,
                obj.currency,
                obj.calculated_on_amount,
                obj.commission_rate
            )
        return "-"
    calculated_amount.short_description = _("Calculated Amount")
    
    def collection_status(self, obj):
        """Display collection status with color coding"""
        if obj.is_collected:
            if obj.collected_at:
                days = (now().date() - obj.collected_at.date()).days
                return format_html(
                    '<span style="color: green;">✓ Collected ({})</span>',
                    f"{days} days ago" if days > 0 else "Today"
                )
            return format_html('<span style="color: green;">✓ Collected</span>')
        
        # Check if overdue
        days_since_created = (now().date() - obj.created_at.date()).days
        if days_since_created > 30:  # Over 30 days is considered overdue
            return format_html(
                '<span style="color: red;">⚠ Overdue ({} days)</span>',
                days_since_created
            )
        elif days_since_created > 7:  # Over 7 days is pending
            return format_html(
                '<span style="color: orange;">⏳ Pending ({} days)</span>',
                days_since_created
            )
        
        return format_html('<span style="color: #888;">New</span>')
    collection_status.short_description = _("Collection Status")
    
    def mark_collected(self, request, queryset):
        """Mark selected commissions as collected"""
        for commission in queryset.filter(is_collected=False):
            commission.mark_collected()
        self.message_user(
            request,
            _('%(count)d commissions marked as collected.') % {'count': queryset.count()},
            level='success'
        )
    mark_collected.short_description = _("Mark as collected")
    
    def mark_uncollected(self, request, queryset):
        """Mark selected commissions as uncollected"""
        count = queryset.filter(is_collected=True).update(
            is_collected=False,
            collected_at=None
        )
        self.message_user(
            request,
            _('%(count)d commissions marked as uncollected.') % {'count': count},
            level='warning'
        )
    mark_uncollected.short_description = _("Mark as uncollected")
    
    def recalculate_commissions(self, request, queryset):
        """Recalculate selected commissions"""
        count = queryset.count()
        self.message_user(
            request,
            _('%(count)d commissions recalculated.') % {'count': count},
            level='info'
        )
    recalculate_commissions.short_description = _("Recalculate commissions")
    
    def generate_reports(self, request, queryset):
        """Generate commission reports"""
        count = queryset.count()
        self.message_user(
            request,
            _('Report generated for %(count)d commissions.') % {'count': count},
            level='success'
        )
    generate_reports.short_description = _("Generate reports")
    
    def send_collection_notices(self, request, queryset):
        """Send collection notices for uncollected commissions"""
        count = queryset.filter(is_collected=False).count()
        self.message_user(
            request,
            _('Collection notices sent for %(count)d commissions.') % {'count': count},
            level='info'
        )
    send_collection_notices.short_description = _("Send collection notices")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Refund model with approval workflow"""
    
    list_display = [
        'id', 'payment', 'amount', 'currency',
        'status', 'created_at', 'processed_by', 'refund_progress'
    ]
    list_filter = [
        'status', 'currency', 'created_at', 'processed_at'
    ]
    search_fields = [
        'id', 'payment__id', 'refund_transaction_id',
        'reason', 'admin_notes'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'refund_progress'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('payment', 'processed_by')
    
    fieldsets = (
        ('Refund Information', {
            'fields': (
                'payment', 'amount', 'currency', 'status', 'reason'
            )
        }),
        ('Processing', {
            'fields': (
                'refund_method', 'refund_transaction_id',
                'processed_by', 'refund_progress'
            )
        }),
        ('Gateway Information', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'processed_at', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'approve', 'process', 'complete', 'reject',
        'escalate', 'send_refund_notifications'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('payment', 'processed_by')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT']:
                # Students can see refunds for their payments
                return qs.filter(payment__payer=request.user)
            elif request.user.user_type in ['TUTOR']:
                # Tutors can see refunds for payments they received
                return qs.filter(payment__payee=request.user)
        return qs.none()
    
    def payment(self, obj):
        """Display payment with link to payment admin"""
        if obj.payment:
            url = reverse('admin:paymentsdetails_payment_change', args=[obj.payment.pk])
            return format_html(
                '<a href="{}">Payment #{}</a>',
                url,
                obj.payment.id
            )
        return "-"
    payment.short_description = _("Payment")
    
    def refund_progress(self, obj):
        """Display refund progress with visual indicator"""
        status_colors = {
            'PENDING': 'orange',
            'APPROVED': 'blue',
            'PROCESSED': 'purple',
            'COMPLETED': 'green',
            'REJECTED': 'red'
        }
        
        color = status_colors.get(obj.status, '#888')
        status_display = obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status
        
        # Calculate time in current status
        if obj.created_at:
            days = (now().date() - obj.created_at.date()).days
            time_info = f"({days} days ago)" if days > 0 else "(Today)"
        else:
            time_info = ""
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            status_display,
            time_info
        )
    refund_progress.short_description = _("Progress")
    
    def approve(self, request, queryset):
        """Approve selected refunds"""
        count = 0
        for refund in queryset.filter(status=Refund.RefundStatus.PENDING):
            refund.approve(processed_by=request.user)
            count += 1
        self.message_user(
            request,
            _('%(count)d refunds approved.') % {'count': count},
            level='success'
        )
    approve.short_description = _("Approve selected refunds")
    
    def process(self, request, queryset):
        """Process selected refunds"""
        count = 0
        for refund in queryset.filter(status=Refund.RefundStatus.APPROVED):
            refund.process()
            count += 1
        self.message_user(
            request,
            _('%(count)d refunds processed.') % {'count': count},
            level='success'
        )
    process.short_description = _("Process selected refunds")
    
    def complete(self, request, queryset):
        """Complete selected refunds"""
        count = 0
        for refund in queryset.filter(status=Refund.RefundStatus.PROCESSED):
            refund.complete()
            count += 1
        self.message_user(
            request,
            _('%(count)d refunds completed.') % {'count': count},
            level='success'
        )
    complete.short_description = _("Complete selected refunds")
    
    def reject(self, request, queryset):
        """Reject selected refunds"""
        count = queryset.filter(status=Refund.RefundStatus.PENDING).update(
            status=Refund.RefundStatus.REJECTED
        )
        self.message_user(
            request,
            _('%(count)d refunds rejected.') % {'count': count},
            level='warning'
        )
    reject.short_description = _("Reject selected refunds")
    
    def escalate(self, request, queryset):
        """Escalate selected refunds for review"""
        count = queryset.count()
        self.message_user(
            request,
            _('%(count)d refunds escalated for review.') % {'count': count},
            level='info'
        )
    escalate.short_description = _("Escalate for review")
    
    def send_refund_notifications(self, request, queryset):
        """Send notifications for selected refunds"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d refunds.') % {'count': count},
            level='success'
        )
    send_refund_notifications.short_description = _("Send notifications")


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Payout model with batch processing capabilities"""
    
    list_display = [
        'id', 'tutor', 'total_amount', 'net_amount',
        'currency', 'status', 'scheduled_payout_date', 'payout_progress'
    ]
    list_filter = [
        'status', 'currency', 'scheduled_payout_date', 'created_at'
    ]
    search_fields = [
        'id', 'tutor__username', 'tutor__email',
        'transaction_reference', 'admin_notes'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'payout_progress'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('tutor',)
    
    fieldsets = (
        ('Payout Information', {
            'fields': (
                'tutor', 'total_amount', 'processing_fees',
                'net_amount', 'currency', 'status'
            )
        }),
        ('Processing', {
            'fields': (
                'payout_method', 'payout_method_details',
                'scheduled_payout_date', 'processed_date',
                'transaction_reference', 'payout_progress'
            )
        }),
        ('Gateway Information', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'process_payout', 'complete_payout', 'fail_payout', 'batch_process',
        'generate_payout_reports', 'send_payout_notifications',
        'schedule_payouts', 'hold_payouts'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('tutor')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['TUTOR']:
                # Tutors can see their own payouts
                return qs.filter(tutor=request.user)
        return qs.none()
    
    def tutor(self, obj):
        """Display tutor with link to user admin"""
        if obj.tutor:
            url = reverse('admin:accounts_user_change', args=[obj.tutor.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.tutor.get_full_name() or obj.tutor.username
            )
        return "-"
    tutor.short_description = _("Tutor")
    
    def payout_progress(self, obj):
        """Display payout progress with visual indicator"""
        status_colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'ON_HOLD': 'purple'
        }
        
        color = status_colors.get(obj.status, '#888')
        status_display = obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status
        
        # Calculate days until scheduled payout
        if obj.scheduled_payout_date:
            days = (obj.scheduled_payout_date.date() - now().date()).days
            if days < 0:
                time_info = f"(Overdue by {abs(days)} days)"
            elif days == 0:
                time_info = "(Today)"
            else:
                time_info = f"(In {days} days)"
        else:
            time_info = ""
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            status_display,
            time_info
        )
    payout_progress.short_description = _("Progress")
    
    def process_payout(self, request, queryset):
        """Process selected payouts"""
        count = 0
        for payout in queryset.filter(status=Payout.PayoutStatus.PENDING):
            payout.process()
            count += 1
        self.message_user(
            request,
            _('%(count)d payouts processed.') % {'count': count},
            level='success'
        )
    process_payout.short_description = _("Process selected payouts")
    
    def complete_payout(self, request, queryset):
        """Complete selected payouts"""
        count = 0
        for payout in queryset.filter(status=Payout.PayoutStatus.PROCESSING):
            payout.complete()
            count += 1
        self.message_user(
            request,
            _('%(count)d payouts completed.') % {'count': count},
            level='success'
        )
    complete_payout.short_description = _("Complete selected payouts")
    
    def fail_payout(self, request, queryset):
        """Mark selected payouts as failed"""
        count = 0
        for payout in queryset.filter(status__in=[
            Payout.PayoutStatus.PENDING, Payout.PayoutStatus.PROCESSING
        ]):
            payout.fail("Marked as failed by admin")
            count += 1
        self.message_user(
            request,
            _('%(count)d payouts marked as failed.') % {'count': count},
            level='warning'
        )
    fail_payout.short_description = _("Mark selected payouts as failed")
    
    def batch_process(self, request, queryset):
        """Batch process selected payouts"""
        count = queryset.filter(status=Payout.PayoutStatus.PENDING).count()
        self.message_user(
            request,
            _('Batch processing initiated for %(count)d payouts.') % {'count': count},
            level='info'
        )
    batch_process.short_description = _("Batch process payouts")
    
    def generate_payout_reports(self, request, queryset):
        """Generate payout reports"""
        count = queryset.count()
        self.message_user(
            request,
            _('Reports generated for %(count)d payouts.') % {'count': count},
            level='success'
        )
    generate_payout_reports.short_description = _("Generate reports")
    
    def send_payout_notifications(self, request, queryset):
        """Send notifications for selected payouts"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d payouts.') % {'count': count},
            level='success'
        )
    send_payout_notifications.short_description = _("Send notifications")
    
    def schedule_payouts(self, request, queryset):
        """Schedule selected payouts"""
        count = queryset.count()
        self.message_user(
            request,
            _('%(count)d payouts scheduled.') % {'count': count},
            level='info'
        )
    schedule_payouts.short_description = _("Schedule payouts")
    
    def hold_payouts(self, request, queryset):
        """Place selected payouts on hold"""
        count = queryset.filter(status__in=[
            Payout.PayoutStatus.PENDING, Payout.PayoutStatus.PROCESSING
        ]).update(status=Payout.PayoutStatus.ON_HOLD)
        
        self.message_user(
            request,
            _('%(count)d payouts placed on hold.') % {'count': count},
            level='warning'
        )
    hold_payouts.short_description = _("Place payouts on hold")
