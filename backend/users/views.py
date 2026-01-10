from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from .models import User, WalletSession, SocialLogin, EmailVerification
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, SocialLoginSerializer,
    WalletConnectSerializer, UserProfileSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, WalletSessionSerializer, EmailVerificationSerializer
)
from .tasks import send_verification_email
from .utils import validate_siwe_signature, generate_siwe_message
import secrets
import hashlib

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate email verification token
        token = secrets.token_hex(32)
        EmailVerification.objects.create(
            user=user,
            email=user.email,
            token=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Send verification email (async)
        send_verification_email.delay(user.email, token)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Registration successful. Please verify your email.'
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })

class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']
        
        # TODO: Implement provider-specific authentication
        # This would validate the token with the provider's API
        # and get user info
        
        # For now, return a placeholder response
        return Response({
            'detail': 'Social login endpoint. Implementation pending.'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)

class WalletConnectView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = WalletConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet_address = serializer.validated_data['wallet_address']
        chain_id = serializer.validated_data['chain_id']
        wallet_type = serializer.validated_data['wallet_type']
        signature = serializer.validated_data['signature']
        message = serializer.validated_data['message']
        
        # Validate SIWE signature
        is_valid, recovered_address = validate_siwe_signature(
            message, signature, wallet_address
        )
        
        if not is_valid:
            return Response(
                {'error': 'Invalid signature or message.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists with this wallet
        try:
            user = User.objects.get(wallet_address=wallet_address.lower())
        except User.DoesNotExist:
            # Create new user with wallet
            user = User.objects.create(
                wallet_address=wallet_address.lower(),
                wallet_type=wallet_type,
                is_wallet_connected=True,
                last_wallet_connection=timezone.now()
            )
            # Set a random email for wallet-only users
            user.email = f"{wallet_address.lower()}@settle.wallet"
            user.save()
        else:
            # Update existing user
            user.is_wallet_connected = True
            user.last_wallet_connection = timezone.now()
            user.save()
        
        # Create or update wallet session
        session_id = secrets.token_hex(32)
        expires_at = timezone.now() + timezone.timedelta(days=30)
        
        WalletSession.objects.update_or_create(
            user=user,
            wallet_address=wallet_address,
            defaults={
                'session_id': session_id,
                'chain_id': chain_id,
                'wallet_type': wallet_type,
                'is_active': True,
                'expires_at': expires_at,
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'session_id': session_id,
            'expires_at': expires_at.isoformat(),
        })
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class GetSIWEMessageView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        wallet_address = request.data.get('wallet_address')
        chain_id = request.data.get('chain_id', settings.SCROLL_CHAIN_ID)
        
        if not wallet_address or not wallet_address.startswith('0x'):
            return Response(
                {'error': 'Valid wallet address required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message = generate_siwe_message(
            wallet_address=wallet_address,
            chain_id=chain_id,
            domain=request.get_host(),
            uri=request.build_absolute_uri('/')
        )
        
        # Store message in cache for validation later
        cache_key = f'siwe_message:{wallet_address.lower()}'
        cache.set(cache_key, message, timeout=300)  # 5 minutes
        
        return Response({
            'message': message,
            'expires_in': 300  # seconds
        })

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = UserUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return full user profile
        return Response(UserProfileSerializer(instance).data)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Password changed successfully.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WalletSessionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WalletSessionSerializer
    
    def get_queryset(self):
        return WalletSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')

class RevokeWalletSessionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        try:
            session = WalletSession.objects.get(
                id=session_id,
                user=request.user,
                is_active=True
            )
            session.is_active = False
            session.save()
            return Response({'message': 'Session revoked successfully.'})
        except WalletSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or already revoked.'},
                status=status.HTTP_404_NOT_FOUND
            )

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, token):
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            verification = EmailVerification.objects.get(
                token=token_hash,
                expires_at__gt=timezone.now(),
                verified=False
            )
            
            verification.verified = True
            verification.verified_at = timezone.now()
            verification.save()
            
            # Update user verification status
            user = verification.user
            user.is_verified = True
            user.save(update_fields=['is_verified'])
            
            return Response({'message': 'Email verified successfully.'})
        
        except EmailVerification.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired verification token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

class ResendVerificationEmailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response(
                {'error': 'Email is already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Invalidate previous tokens
        EmailVerification.objects.filter(
            user=user,
            verified=False
        ).update(verified=True)  # Mark as "used" by setting verified=True
        
        # Create new verification token
        token = secrets.token_hex(32)
        EmailVerification.objects.create(
            user=user,
            email=user.email,
            token=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Send verification email
        send_verification_email.delay(user.email, token)
        
        return Response({'message': 'Verification email sent.'})

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    pass

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats(request):
    user = request.user
    return Response({
        'total_earned_usdc': str(user.total_earned_usdc),
        'total_invoices': user.total_invoices,
        'total_paid_invoices': user.total_paid_invoices,
        'wallet_connected': user.is_wallet_connected,
        'smart_account_deployed': user.smart_account_deployed,
    })