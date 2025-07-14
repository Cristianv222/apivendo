#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para diagnosticar el error 422 en creación de facturas
"""

import os
import sys
import requests
import json
from datetime import date

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
import django
django.setup()

def debug_invoice_creation():
    """Diagnosticar el problema con la creación de facturas"""
    
    base_url = "http://localhost:8000"
    
    # Datos de factura simplificados para debug
    simple_invoice = {
        "company": 1,
        "document_type": "INVOICE",
        "issue_date": date.today().strftime('%Y-%m-%d'),
        "customer_identification_type": "05",
        "customer_identification": "1234567890",
        "customer_name": "CLIENTE TEST",
        "customer_address": "Dirección Test",
        "customer_email": "test@example.com",
        "customer_phone": "0999999999",
        "items": [
            {
                "main_code": "PROD001",
                "auxiliary_code": "",
                "description": "Producto de prueba",
                "quantity": "1.0",
                "unit_price": "10.0",
                "discount": "0.0",
                "additional_details": {}
            }
        ],
        "additional_data": {}
    }
    
    print("🔍 DIAGNÓSTICO DE CREACIÓN DE FACTURAS")
    print("=" * 50)
    
    # Verificar que la empresa existe y tiene configuración SRI
    print("1. Verificando empresa y configuración SRI...")
    try:
        response = requests.get(f"{base_url}/api/sri/configuration/")
        if response.status_code == 200:
            config = response.json()
            print(f"   ✅ Configuración SRI encontrada")
            if isinstance(config, list) and len(config) > 0:
                sri_config = config[0]
                print(f"   📋 Empresa: {sri_config.get('company_name', 'N/A')}")
                print(f"   📋 Activa: {sri_config.get('is_active', False)}")
                print(f"   📋 Secuencial factura: {sri_config.get('invoice_sequence', 'N/A')}")
            else:
                print(f"   ⚠️ Configuración no encontrada o vacía")
        else:
            print(f"   ❌ Error obteniendo configuración: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Verificar endpoint de creación de facturas
    print("\n2. Probando endpoint de creación de facturas...")
    print(f"   📍 URL: {base_url}/api/sri/documents/create_invoice/")
    print(f"   📊 Datos enviados:")
    print(json.dumps(simple_invoice, indent=4, default=str))
    
    try:
        response = requests.post(
            f"{base_url}/api/sri/documents/create_invoice/",
            json=simple_invoice,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"\n   📥 Respuesta HTTP: {response.status_code}")
        print(f"   📥 Headers: {dict(response.headers)}")
        
        if response.status_code == 422:
            try:
                error_detail = response.json()
                print(f"   📝 Error detallado:")
                print(json.dumps(error_detail, indent=4, ensure_ascii=False))
                
                # Analizar errores específicos
                if 'errors' in error_detail:
                    print(f"\n   🔍 Análisis de errores:")
                    for field, errors in error_detail['errors'].items():
                        print(f"      • {field}: {errors}")
                        
                elif 'detail' in error_detail:
                    print(f"\n   🔍 Detalle del error: {error_detail['detail']}")
                    
            except json.JSONDecodeError:
                print(f"   📝 Respuesta sin JSON: {response.text}")
                
        elif response.status_code == 201:
            result = response.json()
            print(f"   ✅ Factura creada exitosamente!")
            print(f"   📋 ID: {result.get('id')}")
            print(f"   📋 Número: {result.get('document_number')}")
            
        else:
            print(f"   ❌ Error inesperado: {response.status_code}")
            print(f"   📝 Respuesta: {response.text[:500]}")
            
    except Exception as e:
        print(f"   💥 Excepción: {e}")
    
    # Verificar también el serializer directamente
    print(f"\n3. Verificación directa del serializer...")
    try:
        from apps.sri_integration.serializers import ElectronicDocumentCreateSerializer
        from apps.companies.models import Company
        
        # Verificar que la empresa existe
        try:
            company = Company.objects.get(id=1)
            print(f"   ✅ Empresa encontrada: {company.business_name}")
            
            # Verificar configuración SRI
            if hasattr(company, 'sri_configuration'):
                sri_config = company.sri_configuration
                print(f"   ✅ Configuración SRI: Activa={sri_config.is_active}")
            else:
                print(f"   ❌ No tiene configuración SRI")
                
        except Company.DoesNotExist:
            print(f"   ❌ Empresa con ID=1 no existe")
        
        # Probar serializer
        serializer = ElectronicDocumentCreateSerializer(data=simple_invoice)
        if serializer.is_valid():
            print(f"   ✅ Serializer válido")
            print(f"   📊 Datos validados: {serializer.validated_data.keys()}")
        else:
            print(f"   ❌ Errores en serializer:")
            for field, errors in serializer.errors.items():
                print(f"      • {field}: {errors}")
                
    except Exception as e:
        print(f"   💥 Error en verificación directa: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"🎯 CONCLUSIÓN DEL DIAGNÓSTICO")
    print(f"El error 422 indica un problema de validación.")
    print(f"Revisa los errores específicos arriba para identificar el campo problemático.")


if __name__ == "__main__":
    debug_invoice_creation()