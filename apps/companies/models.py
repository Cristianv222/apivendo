# -*- coding: utf-8 -*-
"""
Models for companies app
Modelos para empresas en VENDO_SRI
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """
    Modelo para empresas
    
    NOTA: Inicialmente no hereda de BaseModel para evitar dependencia circular.
    Los campos de auditoría (created_by, updated_by) se agregarán en una 
    migración posterior después de que User esté creado.
    """
    
    # Información básica
    ruc = models.CharField(
        _('RUC'),
        max_length=13,
        unique=True,
        help_text=_('RUC number (13 digits)')
    )
    
    business_name = models.CharField(
        _('business name'),
        max_length=300,
        help_text=_('Official business name')
    )
    
    trade_name = models.CharField(
        _('trade name'),
        max_length=300,
        blank=True,
        help_text=_('Commercial or trade name')
    )
    
    # Información de contacto
    email = models.EmailField(
        _('email'),
        help_text=_('Main contact email')
    )
    
    phone = models.CharField(
        _('phone'),
        max_length=20,
        blank=True,
        help_text=_('Main contact phone')
    )
    
    address = models.TextField(
        _('address'),
        help_text=_('Complete business address')
    )
    
    # Estado
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether the company is active in the system')
    )
    
    # Campos básicos de timestamp (sin referencias a User por ahora)
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        help_text=_('Date and time when the record was created.')
    )
    
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_('Date and time when the record was last updated.')
    )
    
    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')
        ordering = ['business_name']
    
    def __str__(self):
        return f"{self.business_name} ({self.ruc})"
    
    @property
    def display_name(self):
        """Devuelve el nombre comercial o razón social"""
        return self.trade_name if self.trade_name else self.business_name
    
    def save(self, *args, **kwargs):
        """Guarda el modelo con validaciones adicionales"""
        self.full_clean()
        super().save(*args, **kwargs)