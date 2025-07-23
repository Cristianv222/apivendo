# -*- coding: utf-8 -*-
"""
Señales para sistema de planes y facturación
apps/billing/signals.py
"""

import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


@receiver(post_save, sender='companies.Company')
def create_billing_profile_for_new_company(sender, instance, created, **kwargs):
    """
    Crear automáticamente perfil de facturación para empresas nuevas
    """
    if created:
        from .models import CompanyBillingProfile
        
        try:
            billing_profile, profile_created = CompanyBillingProfile.objects.get_or_create(
                company=instance,
                defaults={
                    'available_invoices': 0,  # Empiezan sin facturas
                    'total_invoices_purchased': 0,
                    'total_invoices_consumed': 0,
                    'total_spent': Decimal('0.00'),
                    'low_balance_threshold': 5,  # Alertar cuando queden 5 facturas
                }
            )
            
            if profile_created:
                logger.info(f"✅ Billing profile created for new company: {instance.business_name or instance.trade_name}")
            
        except Exception as e:
            logger.error(f"❌ Error creating billing profile for company {instance.id}: {e}")


@receiver(post_save, sender='billing.PlanPurchase')
def handle_plan_purchase_approval(sender, instance, created, **kwargs):
    """
    Manejar aprobación automática de compras de planes
    """
    if not created and instance.payment_status == 'approved':
        # Solo procesar si cambió a aprobado
        if 'payment_status' in kwargs.get('update_fields', []) or hasattr(instance, '_state') and instance._state.adding:
            try:
                logger.info(f"✅ Plan purchase approved: {instance.company.business_name} - {instance.plan_name}")
                
                # Nota: La lógica de aprobación ya está en el método approve_purchase del modelo
                # Esta señal es para futuras extensiones como notificaciones
                
            except Exception as e:
                logger.error(f"❌ Error processing plan purchase approval: {e}")


@receiver(post_save, sender='billing.InvoiceConsumption')
def handle_invoice_consumption(sender, instance, created, **kwargs):
    """
    Manejar consumo de facturas para alertas y notificaciones
    """
    if created:
        try:
            billing_profile = instance.company.billing_profile
            
            # Log del consumo
            logger.info(
                f"📊 Invoice consumed: {instance.company.business_name} - "
                f"Document: {instance.invoice_id} - "
                f"Remaining: {billing_profile.available_invoices}"
            )
            
            # Alertas de saldo bajo
            if billing_profile.is_low_balance:
                logger.warning(
                    f"⚠️ Low balance alert: {instance.company.business_name} - "
                    f"Only {billing_profile.available_invoices} invoices remaining"
                )
                
                # Aquí se pueden agregar notificaciones por email, etc.
                # send_low_balance_notification(billing_profile)
            
            # Alerta de saldo agotado
            if billing_profile.available_invoices == 0:
                logger.warning(
                    f"🚨 Balance depleted: {instance.company.business_name} - "
                    f"No invoices remaining. Company needs to purchase a plan."
                )
                
                # Aquí se pueden agregar notificaciones urgentes
                # send_balance_depleted_notification(billing_profile)
                
        except Exception as e:
            logger.error(f"❌ Error handling invoice consumption: {e}")


@receiver(pre_delete, sender='billing.CompanyBillingProfile')
def prevent_billing_profile_deletion(sender, instance, **kwargs):
    """
    Prevenir eliminación accidental de perfiles de facturación
    """
    logger.warning(
        f"🚨 ATTEMPT TO DELETE BILLING PROFILE: {instance.company.business_name} - "
        f"Available invoices: {instance.available_invoices} - "
        f"Total spent: ${instance.total_spent}"
    )
    
    # Opcional: Cancelar la eliminación en casos críticos
    if instance.available_invoices > 0 or instance.total_spent > 0:
        logger.error(
            f"❌ BILLING PROFILE DELETION BLOCKED: Profile has active data - "
            f"Company: {instance.company.business_name}"
        )
        # Uncomment to actually prevent deletion:
        # raise Exception("Cannot delete billing profile with active invoices or payment history")


# Función auxiliar para futuras notificaciones
def send_low_balance_notification(billing_profile):
    """
    Enviar notificación de saldo bajo (para implementar)
    """
    # TODO: Implementar notificaciones por email
    # TODO: Implementar notificaciones en dashboard
    # TODO: Implementar notificaciones por webhook
    pass


def send_balance_depleted_notification(billing_profile):
    """
    Enviar notificación de saldo agotado (para implementar)
    """
    # TODO: Implementar notificaciones urgentes
    pass


# Log de inicialización
logger.info("📡 Billing signals loaded successfully")