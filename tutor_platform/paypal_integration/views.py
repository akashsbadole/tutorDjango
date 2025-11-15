import json
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, FormView, DetailView, ListView, View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    PayPalAccount, PayPalTransaction, PayPalWebhook, 
    PayPalSubscription, PayPalRefund, PayPalDispute
)
from .forms import (
    PayPalPaymentForm, PayPalPayoutForm, PayPalSubscriptionForm, 
    PayPalAccountForm
)
from .services import PayPalAPIService, PayPalPaymentService, PayPalWebhookService
from .utils import verify_webhook_signature, process_paypal_response

logger = logging.getLogger(__name__)


class PayPalPaymentView(LoginRequiredMixin, FormView):
    """View for initiating PayPal payments"""
    template_name = 'paypal_integration/payment_form.html'
    form_class = PayPalPaymentForm
    success_url = reverse_lazy('paypal_integration:payment_success')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Get PayPal account for user
            paypal_account = PayPalAccount.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
            
            if not paypal_account:
                messages.error(self.request, 'Please link a PayPal account first.')
                return redirect('paypal_integration:account_link')
            
            # Create payment record
            payment_service = PayPalPaymentService()
            payment_data = form.cleaned_data
            
            # Create PayPal order
            paypal_order = payment_service.create_order(
                amount=payment_data['amount'],
                currency=payment_data['currency'],
                description=payment_data.get('description', ''),
                return_url=self.request.build_absolute_uri(reverse('paypal_integration:payment_success')),
                cancel_url=self.request.build_absolute_uri(reverse('paypal_integration:payment_cancel')),
                paypal_account=paypal_account
            )
            
            # Store order ID in session for verification
            self.request.session['paypal_order_id'] = paypal_order['id']
            
            # Redirect to PayPal for approval
            approval_url = None
            for link in paypal_order.get('links', []):
                if link.get('rel') == 'approve':
                    approval_url = link['href']
                    break
            
            if approval_url:
                return redirect(approval_url)
            else:
                messages.error(self.request, 'Could not create PayPal payment. Please try again.')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"PayPal payment creation error: {str(e)}")
            messages.error(self.request, 'An error occurred while creating the payment. Please try again.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PayPalSuccessView(LoginRequiredMixin, TemplateView):
    """View for handling successful PayPal payments"""
    template_name = 'paypal_integration/payment_success.html'
    
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('token')
        payer_id = request.GET.get('PayerID')
        
        if not order_id:
            messages.error(request, 'Invalid payment response.')
            return redirect('paypal_integration:payment_form')
        
        # Verify order ID matches session
        session_order_id = request.session.get('paypal_order_id')
        if not session_order_id or session_order_id != order_id:
            messages.error(request, 'Invalid payment session.')
            return redirect('paypal_integration:payment_form')
        
        try:
            # Get PayPal account
            paypal_account = PayPalAccount.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            
            if not paypal_account:
                messages.error(request, 'PayPal account not found.')
                return redirect('paypal_integration:payment_form')
            
            # Capture the payment
            payment_service = PayPalPaymentService()
            result = payment_service.capture_payment(
                order_id=order_id,
                payer_id=payer_id,
                paypal_account=paypal_account
            )
            
            if result['success']:
                # Clear session
                del request.session['paypal_order_id']
                
                # Create transaction record
                PayPalTransaction.objects.create(
                    paypal_transaction_id=result['transaction_id'],
                    paypal_order_id=order_id,
                    paypal_payer_id=payer_id,
                    paypal_status='COMPLETED',
                    amount=result['amount'],
                    currency=result['currency'],
                    fee_amount=result.get('fee_amount', Decimal('0.00')),
                    net_amount=result.get('net_amount', result['amount']),
                    paypal_account=paypal_account,
                    paypal_response=result['response']
                )
                
                messages.success(request, 'Payment completed successfully!')
                context = {
                    'transaction_id': result['transaction_id'],
                    'amount': result['amount'],
                    'currency': result['currency']
                }
                return self.render_to_response(context)
            else:
                messages.error(request, f'Payment failed: {result.get("error", "Unknown error")}')
                return redirect('paypal_integration:payment_form')
                
        except Exception as e:
            logger.error(f"PayPal payment capture error: {str(e)}")
            messages.error(request, 'An error occurred while processing your payment.')
            return redirect('paypal_integration:payment_form')


class PayPalCancelView(LoginRequiredMixin, TemplateView):
    """View for handling cancelled PayPal payments"""
    template_name = 'paypal_integration/payment_cancel.html'
    
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('token')
        
        if order_id:
            # Log the cancellation
            logger.info(f"PayPal payment cancelled for order: {order_id}")
        
        # Clear session if exists
        if 'paypal_order_id' in request.session:
            del request.session['paypal_order_id']
        
        return super().get(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class PayPalWebhookView(View):
    """View for processing PayPal webhooks"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Get webhook data
            payload = json.loads(request.body)
            headers = dict(request.headers)
            
            # Verify webhook signature
            if not verify_webhook_signature(payload, headers):
                logger.warning("Invalid PayPal webhook signature")
                return HttpResponseBadRequest("Invalid signature")
            
            # Get event details
            event_id = payload.get('id')
            event_type = payload.get('event_type')
            
            if not event_id or not event_type:
                logger.warning("Invalid webhook payload structure")
                return HttpResponseBadRequest("Invalid payload")
            
            # Check if webhook already processed
            if PayPalWebhook.objects.filter(event_id=event_id).exists():
                logger.info(f"Webhook {event_id} already processed")
                return HttpResponse("Already processed")
            
            # Create webhook record
            webhook = PayPalWebhook.objects.create(
                webhook_id=headers.get('PAYPAL-WEBHOOK-ID', ''),
                event_id=event_id,
                event_type=event_type,
                resource_type=payload.get('resource_type', ''),
                payload=payload,
                headers=headers,
                verification_status=True
            )
            
            # Process webhook
            webhook_service = PayPalWebhookService()
            success = webhook_service.process_webhook(webhook)
            
            if success:
                webhook.mark_processed()
                return HttpResponse("Processed")
            else:
                webhook.mark_failed("Processing failed")
                return HttpResponseBadRequest("Processing failed")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponseBadRequest("Invalid JSON")
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponseBadRequest("Processing error")


class PayPalPayoutView(LoginRequiredMixin, FormView):
    """View for tutor withdrawals via PayPal"""
    template_name = 'paypal_integration/payout_form.html'
    form_class = PayPalPayoutForm
    success_url = reverse_lazy('paypal_integration:payout_success')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Check if user is a tutor
            if not hasattr(self.request.user, 'user_type') or self.request.user.user_type != 'TUTOR':
                messages.error(self.request, 'Only tutors can request payouts.')
                return self.form_invalid(form)
            
            # Get PayPal account
            paypal_account = PayPalAccount.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
            
            if not paypal_account:
                messages.error(self.request, 'Please link a PayPal account first.')
                return redirect('paypal_integration:account_link')
            
            # Process payout
            payout_data = form.cleaned_data
            payment_service = PayPalPaymentService()
            
            result = payment_service.create_payout(
                amount=payout_data['amount'],
                currency=payout_data['currency'],
                paypal_account=paypal_account,
                recipient_email=paypal_account.paypal_email,
                note=payout_data.get('note', '')
            )
            
            if result['success']:
                # Create transaction record
                PayPalTransaction.objects.create(
                    paypal_transaction_id=result['payout_id'],
                    paypal_status='COMPLETED',
                    transaction_type=PayPalTransaction.TransactionType.PAYOUT,
                    amount=result['amount'],
                    currency=result['currency'],
                    fee_amount=result.get('fee_amount', Decimal('0.00')),
                    net_amount=result.get('net_amount', result['amount']),
                    paypal_account=paypal_account,
                    paypal_response=result['response']
                )
                
                messages.success(self.request, 'Payout request submitted successfully!')
                return super().form_valid(form)
            else:
                messages.error(self.request, f'Payout failed: {result.get("error", "Unknown error")}')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"PayPal payout creation error: {str(e)}")
            messages.error(self.request, 'An error occurred while creating the payout. Please try again.')
            return self.form_invalid(form)


class PayPalSubscriptionView(LoginRequiredMixin, FormView):
    """View for managing PayPal subscriptions"""
    template_name = 'paypal_integration/subscription_form.html'
    form_class = PayPalSubscriptionForm
    success_url = reverse_lazy('paypal_integration:subscription_success')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Get PayPal account
            paypal_account = PayPalAccount.objects.filter(
                user=self.request.user,
                is_active=True
            ).first()
            
            if not paypal_account:
                messages.error(self.request, 'Please link a PayPal account first.')
                return redirect('paypal_integration:account_link')
            
            # Create subscription
            subscription_data = form.cleaned_data
            payment_service = PayPalPaymentService()
            
            result = payment_service.create_subscription(
                plan_id=subscription_data['plan_id'],
                paypal_account=paypal_account,
                return_url=self.request.build_absolute_uri(reverse('paypal_integration:subscription_success')),
                cancel_url=self.request.build_absolute_uri(reverse('paypal_integration:subscription_cancel'))
            )
            
            if result['success']:
                # Store subscription ID in session
                self.request.session['paypal_subscription_id'] = result['subscription_id']
                
                # Redirect to PayPal for approval
                approval_url = result.get('approval_url')
                if approval_url:
                    return redirect(approval_url)
                else:
                    messages.error(self.request, 'Could not create subscription. Please try again.')
                    return self.form_invalid(form)
            else:
                messages.error(self.request, f'Subscription creation failed: {result.get("error", "Unknown error")}')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"PayPal subscription creation error: {str(e)}")
            messages.error(self.request, 'An error occurred while creating the subscription. Please try again.')
            return self.form_invalid(form)


class PayPalAccountLinkView(LoginRequiredMixin, FormView):
    """View for linking PayPal accounts"""
    template_name = 'paypal_integration/account_link.html'
    form_class = PayPalAccountForm
    success_url = reverse_lazy('paypal_integration:account_list')
    
    def form_valid(self, form):
        try:
            account_data = form.cleaned_data
            
            # Create PayPal account record
            paypal_account = PayPalAccount.objects.create(
                user=self.request.user,
                paypal_email=account_data['paypal_email'],
                paypal_user_id=account_data['paypal_user_id'],
                account_type=account_data['account_type'],
                verification_status=account_data['verification_status'],
                is_primary=account_data.get('is_primary', False),
                metadata=account_data.get('metadata', {})
            )
            
            messages.success(self.request, 'PayPal account linked successfully!')
            return super().form_valid(form)
            
        except Exception as e:
            logger.error(f"PayPal account linking error: {str(e)}")
            messages.error(self.request, 'An error occurred while linking your PayPal account. Please try again.')
            return self.form_invalid(form)


class PayPalAccountListView(LoginRequiredMixin, ListView):
    """View for listing user's PayPal accounts"""
    model = PayPalAccount
    template_name = 'paypal_integration/account_list.html'
    context_object_name = 'paypal_accounts'
    paginate_by = 10
    
    def get_queryset(self):
        return PayPalAccount.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class PayPalTransactionListView(LoginRequiredMixin, ListView):
    """View for listing user's PayPal transactions"""
    model = PayPalTransaction
    template_name = 'paypal_integration/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        return PayPalTransaction.objects.filter(
            paypal_account__user=self.request.user
        ).select_related('paypal_account').order_by('-created_at')


class PayPalSubscriptionListView(LoginRequiredMixin, ListView):
    """View for listing user's PayPal subscriptions"""
    model = PayPalSubscription
    template_name = 'paypal_integration/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 10
    
    def get_queryset(self):
        return PayPalSubscription.objects.filter(
            user=self.request.user
        ).select_related('paypal_account').order_by('-created_at')


@login_required
@require_http_methods(["POST"])
def cancel_paypal_subscription(request, subscription_id):
    """Cancel a PayPal subscription"""
    try:
        subscription = get_object_or_404(
            PayPalSubscription,
            paypal_subscription_id=subscription_id,
            user=request.user
        )
        
        if not subscription.is_active():
            messages.error(request, 'Subscription is already cancelled or inactive.')
            return redirect('paypal_integration:subscription_list')
        
        # Cancel with PayPal
        payment_service = PayPalPaymentService()
        result = payment_service.cancel_subscription(
            subscription_id=subscription_id,
            paypal_account=subscription.paypal_account
        )
        
        if result['success']:
            subscription.cancel(reason="User requested cancellation")
            messages.success(request, 'Subscription cancelled successfully.')
        else:
            messages.error(request, f'Failed to cancel subscription: {result.get("error", "Unknown error")}')
            
    except Exception as e:
        logger.error(f"PayPal subscription cancellation error: {str(e)}")
        messages.error(request, 'An error occurred while cancelling the subscription.')
    
    return redirect('paypal_integration:subscription_list')


@login_required
@require_http_methods(["POST"])
def refund_paypal_payment(request, transaction_id):
    """Process a PayPal refund"""
    try:
        transaction = get_object_or_404(
            PayPalTransaction,
            paypal_transaction_id=transaction_id,
            paypal_account__user=request.user
        )
        
        if transaction.paypal_status != 'COMPLETED':
            messages.error(request, 'Only completed transactions can be refunded.')
            return redirect('paypal_integration:transaction_list')
        
        # Get refund amount from form
        amount = Decimal(request.POST.get('amount', str(transaction.amount)))
        reason = request.POST.get('reason', 'Refund requested by user')
        
        if amount > transaction.amount:
            messages.error(request, 'Refund amount cannot exceed transaction amount.')
            return redirect('paypal_integration:transaction_list')
        
        # Process refund with PayPal
        payment_service = PayPalPaymentService()
        result = payment_service.create_refund(
            transaction_id=transaction_id,
            amount=amount,
            paypal_account=transaction.paypal_account,
            reason=reason
        )
        
        if result['success']:
            # Create refund record
            PayPalRefund.objects.create(
                paypal_refund_id=result['refund_id'],
                paypal_transaction=transaction,
                amount=amount,
                currency=transaction.currency,
                status=PayPalRefund.RefundStatus.COMPLETED,
                reason=reason,
                paypal_response=result['response'],
                processed_at=timezone.now()
            )
            
            messages.success(request, 'Refund processed successfully.')
        else:
            messages.error(request, f'Refund failed: {result.get("error", "Unknown error")}')
            
    except Exception as e:
        logger.error(f"PayPal refund processing error: {str(e)}")
        messages.error(request, 'An error occurred while processing the refund.')
    
    return redirect('paypal_integration:transaction_list')
