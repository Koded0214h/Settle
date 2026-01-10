from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_verification_email(email, token):
    """Send email verification link"""
    try:
        subject = "Verify your Settle account"
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}"
        
        html_message = render_to_string('emails/verification.html', {
            'verification_url': verification_url,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")

@shared_task
def send_welcome_email(email, username):
    """Send welcome email to new users"""
    try:
        subject = "Welcome to Settle!"
        
        html_message = render_to_string('emails/welcome.html', {
            'username': username,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")

@shared_task
def send_invoice_paid_email(email, invoice_data):
    """Send notification when invoice is paid"""
    try:
        subject = f"Invoice #{invoice_data['invoice_number']} has been paid!"
        
        html_message = render_to_string('emails/invoice_paid.html', {
            'invoice': invoice_data,
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Invoice paid email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send invoice paid email to {email}: {e}")

@shared_task
def cleanup_expired_sessions():
    """Clean up expired wallet sessions"""
    from django.utils import timezone
    from .models import WalletSession
    
    expired_count = WalletSession.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    ).update(is_active=False)
    
    logger.info(f"Cleaned up {expired_count} expired wallet sessions")