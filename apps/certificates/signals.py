# -*- coding: utf-8 -*-
"""
Signals para gestión automática de certificados en GlobalCertificateManager
apps/certificates/signals.py
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.certificates.models import DigitalCertificate
from apps.companies.models import Company

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DigitalCertificate)
def certificate_saved_handler(sender, instance, created, **kwargs):
    """
    Handler cuando se guarda un certificado digital
    """
    try:
        # Importar aquí para evitar circular imports
        from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
        
        cert_manager = get_certificate_manager()
        company_id = instance.company.id
        
        if created:
            logger.info(f"🆕 Nuevo certificado creado para empresa {company_id} ({instance.company.business_name})")
            
            # Intentar precargar automáticamente
            if instance.status == 'ACTIVE':
                logger.info(f"🔄 Intentando precargar certificado para empresa {company_id}")
                
                # Cargar en el gestor global
                cert_data = cert_manager._load_certificate(company_id)
                
                if cert_data:
                    logger.info(f"✅ Certificado precargado automáticamente para empresa {company_id}")
                else:
                    logger.warning(f"⚠️  No se pudo precargar certificado para empresa {company_id}")
        else:
            logger.info(f"📝 Certificado actualizado para empresa {company_id} ({instance.company.business_name})")
            
            # Si el certificado fue actualizado, recargar en cache
            if instance.status == 'ACTIVE':
                logger.info(f"🔄 Recargando certificado actualizado para empresa {company_id}")
                
                # Recargar certificado
                success = cert_manager.reload_certificate(company_id)
                
                if success:
                    logger.info(f"✅ Certificado recargado automáticamente para empresa {company_id}")
                else:
                    logger.warning(f"⚠️  No se pudo recargar certificado para empresa {company_id}")
            else:
                # Si el certificado fue desactivado, remover del cache
                if company_id in cert_manager._certificates_cache:
                    del cert_manager._certificates_cache[company_id]
                    logger.info(f"🗑️  Certificado removido del cache para empresa {company_id} (desactivado)")
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_saved_handler: {e}")


@receiver(post_delete, sender=DigitalCertificate)
def certificate_deleted_handler(sender, instance, **kwargs):
    """
    Handler cuando se elimina un certificado digital
    """
    try:
        from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
        
        cert_manager = get_certificate_manager()
        company_id = instance.company.id
        
        # Remover del cache si existe
        if company_id in cert_manager._certificates_cache:
            del cert_manager._certificates_cache[company_id]
            logger.info(f"🗑️  Certificado removido del cache para empresa {company_id} (eliminado)")
        
        logger.info(f"🗑️  Certificado eliminado para empresa {company_id} ({instance.company.business_name})")
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_deleted_handler: {e}")


@receiver(pre_save, sender=DigitalCertificate)
def certificate_pre_save_handler(sender, instance, **kwargs):
    """
    Handler antes de guardar un certificado (para detectar cambios)
    """
    try:
        # Si es una actualización, verificar cambios importantes
        if instance.pk:
            try:
                old_instance = DigitalCertificate.objects.get(pk=instance.pk)
                
                # Detectar cambios críticos
                critical_changes = []
                
                if old_instance.status != instance.status:
                    critical_changes.append(f"Status: {old_instance.status} → {instance.status}")
                
                if old_instance.certificate_file != instance.certificate_file:
                    critical_changes.append("Archivo de certificado cambiado")
                
                if old_instance.password_hash != instance.password_hash:
                    critical_changes.append("Password cambiado")
                
                if critical_changes:
                    logger.info(f"🔄 Cambios críticos detectados en certificado empresa {instance.company.id}: {', '.join(critical_changes)}")
                    
                    # Marcar para recarga después del save
                    instance._needs_reload = True
                
            except DigitalCertificate.DoesNotExist:
                # Es un nuevo certificado
                pass
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_pre_save_handler: {e}")


@receiver(post_save, sender=Company)
def company_saved_handler(sender, instance, created, **kwargs):
    """
    Handler cuando se guarda una empresa
    """
    try:
        if created:
            logger.info(f"🏢 Nueva empresa creada: {instance.business_name} (ID: {instance.id})")
        else:
            # Si la empresa fue desactivada, limpiar certificados del cache
            if not instance.is_active:
                from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
                
                cert_manager = get_certificate_manager()
                
                if instance.id in cert_manager._certificates_cache:
                    del cert_manager._certificates_cache[instance.id]
                    logger.info(f"🗑️  Certificado removido del cache para empresa {instance.id} (empresa desactivada)")
        
    except Exception as e:
        logger.error(f"❌ Error en company_saved_handler: {e}")


# ========== FUNCIONES AUXILIARES ==========

def auto_preload_company_certificate(company_id):
    """
    Función auxiliar para precargar automáticamente un certificado
    """
    try:
        from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
        
        cert_manager = get_certificate_manager()
        cert_data = cert_manager.get_certificate(company_id)
        
        if cert_data:
            logger.info(f"✅ Certificado precargado automáticamente para empresa {company_id}")
            return True
        else:
            logger.warning(f"⚠️  No se pudo precargar certificado para empresa {company_id}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error en auto_preload_company_certificate: {e}")
        return False


def validate_certificate_after_save(instance):
    """
    Valida el certificado después de guardarlo
    """
    try:
        from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
        
        cert_manager = get_certificate_manager()
        is_valid, message = cert_manager.validate_certificate(instance.company.id)
        
        if not is_valid:
            logger.warning(f"⚠️  Certificado inválido para empresa {instance.company.id}: {message}")
        else:
            logger.info(f"✅ Certificado válido para empresa {instance.company.id}")
        
        return is_valid, message
        
    except Exception as e:
        logger.error(f"❌ Error validando certificado: {e}")
        return False, str(e)


def cleanup_expired_certificates():
    """
    Función para limpiar certificados expirados (para usar en tareas periódicas)
    """
    try:
        from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
        
        cert_manager = get_certificate_manager()
        cert_manager.cleanup_expired_certificates()
        
        logger.info("🧹 Limpieza de certificados expirados completada")
        
    except Exception as e:
        logger.error(f"❌ Error en cleanup_expired_certificates: {e}")


# ========== SIGNAL PARA STARTUP DE LA APLICACIÓN ==========

from django.apps import apps
from django.core.management import call_command


def preload_certificates_on_startup():
    """
    Precarga certificados cuando la aplicación inicia
    Solo se ejecuta si hay certificados configurados
    """
    try:
        # Verificar si hay certificados activos
        if not apps.ready:
            return
        
        active_certificates = DigitalCertificate.objects.filter(
            status='ACTIVE',
            company__is_active=True
        ).count()
        
        if active_certificates > 0:
            logger.info(f"🚀 Iniciando precarga automática de {active_certificates} certificados...")
            
            from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
            cert_manager = get_certificate_manager()
            
            # Precargar automáticamente
            result = cert_manager.preload_certificates()
            
            if 'error' not in result:
                logger.info(f"✅ Precarga automática completada: {result['loaded']} cargados, {result['failed']} fallidos")
            else:
                logger.error(f"❌ Error en precarga automática: {result['error']}")
        else:
            logger.info("📋 No hay certificados activos para precargar")
        
    except Exception as e:
        logger.error(f"❌ Error en precarga automática: {e}")


# ========== CONFIGURACIÓN DE LOGGING ESPECÍFICO ==========

import sys

def setup_certificate_logging():
    """
    Configura logging específico para certificados
    """
    certificate_logger = logging.getLogger('apps.certificates')
    certificate_logger.setLevel(logging.INFO)
    
    # Handler para consola con formato específico
    if not certificate_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s [CERTIFICATES] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        certificate_logger.addHandler(handler)


# Configurar logging al importar
setup_certificate_logging()