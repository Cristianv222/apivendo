# -*- coding: utf-8 -*-
"""
Modelos para sistema de planes y facturación
apps/billing/models.py
"""

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Plan(models.Model):
    """
    Planes de facturación disponibles
    """
    name = models.CharField('Nombre del Plan', max_length=100)
    description = models.TextField('Descripción', blank=True)
    invoice_limit = models.PositiveIntegerField('Límite de Facturas', validators=[MinValueValidator(1)])
    price = models.DecimalField('Precio (USD)', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Configuración
    is_active = models.BooleanField('Activo', default=True)
    is_featured = models.BooleanField('Plan Destacado', default=False)
    sort_order = models.PositiveIntegerField('Orden', default=0, help_text='Para ordenar los planes en la interfaz')
    
    # Metadatos
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)
    
    class Meta:
        verbose_name = 'Plan de Facturación'
        verbose_name_plural = 'Planes de Facturación'
        ordering = ['sort_order', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.invoice_limit} facturas por ${self.price}"
    
    @property
    def price_per_invoice(self):
        """Precio por factura"""
        return self.price / self.invoice_limit
    
    def get_badge_color(self):
        """Color del badge según el precio"""
        if self.price <= 10:
            return 'success'  # Verde para básicos
        elif self.price <= 50:
            return 'primary'  # Azul para intermedios
        else:
            return 'warning'  # Amarillo para premium


class CompanyBillingProfile(models.Model):
    """
    Perfil de facturación de cada empresa
    """
    company = models.OneToOneField('companies.Company', on_delete=models.CASCADE, related_name='billing_profile')
    
    # Créditos disponibles
    available_invoices = models.PositiveIntegerField('Facturas Disponibles', default=0)
    total_invoices_purchased = models.PositiveIntegerField('Total Facturas Compradas', default=0)
    total_invoices_consumed = models.PositiveIntegerField('Total Facturas Consumidas', default=0)
    
    # Estadísticas de pago
    total_spent = models.DecimalField('Total Gastado (USD)', max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_purchase_date = models.DateTimeField('Última Compra', null=True, blank=True)
    
    # Configuración
    auto_renewal_enabled = models.BooleanField('Renovación Automática', default=False, help_text='Para futuras funcionalidades')
    low_balance_threshold = models.PositiveIntegerField('Umbral de Alerta', default=5, help_text='Notificar cuando queden X facturas')
    
    # Metadatos
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Facturación'
        verbose_name_plural = 'Perfiles de Facturación'
    
    def __str__(self):
        return f"{self.company.business_name} - {self.available_invoices} facturas disponibles"
    
    def consume_invoice(self):
        """Consumir una factura"""
        if self.available_invoices > 0:
            self.available_invoices -= 1
            self.total_invoices_consumed += 1
            self.save(update_fields=['available_invoices', 'total_invoices_consumed', 'updated_at'])
            return True
        return False
    
    def add_invoices(self, count, cost=None):
        """Agregar facturas al perfil"""
        self.available_invoices += count
        self.total_invoices_purchased += count
        if cost:
            self.total_spent += cost
        self.save(update_fields=['available_invoices', 'total_invoices_purchased', 'total_spent', 'updated_at'])
    
    @property
    def is_low_balance(self):
        """Verificar si el saldo es bajo"""
        return self.available_invoices <= self.low_balance_threshold
    
    @property
    def usage_percentage(self):
        """Porcentaje de uso de facturas compradas"""
        if self.total_invoices_purchased == 0:
            return 0
        return (self.total_invoices_consumed / self.total_invoices_purchased) * 100


class PlanPurchase(models.Model):
    """
    Compras de planes por parte de las empresas
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pendiente de Validación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('expired', 'Expirado'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Transferencia Bancaria'),
        ('deposit', 'Depósito Bancario'),
        ('other', 'Otro'),
    ]
    
    # Identificación
    purchase_id = models.UUIDField('ID de Compra', default=uuid.uuid4, editable=False, unique=True)
    
    # Relaciones
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='plan_purchases')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='purchases')
    
    # Datos del plan al momento de la compra (para histórico)
    plan_name = models.CharField('Nombre del Plan', max_length=100)
    plan_invoice_limit = models.PositiveIntegerField('Facturas del Plan')
    plan_price = models.DecimalField('Precio del Plan', max_digits=10, decimal_places=2)
    
    # Estado del pago
    payment_status = models.CharField('Estado', max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField('Método de Pago', max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    
    # Información del pago
    payer_name = models.CharField('Nombre del Pagador', max_length=200)
    payer_document = models.CharField('Documento del Pagador', max_length=50, help_text='Cédula, RUC, etc.')
    payment_amount = models.DecimalField('Monto Pagado', max_digits=10, decimal_places=2)
    payment_reference = models.CharField('Referencia/Número de Transacción', max_length=100, blank=True)
    payment_date = models.DateField('Fecha de Pago')
    bank_name = models.CharField('Banco', max_length=100, blank=True)
    
    # Comprobante
    payment_receipt = models.FileField('Comprobante de Pago', upload_to='billing/receipts/%Y/%m/', help_text='JPG, PNG o PDF')
    
    # Notas y observaciones
    customer_notes = models.TextField('Notas del Cliente', blank=True, help_text='Observaciones adicionales del cliente')
    admin_notes = models.TextField('Notas del Administrador', blank=True, help_text='Observaciones internas')
    
    # Procesamiento
    processed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_purchases')
    processed_at = models.DateTimeField('Procesado el', null=True, blank=True)
    
    # Metadatos
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)
    
    class Meta:
        verbose_name = 'Compra de Plan'
        verbose_name_plural = 'Compras de Planes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.business_name} - {self.plan_name} - {self.get_payment_status_display()}"
    
    def approve_purchase(self, admin_user):
        """Aprobar la compra y activar el plan"""
        if self.payment_status == 'pending':
            # Crear o obtener perfil de facturación
            billing_profile, created = CompanyBillingProfile.objects.get_or_create(
                company=self.company,
                defaults={
                    'available_invoices': 0,
                    'total_invoices_purchased': 0,
                    'total_invoices_consumed': 0,
                    'total_spent': Decimal('0.00'),
                }
            )
            
            # Agregar facturas al perfil
            billing_profile.add_invoices(self.plan_invoice_limit, self.plan_price)
            billing_profile.last_purchase_date = self.created_at
            billing_profile.save(update_fields=['last_purchase_date'])
            
            # Actualizar el estado de la compra
            self.payment_status = 'approved'
            self.processed_by = admin_user
            self.processed_at = timezone.now()
            self.save(update_fields=['payment_status', 'processed_by', 'processed_at', 'updated_at'])
            
            return True
        return False
    
    def reject_purchase(self, admin_user, reason=None):
        """Rechazar la compra"""
        if self.payment_status == 'pending':
            self.payment_status = 'rejected'
            self.processed_by = admin_user
            self.processed_at = timezone.now()
            if reason:
                self.admin_notes = reason
            self.save(update_fields=['payment_status', 'processed_by', 'processed_at', 'admin_notes', 'updated_at'])
            return True
        return False
    
    @property
    def is_pending(self):
        return self.payment_status == 'pending'
    
    @property
    def is_approved(self):
        return self.payment_status == 'approved'
    
    def get_status_badge_color(self):
        """Color del badge según el estado"""
        status_colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'expired': 'secondary',
        }
        return status_colors.get(self.payment_status, 'secondary')


class InvoiceConsumption(models.Model):
    """
    Registro de consumo de facturas para auditoría
    """
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='invoice_consumptions')
    
    # Detalles del consumo
    invoice_id = models.CharField('ID de Factura', max_length=100, help_text='ID de la factura emitida')
    invoice_type = models.CharField('Tipo de Documento', max_length=50, default='invoice')
    consumed_at = models.DateTimeField('Consumido el', auto_now_add=True)
    
    # Estado antes y después
    balance_before = models.PositiveIntegerField('Saldo Anterior')
    balance_after = models.PositiveIntegerField('Saldo Posterior')
    
    # Metadatos para auditoría
    user_agent = models.TextField('User Agent', blank=True)
    ip_address = models.GenericIPAddressField('Dirección IP', null=True, blank=True)
    api_endpoint = models.CharField('Endpoint API', max_length=200, blank=True)
    
    class Meta:
        verbose_name = 'Consumo de Factura'
        verbose_name_plural = 'Consumos de Facturas'
        ordering = ['-consumed_at']
    
    def __str__(self):
        return f"{self.company.business_name} - Factura {self.invoice_id} - {self.consumed_at.strftime('%d/%m/%Y %H:%M')}"


# Señales para crear automáticamente perfiles de facturación
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

@receiver(post_save, sender='companies.Company')
def create_billing_profile(sender, instance, created, **kwargs):
    """Crear perfil de facturación automáticamente para nuevas empresas"""
    if created:
        CompanyBillingProfile.objects.get_or_create(
            company=instance,
            defaults={
                'available_invoices': 0,  # Empiezan sin facturas
                'total_invoices_purchased': 0,
                'total_invoices_consumed': 0,
                'total_spent': Decimal('0.00'),
            }
        )