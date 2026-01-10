from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, SocialLoginView, WalletConnectView,
    GetSIWEMessageView, UserProfileView, ChangePasswordView,
    WalletSessionsView, RevokeWalletSessionView, VerifyEmailView,
    ResendVerificationEmailView, LogoutView, CustomTokenRefreshView,
    get_user_stats
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # Social Login
    path('social/login/', SocialLoginView.as_view(), name='social_login'),
    
    # Wallet Connection
    path('wallet/connect/', WalletConnectView.as_view(), name='wallet_connect'),
    path('wallet/siwe-message/', GetSIWEMessageView.as_view(), name='siwe_message'),
    
    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('profile/stats/', get_user_stats, name='user_stats'),
    
    # Wallet Sessions
    path('wallet/sessions/', WalletSessionsView.as_view(), name='wallet_sessions'),
    path('wallet/sessions/<uuid:session_id>/revoke/', RevokeWalletSessionView.as_view(), name='revoke_session'),
    
    # Email Verification
    path('verify-email/<str:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
]