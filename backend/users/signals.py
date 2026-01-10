from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import User
from .tasks import send_welcome_email

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created and not instance.email.endswith('@settle.wallet'):
        # Send welcome email to non-wallet users
        send_welcome_email.delay(instance.email, instance.display_name)