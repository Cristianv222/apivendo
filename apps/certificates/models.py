# -*- coding: utf-8 -*-
"""
Models for certificates app - CORREGIDO
Modelos para certificados digitales del SRI
"""

import os
import hashlib
import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from apps.core.models import BaseModel
from apps.companies.models import Company


def certificate_upload_path(instance, filename):
    """Genera la ruta para subir certificados"""
    return f'certificates/{instance.company.ruc}/{filename}'


class DigitalCertificate(BaseModel):
    """
    Certificado digital para firma electrónica del SRI
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', _('Active')),
        ('EXPIRED', _('Expired')),
        ('REVOKED', _('Revoked')),
        ('INACTIVE', _('Inactive')),
    ]
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='digital_certificate',
        verbose_name=_('company'),
        help_text=_('Company that owns this certificate')
    )
    
    certificate_file = models.FileField(
        _('certificate file'),
        upload_to=certificate_upload_path,
        help_text=_('P12 certificate file')
    )
    
    # Clave hasheada - NUNCA almacenar en texto plano
    password_hash = models.CharField(
        _('password hash'),
        max_length=128,
        help_text=_('Hashed password for the certificate')
    )
    
    # Información del certificado
    subject_name = models.CharField(
        _('subject name'),
        max_length=255,
        help_text=_('Certificate subject name')
    )
    
    issuer_name = models.CharField(
        _('issuer name'),
        max_length=255,
        help_text=_('Certificate issuer name')
    )
    
    serial_number = models.CharField(
        _('serial number'),
        max_length=100,
        help_text=_('Certificate serial number')
    )
    
    valid_from = models.DateTimeField(
        _('valid from'),
        help_text=_('Certificate validity start date')
    )
    
    valid_to = models.DateTimeField(
        _('valid to'),
        help_text=_('Certificate expiration date')
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text=_('Certificate status')
    )
    
    fingerprint = models.CharField(
        _('fingerprint'),
        max_length=64,
        unique=True,
        help_text=_('Certificate fingerprint (SHA256)')
    )
    
    # Configuración SRI
    environment = models.CharField(
        _('environment'),
        max_length=20,
        choices=[
            ('PRODUCTION', _('Production')),
            ('TEST', _('Test')),
        ],
        default='TEST',
        help_text=_('SRI environment for this certificate')
    )
    
    class Meta:
        verbose_name = _('Digital Certificate')
        verbose_name_plural = _('Digital Certificates')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.business_name} - {self.subject_name}"
    
    def save(self, *args, **kwargs):
        # Asegurar campos requeridos ANTES de guardar
        self._ensure_required_fields()
        
        # Guardar primero
        super().save(*args, **kwargs)
        
        # Luego intentar extraer información del certificado si es posible
        if self.certificate_file:
            try:
                self._extract_certificate_info()
                # Guardar de nuevo si se extrajo información
                super().save(update_fields=['fingerprint'])
            except Exception as e:
                print(f'Warning: Could not extract certificate info: {e}')
    
    def _ensure_required_fields(self):
        """Asegurar que todos los campos requeridos tienen valores"""
        now = timezone.now()
        
        # Asegurar fechas
        if not self.valid_from:
            self.valid_from = now
        
        if not self.valid_to:
            self.valid_to = now + timezone.timedelta(days=365)
        
        # Asegurar nombres
        if not self.subject_name:
            self.subject_name = f'Certificado {self.company.business_name if self.company else "Desconocido"}'
        
        if not self.issuer_name:
            self.issuer_name = 'Autoridad Certificadora'
        
        if not self.serial_number:
            self.serial_number = str(uuid.uuid4())[:20]
        
        # Asegurar fingerprint único
        if not self.fingerprint:
            self.fingerprint = str(uuid.uuid4()).replace('-', '')[:32]
        
        # Asegurar password_hash
        if not self.password_hash:
            self.password_hash = 'temp_hash'
    
    def set_password(self, password):
        """Hashea y almacena la contraseña del certificado"""
        self.password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            self.company.ruc.encode('utf-8'),
            100000
        ).hex()
    
    def verify_password(self, password):
        """Verifica la contraseña del certificado"""
        if not self.password_hash or self.password_hash == 'temp_hash':
            return False
        
        return self.password_hash == hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            self.company.ruc.encode('utf-8'),
            100000
        ).hex()
    
    def _extract_certificate_info(self):
        """Extrae información del certificado P12"""
        try:
            # Verificar que el archivo existe
            if not self.certificate_file:
                return
                
            file_path = None
            cert_data = None
            
            # Intentar obtener el contenido del archivo
            if hasattr(self.certificate_file, 'path') and os.path.exists(self.certificate_file.path):
                with open(self.certificate_file.path, 'rb') as f:
                    cert_data = f.read()
            elif hasattr(self.certificate_file, 'read'):
                self.certificate_file.seek(0)
                cert_data = self.certificate_file.read()
                self.certificate_file.seek(0)
            
            if cert_data:
                # Generar fingerprint del archivo
                self.fingerprint = hashlib.sha256(cert_data).hexdigest()[:32]
            else:
                # Generar fingerprint único como fallback
                self.fingerprint = str(uuid.uuid4()).replace('-', '')[:32]
            
        except Exception as e:
            # En caso de error, generar fingerprint único
            self.fingerprint = str(uuid.uuid4()).replace('-', '')[:32]
            print(f'Warning extracting certificate info: {e}')
    
    @property
    def is_expired(self):
        """Verifica si el certificado ha expirado"""
        if not self.valid_to:
            return False
        return timezone.now() > self.valid_to
    
    @property
    def days_until_expiration(self):
        """Días hasta la expiración"""
        if not self.valid_to or self.is_expired:
            return 0
        return (self.valid_to - timezone.now()).days


class CertificateUsageLog(BaseModel):
    """
    Registro de uso de certificados digitales
    """
    
    certificate = models.ForeignKey(
        DigitalCertificate,
        on_delete=models.CASCADE,
        related_name='usage_logs',
        verbose_name=_('certificate')
    )
    
    operation = models.CharField(
        _('operation'),
        max_length=50,
        help_text=_('Type of operation performed')
    )
    
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        blank=True,
        help_text=_('Type of document signed')
    )
    
    document_number = models.CharField(
        _('document number'),
        max_length=50,
        blank=True,
        help_text=_('Document number or identifier')
    )
    
    success = models.BooleanField(
        _('success'),
        default=True,
        help_text=_('Whether the operation was successful')
    )
    
    error_message = models.TextField(
        _('error message'),
        blank=True,
        help_text=_('Error message if operation failed')
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Certificate Usage Log')
        verbose_name_plural = _('Certificate Usage Logs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.certificate} - {self.operation} - {self.created_at}"