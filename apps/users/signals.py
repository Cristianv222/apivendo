# -*- coding: utf-8 -*-
"""
Signals for users app
Señales para manejo automático de usuarios y notificaciones
"""

from django.db.models.signals import post_save, user_logged_in
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserCompanyAssignment, AdminNotification
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserCompanyAssignment

@receiver(post_save, sender=User)
def sync_user_assignment(sender, instance, created, **kwargs):
    """Sincroniza el estado del usuario con UserCompanyAssignment"""
    if created:
        # Crear UserCompanyAssignment para nuevos usuarios
        UserCompanyAssignment.objects.create(
            user=instance,
            status='waiting'
        )
    else:
        # Actualizar UserCompanyAssignment existente
        try:
            assignment = UserCompanyAssignment.objects.get(user=instance)
            # Mapear estados
            status_map = {
                'active': 'assigned',
                'waiting': 'waiting',
                'suspended': 'suspended',
                'rejected': 'rejected'
            }
            assignment.status = status_map.get(instance.user_status, 'waiting')
            if instance.user_status in ['suspended', 'rejected']:
                assignment.notes = instance.suspension_reason or instance.rejection_reason or ''
            assignment.save()
        except UserCompanyAssignment.DoesNotExist:
            pass

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_assignment(sender, instance, created, **kwargs):
    """
    Crear automáticamente una asignación cuando se registra un nuevo usuario
    """
    if created and not instance.is_staff and not instance.is_superuser:
        # Crear asignación en estado de espera
        assignment, created = UserCompanyAssignment.objects.get_or_create(
            user=instance,
            defaults={'status': 'waiting'}
        )
        
        if created:
            # Crear notificación para administradores
            AdminNotification.create_user_registered_notification(instance)
            print(f"✅ Usuario {instance.email} creado en sala de espera")

@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """
    Manejar cuando un usuario inicia sesión
    """
    # Solo procesar usuarios normales (no staff/admin)
    if not user.is_staff and not user.is_superuser:
        # Obtener o crear asignación
        assignment, created = UserCompanyAssignment.objects.get_or_create(
            user=user,
            defaults={'status': 'waiting'}
        )
        
        # Si está en sala de espera, crear notificación
        if assignment.is_waiting():
            # Verificar si ya existe una notificación reciente (últimas 24 horas)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_notification = AdminNotification.objects.filter(
                notification_type='user_waiting',
                related_user=user,
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if not recent_notification:
                AdminNotification.create_user_waiting_notification(user)
                print(f"🔔 Notificación creada: Usuario {user.email} en sala de espera")

@receiver(post_save, sender=UserCompanyAssignment)
def handle_assignment_change(sender, instance, created, **kwargs):
    """
    Manejar cambios en la asignación de usuarios
    """
    if not created and instance.status == 'assigned':
        # Marcar todas las notificaciones relacionadas como leídas
        AdminNotification.objects.filter(
            related_user=instance.user,
            notification_type__in=['user_waiting', 'user_registered'],
            is_read=False
        ).update(is_read=True)
        
        print(f"✅ Usuario {instance.user.email} asignado exitosamente")