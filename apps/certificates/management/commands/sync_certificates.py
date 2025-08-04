# -*- coding: utf-8 -*-
"""
Comando para sincronizar certificados existentes a storage/certificates/
apps/certificates/management/commands/sync_certificates.py
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from pathlib import Path
import os
import shutil
from apps.certificates.models import DigitalCertificate


class Command(BaseCommand):
    help = 'Sincroniza certificados existentes al directorio storage/certificates/'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='Solo verificar estado sin copiar archivos',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar copia incluso si el archivo ya existe en storage',
        )
        
        parser.add_argument(
            '--company-ruc',
            type=str,
            help='Sincronizar solo certificados de una empresa específica',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando sincronización de certificados...')
        )
        
        # Filtrar certificados
        queryset = DigitalCertificate.objects.filter(
            certificate_file__isnull=False,
            company__isnull=False
        )
        
        if options['company_ruc']:
            queryset = queryset.filter(company__ruc=options['company_ruc'])
            self.stdout.write(f"📋 Filtrando por empresa RUC: {options['company_ruc']}")
        
        certificates = queryset.select_related('company')
        total_certificates = certificates.count()
        
        if total_certificates == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ No se encontraron certificados para procesar')
            )
            return
        
        self.stdout.write(f"📊 Total de certificados a procesar: {total_certificates}")
        
        # Contadores
        stats = {
            'processed': 0,
            'copied': 0,
            'already_exists': 0,
            'failed': 0,
            'errors': []
        }
        
        # Crear directorio base de storage si no existe
        storage_base = Path(settings.BASE_DIR) / 'storage' / 'certificates'
        storage_base.mkdir(parents=True, exist_ok=True)
        os.chmod(storage_base, 0o700)
        
        # Procesar cada certificado
        for cert in certificates:
            stats['processed'] += 1
            
            try:
                company_ruc = cert.company.ruc
                
                # Crear directorio de la empresa
                company_dir = storage_base / company_ruc
                company_dir.mkdir(exist_ok=True)
                os.chmod(company_dir, 0o700)
                
                # Obtener nombre del archivo
                if not cert.certificate_file.name:
                    stats['failed'] += 1
                    stats['errors'].append(f"Certificado {cert.id}: Sin archivo")
                    continue
                
                filename = os.path.basename(cert.certificate_file.name)
                storage_file_path = company_dir / filename
                
                # Verificar si ya existe
                if storage_file_path.exists() and not options['force']:
                    stats['already_exists'] += 1
                    
                    if options['verify_only']:
                        self.stdout.write(f"  ✅ {company_ruc}/{filename} - Ya existe en storage")
                    
                    # Actualizar storage_path si no está configurado
                    if not cert.storage_path:
                        relative_path = f"certificates/{company_ruc}/{filename}"
                        cert.storage_path = relative_path
                        cert.save(update_fields=['storage_path'])
                    
                    continue
                
                # Solo verificar en modo verify-only
                if options['verify_only']:
                    if storage_file_path.exists():
                        self.stdout.write(f"  ✅ {company_ruc}/{filename} - Existe en storage")
                    else:
                        self.stdout.write(f"  ❌ {company_ruc}/{filename} - Falta en storage")
                    continue
                
                # Copiar archivo
                success = self._copy_certificate(cert, storage_file_path)
                
                if success:
                    stats['copied'] += 1
                    
                    # Actualizar storage_path
                    relative_path = f"certificates/{company_ruc}/{filename}"
                    cert.storage_path = relative_path
                    cert.save(update_fields=['storage_path'])
                    
                    self.stdout.write(f"  ✅ {company_ruc}/{filename} - Copiado exitosamente")
                else:
                    stats['failed'] += 1
                    stats['errors'].append(f"Certificado {cert.id}: Error copiando archivo")
                    self.stdout.write(f"  ❌ {company_ruc}/{filename} - Error copiando")
                
            except Exception as e:
                stats['failed'] += 1
                error_msg = f"Certificado {cert.id}: {str(e)}"
                stats['errors'].append(error_msg)
                self.stdout.write(f"  ❌ Error procesando certificado {cert.id}: {e}")
        
        # Mostrar resumen
        self._show_summary(stats, options['verify_only'])
    
    def _copy_certificate(self, certificate, target_path):
        """
        Copia un certificado al storage
        
        Args:
            certificate: instancia de DigitalCertificate
            target_path: Path donde copiar el archivo
            
        Returns:
            bool: True si se copió exitosamente
        """
        try:
            # Intentar obtener ruta del archivo
            source_path = None
            
            if hasattr(certificate.certificate_file, 'path'):
                source_path = certificate.certificate_file.path
                if not os.path.exists(source_path):
                    return False
            else:
                # Intentar leer contenido directamente
                try:
                    certificate.certificate_file.seek(0)
                    content = certificate.certificate_file.read()
                    certificate.certificate_file.seek(0)
                    
                    with open(target_path, 'wb') as f:
                        f.write(content)
                    
                    os.chmod(target_path, 0o600)
                    return True
                    
                except Exception:
                    return False
            
            # Copiar archivo usando shutil
            if source_path:
                shutil.copy2(source_path, target_path)
                os.chmod(target_path, 0o600)
                return True
            
            return False
            
        except Exception as e:
            self.stdout.write(f"Error copiando archivo: {e}")
            return False
    
    def _show_summary(self, stats, verify_only):
        """Muestra resumen de la operación"""
        
        if verify_only:
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.SUCCESS("📋 RESUMEN DE VERIFICACIÓN"))
            self.stdout.write("="*50)
            self.stdout.write(f"📊 Total procesados: {stats['processed']}")
            self.stdout.write(f"✅ Ya en storage: {stats['already_exists']}")
            self.stdout.write(f"❌ Faltantes: {stats['processed'] - stats['already_exists']}")
        else:
            self.stdout.write("\n" + "="*50)
            self.stdout.write(self.style.SUCCESS("📋 RESUMEN DE SINCRONIZACIÓN"))
            self.stdout.write("="*50)
            self.stdout.write(f"📊 Total procesados: {stats['processed']}")
            self.stdout.write(f"✅ Copiados exitosamente: {stats['copied']}")
            self.stdout.write(f"💾 Ya existían: {stats['already_exists']}")
            self.stdout.write(f"❌ Fallos: {stats['failed']}")
        
        if stats['errors']:
            self.stdout.write(f"\n🚨 Errores encontrados ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Mostrar solo los primeros 10
                self.stdout.write(f"  - {error}")
            
            if len(stats['errors']) > 10:
                remaining = len(stats['errors']) - 10
                self.stdout.write(f"  ... y {remaining} errores más")
        
        self.stdout.write("\n" + self.style.SUCCESS("✅ Operación completada"))