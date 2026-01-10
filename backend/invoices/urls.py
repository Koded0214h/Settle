from django.urls import path
from .views import (
    InvoiceListView, InvoiceDetailView, InvoicePaymentView,
    GasSponsorView, TransactionListView, PaymentStatusView,
    InvoiceStatsView, WebhookReceiverView, get_recent_activity,
    send_invoice_reminder
)

urlpatterns = [
    # Invoice Management
    path('invoices/', InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<uuid:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:invoice_id>/remind/', send_invoice_reminder, name='send_reminder'),
    
    # Payment Processing
    path('pay/<str:payment_link_id>/', InvoicePaymentView.as_view(), name='invoice_payment'),
    path('payment/status/<str:user_op_hash>/', PaymentStatusView.as_view(), name='payment_status'),
    
    # Gas Sponsorship (ERC-4337)
    path('gas/sponsor/', GasSponsorView.as_view(), name='gas_sponsor'),
    
    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    
    # Stats & Analytics
    path('stats/', InvoiceStatsView.as_view(), name='invoice_stats'),
    path('activity/recent/', get_recent_activity, name='recent_activity'),
    
    # Webhooks
    path('webhook/', WebhookReceiverView.as_view(), name='webhook_receiver'),
]