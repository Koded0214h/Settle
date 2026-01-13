from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import Invoice, Transaction, WebhookEvent
from .blockchain.blockchain import (
    create_invoice_on_blockchain, pay_invoice_on_blockchain,
    get_invoice_from_contract, convert_usdc_to_wei,
    create_user_operation, sponsor_gas_with_paymaster,
    submit_user_operation_to_bundler
)
import logging
import json

logger = logging.getLogger(__name__)

@shared_task
def create_invoice_on_chain(invoice_id):
    """Create invoice on blockchain"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Skip if already on chain or no client wallet
        if invoice.is_on_chain or not invoice.client_wallet:
            return
        
        # Prepare invoice data for blockchain
        amount_wei = convert_usdc_to_wei(invoice.amount)
        due_date_timestamp = int(invoice.due_date.timestamp())
        
        # TODO: Upload to IPFS and get hash
        ipfs_hash = invoice.ipfs_hash or f"settle://invoice/{invoice.id}"
        
        invoice_data = {
            'freelancer_address': invoice.creator.wallet_address,
            'amount': amount_wei,
            'due_date': due_date_timestamp,
            'ipfs_hash': ipfs_hash,
        }
        
        # Create transaction on blockchain
        tx = create_invoice_on_blockchain(invoice_data)
        
        if tx:
            # For now, we'll just mark as on-chain
            # In production, we'd send the transaction
            invoice.is_on_chain = True
            invoice.contract_invoice_id = invoice.id  # Placeholder
            invoice.tx_hash = f"0x{invoice.id.hex[:64]}"  # Placeholder
            invoice.status = 'sent'
            invoice.save()
            
            # Create transaction record
            Transaction.objects.create(
                user=invoice.creator,
                invoice=invoice,
                tx_hash=invoice.tx_hash,
                tx_type='invoice_created',
                amount=invoice.amount,
                token_symbol='USDC',
                from_address=invoice.creator.wallet_address,
                to_address=invoice.client_wallet,
                gas_sponsored=True,
                metadata={
                    'invoice_id': str(invoice.id),
                    'contract_invoice_id': invoice.contract_invoice_id,
                    'ipfs_hash': ipfs_hash,
                }
            )
            
            logger.info(f"Invoice {invoice_id} created on chain")
    
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
    except Exception as e:
        logger.error(f"Error creating invoice on chain: {e}")

@shared_task
def process_invoice_payment(invoice_id, payer_wallet, user_op_hash, signature):
    """Process invoice payment with ERC-4337"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Skip if already paid
        if invoice.status == 'paid':
            return
        
        # Verify invoice is payable
        if invoice.status not in ['sent', 'pending']:
            logger.error(f"Invoice {invoice_id} is not payable")
            return
        
        # Create ERC-4337 user operation for payment
        # This is a simplified version - in production, you'd use a proper AA SDK
        
        amount_wei = convert_usdc_to_wei(invoice.amount)
        
        # Prepare user operation data
        user_op = create_user_operation(
            sender=payer_wallet,
            nonce=0,  # Get from contract
            init_code='0x',  # No init code for existing accounts
            call_data=json.dumps({
                'method': 'payInvoice',
                'params': [invoice.contract_invoice_id, settings.USDC_CONTRACT_ADDRESS]
            }),
            call_gas_limit=200000,
            verification_gas_limit=100000,
            pre_verification_gas=21000,
            max_fee_per_gas=1000000000,  # 1 gwei
            max_priority_fee_per_gas=1000000000,
            paymaster_and_data=settings.PAYMASTER_CONTRACT_ADDRESS,
            signature=signature,
        )
        
        # Sponsor gas
        sponsored_user_op = sponsor_gas_with_paymaster(
            user_op,
            settings.PAYMASTER_CONTRACT_ADDRESS
        )
        
        if sponsored_user_op:
            # Submit to bundler
            submitted_hash = submit_user_operation_to_bundler(sponsored_user_op)
            
            if submitted_hash:
                # Update invoice status
                invoice.status = 'pending'
                invoice.save()
                
                # Create pending transaction
                Transaction.objects.create(
                    user=invoice.creator,
                    invoice=invoice,
                    tx_hash=submitted_hash,
                    tx_type='invoice_paid',
                    status='pending',
                    amount=invoice.amount,
                    token_symbol='USDC',
                    from_address=payer_wallet,
                    to_address=invoice.creator.wallet_address,
                    gas_sponsored=True,
                    metadata={
                        'user_op_hash': user_op_hash,
                        'submitted_hash': submitted_hash,
                        'invoice_id': str(invoice.id),
                    }
                )
                
                logger.info(f"Invoice {invoice_id} payment initiated: {submitted_hash}")
        
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
    except Exception as e:
        logger.error(f"Error processing invoice payment: {e}")

@shared_task
def update_transaction_status(tx_hash):
    """Update transaction status from blockchain"""
    try:
        transaction = Transaction.objects.get(tx_hash=tx_hash)
        
        # Check if transaction is confirmed
        # TODO: Implement blockchain check
        
        # For now, simulate confirmation after delay
        if transaction.status == 'pending':
            transaction.status = 'confirmed'
            transaction.confirmed_at = timezone.now()
            transaction.save()
            
            # Update invoice if this is a payment
            if transaction.invoice and transaction.tx_type == 'invoice_paid':
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
    
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {tx_hash} not found")
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}")

@shared_task
def send_invoice_notification(invoice_id):
    """Send invoice notification to client"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # TODO: Implement email/SMS notification
        # For now, just log
        
        if invoice.client_email:
            logger.info(f"Sending invoice notification to {invoice.client_email}")
        
        if invoice.client_wallet:
            logger.info(f"Invoice available for wallet {invoice.client_wallet}")
    
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
    except Exception as e:
        logger.error(f"Error sending invoice notification: {e}")

@shared_task
def check_overdue_invoices():
    """Check and mark overdue invoices"""
    try:
        overdue_invoices = Invoice.objects.filter(
            status__in=['sent', 'pending'],
            due_date__lt=timezone.now()
        )
        
        for invoice in overdue_invoices:
            invoice.status = 'overdue'
            invoice.save()
        
        logger.info(f"Marked {overdue_invoices.count()} invoices as overdue")
    
    except Exception as e:
        logger.error(f"Error checking overdue invoices: {e}")

@shared_task
def sync_invoice_from_blockchain(invoice_id):
    """Sync invoice status from blockchain"""
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        if not invoice.contract_invoice_id:
            return
        
        # Get invoice from blockchain
        contract_data = get_invoice_from_contract(invoice.contract_invoice_id)
        
        if contract_data:
            # Update status based on blockchain
            if contract_data['is_paid'] and invoice.status != 'paid':
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
                invoice.save()
    
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
    except Exception as e:
        logger.error(f"Error syncing invoice from blockchain: {e}")