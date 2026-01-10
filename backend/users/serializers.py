from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, WalletSession, SocialLogin, EmailVerification
import re

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'full_name', 'country')
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': False},
            'country': {'required': False},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        # Validate email format
        email = attrs.get('email')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise serializers.ValidationError({"email": "Enter a valid email address."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
        
        else:
            raise serializers.ValidationError('Must include "email" and "password".')
        
        attrs['user'] = user
        return attrs

class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'twitter', 'github'])
    access_token = serializers.CharField(required=True)
    id_token = serializers.CharField(required=False)
    
    def validate(self, attrs):
        provider = attrs.get('provider')
        access_token = attrs.get('access_token')
        
        # TODO: Implement provider-specific token validation
        # This would call the provider's API to validate the token
        
        return attrs

class WalletConnectSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(max_length=42, required=True)
    chain_id = serializers.IntegerField(required=True)
    wallet_type = serializers.CharField(max_length=50, required=True)
    signature = serializers.CharField(required=True)  # For SIWE (Sign-In with Ethereum)
    message = serializers.CharField(required=True)    # The message that was signed
    
    def validate_wallet_address(self, value):
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid Ethereum address format.")
        return value.lower()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'full_name', 'profile_picture',
            'bio', 'phone_number', 'country', 'preferred_currency',
            'wallet_address', 'is_wallet_connected',
            'smart_account_address', 'smart_account_deployed',
            'total_earned_usdc', 'total_invoices', 'total_paid_invoices',
            'is_verified', 'date_joined',
        )
        read_only_fields = ('id', 'email', 'date_joined', 'total_earned_usdc', 
                          'total_invoices', 'total_paid_invoices')

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('full_name', 'profile_picture', 'bio', 'phone_number', 
                 'country', 'preferred_currency')
    
    def validate_preferred_currency(self, value):
        valid_currencies = ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'GHS', 'ZAR']
        if value not in valid_currencies:
            raise serializers.ValidationError(
                f"Invalid currency. Choose from: {', '.join(valid_currencies)}"
            )
        return value

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        
        try:
            validate_password(attrs['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return attrs

class WalletSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletSession
        fields = ('id', 'wallet_address', 'chain_id', 'wallet_type', 
                 'ip_address', 'created_at', 'expires_at', 'is_active')
        read_only_fields = ('id', 'created_at', 'expires_at', 'is_active')

class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ('email', 'verified', 'verified_at')
        read_only_fields = ('verified', 'verified_at')