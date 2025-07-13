#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el procesamiento completo del SRI
Ubicación: /app/test_sri_process.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

from apps.certificates.models import DigitalCertificate
from apps.sri_integration.models import ElectronicDocument
from apps.sri_integration.services.sri_processor import SRIProcessor


def test_complete_process():
    """Prueba el proceso completo de firma y envío al SRI"""
    
    print("🧪 INICIANDO PRUEBA COMPLETA DEL PROCESO SRI")
    print("=" * 60)
    
    try:
        # 1. Verificar certificado
        print("\n1️⃣ Verificando certificado digital...")
        certificate = DigitalCertificate.objects.filter(
            status='ACTIVE',
            environment='TEST'
        ).first()
        
        if not certificate:
            print("❌ No hay certificado activo en ambiente TEST")
            return False
        
        print(f"✅ Certificado encontrado: {certificate.company.business_name}")
        print(f"   Subject: {certificate.subject_name}")
        
        # 2. Verificar factura pendiente
        print("\n2️⃣ Verificando facturas pendientes...")
        document = ElectronicDocument.objects.filter(
            status='DRAFT',
            company=certificate.company
        ).first()
        
        if not document:
            print("❌ No hay facturas pendientes para esta empresa")
            return False
        
        print(f"✅ Factura encontrada: {document.document_number}")
        print(f"   Cliente: {document.customer_name}")
        print(f"   Total: ${document.total_amount}")
        
        # 3. Solicitar contraseña
        print("\n3️⃣ Verificando contraseña del certificado...")
        
        # Para prueba, usar contraseñas comunes - EN PRODUCCIÓN SOLICITAR AL USUARIO
        test_passwords = ['123456', 'password', 'certificado', '12345678', 'admin', 'test']
        password = None
        
        for test_pass in test_passwords:
            try:
                if certificate.verify_password(test_pass):
                    password = test_pass
                    print(f"✅ Contraseña encontrada: {test_pass}")
                    break
            except Exception as e:
                # Continuar con la siguiente contraseña
                continue
        
        if not password:
            print("❌ No se pudo verificar la contraseña del certificado")
            print("   Contraseñas probadas:", test_passwords)
            print("   💡 Ejecuta el comando manualmente con: --password TU_CONTRASEÑA")
            print("\n🔍 Información del certificado:")
            print(f"   Empresa: {certificate.company.business_name}")
            print(f"   Subject: {certificate.subject_name}")
            print(f"   Archivo: {certificate.certificate_file.name if certificate.certificate_file else 'No disponible'}")
            return False
        
        # 4. Procesar documento
        print("\n4️⃣ Iniciando procesamiento completo...")
        print("-" * 40)
        
        processor = SRIProcessor(certificate, 'TEST')
        result = processor.process_document(document, password)
        
        # 5. Mostrar resultados
        print("\n5️⃣ Resultados del procesamiento:")
        print("-" * 40)
        
        if result['success']:
            print("🎉 ¡PROCESAMIENTO EXITOSO!")
            print(f"   📧 Clave de acceso: {result['access_key']}")
            print(f"   🔢 Número de autorización: {result['authorization_number']}")
            print(f"   📄 XML firmado: {result['signed_xml_path']}")
            print(f"   📋 PDF generado: {result['pdf_path']}")
            
            print("\n✅ Pasos completados:")
            for i, step in enumerate(result['steps'], 1):
                print(f"   {i}. {step}")
                
            return True
        else:
            print("❌ PROCESAMIENTO FALLÓ")
            print("\n🔸 Errores encontrados:")
            for error in result['errors']:
                print(f"   • {error}")
                
            print("\n📝 Pasos completados:")
            for i, step in enumerate(result['steps'], 1):
                print(f"   {i}. {step}")
                
            return False
    
    except Exception as e:
        print(f"\n💥 ERROR GENERAL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def show_system_status():
    """Muestra el estado actual del sistema"""
    
    print("📊 ESTADO ACTUAL DEL SISTEMA")
    print("=" * 50)
    
    # Certificados
    certificates = DigitalCertificate.objects.all()
    print(f"\n📜 Certificados: {certificates.count()}")
    for cert in certificates:
        status = "✅" if cert.status == 'ACTIVE' else "❌"
        password_ok = "🔐" if cert.password_hash and cert.password_hash != 'temp_hash' else "❌"
        print(f"   {status} {cert.company.business_name} - {cert.environment} {password_ok}")
    
    # Documentos
    documents = ElectronicDocument.objects.all()
    print(f"\n📄 Documentos: {documents.count()}")
    
    status_counts = {}
    for doc in documents:
        status_counts[doc.status] = status_counts.get(doc.status, 0) + 1
    
    for status, count in status_counts.items():
        icon = "📝" if status == 'DRAFT' else "✅" if status == 'AUTHORIZED' else "❌"
        print(f"   {icon} {status}: {count}")
    
    # Dependencias
    print(f"\n🔧 Dependencias:")
    try:
        import cryptography
        print(f"   ✅ cryptography: {cryptography.__version__}")
    except ImportError:
        print("   ❌ cryptography: NO INSTALADA")
    
    try:
        import lxml
        print(f"   ✅ lxml: {lxml.__version__}")
    except ImportError:
        print("   ❌ lxml: NO INSTALADA")
    
    try:
        import reportlab
        print(f"   ✅ reportlab: {reportlab.Version}")
    except ImportError:
        print("   ❌ reportlab: NO INSTALADA")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_system_status()
    else:
        success = test_complete_process()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
            print("✅ El sistema está listo para procesar facturas reales")
        else:
            print("❌ PRUEBA FALLÓ")
            print("🔧 Revisa los errores anteriores y corrige la configuración")
        print("=" * 60)