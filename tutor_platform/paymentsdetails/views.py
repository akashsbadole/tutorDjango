"""
Views for payment processing and financial management.
"""

from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, models
from search.utils import get_search_backend
from search.models import SearchQuery

from .models import (
    Payment, EscrowAccount, Transaction, PaymentMethod,
    Commission, Refund, Payout
)
from .forms import (
    PaymentMethodForm, PayoutRequestForm, RefundRequestForm,
    DepositForm, WithdrawalForm, PaymentSearchForm, TransactionSearchForm
)
from .utils import (
    process_escrow_payment, release_escrow_funds, create_payout,
    process_payout, process_refund, get_user_balance_summary,
    validate_payment_method, create_payment
)


@login_required
def dashboard(request):
    """
    Payment dashboard for users showing balance and recent transactions.
    """
    # Get user's balance summary
    balance_summary = get_user_balance_summary(request.user)
    
    # Get recent transactions
    recent_transactions = Transaction.objects.for_user(request.user)[:10]
    
    # Get pending payments
    pending_payments = Payment.objects.for_user(request.user).pending()
    
    # Get pending payouts (for tutors)
    pending_payouts = []
    if request.user.user_type == 'TUTOR':
        pending_payouts = Payout.objects.for_tutor(request.user).pending()
    
    context = {
        'balance_summary': balance_summary,
        'recent_transactions': recent_transactions,
        'pending_payments': pending_payments,
        'pending_payouts': pending_payouts,
    }
    
    return render(request, 'paymentsdetails/dashboard.html', context)


class PaymentMethodListView(LoginRequiredMixin, ListView):
    """List user's payment methods."""
    model = PaymentMethod
    template_name = 'paymentsdetails/payment_method_list.html'
    context_object_name = 'payment_methods'
    
    def get_queryset(self):
        return PaymentMethod.objects.for_user(self.request.user).active()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['default_method'] = PaymentMethod.objects.default_for_user(self.request.user)
        return context


class PaymentMethodCreateView(LoginRequiredMixin, CreateView):
    """Add a new payment method."""
    model = PaymentMethod
    form_class = PaymentMethodForm
    template_name = 'paymentsdetails/payment_method_form.html'
    success_url = reverse_lazy('paymentsdetails:payment_methods')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Payment method added successfully.')
        return super().form_valid(form)


class PaymentMethodUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing payment method."""
    model = PaymentMethod
    form_class = PaymentMethodForm
    template_name = 'paymentsdetails/payment_method_form.html'
    success_url = reverse_lazy('paymentsdetails:payment_methods')
    
    def get_queryset(self):
        return PaymentMethod.objects.for_user(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Payment method updated successfully.')
        return super().form_valid(form)


@login_required
def set_default_payment_method(request, pk):
    """Set a payment method as default."""
    payment_method = get_object_or_404(
        PaymentMethod,
        pk=pk,
        user=request.user
    )
    
    with transaction.atomic():
        # Remove default from all other methods
        PaymentMethod.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        # Set this one as default
        payment_method.is_default = True
        payment_method.save()
    
    messages.success(request, f'{payment_method.display_name} set as default payment method.')
    return redirect('paymentsdetails:payment_methods')


@login_required
def delete_payment_method(request, pk):
    """Delete a payment method."""
    payment_method = get_object_or_404(
        PaymentMethod,
        pk=pk,
        user=request.user
    )
    
    # Check if method is being used
    if Payment.objects.filter(payment_method=payment_method).exists():
        messages.error(request, 'Cannot delete payment method that is being used.')
        return redirect('paymentsdetails:payment_methods')
    
    payment_method.delete()
    messages.success(request, 'Payment method deleted successfully.')
    return redirect('paymentsdetails:payment_methods')


class TransactionListView(LoginRequiredMixin, ListView):
    """Show transaction history for users with filtering and pagination."""
    model = Transaction
    template_name = 'paymentsdetails/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.for_user(user)
        
        # Check if this is a search request
        search_query = self.request.GET.get('q')
        if search_query:
            # Record the search query
            SearchQuery.objects.create(
                user=user,
                query=search_query,
                content_type='paymentsdetails.transaction',
                ip_address=self.get_client_ip(self.request),
            )
            
            # Use search backend to find transactions
            backend = get_search_backend()
            search_results = backend.search(
                query=search_query,
                user=user,
                content_types=['paymentsdetails.transaction'],
                filters={'user': user.id}
            )
            
            # Get transaction IDs from search results
            transaction_ids = [result['object_id'] for result in search_results.get('results', [])]
            
            # Return transactions matching search results
            return Transaction.objects.filter(
                id__in=transaction_ids,
                user=user
            ).order_by('-created_at')
        
        # Apply search form filters
        search_form = TransactionSearchForm(self.request.GET)
        if search_form.is_valid():
            # Filter by transaction type
            transaction_type = search_form.cleaned_data.get('transaction_type')
            if transaction_type:
                queryset = queryset.filter(transaction_type=transaction_type)
            
            # Filter by date range
            date_from = search_form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            date_to = search_form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Order by creation date (newest first)
        return queryset.order_by('-created_at')
    
    def get_client_ip(self, request):
        """Helper method to get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search form to context
        search_form = TransactionSearchForm(self.request.GET)
        context['search_form'] = search_form
        
        # Add search query to context if it exists
        search_query = self.request.GET.get('q')
        if search_query:
            context['search_query'] = search_query
            context['is_search'] = True
        
        # Add filter choices
        context['transaction_types'] = Transaction.TransactionType.choices
        
        # Add current filter values for highlighting
        context['current_filters'] = {
            'transaction_type': self.request.GET.get('transaction_type', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        }
        
        # Add summary statistics
        queryset = self.get_queryset()
        total_count = queryset.count()
        total_amount = queryset.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Calculate totals by transaction type
        type_totals = {}
        for ttype, _ in Transaction.TransactionType.choices:
            type_totals[ttype] = queryset.filter(
                transaction_type=ttype
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        context.update({
            'total_count': total_count,
            'total_amount': total_amount,
            'type_totals': type_totals,
        })
        
        return context


class PaymentListView(LoginRequiredMixin, ListView):
    """List all payments with filtering and pagination."""
    model = Payment
    template_name = 'paymentsdetails/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.for_user(user)
        
        # Check if this is a search request
        search_query = self.request.GET.get('q')
        if search_query:
            # Record the search query
            SearchQuery.objects.create(
                user=user,
                query=search_query,
                content_type='paymentsdetails.payment',
                ip_address=self.get_client_ip(self.request),
            )
            
            # Use search backend to find payments
            backend = get_search_backend()
            search_results = backend.search(
                query=search_query,
                user=user,
                content_types=['paymentsdetails.payment'],
                filters={'user': user.id}
            )
            
            # Get payment IDs from search results
            payment_ids = [result['object_id'] for result in search_results.get('results', [])]
            
            # Return payments matching search results
            return Payment.objects.filter(
                id__in=payment_ids,
                payer=user
            ).order_by('-created_at')
        
        # Apply search form filters
        search_form = PaymentSearchForm(self.request.GET)
        if search_form.is_valid():
            # Filter by status
            status = search_form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Filter by payment type
            payment_type = search_form.cleaned_data.get('payment_type')
            if payment_type:
                queryset = queryset.filter(payment_type=payment_type)
            
            # Filter by date range
            date_from = search_form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            date_to = search_form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            
            # Filter by amount range
            amount_min = search_form.cleaned_data.get('amount_min')
            if amount_min:
                queryset = queryset.filter(amount__gte=amount_min)
            
            amount_max = search_form.cleaned_data.get('amount_max')
            if amount_max:
                queryset = queryset.filter(amount__lte=amount_max)
        
        # Order by creation date (newest first)
        return queryset.order_by('-created_at')
    
    def get_client_ip(self, request):
        """Helper method to get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search form to context
        search_form = PaymentSearchForm(self.request.GET)
        context['search_form'] = search_form
        
        # Add search query to context if it exists
        search_query = self.request.GET.get('q')
        if search_query:
            context['search_query'] = search_query
            context['is_search'] = True
        
        # Add filter choices
        context['payment_statuses'] = Payment.PaymentStatus.choices
        context['payment_types'] = Payment.PaymentType.choices
        
        # Add current filter values for highlighting
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'payment_type': self.request.GET.get('payment_type', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'amount_min': self.request.GET.get('amount_min', ''),
            'amount_max': self.request.GET.get('amount_max', ''),
        }
        
        # Add summary statistics
        queryset = self.get_queryset()
        total_count = queryset.count()
        total_amount = queryset.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        context.update({
            'total_count': total_count,
            'total_amount': total_amount,
        })
        
        return context


class PaymentDetailView(LoginRequiredMixin, DetailView):
    """Show payment details."""
    model = Payment
    template_name = 'paymentsdetails/payment_detail.html'
    context_object_name = 'payment'
    
    def get_queryset(self):
        return Payment.objects.for_user(self.request.user)


@login_required
def make_payment(request, award_id):
    """
    Initiate a payment for an award.
    """
    from requirements.models import Award
    
    award = get_object_or_404(Award, id=award_id)
    
    # Check if payment already exists
    if Payment.objects.for_award(award).exists():
        messages.error(request, 'Payment already initiated for this award.')
        return redirect('paymentsdetails:payment_detail', pk=award.payments.first().pk)
    
    # Get user's payment methods
    payment_methods = PaymentMethod.objects.usable(request.user)
    
    if not payment_methods:
        messages.error(request, 'Please add a payment method first.')
        return redirect('paymentsdetails:payment_method_create')
    
    # Check if user wants to use PayPal
    use_paypal = request.GET.get('paypal', 'false').lower() == 'true'
    
    if use_paypal:
        # Redirect to PayPal payment flow
        from paypal_integration.models import PayPalAccount
        paypal_account = PayPalAccount.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        if not paypal_account:
            messages.error(request, 'Please link a PayPal account first.')
            return redirect('paypal_integration:account_link')
        
        # Create payment with PayPal
        return redirect(f'/paypal/payment/?award_id={award_id}')
    
    context = {
        'award': award,
        'payment_methods': payment_methods,
        'default_method': PaymentMethod.objects.default_for_user(request.user),
        'paypal_available': True,  # PayPal is available as payment option
    }
    
    return render(request, 'paymentsdetails/payment_form.html', context)


class PayoutRequestView(LoginRequiredMixin, FormView):
    """Request a payout."""
    form_class = PayoutRequestForm
    template_name = 'paymentsdetails/payout_request.html'
    success_url = reverse_lazy('paymentsdetails:payouts')
    
    def dispatch(self, request, *args, **kwargs):
        # Only tutors can request payouts
        if request.user.user_type != 'TUTOR':
            messages.error(request, 'Only tutors can request payouts.')
            return redirect('paymentsdetails:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                payment_method = form.cleaned_data['payment_method']
                
                # Check if this is a PayPal payout
                if payment_method.method_type in [
                    PaymentMethod.MethodType.PAYPAL,
                    PaymentMethod.MethodType.PAYPAL_BALANCE
                ]:
                    # Redirect to PayPal payout flow
                    return redirect(f'/paypal/payout/?amount={form.cleaned_data["amount"]}')
                
                # Create regular payout
                payout = create_payout(
                    tutor=self.request.user,
                    amount=form.cleaned_data['amount'],
                    payment_method=payment_method,
                    processing_fees=form.cleaned_data['processing_fees']
                )
                
                messages.success(
                    self.request,
                    f'Payout request for {payout.total_amount} {payout.currency} submitted successfully.'
                )
                return super().form_valid(form)
                
        except Exception as e:
            messages.error(self.request, f'Error creating payout: {str(e)}')
            return self.form_invalid(form)


class PayoutListView(LoginRequiredMixin, ListView):
    """List user's payouts."""
    model = Payout
    template_name = 'paymentsdetails/payout_list.html'
    context_object_name = 'payouts'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Only tutors have payouts
        if request.user.user_type != 'TUTOR':
            messages.error(request, 'Only tutors can view payouts.')
            return redirect('paymentsdetails:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Payout.objects.for_tutor(self.request.user)
        
        # Filter by status if specified
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payout_statuses'] = Payout.PayoutStatus.choices
        context['current_status'] = self.request.GET.get('status', '')
        return context


class RefundRequestView(LoginRequiredMixin, FormView):
    """Request a refund for a payment."""
    form_class = RefundRequestForm
    template_name = 'paymentsdetails/refund_request.html'
    
    def dispatch(self, request, *args, **kwargs):
        payment_id = kwargs.get('payment_id')
        self.payment = get_object_or_404(
            Payment,
            id=payment_id,
            payer=request.user  # Only payer can request refund
        )
        
        # Check if refund is possible
        if self.payment.status not in [Payment.PaymentStatus.COMPLETED]:
            messages.error(request, 'Refund can only be requested for completed payments.')
            return redirect('paymentsdetails:payment_detail', pk=payment_id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['payment'] = self.payment
        return kwargs
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                refund_method = form.cleaned_data['refund_method']
                
                # Check if this is a PayPal refund
                if refund_method.method_type in [
                    PaymentMethod.MethodType.PAYPAL,
                    PaymentMethod.MethodType.PAYPAL_BALANCE
                ]:
                    # Redirect to PayPal refund flow
                    return redirect(f'/paypal/refund/{self.payment.transaction_id}/')
                
                # Process regular refund
                refund = process_refund(
                    payment=self.payment,
                    amount=form.cleaned_data['amount'],
                    reason=form.cleaned_data['reason'],
                    refund_method=refund_method
                )
                
                messages.success(
                    self.request,
                    f'Refund request for {refund.amount} {refund.currency} submitted successfully.'
                )
                return redirect('paymentsdetails:payment_detail', pk=self.payment.pk)
                
        except Exception as e:
            messages.error(self.request, f'Error processing refund: {str(e)}')
            return self.form_invalid(form)


class EscrowAccountView(LoginRequiredMixin, TemplateView):
    """Display user's escrow balance with deposit/withdraw options."""
    template_name = 'paymentsdetails/escrow_account.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create escrow account
        escrow_account = getattr(self.request.user, 'escrow_account', None)
        if not escrow_account:
            from .models import EscrowAccount
            escrow_account = EscrowAccount.objects.create(
                user=self.request.user,
                currency='USD'
            )
        
        # Get balance summary
        balance_summary = get_user_balance_summary(self.request.user)
        
        # Get recent transactions
        recent_transactions = Transaction.objects.for_user(self.request.user)[:10]
        
        # Initialize forms
        context.update({
            'escrow_account': escrow_account,
            'balance_summary': balance_summary,
            'recent_transactions': recent_transactions,
            'deposit_form': DepositForm(user=self.request.user),
            'withdrawal_form': WithdrawalForm(user=self.request.user),
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle deposit or withdrawal form submissions."""
        action = request.POST.get('action')
        
        if action == 'deposit':
            form = DepositForm(request.POST, user=request.user)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Create payment for deposit
                        payment = create_payment(
                            payer=request.user,
                            payee=request.user,  # Depositing to own account
                            amount=form.cleaned_data['amount'],
                            payment_type=Payment.PaymentType.ESCROW_DEPOSIT,
                            payment_method=form.cleaned_data['payment_method'],
                            description=form.cleaned_data['description'] or 'Deposit to escrow'
                        )
                        
                        # Process payment with payment gateway (simplified)
                        # In a real implementation, this would integrate with Stripe/PayPal
                        payment.mark_completed()
                        
                        messages.success(
                            request,
                            f'Successfully deposited {form.cleaned_data["amount"]} to your escrow account.'
                        )
                except Exception as e:
                    messages.error(request, f'Error processing deposit: {str(e)}')
        
        elif action == 'withdraw':
            form = WithdrawalForm(request.POST, user=request.user)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Get escrow account
                        escrow_account = request.user.escrow_account
                        
                        # Withdraw funds
                        escrow_account.withdraw_funds(form.cleaned_data['amount'])
                        
                        # Create withdrawal record
                        payment = create_payment(
                            payer=request.user,
                            payee=request.user,  # Withdrawing from own account
                            amount=form.cleaned_data['amount'],
                            payment_type=Payment.PaymentType.PAYOUT,
                            payment_method=form.cleaned_data['payment_method'],
                            description=form.cleaned_data['description'] or 'Withdrawal from escrow'
                        )
                        
                        messages.success(
                            request,
                            f'Successfully withdrew {form.cleaned_data["amount"]} from your escrow account.'
                        )
                except Exception as e:
                    messages.error(request, f'Error processing withdrawal: {str(e)}')
        
        return redirect('paymentsdetails:escrow_account')


# Webhook handlers for payment gateways
@method_decorator(csrf_exempt, name='dispatch')
def stripe_webhook(request):
    """Handle Stripe webhooks with validation and processing."""
    import json
    import hmac
    import hashlib
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the Stripe signature from headers
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        if not sig_header:
            return JsonResponse({'error': 'Missing signature'}, status=400)
        
        # Get the webhook payload
        payload = request.body
        event = json.loads(payload)
        
        # Verify the webhook signature (in production, use your webhook secret)
        webhook_secret = 'whsec_...'  # Replace with your actual webhook secret
        try:
            # This is a simplified verification - in production use Stripe's SDK
            sig = sig_header.split(',')[1].split('=')[1]
            expected_sig = hmac.new(
                webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(sig, expected_sig):
                return JsonResponse({'error': 'Invalid signature'}, status=401)
        except Exception:
            return JsonResponse({'error': 'Signature verification failed'}, status=401)
        
        # Process the event based on its type
        event_type = event.get('type')
        
        if event_type == 'payment_intent.succeeded':
            payment_intent = event.get('data', {}).get('object', {})
            transaction_id = payment_intent.get('id')
            amount = payment_intent.get('amount') / 100  # Convert from cents
            currency = payment_intent.get('currency', 'usd').upper()
            
            # Find the payment by transaction ID or metadata
            try:
                payment = Payment.objects.get(
                    transaction_id=transaction_id,
                    status=Payment.PaymentStatus.PENDING
                )
                
                # Update payment status
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.gateway_response = event
                payment.completed_at = timezone.now()
                payment.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=payment.payee,
                    transaction_type=Transaction.TransactionType.PAYMENT_RECEIVED,
                    amount=Decimal(str(amount)),
                    currency=currency,
                    payment=payment,
                    description=f"Payment received via Stripe"
                )
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payee,
                    title="Payment Received",
                    message=f"You have received {amount} {currency} from {payment.payer.get_full_name()}",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                # Payment not found, might be a new payment
                pass
        
        elif event_type == 'payment_intent.payment_failed':
            payment_intent = event.get('data', {}).get('object', {})
            transaction_id = payment_intent.get('id')
            
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = Payment.PaymentStatus.FAILED
                payment.gateway_response = event
                payment.save()
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payer,
                    title="Payment Failed",
                    message=f"Your payment of {payment.amount} {payment.currency} has failed",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                pass
        
        elif event_type == 'charge.dispute.created':
            charge = event.get('data', {}).get('object', {})
            payment_id = charge.get('payment_intent')
            
            try:
                payment = Payment.objects.get(transaction_id=payment_id)
                payment.status = Payment.PaymentStatus.DISPUTED
                payment.gateway_response = event
                payment.save()
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payer,
                    title="Payment Disputed",
                    message=f"Your payment has been disputed",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                pass
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
def paypal_webhook(request):
    """Handle PayPal webhooks with validation and processing."""
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get the webhook payload
        payload = request.body
        event = json.loads(payload)
        
        # Verify the webhook (in production, use PayPal's SDK)
        # This is a simplified verification
        webhook_id = event.get('id')
        if not webhook_id:
            return JsonResponse({'error': 'Missing webhook ID'}, status=400)
        
        # Process the event based on its type
        event_type = event.get('event_type')
        resource = event.get('resource', {})
        
        if event_type == 'PAYMENT.SALE.COMPLETED':
            transaction_id = resource.get('id')
            amount = float(resource.get('amount', {}).get('total', 0))
            currency = resource.get('amount', {}).get('currency', 'USD').upper()
            
            # Find the payment by transaction ID
            try:
                payment = Payment.objects.get(
                    transaction_id=transaction_id,
                    status=Payment.PaymentStatus.PENDING
                )
                
                # Update payment status
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.gateway_response = event
                payment.completed_at = timezone.now()
                payment.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=payment.payee,
                    transaction_type=Transaction.TransactionType.PAYMENT_RECEIVED,
                    amount=Decimal(str(amount)),
                    currency=currency,
                    payment=payment,
                    description=f"Payment received via PayPal"
                )
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payee,
                    title="Payment Received",
                    message=f"You have received {amount} {currency} from {payment.payer.get_full_name()}",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                # Payment not found, might be a new payment
                pass
        
        elif event_type == 'PAYMENT.SALE.DENIED' or event_type == 'PAYMENT.SALE.FAILED':
            transaction_id = resource.get('id')
            
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = Payment.PaymentStatus.FAILED
                payment.gateway_response = event
                payment.save()
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payer,
                    title="Payment Failed",
                    message=f"Your payment of {payment.amount} {payment.currency} has failed",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                pass
        
        elif event_type == 'PAYMENT.DISPUTE.CREATED':
            transaction_id = resource.get('sale_id')
            
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = Payment.PaymentStatus.DISPUTED
                payment.gateway_response = event
                payment.save()
                
                # Send notification
                from notifications.utils import create_notification
                create_notification(
                    user=payment.payer,
                    title="Payment Disputed",
                    message=f"Your payment has been disputed",
                    notification_type="PAYMENT"
                )
                
            except Payment.DoesNotExist:
                pass
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def payment_status(request, pk):
    """Check payment status via AJAX."""
    payment = get_object_or_404(
        Payment,
        pk=pk,
        payer=request.user  # Only payer can check status
    )
    
    data = {
        'status': payment.status,
        'status_display': payment.get_status_display(),
        'created_at': payment.created_at.isoformat(),
        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
    }
    
    return JsonResponse(data)


@login_required
def escrow_account(request):
    """Show user's escrow account details (function-based view for backward compatibility)."""
    view = EscrowAccountView.as_view()
    return view(request)


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Overview of all financial activities for administrators."""
    template_name = 'paymentsdetails/admin_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Only admin users can access this view
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('paymentsdetails:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get payment statistics
        total_payments = Payment.objects.count()
        completed_payments = Payment.objects.completed().count()
        pending_payments = Payment.objects.pending().count()
        failed_payments = Payment.objects.failed().count()
        
        # Get total transaction volume
        total_volume = Payment.objects.completed().aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Get commission totals
        total_commission = Commission.objects.collected().aggregate(
            total=models.Sum('commission_amount')
        )['total'] or Decimal('0.00')
        
        pending_commission = Commission.objects.pending().aggregate(
            total=models.Sum('commission_amount')
        )['total'] or Decimal('0.00')
        
        # Get payout statistics
        total_payouts = Payout.objects.count()
        pending_payouts = Payout.objects.pending().count()
        total_payout_amount = Payout.objects.completed().aggregate(
            total=models.Sum('net_amount')
        )['total'] or Decimal('0.00')
        
        # Get refund statistics
        total_refunds = Refund.objects.count()
        pending_refunds = Refund.objects.pending().count()
        total_refund_amount = Refund.objects.completed().aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Get recent activities
        recent_payments = Payment.objects.all()[:10]
        recent_payouts = Payout.objects.all()[:10]
        recent_refunds = Refund.objects.all()[:10]
        
        # Get escrow account statistics
        total_escrow_balance = EscrowAccount.objects.aggregate(
            total=models.Sum('current_balance')
        )['total'] or Decimal('0.00')
        
        active_escrow_accounts = EscrowAccount.objects.active().count()
        
        # Get payment method statistics
        stripe_methods = PaymentMethod.objects.filter(method_type=PaymentMethod.MethodType.STRIPE).count()
        paypal_methods = PaymentMethod.objects.filter(method_type=PaymentMethod.MethodType.PAYPAL).count()
        bank_methods = PaymentMethod.objects.filter(method_type=PaymentMethod.MethodType.BANK_TRANSFER).count()
        
        # Payment status breakdown
        payment_status_counts = {}
        for status, _ in Payment.PaymentStatus.choices:
            payment_status_counts[status] = Payment.objects.filter(status=status).count()
        
        # Payment type breakdown
        payment_type_counts = {}
        for ptype, _ in Payment.PaymentType.choices:
            payment_type_counts[ptype] = Payment.objects.filter(payment_type=ptype).count()
        
        # Transaction type breakdown
        transaction_type_counts = {}
        for ttype, _ in Transaction.TransactionType.choices:
            transaction_type_counts[ttype] = Transaction.objects.filter(transaction_type=ttype).count()
        
        # Monthly transaction volume (last 12 months)
        from django.utils import timezone
        from datetime import timedelta
        
        monthly_volume = []
        for i in range(12):
            month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            volume = Payment.objects.completed().filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
            
            monthly_volume.append({
                'month': month_start.strftime('%b %Y'),
                'volume': volume
            })
        
        # Add all data to context
        context.update({
            # Payment statistics
            'total_payments': total_payments,
            'completed_payments': completed_payments,
            'pending_payments': pending_payments,
            'failed_payments': failed_payments,
            'total_volume': total_volume,
            
            # Commission statistics
            'total_commission': total_commission,
            'pending_commission': pending_commission,
            
            # Payout statistics
            'total_payouts': total_payouts,
            'pending_payouts': pending_payouts,
            'total_payout_amount': total_payout_amount,
            
            # Refund statistics
            'total_refunds': total_refunds,
            'pending_refunds': pending_refunds,
            'total_refund_amount': total_refund_amount,
            
            # Escrow statistics
            'total_escrow_balance': total_escrow_balance,
            'active_escrow_accounts': active_escrow_accounts,
            
            # Payment method statistics
            'stripe_methods': stripe_methods,
            'paypal_methods': paypal_methods,
            'bank_methods': bank_methods,
            
            # Recent activities
            'recent_payments': recent_payments,
            'recent_payouts': recent_payouts,
            'recent_refunds': recent_refunds,
            
            # Breakdown data
            'payment_status_counts': payment_status_counts,
            'payment_type_counts': payment_type_counts,
            'transaction_type_counts': transaction_type_counts,
            
            # Monthly volume data
            'monthly_volume': monthly_volume,
        })
        
        return context
