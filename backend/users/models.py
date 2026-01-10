from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import MinLengthValidator
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    
    # Profile Information
    full_name = models.CharField(max_length=255, blank=True)
    profile_picture = models.URLField(max_length=500, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    preferred_currency = models.CharField(max_length=3, default='USD')
    
    # Wallet Information
    wallet_address = models.CharField(
        max_length=42, 
        unique=True, 
        null=True, 
        blank=True,
        validators=[MinLengthValidator(42)]
    )
    wallet_type = models.CharField(max_length=50, blank=True)  # metamask, coinbase, etc.
    is_wallet_connected = models.BooleanField(default=False)
    last_wallet_connection = models.DateTimeField(null=True, blank=True)
    
    # Social Login
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    twitter_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Smart Account (ERC-4337)
    smart_account_address = models.CharField(
        max_length=42, 
        unique=True, 
        null=True, 
        blank=True,
        validators=[MinLengthValidator(42)]
    )
    smart_account_deployed = models.BooleanField(default=False)
    smart_account_deployment_tx = models.CharField(max_length=66, blank=True)
    
    # Stats
    total_earned_usdc = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    total_invoices = models.PositiveIntegerField(default=0)
    total_paid_invoices = models.PositiveIntegerField(default=0)
    
    # Status & Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['wallet_address']),
            models.Index(fields=['smart_account_address']),
            models.Index(fields=['google_id']),
            models.Index(fields=['twitter_id']),
        ]
    
    def __str__(self):
        return self.email or self.wallet_address
    
    @property
    def display_name(self):
        return self.full_name or self.username or self.email.split('@')[0]
    
    def save(self, *args, **kwargs):
        if not self.username and self.email:
            base_username = self.email.split('@')[0]
            self.username = self.generate_unique_username(base_username)
        super().save(*args, **kwargs)
    
    def generate_unique_username(self, base_username):
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username

class WalletSession(models.Model):
    """Track active wallet sessions for security"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_sessions')
    session_id = models.CharField(max_length=255, unique=True)
    wallet_address = models.CharField(max_length=42)
    chain_id = models.IntegerField()
    wallet_type = models.CharField(max_length=50)
    
    # Session data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.wallet_address}"

class SocialLogin(models.Model):
    """Store social login providers and tokens"""
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('twitter', 'Twitter'),
        ('github', 'GitHub'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_logins')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Profile data from provider
    profile_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['provider', 'provider_user_id']
        indexes = [
            models.Index(fields=['user', 'provider']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.provider}"

class EmailVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'verified']),
        ]
    
    def __str__(self):
        return f"{self.email} - {'Verified' if self.verified else 'Pending'}"