#!/bin/bash
# -*- coding: utf-8 -*-
"""
Script de inicialización para GlobalCertificateManager
startup_certificates.sh
"""

echo "🚀 Inicializando Sistema de Certificados GlobalCertificateManager"
echo "=================================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}📋 $1${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    print_error "Error: No se encontró manage.py. Ejecuta este script desde el directorio raíz del proyecto."
    exit 1
fi

print_info "Verificando estructura del proyecto..."

# Crear directorios necesarios si no existen
echo ""
print_info "Creando directorios necesarios..."

# Comando de gestión
if [ ! -d "apps/sri_integration/management" ]; then
    mkdir -p apps/sri_integration/management/commands
    touch apps/sri_integration/management/__init__.py
    touch apps/sri_integration/management/commands/__init__.py
    print_status "Directorio management creado"
else
    print_status "Directorio management ya existe"
fi

# Logs
if [ ! -d "logs" ]; then
    mkdir -p logs
    touch logs/certificates.log
    touch logs/vendo_sri.log
    print_status "Directorio logs creado"
else
    print_status "Directorio logs ya existe"
fi

# Storage para certificados
if [ ! -d "storage/certificates" ]; then
    mkdir -p storage/certificates
    chmod 700 storage/certificates  # Solo acceso para el propietario
    print_status "Directorio storage/certificates creado con permisos seguros"
else
    print_status "Directorio storage/certificates ya existe"
fi

echo ""
print_info "Verificando configuración de la aplicación..."

# Verificar que las apps estén en INSTALLED_APPS
python << 'EOF'
import os
import sys
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')

try:
    django.setup()
    
    # Verificar apps instaladas
    required_apps = [
        'apps.certificates',
        'apps.sri_integration',
        'apps.companies'
    ]
    
    installed = settings.INSTALLED_APPS
    missing_apps = [app for app in required_apps if app not in installed]
    
    if missing_apps:
        print(f"❌ Apps faltantes en INSTALLED_APPS: {missing_apps}")
        sys.exit(1)
    else:
        print("✅ Todas las apps necesarias están instaladas")
        
    # Verificar configuración de certificados
    if hasattr(settings, 'CERTIFICATE_CACHE_TIMEOUT'):
        print("✅ Configuración de certificados encontrada")
    else:
        print("⚠️  Configuración de certificados no encontrada")
        
except Exception as e:
    print(f"❌ Error verificando configuración: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    print_error "Error en la verificación de configuración"
    exit 1
fi

echo ""
print_info "Ejecutando migraciones..."

# Aplicar migraciones
python manage.py makemigrations --noinput
python manage.py migrate --noinput

if [ $? -eq 0 ]; then
    print_status "Migraciones aplicadas correctamente"
else
    print_error "Error aplicando migraciones"
    exit 1
fi

echo ""
print_info "Verificando certificados en la base de datos..."

# Verificar certificados existentes
python manage.py shell << 'EOF'
from apps.certificates.models import DigitalCertificate
from apps.companies.models import Company

# Estadísticas
total_companies = Company.objects.filter(is_active=True).count()
companies_with_certs = Company.objects.filter(
    is_active=True,
    digital_certificate__isnull=False,
    digital_certificate__status='ACTIVE'
).distinct().count()

active_certs = DigitalCertificate.objects.filter(status='ACTIVE').count()

print(f"📊 ESTADÍSTICAS:")
print(f"   Empresas activas: {total_companies}")
print(f"   Empresas con certificados: {companies_with_certs}")
print(f"   Certificados activos: {active_certs}")

if active_certs > 0:
    print("✅ Hay certificados para precargar")
else:
    print("⚠️  No hay certificados activos configurados")
EOF

echo ""
print_info "Probando GlobalCertificateManager..."

# Probar el gestor global
python manage.py shell << 'EOF'
try:
    from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
    
    cert_manager = get_certificate_manager()
    stats = cert_manager.get_stats()
    
    print("✅ GlobalCertificateManager inicializado correctamente")
    print(f"📊 Estado inicial:")
    print(f"   Cache size: {stats['cache_size']}")
    print(f"   Max cache size: {stats['max_cache_size']}")
    print(f"   Instance ID: {stats['instance_id']}")
    
except Exception as e:
    print(f"❌ Error inicializando GlobalCertificateManager: {e}")
    import traceback
    traceback.print_exc()
EOF

echo ""
print_info "Precargando certificados..."

# Precargar certificados
python manage.py preload_certificates --all --stats

if [ $? -eq 0 ]; then
    print_status "Precarga de certificados completada"
else
    print_warning "La precarga tuvo algunos errores (normal si no hay certificados configurados)"
fi

echo ""
print_info "Verificando estado final..."

# Estado final del sistema
python manage.py shell << 'EOF'
from apps.sri_integration.services.global_certificate_manager import get_certificate_manager

cert_manager = get_certificate_manager()
stats = cert_manager.get_stats()

print("📊 ESTADO FINAL DEL SISTEMA:")
print(f"   Certificados en cache: {stats['cache_size']}")
print(f"   Certificados cargados en sesión: {stats['statistics']['certificates_loaded']}")
print(f"   Cache hits: {stats['statistics']['cache_hits']}")
print(f"   Cache misses: {stats['statistics']['cache_misses']}")

if stats['cache_size'] > 0:
    print("✅ Sistema listo para procesar documentos SIN PASSWORDS")
    print("")
    print("🎉 ENDPOINTS LISTOS:")
    print("   POST /api/sri/documents/{id}/process_complete/")
    print("   POST /api/sri/documents/{id}/sign_document/")
    print("   POST /api/sri/documents/{id}/send_to_sri/")
    print("")
    print("🔑 PASSWORD REQUERIDO: NO")
    print("🏢 MULTI-EMPRESA: SÍ")
    print("💾 CACHE ACTIVO: SÍ")
else:
    print("⚠️  No hay certificados cacheados")
    print("   Para usar el sistema, configura certificados digitales para las empresas")
EOF

echo ""
echo "=================================================================="
print_status "Inicialización completada"

echo ""
print_info "COMANDOS ÚTILES:"
echo "   📋 Ver estado:              python manage.py preload_certificates --stats"
echo "   🔄 Recargar certificados:   python manage.py preload_certificates --all --force-reload"
echo "   🗑️  Limpiar cache:          python manage.py preload_certificates --clear-cache"
echo "   ✅ Validar certificados:    python manage.py preload_certificates --validate-only"
echo ""
print_info "API ENDPOINTS (SIN PASSWORD):"
echo "   🚀 Proceso completo:        POST /api/sri/documents/{id}/process_complete/"
echo "   ✍️  Firmar documento:       POST /api/sri/documents/{id}/sign_document/" 
echo "   📤 Enviar al SRI:          POST /api/sri/documents/{id}/send_to_sri/"
echo "   📊 Estado del cache:       GET /api/sri/documents/certificate_manager_status/"
echo ""

print_status "¡Sistema GlobalCertificateManager listo para usar!"