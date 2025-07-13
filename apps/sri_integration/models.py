# -*- coding: utf-8 -*-
"""
Models for SRI integration
Modelos para integración con el SRI
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.companies.models import Company


class SRIConfiguration(BaseModel):
    """
    Configuración del SRI por empresa
    """
    
    ENVIRONMENT_CHOICES = [
        ('PRODUCTION', _('Production')),
        ('TEST', _('Test')),
    ]
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='sri_configuration',
        verbose_name=_('company')
    )
    
    environment = models.CharField(
        _('environment'),
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default='TEST',
        help_text=_('SRI environment')
    )
    
    # URLs del SRI
    reception_url = models.URLField(
        _('reception URL'),
        help_text=_('SRI reception service URL')
    )
    
    authorization_url = models.URLField(
        _('authorization URL'),
        help_text=_('SRI authorization service URL')
    )
    
    # Configuración de establecimiento
    establishment_code = models.CharField(
        _('establishment code'),
        max_length=3,
        default='001',
        help_text=_('Establishment code (3 digits)')
    )
    
    emission_point = models.CharField(
        _('emission point'),
        max_length=3,
        default='001',
        help_text=_('Emission point code (3 digits)')
    )
    
    # Configuración de secuenciales
    invoice_sequence = models.PositiveIntegerField(
        _('invoice sequence'),
        default=1,
        help_text=_('Current invoice sequence number')
    )
    
    credit_note_sequence = models.PositiveIntegerField(
        _('credit note sequence'),
        default=1,
        help_text=_('Current credit note sequence number')
    )
    
    debit_note_sequence = models.PositiveIntegerField(
        _('debit note sequence'),
        default=1,
        help_text=_('Current debit note sequence number')
    )
    
    retention_sequence = models.PositiveIntegerField(
        _('retention sequence'),
        default=1,
        help_text=_('Current retention sequence number')
    )
    
    remission_guide_sequence = models.PositiveIntegerField(
        _('remission guide sequence'),
        default=1,
        help_text=_('Current remission guide sequence number')
    )
    
    # Configuración de email
    email_enabled = models.BooleanField(
        _('email enabled'),
        default=True,
        help_text=_('Enable automatic email sending')
    )
    
    email_subject_template = models.CharField(
        _('email subject template'),
        max_length=255,
        default='Documento Electrónico - {document_type} {document_number}',
        help_text=_('Email subject template')
    )
    
    email_body_template = models.TextField(
        _('email body template'),
        default='Estimado cliente,\n\nEn archivo adjunto encontrará su {document_type} electrónico número {document_number}.\n\nSaludos cordiales.',
        help_text=_('Email body template')
    )
    
    # Configuración adicional
    special_taxpayer = models.BooleanField(
        _('special taxpayer'),
        default=False,
        help_text=_('Is special taxpayer')
    )
    
    special_taxpayer_number = models.CharField(
        _('special taxpayer number'),
        max_length=20,
        blank=True,
        help_text=_('Special taxpayer resolution number')
    )
    
    accounting_required = models.BooleanField(
        _('accounting required'),
        default=True,
        help_text=_('Required to keep accounting')
    )
    
    class Meta:
        verbose_name = _('SRI Configuration')
        verbose_name_plural = _('SRI Configurations')
    
    def __str__(self):
        return f"SRI Config - {self.company.business_name} ({self.environment})"
    
    def get_next_sequence(self, document_type):
        """Obtiene el siguiente secuencial para un tipo de documento"""
        field_map = {
            'INVOICE': 'invoice_sequence',
            'CREDIT_NOTE': 'credit_note_sequence',
            'DEBIT_NOTE': 'debit_note_sequence',
            'RETENTION': 'retention_sequence',
            'REMISSION_GUIDE': 'remission_guide_sequence',
        }
        
        if document_type not in field_map:
            raise ValidationError(f"Unknown document type: {document_type}")
        
        field_name = field_map[document_type]
        current_value = getattr(self, field_name)
        
        # Incrementar y guardar
        setattr(self, field_name, current_value + 1)
        self.save()
        
        return current_value
    
    def get_full_document_number(self, document_type, sequence=None):
        """Genera el número completo del documento"""
        if sequence is None:
            sequence = self.get_next_sequence(document_type)
        
        return f"{self.establishment_code}-{self.emission_point}-{sequence:09d}"


class ElectronicDocument(BaseModel):
    """
    Modelo base para documentos electrónicos del SRI
    """
    
    DOCUMENT_TYPES = [
        ('INVOICE', _('Invoice')),
        ('CREDIT_NOTE', _('Credit Note')),
        ('DEBIT_NOTE', _('Debit Note')),
        ('RETENTION', _('Retention')),
        ('REMISSION_GUIDE', _('Remission Guide')),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', _('Draft')),
        ('GENERATED', _('Generated')),
        ('SIGNED', _('Signed')),
        ('SENT', _('Sent to SRI')),
        ('AUTHORIZED', _('Authorized')),
        ('REJECTED', _('Rejected')),
        ('ERROR', _('Error')),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='electronic_documents',
        verbose_name=_('company')
    )
    
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        choices=DOCUMENT_TYPES
    )
    
    document_number = models.CharField(
        _('document number'),
        max_length=17,
        help_text=_('Format: 001-001-000000001')
    )
    
    access_key = models.CharField(
        _('access key'),
        max_length=49,
        unique=True,
        help_text=_('49-digit access key')
    )
    
    issue_date = models.DateField(
        _('issue date')
    )
    
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    
    # Información del cliente
    customer_identification_type = models.CharField(
        _('customer identification type'),
        max_length=2,
        choices=[
            ('04', _('RUC')),
            ('05', _('Cedula')),
            ('06', _('Passport')),
            ('07', _('Consumer')),
            ('08', _('Foreign ID')),
        ]
    )
    
    customer_identification = models.CharField(
        _('customer identification'),
        max_length=20
    )
    
    customer_name = models.CharField(
        _('customer name'),
        max_length=300
    )
    
    customer_address = models.TextField(
        _('customer address'),
        blank=True
    )
    
    customer_email = models.EmailField(
        _('customer email'),
        blank=True
    )
    
    customer_phone = models.CharField(
        _('customer phone'),
        max_length=20,
        blank=True
    )
    
    # Totales
    subtotal_without_tax = models.DecimalField(
        _('subtotal without tax'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    subtotal_with_tax = models.DecimalField(
        _('subtotal with tax'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    total_discount = models.DecimalField(
        _('total discount'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    total_tax = models.DecimalField(
        _('total tax'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Archivos generados
    xml_file = models.FileField(
        _('XML file'),
        upload_to='invoices/xml/',
        blank=True
    )
    
    signed_xml_file = models.FileField(
        _('signed XML file'),
        upload_to='invoices/xml/',
        blank=True
    )
    
    pdf_file = models.FileField(
        _('PDF file'),
        upload_to='invoices/pdf/',
        blank=True
    )
    
    # Información del SRI
    sri_authorization_code = models.CharField(
        _('SRI authorization code'),
        max_length=49,
        blank=True
    )
    
    sri_authorization_date = models.DateTimeField(
        _('SRI authorization date'),
        null=True,
        blank=True
    )
    
    sri_response = models.JSONField(
        _('SRI response'),
        default=dict,
        blank=True
    )
    
    # Email
    email_sent = models.BooleanField(
        _('email sent'),
        default=False
    )
    
    email_sent_date = models.DateTimeField(
        _('email sent date'),
        null=True,
        blank=True
    )
    
    # Datos adicionales
    additional_data = models.JSONField(
        _('additional data'),
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Electronic Document')
        verbose_name_plural = _('Electronic Documents')
        unique_together = ['company', 'document_number', 'document_type']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['access_key']),
            models.Index(fields=['issue_date']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} {self.document_number} - {self.company.business_name}"
    
    def save(self, *args, **kwargs):
        if not self.access_key:
            self.access_key = self._generate_access_key()
        super().save(*args, **kwargs)
    
    def _generate_access_key(self):
        """Genera la clave de acceso de 49 dígitos"""
        from datetime import datetime
        
        # Formato: ddmmyyyytipodocumentorucestablecimientopuntoemisionssecuencialcodigonumerico1digito_verificador
        date_str = self.issue_date.strftime('%d%m%Y')
        
        doc_type_map = {
            'INVOICE': '01',
            'CREDIT_NOTE': '04',
            'DEBIT_NOTE': '05',
            'RETENTION': '07',
            'REMISSION_GUIDE': '06',
        }
        
        doc_type_code = doc_type_map.get(self.document_type, '01')
        ruc = self.company.ruc
        establishment = '001'  # Por defecto
        emission_point = '001'  # Por defecto
        sequence = self.document_number.split('-')[-1]
        numeric_code = '12345678'  # Código numérico (configurable)
        emission_type = '1'  # Emisión normal
        
        # Construir clave sin dígito verificador
        partial_key = f"{date_str}{doc_type_code}{ruc}{establishment}{emission_point}{sequence}{numeric_code}{emission_type}"
        
        # Calcular dígito verificador usando módulo 11
        check_digit = self._calculate_check_digit(partial_key)
        
        return f"{partial_key}{check_digit}"
    
    def _calculate_check_digit(self, partial_key):
        """Calcula el dígito verificador usando módulo 11"""
        multipliers = [7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        
        total = sum(int(digit) * multiplier for digit, multiplier in zip(partial_key, multipliers))
        remainder = total % 11
        
        if remainder == 0:
            return 0
        elif remainder == 1:
            return 1
        else:
            return 11 - remainder


class DocumentItem(BaseModel):
    """
    Líneas de detalle de documentos electrónicos
    """
    
    document = models.ForeignKey(
        ElectronicDocument,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('document')
    )
    
    main_code = models.CharField(
        _('main code'),
        max_length=25,
        help_text=_('Product main code')
    )
    
    auxiliary_code = models.CharField(
        _('auxiliary code'),
        max_length=25,
        blank=True,
        help_text=_('Product auxiliary code')
    )
    
    description = models.TextField(
        _('description'),
        help_text=_('Product description')
    )
    
    quantity = models.DecimalField(
        _('quantity'),
        max_digits=12,
        decimal_places=6
    )
    
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=12,
        decimal_places=6
    )
    
    discount = models.DecimalField(
        _('discount'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=12,
        decimal_places=2
    )
    
    # Información adicional del producto
    additional_details = models.JSONField(
        _('additional details'),
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Document Item')
        verbose_name_plural = _('Document Items')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal = (self.quantity * self.unit_price) - self.discount
        super().save(*args, **kwargs)


class DocumentTax(BaseModel):
    """
    Impuestos aplicados a documentos electrónicos
    """
    
    TAX_CODES = [
        ('2', _('IVA')),
        ('3', _('ICE')),
        ('5', _('IRBPNR')),
    ]
    
    TAX_RATES = [
        ('0', _('0%')),
        ('2', _('12%')),
        ('3', _('14%')),
        ('6', _('No Objeto de Impuesto')),
        ('7', _('Exento de IVA')),
    ]
    
    document = models.ForeignKey(
        ElectronicDocument,
        on_delete=models.CASCADE,
        related_name='taxes',
        verbose_name=_('document')
    )
    
    item = models.ForeignKey(
        DocumentItem,
        on_delete=models.CASCADE,
        related_name='taxes',
        verbose_name=_('item'),
        null=True,
        blank=True
    )
    
    tax_code = models.CharField(
        _('tax code'),
        max_length=2,
        choices=TAX_CODES
    )
    
    percentage_code = models.CharField(
        _('percentage code'),
        max_length=2,
        choices=TAX_RATES
    )
    
    rate = models.DecimalField(
        _('tax rate'),
        max_digits=5,
        decimal_places=2
    )
    
    taxable_base = models.DecimalField(
        _('taxable base'),
        max_digits=12,
        decimal_places=2
    )
    
    tax_amount = models.DecimalField(
        _('tax amount'),
        max_digits=12,
        decimal_places=2
    )
    
    class Meta:
        verbose_name = _('Document Tax')
        verbose_name_plural = _('Document Taxes')
    
    def __str__(self):
        return f"{self.get_tax_code_display()} {self.rate}% - {self.tax_amount}"


class SRIResponse(BaseModel):
    """
    Respuestas del SRI
    """
    
    document = models.ForeignKey(
        ElectronicDocument,
        on_delete=models.CASCADE,
        related_name='sri_responses',
        verbose_name=_('document')
    )
    
    operation_type = models.CharField(
        _('operation type'),
        max_length=20,
        choices=[
            ('RECEPTION', _('Reception')),
            ('AUTHORIZATION', _('Authorization')),
        ]
    )
    
    response_code = models.CharField(
        _('response code'),
        max_length=10
    )
    
    response_message = models.TextField(
        _('response message')
    )
    
    raw_response = models.JSONField(
        _('raw response'),
        default=dict
    )
    
    class Meta:
        verbose_name = _('SRI Response')
        verbose_name_plural = _('SRI Responses')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operation_type} - {self.response_code} - {self.document}"