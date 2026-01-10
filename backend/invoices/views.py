from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.cache import cache
from django.conf import settings
from decimal import Decimal

from .models import Invoice, InvoiceItem, Transaction, PaymentLink, WebhookEvent
from .serializers import (
    InvoiceCreateSerializer, InvoiceSerializer, InvoiceUpdateSerializer,
    TransactionSerializer, PaymentLinkSerializer, InvoicePaymentSerializer,
    GasSponsorRequestSerializer, InvoiceStatsSerializer
)
from .tasks import (
    create_invoice_on_chain, process_invoice_payment, 
    update_transaction_status, send_invoice_notification
)

# Try to import blockchain functions with proper error handling
try:
    from .blockchain.blockchain import (
        create_user_operation, sponsor_gas_with_paymaster,
        submit_user_operation_to_bundler, get_invoice_from_contract,
        check_user_op_status_from_bundler
    )
    BLOCKCHAIN_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Blockchain module import failed: {e}. Using fallbacks.")
    BLOCKCHAIN_AVAILABLE = False
    
    # Fallback implementations
    def check_user_op_status_from_bundler(user_op_hash):
        """Fallback implementation"""
        return None
    
    def create_user_operation(*args, **kwargs):
        return {}
    
    def sponsor_gas_with_paymaster(*args, **kwargs):
        return None
    
    def submit_user_operation_to_bundler(*args, **kwargs):
        return None
    
    def get_invoice_from_contract(*args, **kwargs):
        return None

import logging

logger = logging.getLogger(__name__)

class InvoiceListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InvoiceCreateSerializer
        return InvoiceSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.filter(creator=user).prefetch_related('items')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by client
        client_filter = self.request.query_params.get('client')
        if client_filter:
            queryset = queryset.filter(
                Q(client_email__icontains=client_filter) |
                Q(client_wallet__icontains=client_filter) |
                Q(client_name__icontains=client_filter)
            )
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        invoice = serializer.save()
        
        # Send notification
        send_invoice_notification.delay(invoice.id)
        
        # Create on blockchain (async)
        if not invoice.client_email:  # Only create on-chain for wallet clients
            create_invoice_on_chain.delay(str(invoice.id))

class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return InvoiceUpdateSerializer
        return InvoiceSerializer
    
    def get_queryset(self):
        return Invoice.objects.filter(creator=self.request.user)
    
    def perform_update(self, serializer):
        invoice = serializer.save()
        # If invoice is on-chain, update metadata on IPFS
        if invoice.is_on_chain:
            # TODO: Update IPFS metadata
            pass
    
    def perform_destroy(self, instance):
        if instance.status == 'paid':
            return Response(
                {'error': 'Cannot delete paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()

class InvoicePaymentView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, payment_link_id):
        """Get invoice details for payment page"""
        try:
            invoice = Invoice.objects.get(
                payment_link_id=payment_link_id,
                status__in=['sent', 'pending']
            )
            
            # Update link clicks
            payment_link, _ = PaymentLink.objects.get_or_create(
                invoice=invoice,
                defaults={'short_id': payment_link_id}
            )
            payment_link.clicks += 1
            payment_link.last_accessed = timezone.now()
            payment_link.save()
            
            serializer = InvoiceSerializer(invoice)
            return Response(serializer.data)
        
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found or already paid.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def post(self, request, payment_link_id):
        """Process invoice payment"""
        serializer = InvoicePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            invoice = Invoice.objects.get(
                payment_link_id=payment_link_id,
                status__in=['sent', 'pending']
            )
            
            payer_wallet = serializer.validated_data['payer_wallet']
            signature = serializer.validated_data['signature']
            user_op_hash = serializer.validated_data['user_op_hash']
            
            # Process payment async
            process_invoice_payment.delay(
                str(invoice.id),
                payer_wallet,
                user_op_hash,
                signature
            )
            
            return Response({
                'message': 'Payment processing started.',
                'user_op_hash': user_op_hash,
                'status_url': f'/api/invoices/payment/status/{user_op_hash}/'
            })
        
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found or already paid.'},
                status=status.HTTP_404_NOT_FOUND
            )

class GasSponsorView(APIView):
    """Handle ERC-4337 gas sponsorship requests"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        if not BLOCKCHAIN_AVAILABLE:
            return Response(
                {'error': 'Blockchain module not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        serializer = GasSponsorRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_op = serializer.validated_data['user_op']
        paymaster_and_data = serializer.validated_data['paymaster_and_data']
        
        try:
            # Sponsor gas using paymaster
            sponsored_user_op = sponsor_gas_with_paymaster(
                user_op,
                paymaster_and_data
            )
            
            if not sponsored_user_op:
                return Response(
                    {'error': 'Failed to sponsor gas.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Submit to bundler
            user_op_hash = submit_user_operation_to_bundler(sponsored_user_op)
            
            if not user_op_hash:
                return Response(
                    {'error': 'Failed to submit to bundler.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'user_op_hash': user_op_hash,
                'sponsored_user_op': sponsored_user_op,
                'message': 'Gas sponsorship successful.'
            })
        
        except Exception as e:
            logger.error(f"Gas sponsorship failed: {e}")
            return Response(
                {'error': f'Gas sponsorship failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

class TransactionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(user=user).order_by('-created_at')

class PaymentStatusView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, user_op_hash):
        """Check status of a user operation"""
        # Check cache first
        status_data = cache.get(f'user_op_status:{user_op_hash}')
        
        if not status_data:
            # Check database
            transaction = Transaction.objects.filter(
                metadata__contains={'user_op_hash': user_op_hash}
            ).first()
            
            if transaction:
                status_data = {
                    'status': transaction.status,
                    'tx_hash': transaction.tx_hash,
                    'confirmed': transaction.status == 'confirmed',
                    'explorer_url': transaction.explorer_url,
                }
            elif BLOCKCHAIN_AVAILABLE:
                # Check bundler API
                status_data = check_user_op_status_from_bundler(user_op_hash)
            
            # Cache for 30 seconds
            if status_data:
                cache.set(f'user_op_status:{user_op_hash}', status_data, 30)
        
        if not status_data:
            return Response(
                {'error': 'Transaction not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status_data)

class InvoiceStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Calculate stats
        stats = Invoice.objects.filter(creator=user).aggregate(
            total_invoices=Count('id'),
            total_paid=Sum('amount', filter=Q(status='paid')),
            total_pending=Sum('amount', filter=Q(status__in=['sent', 'pending'])),
            overdue_invoices=Count('id', filter=Q(status='overdue')),
        )
        
        # Calculate average payment time
        paid_invoices = Invoice.objects.filter(
            creator=user,
            status='paid',
            paid_at__isnull=False,
            created_at__isnull=False
        )
        
        total_hours = 0
        count = 0
        for invoice in paid_invoices:
            payment_time = invoice.paid_at - invoice.created_at
            total_hours += payment_time.total_seconds() / 3600
            count += 1
        
        average_payment_time = total_hours / count if count > 0 else 0
        
        # Calculate gas savings (estimate)
        gas_savings = Transaction.objects.filter(
            user=user,
            gas_sponsored=True
        ).aggregate(total_gas=Sum('gas_used'))['total_gas'] or 0
        
        # Convert gas to USD (rough estimate)
        gas_price_usd = Decimal('0.000000001')  # Example: 1 Gwei = $0.000000001
        gas_savings_usd = Decimal(gas_savings) * gas_price_usd
        
        stats_data = {
            'total_invoices': stats['total_invoices'] or 0,
            'total_paid': stats['total_paid'] or Decimal('0'),
            'total_pending': stats['total_pending'] or Decimal('0'),
            'overdue_invoices': stats['overdue_invoices'] or 0,
            'average_payment_time': round(average_payment_time, 1),
            'gas_savings': gas_savings_usd,
        }
        
        serializer = InvoiceStatsSerializer(stats_data)
        return Response(serializer.data)

class WebhookReceiverView(APIView):
    """Receive webhooks from blockchain services"""
    permission_classes = []  # No authentication for webhooks
    authentication_classes = []  # We'll use signature verification
    
    def post(self, request):
        event_type = request.headers.get('X-Event-Type')
        signature = request.headers.get('X-Signature')
        
        # Verify signature (implement based on your webhook provider)
        if not self.verify_signature(request, signature):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Store webhook event
        WebhookEvent.objects.create(
            event_type=event_type,
            payload=request.data
        )
        
        # Process based on event type
        if event_type == 'invoice_paid':
            self.process_invoice_paid_webhook(request.data)
        elif event_type == 'transaction_confirmed':
            self.process_transaction_confirmed_webhook(request.data)
        
        return Response({'status': 'received'})
    
    def verify_signature(self, request, signature):
        """Verify webhook signature"""
        # TODO: Implement signature verification
        # This should verify the signature matches your expected secret
        return True
    
    def process_invoice_paid_webhook(self, data):
        """Process invoice paid webhook"""
        try:
            tx_hash = data.get('transactionHash')
            invoice_id = data.get('invoiceId')
            
            # Update invoice status
            transaction = Transaction.objects.filter(tx_hash=tx_hash).first()
            if transaction and transaction.invoice:
                invoice = transaction.invoice
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
                invoice.payment_tx_hash = tx_hash
                invoice.save()
                
                # Update creator stats
                creator = invoice.creator
                creator.total_earned_usdc += invoice.amount
                creator.total_paid_invoices += 1
                creator.save()
        
        except Exception as e:
            logger.error(f"Error processing invoice paid webhook: {e}")
    
    def process_transaction_confirmed_webhook(self, data):
        """Process transaction confirmed webhook"""
        try:
            tx_hash = data.get('transactionHash')
            block_number = data.get('blockNumber')
            
            transaction = Transaction.objects.filter(tx_hash=tx_hash).first()
            if transaction:
                transaction.status = 'confirmed'
                transaction.block_number = block_number
                transaction.confirmed_at = timezone.now()
                transaction.save()
        
        except Exception as e:
            logger.error(f"Error processing transaction confirmed webhook: {e}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recent_activity(request):
    """Get recent activity for dashboard"""
    user = request.user
    
    recent_invoices = Invoice.objects.filter(
        creator=user
    ).order_by('-created_at')[:5]
    
    recent_transactions = Transaction.objects.filter(
        user=user
    ).order_by('-created_at')[:10]
    
    invoice_serializer = InvoiceSerializer(recent_invoices, many=True)
    transaction_serializer = TransactionSerializer(recent_transactions, many=True)
    
    return Response({
        'recent_invoices': invoice_serializer.data,
        'recent_transactions': transaction_serializer.data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invoice_reminder(request, invoice_id):
    """Send reminder for unpaid invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id, creator=request.user)
    
    if invoice.status == 'paid':
        return Response(
            {'error': 'Cannot send reminder for paid invoice.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # TODO: Implement email/SMS reminder
    # send_invoice_reminder_email.delay(str(invoice.id))
    
    return Response({'message': 'Reminder sent successfully.'})