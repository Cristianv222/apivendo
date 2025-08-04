# -*- coding: utf-8 -*-
"""
Signals para gestión automática de certificados con storage dual
apps/certificates/signals.py - VERSIÓN MEJORADA
"""

import logging
import os
import shutil
from pathlib import Path
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.files.storage import default_storage
from apps.certificates.models import DigitalCertificate
from apps.companies.models import Company

logger = logging.getLogger(__name__)


# ========== CONFIGURACIÓN DE RUTAS ==========

def get_storage_certificate_path(company_ruc, filename):
    """
    Genera la ruta en storage/certificates/ para un certificado
    
    Args:
        company_ruc: RUC de la empresa
        filename: nombre del archivo
        
    Returns:
        Path: ruta completa en storage/certificates/
    """
    storage_base = Path(settings.BASE_DIR) / 'storage' / 'certificates'
    company_dir = storage_base / company_ruc
    return company_dir / filename


def ensure_storage_directory(company_ruc):
    """
    Asegura que el directorio de storage existe con permisos correctos
    
    Args:
        company_ruc: RUC de la empresa
        
    Returns:
        Path: ruta del directorio creado
    """
    storage_base = Path(settings.BASE_DIR) / 'storage' / 'certificates'
    company_dir = storage_base / company_ruc
    
    # Crear directorio si no existe
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Configurar permisos seguros (solo propietario)
    os.chmod(company_dir, 0o700)
    
    logger.info(f"📁 Directorio de storage asegurado: {company_dir}")
    return company_dir


# ========== SIGNALS PRINCIPALES ==========

@receiver(post_save, sender=DigitalCertificate)
def certificate_saved_handler(sender, instance, created, **kwargs):
    """
    Handler cuando se guarda un certificado digital
    Guarda automáticamente en storage/certificates/ además del media
    """
    try:
        # Solo procesar si hay archivo de certificado
        if not instance.certificate_file:
            logger.warning(f"⚠️ Certificado {instance.id} guardado sin archivo")
            return
        
        company_ruc = instance.company.ruc
        
        # Asegurar directorio de storage
        storage_dir = ensure_storage_directory(company_ruc)
        
        # Obtener nombre del archivo original
        original_filename = os.path.basename(instance.certificate_file.name)
        storage_file_path = storage_dir / original_filename
        
        # Copiar archivo a storage si no existe o es diferente
        should_copy = False
        
        if not storage_file_path.exists():
            should_copy = True
            logger.info(f"📄 Archivo no existe en storage, copiando: {original_filename}")
        else:
            # Verificar si el archivo ha cambiado comparando tamaños
            try:
                media_size = instance.certificate_file.size
                storage_size = storage_file_path.stat().st_size
                
                if media_size != storage_size:
                    should_copy = True
                    logger.info(f"📄 Archivo modificado (tamaño diferente), actualizando storage: {original_filename}")
            except Exception as e:
                should_copy = True
                logger.warning(f"⚠️ Error comparando archivos, forzando copia: {e}")
        
        # Realizar copia si es necesario
        if should_copy:
            try:
                # Obtener ruta del archivo en media
                media_file_path = None
                
                if hasattr(instance.certificate_file, 'path') and os.path.exists(instance.certificate_file.path):
                    # Archivo ya guardado en media
                    media_file_path = instance.certificate_file.path
                elif hasattr(instance.certificate_file, 'file'):
                    # Archivo temporal, leer contenido
                    instance.certificate_file.seek(0)
                    file_content = instance.certificate_file.read()
                    instance.certificate_file.seek(0)
                    
                    # Escribir directamente a storage
                    with open(storage_file_path, 'wb') as storage_file:
                        storage_file.write(file_content)
                    
                    # Configurar permisos seguros
                    os.chmod(storage_file_path, 0o600)
                    
                    logger.info(f"✅ Certificado copiado a storage desde memoria: {storage_file_path}")
                    media_file_path = None  # Ya procesado
                
                # Si tenemos ruta de media, copiar archivo
                if media_file_path:
                    shutil.copy2(media_file_path, storage_file_path)
                    os.chmod(storage_file_path, 0o600)
                    logger.info(f"✅ Certificado copiado a storage: {media_file_path} → {storage_file_path}")
                
                # Actualizar el campo storage_path en el modelo
                if hasattr(instance, 'storage_path'):
                    relative_path = f"certificates/{company_ruc}/{original_filename}"
                    instance.storage_path = relative_path
                    # Actualizar sin trigger signals para evitar recursión
                    DigitalCertificate.objects.filter(id=instance.id).update(storage_path=relative_path)
                    logger.info(f"📝 storage_path actualizado: {relative_path}")
                
            except Exception as e:
                logger.error(f"❌ Error copiando certificado a storage: {e}")
                # No fallar el guardado por error de copia
        
        # Manejar integración con GlobalCertificateManager
        try:
            from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
            
            cert_manager = get_certificate_manager()
            company_id = instance.company.id
            
            if created:
                logger.info(f"🆕 Nuevo certificado creado para empresa {company_id} ({instance.company.business_name})")
                
                # Intentar precargar automáticamente si está activo
                if instance.status == 'ACTIVE':
                    logger.info(f"🔄 Intentando precargar certificado para empresa {company_id}")
                    cert_data = cert_manager._load_certificate(company_id)
                    
                    if cert_data:
                        logger.info(f"✅ Certificado precargado automáticamente para empresa {company_id}")
                    else:
                        logger.warning(f"⚠️ No se pudo precargar certificado para empresa {company_id}")
            else:
                logger.info(f"📝 Certificado actualizado para empresa {company_id} ({instance.company.business_name})")
                
                # Si el certificado fue actualizado, recargar en cache
                if instance.status == 'ACTIVE':
                    logger.info(f"🔄 Recargando certificado actualizado para empresa {company_id}")
                    success = cert_manager.reload_certificate(company_id)
                    
                    if success:
                        logger.info(f"✅ Certificado recargado automáticamente para empresa {company_id}")
                    else:
                        logger.warning(f"⚠️ No se pudo recargar certificado para empresa {company_id}")
                else:
                    # Si el certificado fue desactivado, remover del cache
                    if company_id in cert_manager._certificates_cache:
                        del cert_manager._certificates_cache[company_id]
                        logger.info(f"🗑️ Certificado removido del cache para empresa {company_id} (desactivado)")
        
        except ImportError:
            logger.warning("⚠️ GlobalCertificateManager no disponible")
        except Exception as e:
            logger.error(f"❌ Error en integración con GlobalCertificateManager: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_saved_handler: {e}")


@receiver(pre_delete, sender=DigitalCertificate)
def certificate_pre_delete_handler(sender, instance, **kwargs):
    """
    Handler antes de eliminar un certificado
    Guarda información para limpiar archivos después
    """
    try:
        # Guardar información para cleanup posterior
        if hasattr(instance, 'certificate_file') and instance.certificate_file:
            # Guardar rutas para limpieza
            instance._cleanup_media_path = getattr(instance.certificate_file, 'path', None)
            instance._cleanup_storage_path = None
            
            if instance.company and instance.company.ruc:
                company_ruc = instance.company.ruc
                filename = os.path.basename(instance.certificate_file.name)
                storage_path = get_storage_certificate_path(company_ruc, filename)
                instance._cleanup_storage_path = str(storage_path)
        
        logger.info(f"📋 Preparando eliminación de certificado para empresa {instance.company.id}")
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_pre_delete_handler: {e}")


@receiver(post_delete, sender=DigitalCertificate)
def certificate_deleted_handler(sender, instance, **kwargs):
    """
    Handler cuando se elimina un certificado digital
    Limpia archivos tanto de media como de storage
    """
    try:
        # Limpiar del cache del GlobalCertificateManager
        try:
            from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
            
            cert_manager = get_certificate_manager()
            company_id = instance.company.id
            
            # Remover del cache si existe
            if company_id in cert_manager._certificates_cache:
                del cert_manager._certificates_cache[company_id]
                logger.info(f"🗑️ Certificado removido del cache para empresa {company_id} (eliminado)")
        
        except ImportError:
            logger.warning("⚠️ GlobalCertificateManager no disponible para cleanup")
        except Exception as e:
            logger.error(f"❌ Error limpiando cache: {e}")
        
        # Limpiar archivos del storage
        cleanup_paths = []
        
        # Agregar ruta de storage si se guardó
        if hasattr(instance, '_cleanup_storage_path') and instance._cleanup_storage_path:
            cleanup_paths.append(('storage', instance._cleanup_storage_path))
        
        # Agregar ruta de media si existe
        if hasattr(instance, '_cleanup_media_path') and instance._cleanup_media_path:
            cleanup_paths.append(('media', instance._cleanup_media_path))
        
        # Limpiar archivos
        for location, file_path in cleanup_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"🗑️ Archivo eliminado de {location}: {file_path}")
                else:
                    logger.info(f"📄 Archivo no encontrado en {location}: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Error eliminando archivo de {location}: {e}")
        
        # Intentar limpiar directorio de la empresa si está vacío
        if instance.company and instance.company.ruc:
            try:
                company_storage_dir = Path(settings.BASE_DIR) / 'storage' / 'certificates' / instance.company.ruc
                if company_storage_dir.exists() and not any(company_storage_dir.iterdir()):
                    company_storage_dir.rmdir()
                    logger.info(f"🗑️ Directorio de empresa eliminado (vacío): {company_storage_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Error eliminando directorio de empresa: {e}")
        
        logger.info(f"🗑️ Certificado eliminado completamente para empresa {instance.company.id} ({instance.company.business_name})")
        
    except Exception as e:
        logger.error(f"❌ Error en certificate_deleted_handler: {e}")


# ========== SIGNALS PARA EMPRESAS ==========

@receiver(post_save, sender=Company)
def company_saved_handler(sender, instance, created, **kwargs):
    """
    Handler cuando se guarda una empresa
    """
    try:
        if created:
            logger.info(f"🏢 Nueva empresa creada: {instance.business_name} (ID: {instance.id})")
            
            # Crear directorio de storage para la nueva empresa
            if instance.ruc:
                ensure_storage_directory(instance.ruc)
        else:
            # Si la empresa fue desactivada, limpiar certificados del cache
            if not instance.is_active:
                try:
                    from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
                    
                    cert_manager = get_certificate_manager()
                    
                    if instance.id in cert_manager._certificates_cache:
                        del cert_manager._certificates_cache[instance.id]
                        logger.info(f"🗑️ Certificado removido del cache para empresa {instance.id} (empresa desactivada)")
                
                except ImportError:
                    pass
                except Exception as e:
                    logger.error(f"❌ Error limpiando cache de empresa: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error en company_saved_handler: {e}")


# ========== FUNCIONES AUXILIARES ==========

def copy_certificate_to_storage(certificate_instance):
    """
    Función auxiliar para copiar manualmente un certificado a storage
    
    Args:
        certificate_instance: instancia de DigitalCertificate
        
    Returns:
        bool: True si se copió exitosamente
    """
    try:
        if not certificate_instance.certificate_file or not certificate_instance.company:
            return False
        
        company_ruc = certificate_instance.company.ruc
        storage_dir = ensure_storage_directory(company_ruc)
        
        filename = os.path.basename(certificate_instance.certificate_file.name)
        storage_file_path = storage_dir / filename
        
        # Copiar archivo
        if hasattr(certificate_instance.certificate_file, 'path'):
            media_path = certificate_instance.certificate_file.path
            if os.path.exists(media_path):
                shutil.copy2(media_path, storage_file_path)
                os.chmod(storage_file_path, 0o600)
                
                logger.info(f"✅ Certificado copiado manualmente a storage: {storage_file_path}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error copiando certificado manualmente: {e}")
        return False


def verify_storage_integrity():
    """
    Función para verificar integridad entre media y storage
    
    Returns:
        dict: reporte de integridad
    """
    report = {
        'total_certificates': 0,
        'in_media_only': [],
        'in_storage_only': [],
        'in_both': [],
        'missing_completely': []
    }
    
    try:
        certificates = DigitalCertificate.objects.filter(
            certificate_file__isnull=False,
            company__isnull=False
        )
        
        report['total_certificates'] = certificates.count()
        
        for cert in certificates:
            company_ruc = cert.company.ruc
            filename = os.path.basename(cert.certificate_file.name)
            
            # Verificar media
            media_exists = False
            if hasattr(cert.certificate_file, 'path'):
                media_exists = os.path.exists(cert.certificate_file.path)
            
            # Verificar storage
            storage_path = get_storage_certificate_path(company_ruc, filename)
            storage_exists = storage_path.exists()
            
            # Clasificar
            cert_info = {
                'id': cert.id,
                'company': cert.company.business_name,
                'filename': filename,
                'media_path': getattr(cert.certificate_file, 'path', 'N/A'),
                'storage_path': str(storage_path)
            }
            
            if media_exists and storage_exists:
                report['in_both'].append(cert_info)
            elif media_exists and not storage_exists:
                report['in_media_only'].append(cert_info)
            elif not media_exists and storage_exists:
                report['in_storage_only'].append(cert_info)
            else:
                report['missing_completely'].append(cert_info)
        
        logger.info(f"🔍 Verificación de integridad completada: {report['total_certificates']} certificados")
        
    except Exception as e:
        logger.error(f"❌ Error en verificación de integridad: {e}")
        report['error'] = str(e)
    
    return report


def sync_all_certificates_to_storage():
    """
    Función para sincronizar todos los certificados existentes a storage
    
    Returns:
        dict: reporte de sincronización
    """
    report = {
        'total_processed': 0,
        'successful_copies': 0,
        'failed_copies': 0,
        'already_in_storage': 0,
        'errors': []
    }
    
    try:
        certificates = DigitalCertificate.objects.filter(
            certificate_file__isnull=False,
            company__isnull=False
        )
        
        for cert in certificates:
            report['total_processed'] += 1
            
            try:
                company_ruc = cert.company.ruc
                filename = os.path.basename(cert.certificate_file.name)
                storage_path = get_storage_certificate_path(company_ruc, filename)
                
                if storage_path.exists():
                    report['already_in_storage'] += 1
                    continue
                
                success = copy_certificate_to_storage(cert)
                
                if success:
                    report['successful_copies'] += 1
                else:
                    report['failed_copies'] += 1
                    report['errors'].append(f"Certificado {cert.id}: No se pudo copiar")
                
            except Exception as e:
                report['failed_copies'] += 1
                report['errors'].append(f"Certificado {cert.id}: {str(e)}")
        
        logger.info(f"🔄 Sincronización completada: {report['successful_copies']} copiados, {report['failed_copies']} fallidos")
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización masiva: {e}")
        report['error'] = str(e)
    
    return report


# ========== COMANDO DE MANAGEMENT ==========

def create_management_command():
    """
    Crear archivo de comando de management para sincronización
    """
    command_content = '''# -*- coding: utf-8 -*-
"""
Comando para sincronizar certificados a storage
"""

from django.core.management.base import BaseCommand
from apps.certificates.signals import sync_all_certificates_to_storage, verify_storage_integrity


class Command(BaseCommand):
    help = 'Sincroniza certificados existentes a storage/certificates/'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Solo verificar integridad sin copiar archivos',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar copia incluso si el archivo ya existe',
        )
    
    def handle(self, *args, **options):
        if options['verify_only']:
            self.stdout.write("🔍 Verificando integridad de certificados...")
            report = verify_storage_integrity()
            
            self.stdout.write(f"📊 Total de certificados: {report['total_certificates']}")
            self.stdout.write(f"✅ En ambos locations: {len(report['in_both'])}")
            self.stdout.write(f"📄 Solo en media: {len(report['in_media_only'])}")
            self.stdout.write(f"💾 Solo en storage: {len(report['in_storage_only'])}")
            self.stdout.write(f"❌ Faltantes completamente: {len(report['missing_completely'])}")
        else:
            self.stdout.write("🔄 Sincronizando certificados a storage...")
            report = sync_all_certificates_to_storage()
            
            self.stdout.write(f"📊 Total procesados: {report['total_processed']}")
            self.stdout.write(f"✅ Copiados exitosamente: {report['successful_copies']}")
            self.stdout.write(f"❌ Fallos: {report['failed_copies']}")
            self.stdout.write(f"💾 Ya en storage: {report['already_in_storage']}")
            
            if report['errors']:
                self.stdout.write("🚨 Errores encontrados:")
                for error in report['errors']:
                    self.stdout.write(f"  - {error}")
        
        self.stdout.write(self.style.SUCCESS("✅ Operación completada"))
'''
    
    # Crear directorio de comandos si no existe
    command_dir = Path(settings.BASE_DIR) / 'apps' / 'certificates' / 'management' / 'commands'
    command_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear archivo __init__.py
    (command_dir / '__init__.py').touch(exist_ok=True)
    (command_dir.parent / '__init__.py').touch(exist_ok=True)
    
    # Escribir comando
    command_file = command_dir / 'sync_certificates.py'
    command_file.write_text(command_content, encoding='utf-8')
    
    logger.info(f"📝 Comando de management creado: {command_file}")


# ========== CONFIGURACIÓN DE LOGGING ESPECÍFICO ==========

def setup_certificate_logging():
    """
    Configura logging específico para certificados con storage
    """
    certificate_logger = logging.getLogger('apps.certificates')
    certificate_logger.setLevel(logging.INFO)
    
    # Handler para archivo específico de certificados
    if not certificate_logger.handlers:
        import sys
        from logging import StreamHandler, FileHandler, Formatter
        
        # Handler para consola
        console_handler = StreamHandler(sys.stdout)
        console_formatter = Formatter(
            '%(asctime)s [CERTIFICATES] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        certificate_logger.addHandler(console_handler)
        
        # Handler para archivo
        try:
            log_file = Path(settings.BASE_DIR) / 'logs' / 'certificates.log'
            log_file.parent.mkdir(exist_ok=True)
            
            file_handler = FileHandler(log_file)
            file_formatter = Formatter(
                '%(asctime)s [CERTIFICATES] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            certificate_logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo configurar logging a archivo: {e}")


# Configurar logging al importar
setup_certificate_logging()

# Crear comando de management al importar (solo en desarrollo)
if settings.DEBUG:
    try:
        create_management_command()
    except Exception as e:
        logger.warning(f"⚠️ No se pudo crear comando de management: {e}")

logger.info("🔧 Signals de certificados con storage dual configurados exitosamente")