# -*- coding: utf-8 -*-
"""
Signals for users app
Señales para crear automáticamente perfiles y logs de auditoría
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Crea automáticamente un UserProfile cuando se crea un User
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Guarda el UserProfile cuando se guarda un User
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Si por alguna razón no existe el perfil, lo creamos
        UserProfile.objects.create(user=instance)