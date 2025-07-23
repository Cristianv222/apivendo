# -*- coding: utf-8 -*-
"""
Models for companies app
Modelos para empresas en VENDO_SRI
"""

import secrets
from django.db import models
from django.utils import timezone
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


# ===================================================================
# 🔥🔥🔥 NUEVO MODELO - TOKEN DE API POR EMPRESA 🔥🔥🔥
# ===================================================================

class CompanyAPIToken(models.Model):
    """
    Token de API específico por empresa
    
    Permite que sistemas externos accedan directamente a UNA empresa
    sin necesidad de especificar company_id en cada request.
    """
    
    company = models.OneToOneField(
        'companies.Company', 
        on_delete=models.CASCADE,
        related_name='api_token',
        verbose_name=_('Company'),
        help_text=_('Company this token belongs to')
    )
    
    key = models.CharField(
        _('Token Key'),
        max_length=64, 
        unique=True,
        help_text=_('Unique token for this company (auto-generated)')
    )
    
    name = models.CharField(
        _('Token Name'),
        max_length=100,
        help_text=_('Descriptive name for this token')
    )
    
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this token is active and can be used')
    )
    
    created_at = models.DateTimeField(
        _('Created At'),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _('Updated At'),
        auto_now=True
    )
    
    # ===============================================================
    # PERMISOS ESPECÍFICOS DEL TOKEN
    # ===============================================================
    
    can_create_documents = models.BooleanField(
        _('Can Create Documents'),
        default=True,
        help_text=_('Permission to create SRI documents (invoices, etc.)')
    )
    
    can_read_documents = models.BooleanField(
        _('Can Read Documents'),
        default=True,
        help_text=_('Permission to read/list SRI documents')
    )
    
    can_update_documents = models.BooleanField(
        _('Can Update Documents'),
        default=False,
        help_text=_('Permission to update SRI documents')
    )
    
    can_delete_documents = models.BooleanField(
        _('Can Delete Documents'),
        default=False,
        help_text=_('Permission to delete SRI documents')
    )
    
    can_manage_customers = models.BooleanField(
        _('Can Manage Customers'),
        default=True,
        help_text=_('Permission to create/edit customers')
    )
    
    can_manage_products = models.BooleanField(
        _('Can Manage Products'),
        default=True,
        help_text=_('Permission to create/edit products')
    )
    
    # ===============================================================
    # LÍMITES Y CONTROL DE USO
    # ===============================================================
    
    requests_per_hour = models.PositiveIntegerField(
        _('Requests Per Hour'),
        default=1000,
        help_text=_('Maximum number of API requests per hour')
    )
    
    requests_per_day = models.PositiveIntegerField(
        _('Requests Per Day'),
        default=10000,
        help_text=_('Maximum number of API requests per day')
    )
    
    # ===============================================================
    # ESTADÍSTICAS DE USO
    # ===============================================================
    
    total_requests = models.PositiveIntegerField(
        _('Total Requests'),
        default=0,
        help_text=_('Total number of requests made with this token')
    )
    
    last_used_at = models.DateTimeField(
        _('Last Used At'),
        null=True, 
        blank=True,
        help_text=_('When this token was last used')
    )
    
    last_used_ip = models.GenericIPAddressField(
        _('Last Used IP'),
        null=True,
        blank=True,
        help_text=_('IP address of last request')
    )
    
    # ===============================================================
    # CONFIGURACIÓN DE EXPIRACIÓN (OPCIONAL)
    # ===============================================================
    
    expires_at = models.DateTimeField(
        _('Expires At'),
        null=True,
        blank=True,
        help_text=_('When this token expires (null = never expires)')
    )
    
    class Meta:
        db_table = 'company_api_tokens'
        verbose_name = _('Company API Token')
        verbose_name_plural = _('Company API Tokens')
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Auto-generar token y nombre si no existen"""
        if not self.key:
            self.key = self.generate_token()
        if not self.name:
            self.name = f"API Token for {self.company.business_name}"
        super().save(*args, **kwargs)
    
    def generate_token(self):
        """
        Generar token único con prefijo identificable
        Formato: vsr_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (48 chars total)
        """
        # Prefijo 'vsr_' para identificar tokens de VendoSRI
        return f"vsr_{secrets.token_urlsafe(33)}"  # 33 bytes = 44 chars + 4 prefix = 48 total
    
    def is_valid(self):
        """
        Verificar si el token es válido para uso
        """
        if not self.is_active:
            return False
        
        if not self.company.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        return True
    
    def increment_usage(self, ip_address=None):
        """
        Incrementar contador de uso y actualizar estadísticas
        """
        self.total_requests += 1
        self.last_used_at = timezone.now()
        
        if ip_address:
            self.last_used_ip = ip_address
        
        # Solo actualizar estos campos específicos para optimizar
        update_fields = ['total_requests', 'last_used_at']
        if ip_address:
            update_fields.append('last_used_ip')
        
        self.save(update_fields=update_fields)
    
    def get_permissions(self):
        """
        Obtener permisos activos del token como diccionario
        """
        return {
            'create_documents': self.can_create_documents,
            'read_documents': self.can_read_documents,
            'update_documents': self.can_update_documents,
            'delete_documents': self.can_delete_documents,
            'manage_customers': self.can_manage_customers,
            'manage_products': self.can_manage_products,
        }
    
    def check_rate_limit(self, period='hour'):
        """
        Verificar si el token está dentro de los límites de rate limiting
        """
        now = timezone.now()
        
        if period == 'hour':
            # Verificar requests en la última hora
            limit = self.requests_per_hour
            time_threshold = now - timezone.timedelta(hours=1)
        elif period == 'day':
            # Verificar requests en el último día
            limit = self.requests_per_day
            time_threshold = now - timezone.timedelta(days=1)
        else:
            return True  # Período no reconocido, permitir
        
        # Aquí podrías implementar un sistema más sofisticado
        # que trackee requests individuales en una tabla separada
        # Por ahora, asumimos que está dentro del límite
        return True
    
    def __str__(self):
        return f"API Token: {self.name} ({self.company.business_name})"
    
    def __repr__(self):
        return f"<CompanyAPIToken: {self.key[:8]}... for {self.company.business_name}>"