# -*- coding: utf-8 -*-
"""
Models for users app
Sistema de Usuarios personalizado para VENDO_SRI
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo User
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Crea y guarda un usuario regular con el email y password dados
        """
        if not email:
            raise ValueError(_('The Email field must be set'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el email y password dados
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Usuario personalizado para el sistema VENDO_SRI
    """
    
    # Remover el campo username (no lo usaremos)
    username = None
    
    # Campos adicionales
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Required. Enter a valid email address.')
    )
    
    phone = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        help_text=_('Optional. Phone number for contact.')
    )
    
    company = models.ForeignKey(
        'companies.Company',  # Usar string reference para evitar problemas de importación
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('company'),
        help_text=_('Company associated with this user.')
    )
    
    is_company_admin = models.BooleanField(
        _('is company admin'),
        default=False,
        help_text=_('Designates whether this user can manage company settings.')
    )
    
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profiles/',
        blank=True,
        null=True,
        help_text=_('Optional profile picture.')
    )
    
    # Manager personalizado
    objects = UserManager()
    
    # Configuración de autenticación
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['email']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})" if self.get_full_name() else self.email
    
    def get_display_name(self):
        """Devuelve el nombre completo o email si no hay nombre"""
        full_name = self.get_full_name()
        return full_name if full_name else self.email
    
    @property
    def is_company_user(self):
        """Verifica si el usuario pertenece a una empresa"""
        return self.company is not None


class UserProfile(models.Model):
    """
    Perfil extendido del usuario
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )
    
    bio = models.TextField(
        _('biography'),
        max_length=500,
        blank=True,
        help_text=_('Brief description about the user.')
    )
    
    birth_date = models.DateField(
        _('birth date'),
        null=True,
        blank=True
    )
    
    timezone = models.CharField(
        _('timezone'),
        max_length=50,
        default='America/Guayaquil',
        help_text=_('User timezone for date/time display.')
    )
    
    language = models.CharField(
        _('language'),
        max_length=10,
        default='es',
        choices=[
            ('es', _('Spanish')),
            ('en', _('English')),
        ],
        help_text=_('Preferred language for the interface.')
    )
    
    notifications_enabled = models.BooleanField(
        _('notifications enabled'),
        default=True,
        help_text=_('Whether to receive email notifications.')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"Profile for {self.user.get_display_name()}"