"""
URL configuration for paymentsdetails app.
"""

from django.urls import path
from . import views

app_name = 'paymentsdetails'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin Dashboard (staff only)
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Escrow Account
    path('escrow/', views.escrow_account, name='escrow_account'),
    
    # Payment Methods
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment_methods'),
    path('payment-methods/add/', views.PaymentMethodCreateView.as_view(), name='payment_method_create'),
    path('payment-methods/<uuid:pk>/edit/', views.PaymentMethodUpdateView.as_view(), name='payment_method_update'),
    path('payment-methods/<uuid:pk>/set-default/', views.set_default_payment_method, name='set_default_payment_method'),
    path('payment-methods/<uuid:pk>/delete/', views.delete_payment_method, name='delete_payment_method'),
    
    # Transactions
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    
    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payments'),
    path('payments/<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('payments/<uuid:award_id>/make/', views.make_payment, name='make_payment'),
    path('payments/<uuid:pk>/status/', views.payment_status, name='payment_status'),
    
    # Payouts
    path('payouts/', views.PayoutListView.as_view(), name='payouts'),
    path('payouts/request/', views.PayoutRequestView.as_view(), name='payout_request'),
    
    # Refunds
    path('refunds/<uuid:payment_id>/request/', views.RefundRequestView.as_view(), name='refund_request'),
    
    # Webhooks
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('webhooks/paypal/', views.paypal_webhook, name='paypal_webhook'),
]