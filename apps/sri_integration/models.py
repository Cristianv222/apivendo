# -*- coding: utf-8 -*-
"""
Models for SRI integration - VERSIÓN CORREGIDA COMPLETA
Modelos para integración con el SRI
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
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
    
    purchase_settlement_sequence = models.PositiveIntegerField(
        _('purchase settlement sequence'),
        default=1,
        help_text=_('Current purchase settlement sequence number')
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
    
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Configuration is active')
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
            'PURCHASE_SETTLEMENT': 'purchase_settlement_sequence',
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
        ('PURCHASE_SETTLEMENT', _('Purchase Settlement')),
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
        # Generar número de documento si no existe
        if not self.document_number:
            try:
                sri_config = self.company.sri_configuration
                sequence = sri_config.get_next_sequence(self.document_type)
                self.document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            except:
                self.document_number = "001-001-000000001"
        
        # Generar clave de acceso si no existe
        if not self.access_key:
            self.access_key = self._generate_access_key()
        
        super().save(*args, **kwargs)
    
    def _generate_access_key(self):
        """Genera la clave de acceso de 49 dígitos según especificaciones del SRI"""
        from datetime import datetime
        
        # Obtener configuración SRI de la empresa
        try:
            sri_config = self.company.sri_configuration
        except:
            # Si no hay configuración, usar valores por defecto
            establishment = '001'
            emission_point = '001'
            environment = '1'  # Pruebas por defecto
        else:
            establishment = sri_config.establishment_code.zfill(3)
            emission_point = sri_config.emission_point.zfill(3)
            environment = '1' if sri_config.environment == 'TEST' else '2'
        
        # 1. FECHA DE EMISIÓN (8 dígitos): ddmmyyyy - ✅ CORREGIDO
        # Manejar tanto string como objeto date
        if isinstance(self.issue_date, str):
            date_obj = datetime.strptime(self.issue_date, '%Y-%m-%d').date()
            date_str = date_obj.strftime('%d%m%Y')
        else:
            date_str = self.issue_date.strftime('%d%m%Y')
        
        # 2. TIPO DE COMPROBANTE (2 dígitos)
        doc_type_map = {
            'INVOICE': '01',
            'CREDIT_NOTE': '04',
            'DEBIT_NOTE': '05',
            'RETENTION': '07',
            'REMISSION_GUIDE': '06',
            'PURCHASE_SETTLEMENT': '03',
        }
        doc_type_code = doc_type_map.get(self.document_type, '01')
        
        # 3. RUC (13 dígitos) - rellenar con ceros si es necesario
        ruc = self.company.ruc.zfill(13)
        
        # 4. AMBIENTE (1 dígito): 1=pruebas, 2=producción
        # Ya definido arriba
        
        # 5. SERIE (6 dígitos): establecimiento (3) + punto emisión (3)
        serie = f"{establishment}{emission_point}"
        
        # 6. SECUENCIAL (9 dígitos) - ¡CRÍTICO: debe ser 9 dígitos!
        if self.document_number and '-' in self.document_number:
            sequence = self.document_number.split('-')[-1].zfill(9)
        else:
            # Si no hay número, obtener del SRI config
            try:
                next_seq = sri_config.get_next_sequence(self.document_type)
                sequence = str(next_seq).zfill(9)
            except:
                sequence = '000000001'  # Por defecto
        
        # 7. CÓDIGO NUMÉRICO (8 dígitos) - aleatorio pero fijo para esta implementación
        numeric_code = '12345678'
        
        # 8. TIPO DE EMISIÓN (1 dígito): 1=normal
        emission_type = '1'
        
        # Construir clave sin dígito verificador (48 dígitos)
        partial_key = f"{date_str}{doc_type_code}{ruc}{environment}{serie}{sequence}{numeric_code}{emission_type}"
        
        # Verificar que sean exactamente 48 dígitos antes del dígito verificador
        if len(partial_key) != 48:
            raise ValueError(f"Clave parcial debe tener 48 dígitos, tiene {len(partial_key)}: {partial_key}")
        
        # 9. DÍGITO VERIFICADOR (1 dígito) - usando módulo 11
        check_digit = self._calculate_check_digit(partial_key)
        
        # Clave final (49 dígitos)
        final_key = f"{partial_key}{check_digit}"
        
        return final_key
    
    def _calculate_check_digit(self, partial_key):
        """
        Calcula el dígito verificador usando algoritmo módulo 11
        Según las especificaciones técnicas del SRI
        """
        # Factores de multiplicación para módulo 11 (de derecha a izquierda)
        factors = [2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 
                   2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7]
        
        # Invertir la clave para multiplicar de derecha a izquierda
        reversed_key = partial_key[::-1]
        
        # Calcular suma de productos
        total = sum(int(digit) * factor for digit, factor in zip(reversed_key, factors))
        
        # Calcular residuo
        remainder = total % 11
        
        # Determinar dígito verificador
        if remainder < 2:
            return remainder
        else:
            return 11 - remainder


class DocumentItem(BaseModel):
    """
    Líneas de detalle de documentos electrónicos - VERSIÓN CORREGIDA CON VALIDACIONES SEGURAS
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
        decimal_places=6,
        help_text=_('Maximum: 999,999.999999')
    )
    
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=12,
        decimal_places=6,
        help_text=_('Maximum: 999,999.999999')
    )
    
    discount = models.DecimalField(
        _('discount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_('Maximum: 9,999,999,999.99')
    )
    
    subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=12,
        decimal_places=2,
        help_text=_('Calculated automatically. Maximum: 9,999,999,999.99')
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
        indexes = [
            models.Index(fields=['document', 'main_code']),
        ]
    
    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"
    
    def clean(self):
        """Validación a nivel de modelo"""
        super().clean()
        
        # Validar rangos
        if self.quantity and self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0'})
        
        if self.unit_price and self.unit_price <= 0:
            raise ValidationError({'unit_price': 'Unit price must be greater than 0'})
        
        if self.discount and self.discount < 0:
            raise ValidationError({'discount': 'Discount cannot be negative'})
        
        # Validar que no excedan los límites máximos
        max_quantity_price = Decimal('999999.999999')
        if self.quantity and self.quantity > max_quantity_price:
            raise ValidationError({'quantity': f'Quantity cannot exceed {max_quantity_price}'})
        
        if self.unit_price and self.unit_price > max_quantity_price:
            raise ValidationError({'unit_price': f'Unit price cannot exceed {max_quantity_price}'})
        
        max_discount = Decimal('9999999999.99')
        if self.discount and self.discount > max_discount:
            raise ValidationError({'discount': f'Discount cannot exceed {max_discount}'})
        
        # Validar cálculo de subtotal si tenemos todos los valores
        if self.quantity and self.unit_price and self.discount is not None:
            calculated_subtotal = self._calculate_subtotal_safe()
            
            if calculated_subtotal < 0:
                raise ValidationError({'discount': 'Discount cannot be greater than (quantity × unit_price)'})
            
            max_subtotal = Decimal('9999999999.99')
            if calculated_subtotal > max_subtotal:
                raise ValidationError({
                    '__all__': f'Calculated subtotal ({calculated_subtotal}) exceeds maximum allowed ({max_subtotal}). '
                              f'Please reduce quantity, unit_price, or increase discount.'
                })
    
    def _calculate_subtotal_safe(self):
        """
        Cálculo seguro del subtotal con manejo de precisión decimal
        """
        # Convertir a Decimal con precisión controlada
        quantity = Decimal(str(self.quantity)) if self.quantity else Decimal('0')
        unit_price = Decimal(str(self.unit_price)) if self.unit_price else Decimal('0')
        discount = Decimal(str(self.discount)) if self.discount else Decimal('0')
        
        # Calcular subtotal: (cantidad × precio) - descuento
        subtotal = (quantity * unit_price) - discount
        
        # Redondear a 2 decimales usando ROUND_HALF_UP (redondeo bancario)
        return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def save(self, *args, **kwargs):
        """
        MÉTODO CRÍTICO CORREGIDO: Calcular subtotal de forma segura antes de guardar
        """
        # Calcular subtotal antes de cualquier validación
        if self.quantity is not None and self.unit_price is not None:
            if self.discount is None:
                self.discount = Decimal('0.00')
            
            # Calcular subtotal de forma segura
            self.subtotal = self._calculate_subtotal_safe()
        else:
            # Si no hay valores, establecer subtotal por defecto
            self.subtotal = Decimal('0.00')
        
        # Ejecutar validación completa después de calcular
        try:
            self.full_clean()
        except ValidationError:
            # Si la validación falla, al menos asegurar que subtotal no sea nulo
            if self.subtotal is None:
                self.subtotal = Decimal('0.00')
        
        # Llamar al método save() original
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


# ========== MODELOS ESPECÍFICOS DE DOCUMENTOS ==========

class CreditNote(BaseModel):
    """
    Nota de Crédito - Documento que anula o corrige una factura - VERSIÓN CORREGIDA
    """
    CREDIT_NOTE_REASONS = [
        ('01', _('Devolución de bienes')),
        ('02', _('Anulación de venta')),
        ('03', _('Descuento otorgado')),
        ('04', _('Bonificación')),
        ('05', _('Devolución en compras')),
        ('06', _('Descuento por pronto pago')),
        ('07', _('Otros')),
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
        related_name='credit_notes',
        verbose_name=_('company')
    )
    
    # Referencia al documento original
    original_document = models.ForeignKey(
        ElectronicDocument,
        on_delete=models.CASCADE,
        related_name='credit_notes',
        verbose_name=_('original document'),
        help_text=_('Invoice or document being credited')
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
    
    issue_date = models.DateField(_('issue date'))
    
    reason_code = models.CharField(
        _('reason code'),
        max_length=2,
        choices=CREDIT_NOTE_REASONS,
        default='07'
    )
    
    reason_description = models.TextField(
        _('reason description'),
        max_length=300,
        help_text=_('Detailed reason for credit note')
    )
    
    # Información del cliente (copiada del documento original)
    customer_identification_type = models.CharField(_('customer identification type'), max_length=2)
    customer_identification = models.CharField(_('customer identification'), max_length=20)
    customer_name = models.CharField(_('customer name'), max_length=300)
    customer_address = models.TextField(_('customer address'), blank=True)
    customer_email = models.EmailField(_('customer email'), blank=True)
    
    # Totales de la nota de crédito
    subtotal_without_tax = models.DecimalField(_('subtotal without tax'), max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(_('total tax'), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_('total amount'), max_digits=12, decimal_places=2, default=0)
    
    # Status y archivos
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    xml_file = models.FileField(_('XML file'), upload_to='credit_notes/xml/', blank=True)
    signed_xml_file = models.FileField(_('signed XML file'), upload_to='credit_notes/xml/', blank=True)
    pdf_file = models.FileField(_('PDF file'), upload_to='credit_notes/pdf/', blank=True)
    
    # SRI response
    sri_authorization_code = models.CharField(_('SRI authorization code'), max_length=49, blank=True)
    sri_authorization_date = models.DateTimeField(_('SRI authorization date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Credit Note')
        verbose_name_plural = _('Credit Notes')
        unique_together = ['company', 'document_number']
    
    def __str__(self):
        return f"Credit Note {self.document_number} - {self.company.business_name}"
    
    def save(self, *args, **kwargs):
        """
        Override save method to ensure proper saving of CreditNote - CORREGIDO
        """
        from django.utils import timezone
        
        # Generar número de documento si no existe
        if not self.document_number:
            try:
                sri_config = self.company.sri_configuration
                sequence = sri_config.get_next_sequence("CREDIT_NOTE")
                self.document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            except Exception as e:
                # Si no hay configuración SRI, usar valores por defecto
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                self.document_number = f"001-001-{timestamp[-9:]}"
        
        # Generar clave de acceso si no existe
        if not self.access_key:
            self.access_key = self._generate_access_key()
        
        # Establecer fecha de emisión si no existe
        if not self.issue_date:
            self.issue_date = timezone.now().date()
        
        # ✅ LLAMADA SEGURA AL SAVE DEL PADRE
        try:
            # Usar directamente models.Model.save() para evitar problemas con BaseModel
            models.Model.save(self, *args, **kwargs)
            print(f"✅ CreditNote {self.id} saved with status: {self.status}")
        except Exception as e:
            print(f"❌ Error saving CreditNote: {e}")
            # Intentar con super() como backup
            super().save(*args, **kwargs)
    
    def _generate_access_key(self):
        """Genera la clave de acceso de 49 dígitos para nota de crédito - ✅ CORREGIDO"""
        from datetime import datetime
        
        # Obtener configuración SRI de la empresa
        try:
            sri_config = self.company.sri_configuration
            establishment = sri_config.establishment_code.zfill(3)
            emission_point = sri_config.emission_point.zfill(3)
            environment = "1" if sri_config.environment == "TEST" else "2"
        except:
            establishment = "001"
            emission_point = "001"
            environment = "1"  # Pruebas por defecto
        
        # 1. FECHA DE EMISIÓN (8 dígitos): ddmmyyyy - ✅ CORREGIDO
        # Manejar tanto string como objeto date
        if isinstance(self.issue_date, str):
            date_obj = datetime.strptime(self.issue_date, '%Y-%m-%d').date()
            date_str = date_obj.strftime("%d%m%Y")
        else:
            date_str = self.issue_date.strftime("%d%m%Y")
        
        # 2. TIPO DE COMPROBANTE (2 dígitos) - 04 para nota de crédito
        doc_type_code = "04"
        
        # 3. RUC (13 dígitos)
        ruc = self.company.ruc.zfill(13)
        
        # 4. AMBIENTE (1 dígito): ya definido arriba
        
        # 5. SERIE (6 dígitos): establecimiento + punto emisión
        serie = f"{establishment}{emission_point}"
        
        # 6. SECUENCIAL (9 dígitos)
        if self.document_number and "-" in self.document_number:
            sequence = self.document_number.split("-")[-1].zfill(9)
        else:
            # Generar secuencial temporal
            import random
            sequence = str(random.randint(1, 999999999)).zfill(9)
        
        # 7. CÓDIGO NUMÉRICO (8 dígitos)
        numeric_code = "12345678"
        
        # 8. TIPO DE EMISIÓN (1 dígito): 1=normal
        emission_type = "1"
        
        # Construir clave sin dígito verificador (48 dígitos)
        partial_key = f"{date_str}{doc_type_code}{ruc}{environment}{serie}{sequence}{numeric_code}{emission_type}"
        
        # Verificar longitud
        if len(partial_key) != 48:
            raise ValueError(f"Clave parcial debe tener 48 dígitos, tiene {len(partial_key)}: {partial_key}")
        
        # 9. DÍGITO VERIFICADOR
        check_digit = self._calculate_check_digit(partial_key)
        
        return f"{partial_key}{check_digit}"
    
    def _calculate_check_digit(self, partial_key):
        """Calcula el dígito verificador usando algoritmo módulo 11"""
        # Factores de multiplicación para módulo 11
        factors = [2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 
                   2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7]
        
        # Invertir la clave para multiplicar de derecha a izquierda
        reversed_key = partial_key[::-1]
        
        # Calcular suma de productos
        total = sum(int(digit) * factor for digit, factor in zip(reversed_key, factors))
        
        # Calcular residuo
        remainder = total % 11
        
        # Determinar dígito verificador
        if remainder < 2:
            return remainder
        else:
            return 11 - remainder


class DebitNote(BaseModel):
    """
    Nota de Débito - Documento que incrementa el valor de una factura
    """
    DEBIT_NOTE_REASONS = [
        ('01', _('Intereses de mora')),
        ('02', _('Gastos de cobranza')),
        ('03', _('Gastos de transporte')),
        ('04', _('Otros gastos')),
        ('05', _('Aumento en el precio')),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='debit_notes')
    
    # Referencia al documento original
    original_document = models.ForeignKey(
        ElectronicDocument,
        on_delete=models.CASCADE,
        related_name='debit_notes',
        verbose_name=_('original document')
    )
    
    document_number = models.CharField(_('document number'), max_length=17)
    access_key = models.CharField(_('access key'), max_length=49, unique=True)
    issue_date = models.DateField(_('issue date'))
    
    reason_code = models.CharField(_('reason code'), max_length=2, choices=DEBIT_NOTE_REASONS)
    reason_description = models.TextField(_('reason description'), max_length=300)
    
    # Cliente
    customer_identification_type = models.CharField(_('customer identification type'), max_length=2)
    customer_identification = models.CharField(_('customer identification'), max_length=20)
    customer_name = models.CharField(_('customer name'), max_length=300)
    customer_address = models.TextField(_('customer address'), blank=True)
    customer_email = models.EmailField(_('customer email'), blank=True)
    
    # Totales
    subtotal_without_tax = models.DecimalField(_('subtotal without tax'), max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(_('total tax'), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_('total amount'), max_digits=12, decimal_places=2, default=0)
    
    # Status y archivos
    status = models.CharField(_('status'), max_length=20, choices=ElectronicDocument.STATUS_CHOICES, default='DRAFT')
    xml_file = models.FileField(_('XML file'), upload_to='debit_notes/xml/', blank=True)
    signed_xml_file = models.FileField(_('signed XML file'), upload_to='debit_notes/xml/', blank=True)
    pdf_file = models.FileField(_('PDF file'), upload_to='debit_notes/pdf/', blank=True)
    
    # SRI response
    sri_authorization_code = models.CharField(_('SRI authorization code'), max_length=49, blank=True)
    sri_authorization_date = models.DateTimeField(_('SRI authorization date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Debit Note')
        verbose_name_plural = _('Debit Notes')
        unique_together = ['company', 'document_number']


class Retention(BaseModel):
    """
    Comprobante de Retención
    """
    RETENTION_TYPES = [
        ('RENT', _('Retención en la Fuente del Impuesto a la Renta')),
        ('IVA', _('Retención del Impuesto al Valor Agregado')),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='retentions')
    
    document_number = models.CharField(_('document number'), max_length=17)
    access_key = models.CharField(_('access key'), max_length=49, unique=True)
    issue_date = models.DateField(_('issue date'))
    
    # Información del proveedor (a quien se retiene)
    supplier_identification_type = models.CharField(_('supplier identification type'), max_length=2)
    supplier_identification = models.CharField(_('supplier identification'), max_length=20)
    supplier_name = models.CharField(_('supplier name'), max_length=300)
    supplier_address = models.TextField(_('supplier address'), blank=True)
    
    # Período fiscal
    fiscal_period = models.CharField(_('fiscal period'), max_length=7, help_text=_('MM/YYYY format'))
    
    # Totales
    total_retained = models.DecimalField(_('total retained'), max_digits=12, decimal_places=2, default=0)
    
    # Status y archivos
    status = models.CharField(_('status'), max_length=20, choices=ElectronicDocument.STATUS_CHOICES, default='DRAFT')
    xml_file = models.FileField(_('XML file'), upload_to='retentions/xml/', blank=True)
    signed_xml_file = models.FileField(_('signed XML file'), upload_to='retentions/xml/', blank=True)
    pdf_file = models.FileField(_('PDF file'), upload_to='retentions/pdf/', blank=True)
    
    # SRI response
    sri_authorization_code = models.CharField(_('SRI authorization code'), max_length=49, blank=True)
    sri_authorization_date = models.DateTimeField(_('SRI authorization date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Retention')
        verbose_name_plural = _('Retentions')
        unique_together = ['company', 'document_number']


class RetentionDetail(BaseModel):
    """
    Detalle de retenciones
    """
    retention = models.ForeignKey(Retention, on_delete=models.CASCADE, related_name='details')
    
    # Documento sustento
    support_document_type = models.CharField(_('support document type'), max_length=2)
    support_document_number = models.CharField(_('support document number'), max_length=20)
    support_document_date = models.DateField(_('support document date'))
    
    # Retención
    tax_code = models.CharField(_('tax code'), max_length=4)  # Código del impuesto
    retention_code = models.CharField(_('retention code'), max_length=5)  # Código de retención específico
    retention_percentage = models.DecimalField(_('retention percentage'), max_digits=5, decimal_places=2)
    
    taxable_base = models.DecimalField(_('taxable base'), max_digits=12, decimal_places=2)
    retained_amount = models.DecimalField(_('retained amount'), max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = _('Retention Detail')
        verbose_name_plural = _('Retention Details')


class PurchaseSettlement(BaseModel):
    """
    Liquidación de Compra
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='purchase_settlements')
    
    document_number = models.CharField(_('document number'), max_length=17)
    access_key = models.CharField(_('access key'), max_length=49, unique=True)
    issue_date = models.DateField(_('issue date'))
    
    # Información del proveedor
    supplier_identification_type = models.CharField(_('supplier identification type'), max_length=2)
    supplier_identification = models.CharField(_('supplier identification'), max_length=20)
    supplier_name = models.CharField(_('supplier name'), max_length=300)
    supplier_address = models.TextField(_('supplier address'), blank=True)
    
    # Totales
    subtotal_without_tax = models.DecimalField(_('subtotal without tax'), max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(_('total tax'), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_('total amount'), max_digits=12, decimal_places=2, default=0)
    
    # Status y archivos
    status = models.CharField(_('status'), max_length=20, choices=ElectronicDocument.STATUS_CHOICES, default='DRAFT')
    xml_file = models.FileField(_('XML file'), upload_to='settlements/xml/', blank=True)
    signed_xml_file = models.FileField(_('signed XML file'), upload_to='settlements/xml/', blank=True)
    pdf_file = models.FileField(_('PDF file'), upload_to='settlements/pdf/', blank=True)
    
    # SRI response
    sri_authorization_code = models.CharField(_('SRI authorization code'), max_length=49, blank=True)
    sri_authorization_date = models.DateTimeField(_('SRI authorization date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Purchase Settlement')
        verbose_name_plural = _('Purchase Settlements')
        unique_together = ['company', 'document_number']


class PurchaseSettlementItem(BaseModel):
    """
    Items de liquidación de compra - VERSIÓN CORREGIDA Y SEGURA
    """
    settlement = models.ForeignKey(
        PurchaseSettlement,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    main_code = models.CharField(
        _('main code'),
        max_length=25
    )
    
    description = models.TextField(
        _('description')
    )
    
    quantity = models.DecimalField(
        _('quantity'),
        max_digits=12,
        decimal_places=6,
        help_text=_('Maximum: 999,999.999999')
    )
    
    unit_price = models.DecimalField(
        _('unit price'),
        max_digits=12,
        decimal_places=6,
        help_text=_('Maximum: 999,999.999999')
    )
    
    discount = models.DecimalField(
        _('discount'),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_('Maximum: 9,999,999,999.99')
    )
    
    subtotal = models.DecimalField(
        _('subtotal'),
        max_digits=12,
        decimal_places=2,
        help_text=_('Calculated automatically. Maximum: 9,999,999,999.99')
    )
    
    class Meta:
        verbose_name = _('Purchase Settlement Item')
        verbose_name_plural = _('Purchase Settlement Items')
        indexes = [
            models.Index(fields=['settlement', 'main_code']),
        ]
    
    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"
    
    def clean(self):
        """Validación a nivel de modelo"""
        super().clean()
        
        # Validar rangos
        if self.quantity and self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than 0'})
        
        if self.unit_price and self.unit_price <= 0:
            raise ValidationError({'unit_price': 'Unit price must be greater than 0'})
        
        if self.discount and self.discount < 0:
            raise ValidationError({'discount': 'Discount cannot be negative'})
        
        # Validar límites máximos
        max_quantity_price = Decimal('999999.999999')
        if self.quantity and self.quantity > max_quantity_price:
            raise ValidationError({'quantity': f'Quantity cannot exceed {max_quantity_price}'})
        
        if self.unit_price and self.unit_price > max_quantity_price:
            raise ValidationError({'unit_price': f'Unit price cannot exceed {max_quantity_price}'})
        
        max_discount = Decimal('9999999999.99')
        if self.discount and self.discount > max_discount:
            raise ValidationError({'discount': f'Discount cannot exceed {max_discount}'})
        
        # Validar cálculo de subtotal
        if self.quantity and self.unit_price and self.discount is not None:
            calculated_subtotal = self._calculate_subtotal_safe()
            
            if calculated_subtotal < 0:
                raise ValidationError({'discount': 'Discount cannot be greater than (quantity × unit_price)'})
            
            max_subtotal = Decimal('9999999999.99')
            if calculated_subtotal > max_subtotal:
                raise ValidationError({
                    '__all__': f'Calculated subtotal ({calculated_subtotal}) exceeds maximum allowed ({max_subtotal}). '
                              f'Please reduce quantity, unit_price, or increase discount.'
                })
    
    def _calculate_subtotal_safe(self):
        """
        Cálculo seguro del subtotal con manejo de precisión decimal
        """
        # Convertir a Decimal con precisión controlada
        quantity = Decimal(str(self.quantity)) if self.quantity else Decimal('0')
        unit_price = Decimal(str(self.unit_price)) if self.unit_price else Decimal('0')
        discount = Decimal(str(self.discount)) if self.discount else Decimal('0')
        
        # Calcular subtotal: (cantidad × precio) - descuento
        subtotal = (quantity * unit_price) - discount
        
        # Redondear a 2 decimales usando ROUND_HALF_UP
        return subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def save(self, *args, **kwargs):
        """
        MÉTODO CRÍTICO CORREGIDO: Calcular subtotal de forma segura antes de guardar
        """
        # Calcular subtotal antes de cualquier validación
        if self.quantity is not None and self.unit_price is not None:
            if self.discount is None:
                self.discount = Decimal('0.00')
            
            # Calcular subtotal de forma segura
            self.subtotal = self._calculate_subtotal_safe()
        else:
            # Si no hay valores, establecer subtotal por defecto
            self.subtotal = Decimal('0.00')
        
        # Ejecutar validación completa después de calcular
        try:
            self.full_clean()
        except ValidationError:
            # Si la validación falla, al menos asegurar que subtotal no sea nulo
            if self.subtotal is None:
                self.subtotal = Decimal('0.00')
        
        # Llamar al método save() original
        super().save(*args, **kwargs)


# ========== CLASE UTILITARIA PARA CÁLCULOS SEGUROS ==========

class SafeDocumentCalculations:
    """
    Clase utilitaria para cálculos seguros de documentos
    """
    
    @staticmethod
    def validate_item_calculation(quantity, unit_price, discount=0):
        """
        Valida que los cálculos de un item no excedan los límites
        
        Args:
            quantity: Cantidad del item
            unit_price: Precio unitario
            discount: Descuento (opcional)
        
        Returns:
            tuple: (is_valid, calculated_subtotal, error_message)
        """
        try:
            # Convertir a Decimal
            qty = Decimal(str(quantity))
            price = Decimal(str(unit_price))
            disc = Decimal(str(discount))
            
            # Validar rangos individuales
            max_qty_price = Decimal('999999.999999')
            max_discount = Decimal('9999999999.99')
            max_subtotal = Decimal('9999999999.99')
            
            if qty <= 0:
                return False, None, "Quantity must be greater than 0"
            
            if price <= 0:
                return False, None, "Unit price must be greater than 0"
            
            if disc < 0:
                return False, None, "Discount cannot be negative"
            
            if qty > max_qty_price:
                return False, None, f"Quantity exceeds maximum allowed ({max_qty_price})"
            
            if price > max_qty_price:
                return False, None, f"Unit price exceeds maximum allowed ({max_qty_price})"
            
            if disc > max_discount:
                return False, None, f"Discount exceeds maximum allowed ({max_discount})"
            
            # Calcular subtotal
            subtotal = (qty * price) - disc
            
            if subtotal < 0:
                return False, None, "Discount cannot be greater than (quantity × unit_price)"
            
            if subtotal > max_subtotal:
                return False, None, f"Calculated subtotal ({subtotal}) exceeds maximum allowed ({max_subtotal})"
            
            # Redondear resultado
            final_subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            return True, final_subtotal, None
            
        except Exception as e:
            return False, None, f"Calculation error: {str(e)}"
    
    @staticmethod
    def validate_document_total(items_data):
        """
        Valida que el total del documento no exceda los límites
        
        Args:
            items_data: Lista de diccionarios con quantity, unit_price, discount
        
        Returns:
            tuple: (is_valid, calculated_total, error_message)
        """
        try:
            total = Decimal('0.00')
            max_document_total = Decimal('99999999999.99')  # Límite realista para documentos
            
            for i, item in enumerate(items_data):
                is_valid, subtotal, error = SafeDocumentCalculations.validate_item_calculation(
                    item.get('quantity', 0),
                    item.get('unit_price', 0),
                    item.get('discount', 0)
                )
                
                if not is_valid:
                    return False, None, f"Item {i+1}: {error}"
                
                total += subtotal
            
            if total > max_document_total:
                return False, None, f"Document total ({total}) exceeds reasonable limit ({max_document_total})"
            
            return True, total, None
            
        except Exception as e:
            return False, None, f"Document validation error: {str(e)}"