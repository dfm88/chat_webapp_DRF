from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile
from django.core.cache import cache
from django.conf import settings

## LOGGING
import logging
logger = logging.getLogger(__name__)

AUTHENTICATION_CACHE_KEY = getattr(settings, 'AUTHENTICATION_CACHE_KEY', '')

# User -Profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    
@receiver(post_save, sender=User)
def save_user_profile(sender, instance: User, **kwargs):
    try:
        instance.profile.save()
    except Exception as ex:
        Profile.objects.create(user=instance)

    
@receiver(post_save, sender=User)
def clear_cache(sender, instance: User, **kwargs):
    for key in cache.keys(f'*{AUTHENTICATION_CACHE_KEY}*'):
        cache.delete(key)


