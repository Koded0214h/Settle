from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, WalletSession, SocialLogin, EmailVerification

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'wallet_address', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_verified')
    search_fields = ('email', 'full_name', 'wallet_address')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'profile_picture', 'bio', 'phone_number', 'country')}),
        ('Wallet Info', {'fields': ('wallet_address', 'wallet_type', 'smart_account_address', 'smart_account_deployed')}),
        ('Social Login', {'fields': ('google_id', 'twitter_id')}),
        ('Stats', {'fields': ('total_earned_usdc', 'total_invoices', 'total_paid_invoices')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

@admin.register(WalletSession)
class WalletSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'wallet_address', 'chain_id', 'is_active', 'created_at', 'expires_at')
    list_filter = ('is_active', 'chain_id', 'wallet_type')
    search_fields = ('user__email', 'wallet_address')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(SocialLogin)
class SocialLoginAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'created_at')
    list_filter = ('provider',)
    search_fields = ('user__email', 'provider_user_id')

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'verified', 'created_at', 'expires_at')
    list_filter = ('verified',)
    search_fields = ('email', 'user__email')
    readonly_fields = ('created_at',)