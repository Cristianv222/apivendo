# -*- coding: utf-8 -*-
"""
Modelos del módulo Users para VENDO_SRI
Sistema de autenticación con OAuth y gestión de usuarios
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone


class User(AbstractUser):
    """
    Modelo de usuario personalizado para VENDO_SRI
    Incluye soporte para OAuth y autenticación por email
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        verbose_name=_('ID')
    )
    
    # Email como username field
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("Ya existe un usuario con este email."),
        },
    )
    
    # Información personal
    document_type = models.CharField(
        max_length=20,
        choices=[
            ('cedula', _('Cédula')),
            ('pasaporte', _('Pasaporte')),
            ('ruc', _('RUC')),
        ],
        default='cedula',
        verbose_name=_('Tipo de documento')
    )
    
    document_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Número de documento'),
        help_text=_('Número de cédula o documento de identidad (opcional para registro social)'),
        validators=[
            RegexValidator(
                regex=r'^[\d\-]+$',
                message=_('El número de documento solo puede contener números y guiones.'),
            ),
        ]   
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono'),
        validators=[
            RegexValidator(
                regex=r'^[\d\+\-\(\)\s]+$',
                message=_('Formato de teléfono inválido.'),
            ),
        ]
    )
    
    mobile = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Celular'),
        validators=[
            RegexValidator(
                regex=r'^[\d\+\-\(\)\s]+$',
                message=_('Formato de celular inválido.'),
            ),
        ]
    )
    
    # Campos adicionales
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        verbose_name=_('Avatar')
    )
    
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de nacimiento')
    )
    
    address = models.TextField(
        blank=True,
        verbose_name=_('Dirección')
    )
    
    # Configuración de usuario
    language = models.CharField(
        max_length=10,
        choices=[
            ('es', _('Español')),
            ('en', _('Inglés')),
        ],
        default='es',
        verbose_name=_('Idioma')
    )
    
    timezone = models.CharField(
        max_length=50,
        default='America/Guayaquil',
        verbose_name=_('Zona horaria')
    )
    
    # Control de acceso
    is_system_admin = models.BooleanField(
        default=False,
        verbose_name=_('Administrador del sistema')
    )
    
    force_password_change = models.BooleanField(
        default=False,
        verbose_name=_('Forzar cambio de contraseña')
    )
    
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Contraseña cambiada el')
    )
    
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última actividad')
    )
    
    # ==========================================
    # SISTEMA DE APROBACIÓN - SALA DE ESPERA
    # ==========================================
    
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('Pendiente de aprobación')),
            ('approved', _('Aprobado')),
            ('rejected', _('Rechazado')),
        ],
        default='pending',
        verbose_name=_('Estado de aprobación'),
        help_text=_('Estado del usuario en el sistema de aprobación')
    )
    
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        verbose_name=_('Aprobado por'),
        help_text=_('Administrador que aprobó/rechazó al usuario')
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de aprobación'),
        help_text=_('Fecha y hora de aprobación o rechazo')
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_('Motivo de rechazo'),
        help_text=_('Razón por la cual se rechazó al usuario')
    )
    
    # Fechas de control
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de creación')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de actualización')
    )
    
    # Corregir conflictos de related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='vendo_sri_user_set',
        related_query_name='vendo_sri_user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='vendo_sri_user_set',
        related_query_name='vendo_sri_user',
    )
    
    # Configuración para login con email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        db_table = 'users_user'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['document_number']),
            models.Index(fields=['is_active', 'is_staff']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def clean(self):
        """Validaciones personalizadas"""
        from django.core.exceptions import ValidationError
        
        super().clean()
        
        # Validar email
        if self.email:
            self.email = self.email.lower().strip()
        
        # Validar documento
        if self.document_type == 'cedula' and self.document_number:
            if len(self.document_number) != 10:
                raise ValidationError({
                    'document_number': _('La cédula debe tener 10 dígitos.')
                })
        elif self.document_type == 'ruc' and self.document_number:
            if len(self.document_number) != 13:
                raise ValidationError({
                    'document_number': _('El RUC debe tener 13 dígitos.')
                })
    
    def save(self, *args, **kwargs):
        """Sobrescribir save para lógica adicional"""
        self.full_clean()  # Ejecutar validaciones
        
        # Normalizar email
        if self.email:
            self.email = self.email.lower().strip()
        
        # Lógica de usuarios nuevos - automáticamente en estado pendiente
        if not self.pk:  # Usuario nuevo
            # Solo los superusuarios y system_admin se aprueban automáticamente
            if self.is_superuser or self.is_system_admin:
                self.approval_status = 'approved'
                self.approved_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Crear perfil automáticamente
        if not hasattr(self, 'profile'):
            UserProfile.objects.get_or_create(user=self)
    
    def get_absolute_url(self):
        return reverse('users:user_detail', kwargs={'pk': self.pk})
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    # ==========================================
    # MÉTODOS DE APROBACIÓN
    # ==========================================
    
    def is_pending_approval(self):
        """Verifica si el usuario está pendiente de aprobación"""
        return self.approval_status == 'pending'
    
    def is_approved(self):
        """Verifica si el usuario ha sido aprobado"""
        return self.approval_status == 'approved'
    
    def is_rejected(self):
        """Verifica si el usuario ha sido rechazado"""
        return self.approval_status == 'rejected'
    
    def can_login(self):
        """Verifica si el usuario puede iniciar sesión"""
        return self.is_active and self.is_approved()
    
    def approve_user(self, approved_by_user, send_notification=True):
        """Aprueba al usuario"""
        self.approval_status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.is_active = True  # También activarlo
        self.save(update_fields=[
            'approval_status', 'approved_by', 'approved_at', 'is_active'
        ])
        
        if send_notification:
            # Aquí se podría agregar lógica de notificación
            pass
    
    def reject_user(self, rejected_by_user, reason='', send_notification=True):
        """Rechaza al usuario"""
        self.approval_status = 'rejected'
        self.approved_by = rejected_by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.is_active = False  # También desactivarlo
        self.save(update_fields=[
            'approval_status', 'approved_by', 'approved_at', 
            'rejection_reason', 'is_active'
        ])
        
        if send_notification:
            # Aquí se podría agregar lógica de notificación
            pass

    def get_approval_status_display_with_icon(self):
        """Retorna el estado de aprobación con icono"""
        status_icons = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
        }
        icon = status_icons.get(self.approval_status, '❓')
        display = self.get_approval_status_display()
        return f"{icon} {display}"


class UserProfile(models.Model):
    """
    Perfil extendido del usuario
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Usuario')
    )
    
    # Información profesional
    position = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Cargo')
    )
    
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Departamento')
    )
    
    employee_code = models.CharField(
        max_length=20,
        blank=True,
        unique=True,
        null=True,
        verbose_name=_('Código de empleado')
    )
    
    # Configuraciones de la interfaz
    theme = models.CharField(
        max_length=20,
        choices=[
            ('light', _('Claro')),
            ('dark', _('Oscuro')),
            ('auto', _('Automático')),
        ],
        default='light',
        verbose_name=_('Tema')
    )
    
    sidebar_collapsed = models.BooleanField(
        default=False,
        verbose_name=_('Sidebar colapsado')
    )
    
    # Notificaciones
    email_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Notificaciones por email')
    )
    
    sms_notifications = models.BooleanField(
        default=False,
        verbose_name=_('Notificaciones por SMS')
    )
    
    system_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Notificaciones del sistema')
    )
    
    # Información adicional
    bio = models.TextField(
        blank=True,
        verbose_name=_('Biografía')
    )
    
    social_media = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Redes sociales')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Perfil de usuario')
        verbose_name_plural = _('Perfiles de usuario')
        db_table = 'users_user_profile'
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"


class UserSession(models.Model):
    """
    Modelo para gestionar sesiones de usuario
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('Usuario')
    )
    
    # Información de la sesión
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name=_('Clave de sesión')
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name=_('Dirección IP')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    # Control de tiempo
    login_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Inicio de sesión')
    )
    
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última actividad')
    )
    
    logout_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Cierre de sesión')
    )
    
    # Estado
    is_expired = models.BooleanField(
        default=False,
        verbose_name=_('Expirada')
    )
    
    class Meta:
        verbose_name = _('Sesión de usuario')
        verbose_name_plural = _('Sesiones de usuario')
        db_table = 'users_user_session'
        indexes = [
            models.Index(fields=['user', 'login_at']),
            models.Index(fields=['session_key']),
            models.Index(fields=['is_expired']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.login_at}"
    
    @property
    def duration(self):
        """Retorna la duración de la sesión"""
        end_time = self.logout_at or self.last_activity
        return end_time - self.login_at if end_time else None