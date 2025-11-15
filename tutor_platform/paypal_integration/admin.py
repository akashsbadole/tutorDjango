"""
Admin configuration for PayPal integration models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    PayPalAccount, PayPalTransaction, PayPalWebhook, 
    PayPalSubscription, PayPalRefund, PayPalDispute
)


@admin.register(PayPalAccount)
class PayPalAccountAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal accounts"""
    
    list_display = [
        'user', 'paypal_email', 'account_type', 'verification_status',
        'is_primary', 'is_active', 'created_at'
    ]
    list_filter = [
        'account_type', 'verification_status', 'is_primary', 'is_active',
        'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name', 'paypal_email',
        'paypal_user_id'
    ]
    readonly_fields = [
        'paypal_user_id', 'access_token', 'refresh_token', 'token_expires_at',
        'created_at', 'updated_at'
    ]
    list_editable = ['is_primary', 'is_active']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'paypal_email', 'paypal_user_id')
        }),
        ('Account Details', {
            'fields': ('account_type', 'verification_status', 'is_primary', 'is_active')
        }),
        ('API Credentials', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user')
    
    def user_email(self, obj):
        """Display user email with link"""
        if obj.user:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:accounts_user_change', args=[obj.user.id]),
                obj.user.email
            )
        return '-'
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def is_token_expired(self, obj):
        """Check if token is expired"""
        if obj.token_expires_at:
            from django.utils import timezone
            is_expired = timezone.now() > obj.token_expires_at
            if is_expired:
                return format_html(
                    '<span style="color: red;">⚠ Expired</span>'
                )
            else:
                return format_html(
                    '<span style="color: green;">✓ Valid</span>'
                )
        return '-'
    is_token_expired.short_description = 'Token Status'
    is_token_expired.admin_order_field = 'token_expires_at'


@admin.register(PayPalTransaction)
class PayPalTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal transactions"""
    
    list_display = [
        'paypal_transaction_id', 'paypal_account', 'paypal_status',
        'amount', 'currency', 'fee_amount', 'net_amount',
        'created_at'
    ]
    list_filter = [
        'paypal_status', 'currency', 'transaction_type', 'created_at'
    ]
    search_fields = [
        'paypal_transaction_id', 'paypal_order_id', 'paypal_payment_id',
        'paypal_payer_id', 'paypal_account__paypal_email',
        'paypal_account__user__email'
    ]
    readonly_fields = [
        'paypal_transaction_id', 'paypal_order_id', 'paypal_payment_id',
        'paypal_payer_id', 'paypal_status', 'paypal_intent', 'amount',
        'currency', 'fee_amount', 'net_amount', 'paypal_response',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'paypal_transaction_id', 'paypal_order_id', 'paypal_payment_id',
                'paypal_payer_id', 'paypal_status', 'paypal_intent'
            )
        }),
        ('Financial Details', {
            'fields': (
                'amount', 'currency', 'fee_amount', 'net_amount'
            )
        }),
        ('Account Information', {
            'fields': ('paypal_account',)
        }),
        ('Response Data', {
            'fields': ('paypal_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('paypal_account__user')
    
    def paypal_account_email(self, obj):
        """Display PayPal account email"""
        if obj.paypal_account:
            return obj.paypal_account.paypal_email
        return '-'
    paypal_account_email.short_description = 'PayPal Account'
    paypal_account_email.admin_order_field = 'paypal_account__paypal_email'
    
    def status_badge(self, obj):
        """Display status with color coding"""
        status_colors = {
            'COMPLETED': 'green',
            'PENDING': 'orange',
            'FAILED': 'red',
            'CANCELLED': 'red',
            'REFUNDED': 'blue',
        }
        color = status_colors.get(obj.paypal_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.paypal_status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'paypal_status'
    
    def has_refund(self, obj):
        """Check if transaction has refunds"""
        if obj.refunds.exists():
            return format_html(
                '<span style="color: red;">✓ Yes</span>'
            )
        return format_html(
            '<span style="color: green;">✗ No</span>'
        )
    has_refund.short_description = 'Refunded'
    has_refund.boolean = True


@admin.register(PayPalWebhook)
class PayPalWebhookAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal webhooks"""
    
    list_display = [
        'event_id', 'event_type', 'resource_type', 'verification_status',
        'status', 'created_at'
    ]
    list_filter = [
        'event_type', 'resource_type', 'verification_status', 'status',
        'created_at'
    ]
    search_fields = [
        'event_id', 'webhook_id', 'event_type', 'resource_type'
    ]
    readonly_fields = [
        'webhook_id', 'event_id', 'event_type', 'resource_type',
        'payload', 'headers', 'verification_status', 'status',
        'error_message', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Webhook Information', {
            'fields': (
                'webhook_id', 'event_id', 'event_type', 'resource_type'
            )
        }),
        ('Processing Status', {
            'fields': (
                'verification_status', 'status', 'error_message'
            )
        }),
        ('Request Data', {
            'fields': ('headers',),
            'classes': ('collapse',)
        }),
        ('Payload Data', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request)
    
    def event_type_badge(self, obj):
        """Display event type with color coding"""
        event_colors = {
            'PAYMENT': 'green',
            'BILLING': 'blue',
            'CHECKOUT': 'orange',
            'DISPUTE': 'red',
            'MERCHANT': 'purple',
            'RISK': 'red',
        }
        
        # Extract main event type
        main_type = obj.event_type.split('.')[0] if obj.event_type else 'UNKNOWN'
        color = event_colors.get(main_type, 'gray')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.event_type
        )
    event_type_badge.short_description = 'Event Type'
    event_type_badge.admin_order_field = 'event_type'
    
    def payload_preview(self, obj):
        """Show preview of payload"""
        if obj.payload:
            import json
            preview = json.dumps(obj.payload, indent=2)
            if len(preview) > 200:
                preview = preview[:200] + '...'
            return format_html(
                '<pre style="font-size: 11px; max-height: 100px; overflow-y: auto;">{}</pre>',
                preview
            )
        return '-'
    payload_preview.short_description = 'Payload Preview'
    
    actions = ['reprocess_webhook', 'verify_webhook']
    
    def reprocess_webhook(self, request, queryset):
        """Reprocess selected webhooks"""
        from .services import PayPalWebhookService
        
        count = 0
        for webhook in queryset:
            try:
                service = PayPalWebhookService()
                if service.process_webhook(webhook):
                    webhook.mark_processed()
                    count += 1
            except Exception as e:
                webhook.mark_failed(str(e))
        
        self.message_user(
            request,
            f'Successfully reprocessed {count} out of {queryset.count()} webhooks.',
            'success'
        )
    reprocess_webhook.short_description = 'Reprocess selected webhooks'
    
    def verify_webhook(self, request, queryset):
        """Verify selected webhooks"""
        from .utils import verify_webhook_signature
        
        count = 0
        for webhook in queryset:
            try:
                if verify_webhook_signature(webhook.payload, webhook.headers):
                    webhook.verification_status = True
                    webhook.save()
                    count += 1
            except Exception:
                pass
        
        self.message_user(
            request,
            f'Successfully verified {count} out of {queryset.count()} webhooks.',
            'success'
        )
    verify_webhook.short_description = 'Verify selected webhooks'


@admin.register(PayPalSubscription)
class PayPalSubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal subscriptions"""
    
    list_display = [
        'paypal_subscription_id', 'user', 'paypal_plan_id', 'status',
        'amount', 'currency', 'created_at'
    ]
    list_filter = [
        'status', 'currency', 'created_at'
    ]
    search_fields = [
        'paypal_subscription_id', 'plan_id', 'user__email',
        'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'paypal_subscription_id', 'paypal_plan_id', 'status', 'amount',
        'currency', 'created_at', 'updated_at', 'cancelled_at',
        'paypal_response'
    ]
    
    fieldsets = (
        ('Subscription Details', {
            'fields': (
                'paypal_subscription_id', 'paypal_plan_id',
                'status', 'amount', 'currency'
            )
        }),
        ('Account Information', {
            'fields': ('user', 'paypal_account')
        }),
        ('Billing Information', {
            'fields': (
                'next_billing_date', 'cancelled_at', 'cancellation_reason'
            )
        }),
        ('Response Data', {
            'fields': ('paypal_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user', 'paypal_account')
    
    def status_badge(self, obj):
        """Display status with color coding"""
        status_colors = {
            'ACTIVE': 'green',
            'CANCELLED': 'red',
            'EXPIRED': 'orange',
            'SUSPENDED': 'red',
            'PENDING': 'orange',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def is_active(self, obj):
        """Check if subscription is active"""
        return obj.status == 'ACTIVE'
    is_active.boolean = True
    is_active.short_description = 'Active'
    
    actions = ['cancel_subscription', 'reactivate_subscription']
    
    def cancel_subscription(self, request, queryset):
        """Cancel selected subscriptions"""
        from .services import PayPalPaymentService
        
        count = 0
        for subscription in queryset:
            if subscription.status == 'ACTIVE':
                try:
                    service = PayPalPaymentService()
                    if service.cancel_subscription(
                        subscription.paypal_subscription_id,
                        subscription.paypal_account
                    ):
                        subscription.cancel(reason="Cancelled by admin")
                        count += 1
                except Exception:
                    pass
        
        self.message_user(
            request,
            f'Successfully cancelled {count} out of {queryset.count()} subscriptions.',
            'success'
        )
    cancel_subscription.short_description = 'Cancel selected subscriptions'
    
    def reactivate_subscription(self, request, queryset):
        """Reactivate selected subscriptions"""
        from .services import PayPalPaymentService
        
        count = 0
        for subscription in queryset:
            if subscription.status in ['CANCELLED', 'SUSPENDED']:
                try:
                    service = PayPalPaymentService()
                    if service.reactivate_subscription(
                        subscription.paypal_subscription_id,
                        subscription.paypal_account
                    ):
                        subscription.reactivate()
                        count += 1
                except Exception:
                    pass
        
        self.message_user(
            request,
            f'Successfully reactivated {count} out of {queryset.count()} subscriptions.',
            'success'
        )
    reactivate_subscription.short_description = 'Reactivate selected subscriptions'


@admin.register(PayPalRefund)
class PayPalRefundAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal refunds"""
    
    list_display = [
        'paypal_refund_id', 'paypal_transaction', 'amount', 'currency',
        'status', 'reason', 'processed_at'
    ]
    list_filter = [
        'status', 'currency', 'processed_at'
    ]
    search_fields = [
        'paypal_refund_id', 'paypal_transaction__paypal_transaction_id',
        'reason', 'paypal_transaction__paypal_account__user__email'
    ]
    readonly_fields = [
        'paypal_refund_id', 'paypal_transaction', 'amount', 'currency',
        'status', 'reason', 'paypal_response', 'created_at',
        'updated_at', 'processed_at'
    ]
    
    fieldsets = (
        ('Refund Details', {
            'fields': (
                'paypal_refund_id', 'paypal_transaction', 'amount',
                'currency', 'status', 'reason'
            )
        }),
        ('Response Data', {
            'fields': ('paypal_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'paypal_transaction__paypal_account__user'
        )
    
    def status_badge(self, obj):
        """Display status with color coding"""
        status_colors = {
            'COMPLETED': 'green',
            'PENDING': 'orange',
            'FAILED': 'red',
            'CANCELLED': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def transaction_link(self, obj):
        """Link to transaction"""
        if obj.paypal_transaction:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:paypal_integration_paypaltransaction_change', 
                       args=[obj.paypal_transaction.id]),
                obj.paypal_transaction.paypal_transaction_id
            )
        return '-'
    transaction_link.short_description = 'Transaction'
    transaction_link.admin_order_field = 'paypal_transaction__paypal_transaction_id'


@admin.register(PayPalDispute)
class PayPalDisputeAdmin(admin.ModelAdmin):
    """Admin configuration for PayPal disputes"""
    
    list_display = [
        'paypal_dispute_id', 'paypal_transaction', 'status',
        'reason', 'amount', 'currency', 'created_at'
    ]
    list_filter = [
        'status', 'reason', 'currency', 'created_at'
    ]
    search_fields = [
        'paypal_dispute_id', 'paypal_transaction__paypal_transaction_id',
        'reason', 'paypal_transaction__paypal_account__user__email'
    ]
    readonly_fields = [
        'paypal_dispute_id', 'paypal_transaction', 'status',
        'reason', 'amount', 'currency',
        'paypal_response', 'created_at', 'updated_at', 'resolved_at'
    ]
    
    fieldsets = (
        ('Dispute Details', {
            'fields': (
                'paypal_dispute_id', 'paypal_transaction', 'status',
                'reason', 'amount', 'currency'
            )
        }),
        ('Resolution', {
            'fields': (
                'resolution', 'resolved_at'
            )
        }),
        ('Response Data', {
            'fields': ('paypal_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'paypal_transaction__paypal_account__user'
        )
    
    def status_badge(self, obj):
        """Display status with color coding"""
        status_colors = {
            'OPEN': 'orange',
            'WAITING_FOR_BUYER_RESPONSE': 'orange',
            'WAITING_FOR_SELLER_RESPONSE': 'orange',
            'UNDER_REVIEW': 'blue',
            'RESOLVED': 'green',
            'CLOSED': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def is_resolved(self, obj):
        """Check if dispute is resolved"""
        return obj.status in ['RESOLVED', 'CLOSED']
    is_resolved.boolean = True
    is_resolved.short_description = 'Resolved'
    
    actions = ['respond_to_dispute', 'escalate_dispute']
    
    def respond_to_dispute(self, request, queryset):
        """Respond to selected disputes"""
        count = queryset.count()
        self.message_user(
            request,
            f'Please use the dispute response form to respond to {count} disputes.',
            'info'
        )
    respond_to_dispute.short_description = 'Respond to disputes'
    
    def escalate_dispute(self, request, queryset):
        """Escalate selected disputes"""
        from .services import PayPalPaymentService
        
        count = 0
        for dispute in queryset:
            if dispute.status in ['OPEN', 'WAITING_FOR_SELLER_RESPONSE']:
                try:
                    service = PayPalPaymentService()
                    if service.escalate_dispute(
                        dispute.paypal_dispute_id,
                        dispute.paypal_transaction.paypal_account
                    ):
                        dispute.escalate()
                        count += 1
                except Exception:
                    pass
        
        self.message_user(
            request,
            f'Successfully escalated {count} out of {queryset.count()} disputes.',
            'success'
        )
    escalate_dispute.short_description = 'Escalate disputes'


# Customize admin site header
admin.site.site_header = "PayPal Integration Administration"
admin.site.site_title = "PayPal Integration Admin"
