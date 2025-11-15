from django.urls import path
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from . import views

app_name = 'paypal_integration'

urlpatterns = [
    # Payment processing URLs
    path('payment/', login_required(views.PayPalPaymentView.as_view()), name='payment'),
    path('payment/success/', login_required(views.PayPalSuccessView.as_view()), name='payment_success'),
    path('payment/cancel/', login_required(views.PayPalCancelView.as_view()), name='payment_cancel'),
    
    # Webhook URLs (no login required)
    path('webhook/', views.PayPalWebhookView.as_view(), name='webhook'),
    
    # Payout URLs
    path('payout/', login_required(views.PayPalPayoutView.as_view()), name='payout'),
    
    # Subscription URLs
    path('subscription/', login_required(views.PayPalSubscriptionView.as_view()), name='subscription'),
    path('subscription/cancel/<str:subscription_id>/',
         require_http_methods(["POST"])(views.cancel_paypal_subscription),
         name='subscription_cancel'),
    
    # Account management URLs
    path('account/link/', login_required(views.PayPalAccountLinkView.as_view()), name='account_link'),
    path('account/list/', login_required(views.PayPalAccountListView.as_view()), name='account_list'),
    
    # Transaction history URLs
    path('transactions/', login_required(views.PayPalTransactionListView.as_view()), name='transaction_list'),
    
    # Subscription management URLs
    path('subscriptions/', login_required(views.PayPalSubscriptionListView.as_view()), name='subscription_list'),
    
    # Refund URLs
    path('refund/<str:transaction_id>/',
         require_http_methods(["POST"])(views.refund_paypal_payment),
         name='refund'),
]