from rest_framework import serializers
from django.utils import timezone
from .models import Invoice, InvoiceItem, Transaction, PaymentLink
from users.serializers import UserProfileSerializer

class InvoiceItemSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=20, decimal_places=6, read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = ('id', 'description', 'quantity', 'unit_price', 'total')
        read_only_fields = ('id',)

class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    client_email = serializers.EmailField(required=False)
    client_wallet = serializers.CharField(max_length=42, required=False, allow_blank=True)
    
    class Meta:
        model = Invoice
        fields = (
            'id', 'title', 'description', 'client_email', 'client_wallet', 
            'client_name', 'amount', 'currency', 'due_date', 'items', 'metadata'
        )
        read_only_fields = ('id',)
    
    def validate(self, attrs):
        # Validate either client_email or client_wallet is provided
        if not attrs.get('client_email') and not attrs.get('client_wallet'):
            raise serializers.ValidationError(
                "Either client_email or client_wallet must be provided."
            )
        
        # Validate wallet address format if provided
        client_wallet = attrs.get('client_wallet')
        if client_wallet and client_wallet.strip():
            if not client_wallet.startswith('0x') or len(client_wallet) != 42:
                raise serializers.ValidationError(
                    {"client_wallet": "Invalid Ethereum address format."}
                )
            attrs['client_wallet'] = client_wallet.lower()
        
        # Validate due date is in future
        due_date = attrs.get('due_date')
        if due_date and due_date <= timezone.now():
            raise serializers.ValidationError(
                {"due_date": "Due date must be in the future."}
            )
        
        return attrs
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        
        # Set creator
        validated_data['creator'] = request.user
        
        # Create invoice
        invoice = Invoice.objects.create(**validated_data)
        
        # Create invoice items
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        return invoice

class InvoiceSerializer(serializers.ModelSerializer):
    creator = UserProfileSerializer(read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    amount_in_local = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    payment_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number', 'creator', 'client_email', 'client_wallet',
            'client_name', 'title', 'description', 'amount', 'currency',
            'amount_in_local', 'status', 'due_date', 'paid_at', 'created_at',
            'is_on_chain', 'gas_sponsored', 'contract_invoice_id',
            'tx_hash', 'payment_tx_hash', 'is_overdue', 'items', 'metadata',
            'payment_url', 'payment_link_id'
        )
        read_only_fields = fields

class InvoiceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('title', 'description', 'due_date', 'metadata')
    
    def validate_due_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Due date must be in the future.")
        return value

class TransactionSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    invoice = InvoiceSerializer(read_only=True)
    explorer_url = serializers.CharField(read_only=True)
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'user', 'invoice', 'tx_hash', 'tx_type', 'status',
            'amount', 'token_symbol', 'from_address', 'to_address',
            'block_number', 'gas_used', 'gas_price', 'gas_sponsored',
            'created_at', 'confirmed_at', 'explorer_url', 'metadata'
        )
        read_only_fields = fields

class PaymentLinkSerializer(serializers.ModelSerializer):
    invoice = InvoiceSerializer(read_only=True)
    url = serializers.CharField(read_only=True)
    
    class Meta:
        model = PaymentLink
        fields = ('id', 'invoice', 'short_id', 'url', 'clicks', 'last_accessed', 'created_at')
        read_only_fields = fields

class InvoicePaymentSerializer(serializers.Serializer):
    """Serializer for paying an invoice"""
    payer_wallet = serializers.CharField(max_length=42, required=True)
    signature = serializers.CharField(required=True)  # ERC-4337 user operation signature
    user_op_hash = serializers.CharField(required=True)  # User operation hash
    
    def validate_payer_wallet(self, value):
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid Ethereum address format.")
        return value.lower()

class GasSponsorRequestSerializer(serializers.Serializer):
    """Serializer for requesting gas sponsorship"""
    user_op = serializers.JSONField(required=True)  # ERC-4337 User Operation
    paymaster_and_data = serializers.CharField(required=True)
    
    def validate(self, attrs):
        user_op = attrs.get('user_op')
        required_fields = ['sender', 'nonce', 'initCode', 'callData', 'callGasLimit',
                          'verificationGasLimit', 'preVerificationGas', 'maxFeePerGas',
                          'maxPriorityFeePerGas', 'paymasterAndData', 'signature']
        
        for field in required_fields:
            if field not in user_op:
                raise serializers.ValidationError(
                    f"Missing required field in user operation: {field}"
                )
        
        return attrs

class InvoiceStatsSerializer(serializers.Serializer):
    total_invoices = serializers.IntegerField()
    total_paid = serializers.DecimalField(max_digits=20, decimal_places=6)
    total_pending = serializers.DecimalField(max_digits=20, decimal_places=6)
    overdue_invoices = serializers.IntegerField()
    average_payment_time = serializers.IntegerField()  # in hours
    gas_savings = serializers.DecimalField(max_digits=20, decimal_places=6)