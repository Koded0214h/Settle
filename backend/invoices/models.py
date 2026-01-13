import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MinLengthValidator
from django.conf import settings
from decimal import Decimal

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    CURRENCY_CHOICES = [
        ('USDC', 'USDC'),
        ('USD', 'USD'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Creator & Client
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_invoices'
    )
    client_email = models.EmailField(blank=True)  # For non-wallet clients
    client_wallet = models.CharField(
        max_length=42, 
        blank=True,
        validators=[MinLengthValidator(42)]
    )
    client_name = models.CharField(max_length=255, blank=True)
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Amount & Currency
    amount = models.DecimalField(
        max_digits=20, 
        decimal_places=6,  # USDC has 6 decimals
        validators=[MinValueValidator(Decimal('0.000001'))]
    )
    currency = models.CharField(max_length=4, choices=CURRENCY_CHOICES, default='USDC')
    
    # Blockchain Integration
    contract_invoice_id = models.BigIntegerField(null=True, blank=True)  # ID on-chain
    contract_address = models.CharField(max_length=42, blank=True)  # Invoice contract address
    tx_hash = models.CharField(max_length=66, blank=True)  # Transaction hash for creation
    payment_tx_hash = models.CharField(max_length=66, blank=True)  # Transaction hash for payment
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_on_chain = models.BooleanField(default=False)  # Is registered on blockchain?
    gas_sponsored = models.BooleanField(default=True)  # Gas sponsored by paymaster
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)  # For line items, terms, etc.
    ipfs_hash = models.CharField(max_length=100, blank=True)  # IPFS hash for invoice metadata
    
    # Payment Link
    payment_link_id = models.CharField(max_length=32, unique=True, db_index=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['payment_link_id']),
            models.Index(fields=['client_wallet']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.creator.email}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        if not self.payment_link_id:
            self.payment_link_id = uuid.uuid4().hex[:32]
        super().save(*args, **kwargs)
    
    def generate_invoice_number(self):
        """Generate invoice number like INV-2024-001"""
        year = timezone.now().year
        last_invoice = Invoice.objects.filter(
            invoice_number__startswith=f'INV-{year}-'
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"INV-{year}-{new_number:03d}"
    
    @property
    def is_overdue(self):
        if self.status == 'paid':
            return False
        return timezone.now() > self.due_date
    
    @property
    def amount_in_local(self):
        """Convert USDC amount to local currency"""
        # TODO: Implement currency conversion API
        return self.amount * Decimal('1400')  # Example: 1 USDC = 1400 NGN
    
    @property
    def payment_url(self):
        return f"https://settle.me/pay/{self.payment_link_id}"

class InvoiceItem(models.Model):
    """Line items for invoices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=20, decimal_places=6)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    @property
    def total(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.description} - {self.total} USDC"

class Transaction(models.Model):
    """Track all blockchain transactions"""
    TYPE_CHOICES = [
        ('invoice_created', 'Invoice Created'),
        ('invoice_paid', 'Invoice Paid'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='transactions'
    )
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions'
    )
    
    # Transaction Details
    tx_hash = models.CharField(max_length=66, unique=True, db_index=True)
    tx_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Amount & Token
    amount = models.DecimalField(max_digits=20, decimal_places=6)
    token_address = models.CharField(max_length=42, blank=True)
    token_symbol = models.CharField(max_length=10, default='USDC')
    
    # Blockchain Data
    from_address = models.CharField(max_length=42)
    to_address = models.CharField(max_length=42)
    block_number = models.BigIntegerField(null=True, blank=True)
    gas_used = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True)
    gas_price = models.DecimalField(max_digits=20, decimal_places=0, null=True, blank=True)
    gas_sponsored = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['user', 'tx_type']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['block_number']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tx_type} - {self.tx_hash[:10]}..."
    
    @property
    def explorer_url(self):
        base_url = settings.SCROLL_EXPLORER or "https://sepolia.scrollscan.dev"
        return f"{base_url}/tx/{self.tx_hash}"

class PaymentLink(models.Model):
    """Payment link for sharing invoices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='payment_link')
    short_id = models.CharField(max_length=32, unique=True, db_index=True)
    clicks = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['short_id']),
        ]
    
    def __str__(self):
        return f"pay/{self.short_id}"
    
    @property
    def url(self):
        return f"https://settle.me/pay/{self.short_id}"

class WebhookEvent(models.Model):
    """Store webhook events from blockchain/third-party services"""
    EVENT_CHOICES = [
        ('invoice_paid', 'Invoice Paid'),
        ('transaction_confirmed', 'Transaction Confirmed'),
        ('gas_sponsored', 'Gas Sponsored'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"