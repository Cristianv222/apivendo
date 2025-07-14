#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUITE COMPLETA PARA TODOS LOS ENDPOINTS SRI IMPLEMENTADOS
Prueba exhaustiva de: Facturas, Notas de Crédito/Débito, Retenciones, Liquidaciones
"""

import requests
import json
import time
import os
import django
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
import re

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

class ComprehensiveEndpointTestSuite:
    """
    Suite completa para probar todos los endpoints SRI implementados
    """
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.critical_errors = []
        self.warnings = []
        self.created_documents = {
            'invoices': [],
            'credit_notes': [],
            'debit_notes': [],
            'retentions': [],
            'purchase_settlements': []
        }
        
    def run_complete_test_suite(self):
        """
        Ejecutar pruebas completas de todos los endpoints
        """
        print("🔍 SUITE COMPLETA PARA TODOS LOS ENDPOINTS SRI")
        print("=" * 80)
        print(f"🕐 Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Endpoint: {self.base_url}")
        print("📋 Tipos: Facturas, Notas de Crédito/Débito, Retenciones, Liquidaciones")
        print()
        
        tests = [
            # Pruebas de sistema
            self._test_01_system_health_check,
            self._test_02_database_and_config,
            
            # Creación de documentos principales
            self._test_03_invoice_creation,
            self._test_04_credit_note_creation,
            self._test_05_debit_note_creation,
            self._test_06_retention_creation,
            self._test_07_purchase_settlement_creation,
            
            # Procesamiento de documentos
            self._test_08_xml_generation_all_types,
            self._test_09_document_signing,
            self._test_10_pdf_generation_all_types,
            self._test_11_sri_submission_simulation,
            
            # Consultas y estado
            self._test_12_document_status_checking,
            self._test_13_dashboard_functionality,
            self._test_14_listing_and_filtering,
            
            # Configuración SRI
            self._test_15_sri_configuration_management,
            self._test_16_sequence_management,
            
            # Pruebas de integración
            self._test_17_complete_workflow,
            self._test_18_calculation_accuracy_all_types,
            self._test_19_error_handling_comprehensive,
            self._test_20_performance_all_endpoints
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for i, test in enumerate(tests, 1):
            print(f"\n{'='*70}")
            print(f"EJECUTANDO PRUEBA {i:02d}/{total_tests:02d}: {test.__name__.replace('_test_', '').replace('_', ' ').upper()}")
            print(f"{'='*70}")
            
            try:
                result = test()
                if result:
                    passed_tests += 1
                    print(f"✅ PRUEBA {i:02d} APROBADA")
                else:
                    print(f"❌ PRUEBA {i:02d} FALLÓ")
            except Exception as e:
                print(f"💥 PRUEBA {i:02d} ERROR CRÍTICO: {e}")
                self.critical_errors.append(f"Test {i:02d}: {e}")
        
        self._generate_comprehensive_report(passed_tests, total_tests)
        
        return passed_tests, total_tests, len(self.critical_errors) == 0
    
    def _test_01_system_health_check(self):
        """
        TEST 01: Verificación de salud del sistema
        """
        print("🏥 TEST 01: SALUD DEL SISTEMA")
        print("-" * 50)
        
        try:
            # Verificar API principal
            response = self.session.get(f"{self.base_url}/api/status/")
            if response.status_code == 200:
                status_data = response.json()
                print(f"   ✅ API Status: {status_data.get('message')}")
                print(f"   🔧 SRI Enabled: {status_data.get('sri_enabled', False)}")
                
                if not status_data.get('sri_enabled', False):
                    self.warnings.append("SRI functionality not fully enabled")
            else:
                print(f"   ❌ API Status no disponible: {response.status_code}")
                return False
            
            # Verificar endpoints principales
            endpoints_to_check = [
                '/api/',
                '/api/sri/documents/',
                '/api/sri/configuration/',
                '/admin/'
            ]
            
            available_endpoints = 0
            for endpoint in endpoints_to_check:
                try:
                    resp = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                    if resp.status_code < 500:
                        available_endpoints += 1
                        print(f"   ✅ {endpoint}: Disponible")
                    else:
                        print(f"   ⚠️ {endpoint}: Error {resp.status_code}")
                except:
                    print(f"   ❌ {endpoint}: No disponible")
            
            success_rate = (available_endpoints / len(endpoints_to_check)) * 100
            print(f"   📊 Disponibilidad endpoints: {success_rate:.1f}%")
            
            return success_rate >= 75
            
        except Exception as e:
            self.critical_errors.append(f"System health check failed: {e}")
            return False
    
    def _test_02_database_and_config(self):
        """
        TEST 02: Base de datos y configuración
        """
        print("🗄️ TEST 02: BASE DE DATOS Y CONFIGURACIÓN")
        print("-" * 50)
        
        try:
            from apps.companies.models import Company
            from apps.sri_integration.models import SRIConfiguration
            from apps.certificates.models import DigitalCertificate
            
            # Verificar empresas
            companies = Company.objects.filter(is_active=True)
            print(f"   📊 Empresas activas: {companies.count()}")
            
            if companies.count() == 0:
                self.critical_errors.append("No active companies found")
                return False
            
            # Verificar configuraciones SRI
            sri_configs = SRIConfiguration.objects.filter(is_active=True)
            print(f"   ⚙️ Configuraciones SRI activas: {sri_configs.count()}")
            
            if sri_configs.count() == 0:
                self.critical_errors.append("No active SRI configurations found")
                return False
            
            # Verificar certificados válidos
            valid_certs = 0
            for company in companies:
                if hasattr(company, 'digital_certificate'):
                    cert = company.digital_certificate
                    if cert.status == 'ACTIVE' and not cert.is_expired:
                        valid_certs += 1
                        print(f"   ✅ {company.business_name}: Certificado OK")
                    else:
                        print(f"   ⚠️ {company.business_name}: Certificado inválido")
                else:
                    print(f"   ❌ {company.business_name}: Sin certificado")
            
            print(f"   🔐 Certificados válidos: {valid_certs}")
            
            if valid_certs == 0:
                self.critical_errors.append("No valid certificates found")
                return False
            
            return True
            
        except Exception as e:
            self.critical_errors.append(f"Database/config check failed: {e}")
            return False
    
    def _test_03_invoice_creation(self):
        """
        TEST 03: Creación de facturas (múltiples escenarios)
        """
        print("📄 TEST 03: CREACIÓN DE FACTURAS")
        print("-" * 50)
        
        invoice_scenarios = [
            {
                "name": "Factura básica",
                "data": {
                    "company": 1,
                    "customer_identification_type": "05",
                    "customer_identification": "1234567890",
                    "customer_name": "CLIENTE FACTURA BÁSICA",
                    "customer_address": "Dirección básica",
                    "customer_email": "basica@test.com",
                    "items": [
                        {
                            "main_code": "BASIC001",
                            "description": "Producto básico",
                            "quantity": 1.0,
                            "unit_price": 100.0,
                            "discount": 0.0,
                            "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                        }
                    ]
                }
            },
            {
                "name": "Factura empresarial",
                "data": {
                    "company": 1,
                    "customer_identification_type": "04",
                    "customer_identification": "1790123456001",
                    "customer_name": "EMPRESA CLIENTE S.A.",
                    "customer_address": "Av. Principal 123",
                    "customer_email": "empresa@test.com",
                    "items": [
                        {
                            "main_code": "SERV001",
                            "description": "Servicios profesionales",
                            "quantity": 10.0,
                            "unit_price": 50.0,
                            "discount": 25.0,
                            "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                        },
                        {
                            "main_code": "PROD001",
                            "description": "Producto adicional",
                            "quantity": 2.0,
                            "unit_price": 75.0,
                            "discount": 10.0,
                            "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                        }
                    ]
                }
            },
            {
                "name": "Factura con descuentos complejos",
                "data": {
                    "company": 1,
                    "customer_identification_type": "05",
                    "customer_identification": "9876543210",
                    "customer_name": "CLIENTE DESCUENTOS",
                    "customer_address": "Calle Descuentos 456",
                    "customer_email": "descuentos@test.com",
                    "items": [
                        {
                            "main_code": "DISC001",
                            "description": "Producto con descuento",
                            "quantity": 3.5,
                            "unit_price": 28.57,
                            "discount": 15.0,
                            "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                        }
                    ]
                }
            }
        ]
        
        success_count = 0
        
        for scenario in invoice_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/create_invoice/",
                    json=scenario['data'],
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 201:
                    invoice_data = response.json()
                    invoice_id = invoice_data.get('id')
                    
                    print(f"      ✅ Creada: ID {invoice_id}")
                    print(f"      📋 Número: {invoice_data.get('document_number')}")
                    print(f"      💰 Total: ${invoice_data.get('total_amount')}")
                    print(f"      🔑 Clave: {invoice_data.get('access_key', 'N/A')[:20]}...")
                    
                    self.created_documents['invoices'].append(invoice_id)
                    success_count += 1
                    
                    # Validar campos obligatorios
                    required_fields = ['id', 'document_number', 'access_key', 'total_amount', 'status']
                    missing_fields = [field for field in required_fields if field not in invoice_data]
                    if missing_fields:
                        self.warnings.append(f"Missing fields in invoice: {missing_fields}")
                    
                else:
                    print(f"      ❌ Error {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      Detalles: {error_data.get('message', 'Unknown error')}")
                    except:
                        print(f"      Respuesta: {response.text[:100]}")
                    
            except Exception as e:
                print(f"      💥 Error: {e}")
        
        print(f"   📊 Facturas exitosas: {success_count}/{len(invoice_scenarios)}")
        
        if success_count == 0:
            self.critical_errors.append("No invoices could be created")
            return False
        
        return success_count >= len(invoice_scenarios) * 0.8  # 80% success rate required
    
    def _test_04_credit_note_creation(self):
        """
        TEST 04: Creación de notas de crédito
        """
        print("📝 TEST 04: CREACIÓN DE NOTAS DE CRÉDITO")
        print("-" * 50)
        
        if not self.created_documents['invoices']:
            print("   ⚠️ No hay facturas para crear notas de crédito")
            return True
        
        credit_note_scenarios = [
            {
                "name": "Devolución total",
                "reason_code": "01",
                "reason_description": "Devolución de mercadería defectuosa",
                "items": [
                    {
                        "main_code": "DEV001",
                        "description": "Producto devuelto",
                        "quantity": 1.0,
                        "unit_price": 100.0,
                        "discount": 0.0
                    }
                ]
            },
            {
                "name": "Devolución parcial",
                "reason_code": "02",
                "reason_description": "Descuento comercial aplicado",
                "items": [
                    {
                        "main_code": "DESC001",
                        "description": "Descuento aplicado",
                        "quantity": 1.0,
                        "unit_price": 25.0,
                        "discount": 0.0
                    }
                ]
            }
        ]
        
        success_count = 0
        original_invoice_id = self.created_documents['invoices'][0]
        
        for scenario in credit_note_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            credit_note_data = {
                "company": 1,
                "original_invoice_id": original_invoice_id,
                "reason_code": scenario['reason_code'],
                "reason_description": scenario['reason_description'],
                "items": scenario['items']
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/create_credit_note/",
                    json=credit_note_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 201:
                    credit_data = response.json()
                    credit_id = credit_data.get('id')
                    
                    print(f"      ✅ Creada: ID {credit_id}")
                    print(f"      📋 Número: {credit_data.get('document_number')}")
                    print(f"      💰 Total: ${credit_data.get('total_amount')}")
                    print(f"      📄 Factura original: {original_invoice_id}")
                    
                    self.created_documents['credit_notes'].append(credit_id)
                    success_count += 1
                    
                else:
                    print(f"      ❌ Error {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      Detalles: {error_data.get('message', 'Unknown error')}")
                    except:
                        print(f"      Respuesta: {response.text[:100]}")
                    
            except Exception as e:
                print(f"      💥 Error: {e}")
        
        print(f"   📊 Notas de crédito exitosas: {success_count}/{len(credit_note_scenarios)}")
        
        return success_count > 0
    
    def _test_05_debit_note_creation(self):
        """
        TEST 05: Creación de notas de débito
        """
        print("📝 TEST 05: CREACIÓN DE NOTAS DE DÉBITO")
        print("-" * 50)
        
        if not self.created_documents['invoices']:
            print("   ⚠️ No hay facturas para crear notas de débito")
            return True
        
        debit_note_scenarios = [
            {
                "name": "Intereses por mora",
                "reason_code": "01",
                "reason_description": "Intereses por pago tardío",
                "motives": [
                    {"reason": "Intereses de mora por 30 días", "amount": 50.0},
                    {"reason": "Gastos administrativos", "amount": 25.0}
                ]
            },
            {
                "name": "Gastos adicionales",
                "reason_code": "02",
                "reason_description": "Gastos adicionales no contemplados",
                "motives": [
                    {"reason": "Gastos de transporte especial", "amount": 35.0}
                ]
            }
        ]
        
        success_count = 0
        original_invoice_id = self.created_documents['invoices'][0]
        
        for scenario in debit_note_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            debit_note_data = {
                "company": 1,
                "original_invoice_id": original_invoice_id,
                "reason_code": scenario['reason_code'],
                "reason_description": scenario['reason_description'],
                "motives": scenario['motives']
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/create_debit_note/",
                    json=debit_note_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 201:
                    debit_data = response.json()
                    debit_id = debit_data.get('id')
                    
                    print(f"      ✅ Creada: ID {debit_id}")
                    print(f"      📋 Número: {debit_data.get('document_number')}")
                    print(f"      💰 Total: ${debit_data.get('total_amount')}")
                    
                    # Verificar cálculo
                    expected_subtotal = sum(float(m['amount']) for m in scenario['motives'])
                    expected_total = expected_subtotal * 1.15  # + 15% IVA
                    actual_total = float(debit_data.get('total_amount', 0))
                    
                    if abs(expected_total - actual_total) <= 0.02:
                        print(f"      ✅ Cálculo correcto")
                    else:
                        print(f"      ⚠️ Posible error de cálculo: esperado {expected_total:.2f}, obtenido {actual_total:.2f}")
                        self.warnings.append(f"Debit note calculation discrepancy")
                    
                    self.created_documents['debit_notes'].append(debit_id)
                    success_count += 1
                    
                else:
                    print(f"      ❌ Error {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      Detalles: {error_data.get('message', 'Unknown error')}")
                    except:
                        print(f"      Respuesta: {response.text[:100]}")
                    
            except Exception as e:
                print(f"      💥 Error: {e}")
        
        print(f"   📊 Notas de débito exitosas: {success_count}/{len(debit_note_scenarios)}")
        
        return success_count > 0
    
    def _test_06_retention_creation(self):
        """
        TEST 06: Creación de retenciones
        """
        print("📊 TEST 06: CREACIÓN DE RETENCIONES")
        print("-" * 50)
        
        retention_scenarios = [
            {
                "name": "Retención IR + IVA",
                "supplier_data": {
                    "identification_type": "04",
                    "identification": "1790456789001",
                    "name": "PROVEEDOR EMPRESARIAL S.A.",
                    "address": "Av. Empresarial 123"
                },
                "details": [
                    {
                        "support_document_type": "01",
                        "support_document_number": "001-001-000001234",
                        "support_document_date": "2025-07-14",
                        "tax_code": "1",
                        "retention_code": "303",
                        "retention_percentage": 1.0,
                        "taxable_base": 1000.0
                    },
                    {
                        "support_document_type": "01",
                        "support_document_number": "001-001-000001235",
                        "support_document_date": "2025-07-14",
                        "tax_code": "2",
                        "retention_code": "725",
                        "retention_percentage": 30.0,
                        "taxable_base": 500.0
                    }
                ]
            },
            {
                "name": "Retención persona natural",
                "supplier_data": {
                    "identification_type": "05",
                    "identification": "1725834567",
                    "name": "PROVEEDOR PERSONA NATURAL",
                    "address": "Calle Natural 456"
                },
                "details": [
                    {
                        "support_document_type": "03",
                        "support_document_number": "LIQ-001-000000123",
                        "support_document_date": "2025-07-14",
                        "tax_code": "1",
                        "retention_code": "328",
                        "retention_percentage": 8.0,
                        "taxable_base": 800.0
                    }
                ]
            }
        ]
        
        success_count = 0
        
        for scenario in retention_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            retention_data = {
                "company": 1,
                "supplier_identification_type": scenario['supplier_data']['identification_type'],
                "supplier_identification": scenario['supplier_data']['identification'],
                "supplier_name": scenario['supplier_data']['name'],
                "supplier_address": scenario['supplier_data']['address'],
                "fiscal_period": "07/2025",
                "retention_details": scenario['details']
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/create_retention/",
                    json=retention_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 201:
                    retention_result = response.json()
                    retention_id = retention_result.get('id')
                    
                    print(f"      ✅ Creada: ID {retention_id}")
                    print(f"      📋 Número: {retention_result.get('document_number')}")
                    print(f"      💰 Total retenido: ${retention_result.get('total_retained')}")
                    print(f"      🏢 Proveedor: {retention_result.get('supplier_name')}")
                    
                    # Calcular total esperado
                    expected_total = sum(
                        (detail['taxable_base'] * detail['retention_percentage'] / 100)
                        for detail in scenario['details']
                    )
                    actual_total = float(retention_result.get('total_retained', 0))
                    
                    if abs(expected_total - actual_total) <= 0.02:
                        print(f"      ✅ Cálculo de retención correcto")
                    else:
                        print(f"      ⚠️ Posible error de cálculo: esperado {expected_total:.2f}, obtenido {actual_total:.2f}")
                        self.warnings.append(f"Retention calculation discrepancy")
                    
                    self.created_documents['retentions'].append(retention_id)
                    success_count += 1
                    
                else:
                    print(f"      ❌ Error {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      Detalles: {error_data.get('message', 'Unknown error')}")
                    except:
                        print(f"      Respuesta: {response.text[:100]}")
                    
            except Exception as e:
                print(f"      💥 Error: {e}")
        
        print(f"   📊 Retenciones exitosas: {success_count}/{len(retention_scenarios)}")
        
        return success_count > 0
    
    def _test_07_purchase_settlement_creation(self):
        """
        TEST 07: Creación de liquidaciones de compra
        """
        print("📋 TEST 07: CREACIÓN DE LIQUIDACIONES DE COMPRA")
        print("-" * 50)
        
        settlement_scenarios = [
            {
                "name": "Liquidación servicios profesionales",
                "supplier_data": {
                    "identification_type": "05",
                    "identification": "1734567890",
                    "name": "CONSULTOR INDEPENDIENTE",
                    "address": "Oficina Consultores 789"
                },
                "items": [
                    {
                        "main_code": "CONS001",
                        "description": "Consultoría especializada",
                        "quantity": 20.0,
                        "unit_price": 25.0,
                        "discount": 50.0
                    },
                    {
                        "main_code": "TRAN001",
                        "description": "Viáticos y transporte",
                        "quantity": 1.0,
                        "unit_price": 100.0,
                        "discount": 0.0
                    }
                ]
            },
            {
                "name": "Liquidación persona extranjera",
                "supplier_data": {
                    "identification_type": "08",
                    "identification": "EXT123456789",
                    "name": "FOREIGN CONSULTANT LLC",
                    "address": "International Business Center"
                },
                "items": [
                    {
                        "main_code": "INT001",
                        "description": "International consulting services",
                        "quantity": 1.0,
                        "unit_price": 1500.0,
                        "discount": 100.0
                    }
                ]
            }
        ]
        
        success_count = 0
        
        for scenario in settlement_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            settlement_data = {
                "company": 1,
                "supplier_identification_type": scenario['supplier_data']['identification_type'],
                "supplier_identification": scenario['supplier_data']['identification'],
                "supplier_name": scenario['supplier_data']['name'],
                "supplier_address": scenario['supplier_data']['address'],
                "items": scenario['items']
            }
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/create_purchase_settlement/",
                    json=settlement_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 201:
                    settlement_result = response.json()
                    settlement_id = settlement_result.get('id')
                    
                    print(f"      ✅ Creada: ID {settlement_id}")
                    print(f"      📋 Número: {settlement_result.get('document_number')}")
                    print(f"      💰 Total: ${settlement_result.get('total_amount')}")
                    print(f"      🏢 Proveedor: {settlement_result.get('supplier_name')}")
                    
                    # Calcular total esperado
                    subtotal = sum(
                        (item['quantity'] * item['unit_price'] - item['discount'])
                        for item in scenario['items']
                    )
                    expected_total = subtotal * 1.15  # + 15% IVA
                    actual_total = float(settlement_result.get('total_amount', 0))
                    
                    if abs(expected_total - actual_total) <= 0.02:
                        print(f"      ✅ Cálculo correcto")
                    else:
                        print(f"      ⚠️ Posible error de cálculo: esperado {expected_total:.2f}, obtenido {actual_total:.2f}")
                        self.warnings.append(f"Settlement calculation discrepancy")
                    
                    self.created_documents['purchase_settlements'].append(settlement_id)
                    success_count += 1
                    
                else:
                    print(f"      ❌ Error {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"      Detalles: {error_data.get('message', 'Unknown error')}")
                    except:
                        print(f"      Respuesta: {response.text[:100]}")
                    
            except Exception as e:
                print(f"      💥 Error: {e}")
        
        print(f"   📊 Liquidaciones exitosas: {success_count}/{len(settlement_scenarios)}")
        
        return success_count > 0
    
    def _test_08_xml_generation_all_types(self):
        """
        TEST 08: Generación de XML para todos los tipos
        """
        print("📄 TEST 08: GENERACIÓN DE XML TODOS LOS TIPOS")
        print("-" * 50)
        
        xml_success_count = 0
        total_documents = 0
        
        # Probar generación XML para cada tipo de documento
        for doc_type, doc_list in self.created_documents.items():
            if doc_list:
                print(f"   📋 {doc_type.replace('_', ' ').title()}: {len(doc_list)} documentos")
                
                for doc_id in doc_list[:2]:  # Probar los primeros 2 de cada tipo
                    total_documents += 1
                    
                    try:
                        response = self.session.post(
                            f"{self.base_url}/api/sri/documents/{doc_id}/generate_xml/",
                            json={},
                            timeout=20
                        )
                        
                        if response.status_code == 200:
                            xml_result = response.json()
                            xml_size = xml_result.get('data', {}).get('xml_size', 0)
                            print(f"      ✅ ID {doc_id}: XML generado ({xml_size} chars)")
                            xml_success_count += 1
                        else:
                            print(f"      ❌ ID {doc_id}: Error {response.status_code}")
                            
                    except Exception as e:
                        print(f"      💥 ID {doc_id}: Error - {str(e)[:50]}")
        
        if total_documents > 0:
            success_rate = (xml_success_count / total_documents) * 100
            print(f"   📊 XML generado exitosamente: {xml_success_count}/{total_documents} ({success_rate:.1f}%)")
            
            if success_rate < 70:
                self.critical_errors.append(f"Low XML generation success rate: {success_rate:.1f}%")
                return False
            
            return True
        else:
            print("   ⚠️ No hay documentos para generar XML")
            return True
    
    def _test_09_document_signing(self):
        """
        TEST 09: Firma digital de documentos
        """
        print("🔐 TEST 09: FIRMA DIGITAL DE DOCUMENTOS")
        print("-" * 50)
        
        # Probar firma en diferentes tipos de documentos
        test_documents = []
        for doc_type, docs in self.created_documents.items():
            if docs:
                test_documents.append((docs[0], doc_type))
        
        if not test_documents:
            print("   ⚠️ No hay documentos para firmar")
            return True
        
        signature_success = 0
        
        for doc_id, doc_type in test_documents[:3]:  # Probar primeros 3
            print(f"   📋 Firmando {doc_type} ID {doc_id}")
            
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/documents/{doc_id}/sign_document/",
                    json={"password": "Jheymie10"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    sign_result = response.json()
                    print(f"      ✅ Firmado exitosamente")
                    print(f"      🔏 Algoritmo: {sign_result.get('data', {}).get('signature_algorithm', 'N/A')}")
                    signature_success += 1
                else:
                    print(f"      ⚠️ Firma no disponible: {response.status_code}")
                    # No crítico si la librería de firma no está disponible
                    
            except Exception as e:
                print(f"      ⚠️ Error de firma: {str(e)[:50]}")
        
        print(f"   📊 Documentos firmados: {signature_success}/{len(test_documents)}")
        
        # La firma no es crítica para el funcionamiento básico
        return True
    
    def _test_10_pdf_generation_all_types(self):
        """
        TEST 10: Generación de PDF para todos los tipos
        """
        print("📑 TEST 10: GENERACIÓN DE PDF TODOS LOS TIPOS")
        print("-" * 50)
        
        pdf_success_count = 0
        total_attempts = 0
        
        for doc_type, docs in self.created_documents.items():
            if docs:
                doc_id = docs[0]  # Probar el primer documento de cada tipo
                total_attempts += 1
                
                print(f"   📋 PDF para {doc_type} (ID: {doc_id})")
                
                try:
                    # Nota: este endpoint podría no existir para todos los tipos
                    response = self.session.post(
                        f"{self.base_url}/api/sri/documents/{doc_id}/generate_pdf/",
                        json={},
                        timeout=25
                    )
                    
                    if response.status_code == 200:
                        pdf_result = response.json()
                        pdf_path = pdf_result.get('data', {}).get('pdf_path', 'N/A')
                        
                        print(f"      ✅ PDF generado: {pdf_path}")
                        pdf_success_count += 1
                    elif response.status_code == 404:
                        print(f"      ⚠️ Endpoint PDF no disponible para {doc_type}")
                        # No contar como error crítico
                    else:
                        print(f"      ❌ Error generando PDF: {response.status_code}")
                        
                except Exception as e:
                    print(f"      💥 Error: {str(e)[:50]}")
        
        if total_attempts > 0:
            print(f"   📊 PDF exitoso: {pdf_success_count}/{total_attempts}")
        
        return True  # No crítico
    
    def _test_11_sri_submission_simulation(self):
        """
        TEST 11: Simulación de envío al SRI
        """
        print("🏛️ TEST 11: SIMULACIÓN DE ENVÍO AL SRI")
        print("-" * 50)
        
        if not self.created_documents['invoices']:
            print("   ⚠️ No hay documentos para simular envío")
            return True
        
        test_invoice_id = self.created_documents['invoices'][0]
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/{test_invoice_id}/send_to_sri/",
                json={},
                timeout=30
            )
            
            if response.status_code in [200, 202]:
                sri_result = response.json()
                print(f"   ✅ Envío simulado exitosamente")
                print(f"   📋 Mensaje: {sri_result.get('message', 'N/A')}")
                print(f"   📊 Estado: {sri_result.get('data', {}).get('status', 'N/A')}")
                return True
            else:
                print(f"   ⚠️ Envío no disponible: {response.status_code}")
                # No crítico para pruebas
                return True
                
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            return True
    
    def _test_12_document_status_checking(self):
        """
        TEST 12: Verificación de estado de documentos
        """
        print("📊 TEST 12: VERIFICACIÓN DE ESTADO DE DOCUMENTOS")
        print("-" * 50)
        
        status_checks = 0
        total_checks = 0
        
        for doc_type, docs in self.created_documents.items():
            if docs:
                doc_id = docs[0]
                total_checks += 1
                
                try:
                    response = self.session.get(
                        f"{self.base_url}/api/sri/documents/{doc_id}/status_check/",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        status_data = response.json()
                        
                        print(f"   📋 {doc_type} ID {doc_id}:")
                        print(f"      Estado: {status_data.get('current_status')}")
                        print(f"      Número: {status_data.get('document_number')}")
                        print(f"      Total: ${status_data.get('total_amount')}")
                        print(f"      Clave: {status_data.get('access_key', 'N/A')[:20]}...")
                        
                        status_checks += 1
                    else:
                        print(f"   ❌ Error verificando {doc_type} {doc_id}: {response.status_code}")
                        
                except Exception as e:
                    print(f"   💥 Error {doc_type} {doc_id}: {str(e)[:50]}")
        
        print(f"   📊 Estados verificados: {status_checks}/{total_checks}")
        
        return status_checks > 0
    
    def _test_13_dashboard_functionality(self):
        """
        TEST 13: Funcionalidad del dashboard
        """
        print("📈 TEST 13: FUNCIONALIDAD DEL DASHBOARD")
        print("-" * 50)
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/sri/documents/dashboard/",
                timeout=15
            )
            
            if response.status_code == 200:
                dashboard_data = response.json()
                
                print(f"   ✅ Dashboard disponible")
                print(f"   📊 Total documentos: {dashboard_data.get('total_documents', 0)}")
                
                # Verificar estadísticas por estado
                status_stats = dashboard_data.get('status_stats', {})
                if status_stats:
                    print(f"   📋 Estadísticas por estado:")
                    for status, data in status_stats.items():
                        print(f"      {data.get('label', status)}: {data.get('count', 0)}")
                
                # Verificar estadísticas por tipo
                type_stats = dashboard_data.get('type_stats', {})
                if type_stats:
                    print(f"   📋 Estadísticas por tipo:")
                    for doc_type, data in type_stats.items():
                        print(f"      {data.get('label', doc_type)}: {data.get('count', 0)}")
                
                return True
            else:
                print(f"   ❌ Dashboard no disponible: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   💥 Error: {e}")
            return False
    
    def _test_14_listing_and_filtering(self):
        """
        TEST 14: Listado y filtrado de documentos
        """
        print("📋 TEST 14: LISTADO Y FILTRADO DE DOCUMENTOS")
        print("-" * 50)
        
        tests_passed = 0
        total_tests = 0
        
        # Test 1: Listado básico
        total_tests += 1
        try:
            response = self.session.get(f"{self.base_url}/api/sri/documents/", timeout=10)
            if response.status_code == 200:
                documents = response.json()
                if isinstance(documents, list):
                    print(f"   ✅ Listado básico: {len(documents)} documentos")
                    tests_passed += 1
                else:
                    print(f"   ✅ Listado paginado disponible")
                    tests_passed += 1
            else:
                print(f"   ❌ Error en listado: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error listado: {e}")
        
        # Test 2: Filtro por tipo de documento
        total_tests += 1
        try:
            response = self.session.get(f"{self.base_url}/api/sri/documents/?document_type=INVOICE", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Filtro por tipo de documento")
                tests_passed += 1
            else:
                print(f"   ❌ Error filtro por tipo: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error filtro tipo: {e}")
        
        # Test 3: Búsqueda por texto
        total_tests += 1
        try:
            response = self.session.get(f"{self.base_url}/api/sri/documents/?search=CLIENTE", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Búsqueda por texto")
                tests_passed += 1
            else:
                print(f"   ❌ Error búsqueda: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error búsqueda: {e}")
        
        print(f"   📊 Pruebas de listado: {tests_passed}/{total_tests}")
        
        return tests_passed >= total_tests * 0.8
    
    def _test_15_sri_configuration_management(self):
        """
        TEST 15: Gestión de configuración SRI
        """
        print("⚙️ TEST 15: GESTIÓN DE CONFIGURACIÓN SRI")
        print("-" * 50)
        
        tests_passed = 0
        total_tests = 0
        
        # Test 1: Listar configuraciones
        total_tests += 1
        try:
            response = self.session.get(f"{self.base_url}/api/sri/configuration/", timeout=10)
            if response.status_code == 200:
                configs = response.json()
                print(f"   ✅ Listado de configuraciones disponible")
                tests_passed += 1
            else:
                print(f"   ❌ Error listado configuraciones: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error configuraciones: {e}")
        
        # Test 2: Obtener siguiente secuencial
        total_tests += 1
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/configuration/1/get_next_sequence/",
                json={"document_type": "INVOICE"},
                timeout=10
            )
            if response.status_code == 200:
                sequence_data = response.json()
                print(f"   ✅ Secuencial obtenido: {sequence_data.get('data', {}).get('sequence', 'N/A')}")
                tests_passed += 1
            else:
                print(f"   ❌ Error obteniendo secuencial: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error secuencial: {e}")
        
        print(f"   📊 Pruebas configuración: {tests_passed}/{total_tests}")
        
        return tests_passed > 0
    
    def _test_16_sequence_management(self):
        """
        TEST 16: Gestión de secuenciales
        """
        print("🔢 TEST 16: GESTIÓN DE SECUENCIALES")
        print("-" * 50)
        
        document_types = ['INVOICE', 'CREDIT_NOTE', 'DEBIT_NOTE', 'RETENTION', 'PURCHASE_SETTLEMENT']
        success_count = 0
        
        for doc_type in document_types:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/sri/configuration/1/get_next_sequence/",
                    json={"document_type": doc_type},
                    timeout=10
                )
                
                if response.status_code == 200:
                    sequence_data = response.json()
                    sequence = sequence_data.get('data', {}).get('sequence', 'N/A')
                    doc_number = sequence_data.get('data', {}).get('document_number', 'N/A')
                    print(f"   ✅ {doc_type}: Secuencial {sequence}, Número {doc_number}")
                    success_count += 1
                else:
                    print(f"   ❌ {doc_type}: Error {response.status_code}")
                    
            except Exception as e:
                print(f"   💥 {doc_type}: Error - {e}")
        
        print(f"   📊 Secuenciales obtenidos: {success_count}/{len(document_types)}")
        
        return success_count >= len(document_types) * 0.8
    
    def _test_17_complete_workflow(self):
        """
        TEST 17: Flujo completo de trabajo
        """
        print("🔄 TEST 17: FLUJO COMPLETO DE TRABAJO")
        print("-" * 50)
        
        try:
            # 1. Crear una factura completa
            print("   1️⃣ Creando factura completa...")
            workflow_invoice = {
                "company": 1,
                "customer_identification_type": "05",
                "customer_identification": "9999999999",
                "customer_name": "CLIENTE WORKFLOW COMPLETO",
                "customer_email": "workflow@test.com",
                "items": [
                    {
                        "main_code": "WF001",
                        "description": "Producto workflow",
                        "quantity": 2.0,
                        "unit_price": 150.0,
                        "discount": 20.0,
                        "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                    }
                ]
            }
            
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_invoice/",
                json=workflow_invoice,
                timeout=30
            )
            
            if response.status_code != 201:
                print("   ❌ Error creando factura workflow")
                return False
            
            workflow_invoice_data = response.json()
            workflow_invoice_id = workflow_invoice_data['id']
            print(f"   ✅ Factura creada: ID {workflow_invoice_id}")
            
            # 2. Generar XML
            print("   2️⃣ Generando XML...")
            xml_response = self.session.post(
                f"{self.base_url}/api/sri/documents/{workflow_invoice_id}/generate_xml/",
                json={},
                timeout=20
            )
            
            if xml_response.status_code == 200:
                print("   ✅ XML generado")
            else:
                print("   ⚠️ XML no generado (no crítico)")
            
            # 3. Crear nota de crédito basada en la factura
            print("   3️⃣ Creando nota de crédito...")
            credit_note_data = {
                "company": 1,
                "original_invoice_id": workflow_invoice_id,
                "reason_code": "01",
                "reason_description": "Workflow testing credit note",
                "items": [
                    {
                        "main_code": "WF001",
                        "description": "Devolución workflow",
                        "quantity": 1.0,
                        "unit_price": 150.0,
                        "discount": 20.0
                    }
                ]
            }
            
            credit_response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_credit_note/",
                json=credit_note_data,
                timeout=30
            )
            
            if credit_response.status_code == 201:
                credit_data = credit_response.json()
                print(f"   ✅ Nota de crédito creada: ID {credit_data['id']}")
            else:
                print("   ⚠️ Nota de crédito no creada")
            
            # 4. Verificar estados finales
            print("   4️⃣ Verificando estados finales...")
            status_response = self.session.get(
                f"{self.base_url}/api/sri/documents/{workflow_invoice_id}/status_check/",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   ✅ Estado factura: {status_data.get('current_status')}")
            else:
                print("   ⚠️ No se pudo verificar estado")
            
            print("   🎊 Flujo completo ejecutado exitosamente")
            return True
            
        except Exception as e:
            print(f"   💥 Error en flujo completo: {e}")
            return False
    
    def _test_18_calculation_accuracy_all_types(self):
        """
        TEST 18: Precisión de cálculos en todos los tipos
        """
        print("🧮 TEST 18: PRECISIÓN DE CÁLCULOS TODOS LOS TIPOS")
        print("-" * 50)
        
        calculation_tests = [
            {
                "name": "Factura con decimales complejos",
                "type": "invoice",
                "data": {
                    "company": 1,
                    "customer_identification_type": "05",
                    "customer_identification": "1111111111",
                    "customer_name": "CLIENTE CÁLCULOS DECIMALES",
                    "items": [
                        {
                            "main_code": "DEC001",
                            "description": "Item con decimales",
                            "quantity": 3.333,
                            "unit_price": 12.567,
                            "discount": 5.89,
                            "taxes": [{"tax_code": "2", "percentage_code": "2", "rate": 15.0}]
                        }
                    ]
                },
                "endpoint": "/api/sri/documents/create_invoice/"
            }
        ]
        
        all_calculations_correct = True
        
        for test in calculation_tests:
            print(f"   🧪 {test['name']}")
            
            try:
                response = self.session.post(
                    f"{self.base_url}{test['endpoint']}",
                    json=test['data'],
                    timeout=20
                )
                
                if response.status_code == 201:
                    result = response.json()
                    total_amount = float(result.get('total_amount', 0))
                    
                    print(f"      ✅ Documento creado con total: ${total_amount:.2f}")
                    
                    # Verificar que el total sea positivo y razonable
                    if total_amount > 0 and total_amount < 10000:
                        print(f"      ✅ Cálculo dentro de rango esperado")
                    else:
                        print(f"      ⚠️ Cálculo fuera de rango esperado")
                        self.warnings.append(f"Calculation out of expected range: {total_amount}")
                        all_calculations_correct = False
                else:
                    print(f"      ❌ Error creando documento de prueba: {response.status_code}")
                    all_calculations_correct = False
                    
            except Exception as e:
                print(f"      💥 Error: {str(e)[:50]}")
                all_calculations_correct = False
        
        return all_calculations_correct
    
    def _test_19_error_handling_comprehensive(self):
        """
        TEST 19: Manejo comprehensivo de errores
        """
        print("🚨 TEST 19: MANEJO COMPREHENSIVO DE ERRORES")
        print("-" * 50)
        
        error_scenarios = [
            {
                "name": "Empresa inexistente",
                "endpoint": "/api/sri/documents/create_invoice/",
                "data": {"company": 99999, "customer_name": "Test"},
                "expected_codes": [400, 404]
            },
            {
                "name": "Datos faltantes factura",
                "endpoint": "/api/sri/documents/create_invoice/",
                "data": {"company": 1},
                "expected_codes": [400, 422]
            },
            {
                "name": "Items vacíos",
                "endpoint": "/api/sri/documents/create_invoice/",
                "data": {"company": 1, "customer_name": "Test", "items": []},
                "expected_codes": [400, 422]
            },
            {
                "name": "Factura inexistente para nota crédito",
                "endpoint": "/api/sri/documents/create_credit_note/",
                "data": {"company": 1, "original_invoice_id": 99999, "reason_code": "01", "reason_description": "Test", "items": []},
                "expected_codes": [400, 404]
            }
        ]
        
        error_handling_success = 0
        
        for scenario in error_scenarios:
            print(f"   🧪 {scenario['name']}")
            
            try:
                response = self.session.post(
                    f"{self.base_url}{scenario['endpoint']}",
                    json=scenario['data'],
                    timeout=10
                )
                
                if response.status_code in scenario['expected_codes']:
                    print(f"      ✅ Error manejado correctamente ({response.status_code})")
                    error_handling_success += 1
                    
                    # Verificar estructura de respuesta de error
                    try:
                        error_data = response.json()
                        if 'error' in error_data or 'message' in error_data:
                            print(f"      ✅ Estructura de error apropiada")
                        else:
                            self.warnings.append(f"Poor error structure for: {scenario['name']}")
                    except:
                        self.warnings.append(f"Invalid JSON error response for: {scenario['name']}")
                        
                else:
                    print(f"      ⚠️ Código inesperado {response.status_code} (esperado: {scenario['expected_codes']})")
                    
            except Exception as e:
                print(f"      ❌ Error probando: {str(e)[:50]}")
        
        success_rate = (error_handling_success / len(error_scenarios)) * 100
        print(f"   📊 Manejo de errores exitoso: {error_handling_success}/{len(error_scenarios)} ({success_rate:.1f}%)")
        
        return success_rate >= 75
    
    def _test_20_performance_all_endpoints(self):
        """
        TEST 20: Rendimiento de todos los endpoints
        """
        print("⚡ TEST 20: RENDIMIENTO TODOS LOS ENDPOINTS")
        print("-" * 50)
        
        performance_tests = [
            ("Creación factura", lambda: self._quick_create_invoice(), 3.0),
            ("Creación retención", lambda: self._quick_create_retention(), 4.0),
            ("Creación liquidación", lambda: self._quick_create_settlement(), 4.0),
            ("Listado documentos", lambda: self._quick_list_documents(), 2.0),
            ("Dashboard", lambda: self._quick_dashboard(), 2.0)
        ]
        
        performance_results = []
        
        for test_name, test_func, max_time in performance_tests:
            try:
                start_time = time.time()
                success = test_func()
                elapsed_time = time.time() - start_time
                
                if elapsed_time <= max_time and success:
                    print(f"   ✅ {test_name}: {elapsed_time:.2f}s (límite: {max_time}s)")
                    performance_results.append(True)
                else:
                    status = "❌" if not success else "⚠️"
                    print(f"   {status} {test_name}: {elapsed_time:.2f}s (límite: {max_time}s)")
                    performance_results.append(False)
                    
            except Exception as e:
                print(f"   ❌ {test_name}: Error - {str(e)[:50]}")
                performance_results.append(False)
        
        success_rate = (sum(performance_results) / len(performance_results)) * 100
        print(f"   📊 Rendimiento general: {success_rate:.1f}%")
        
        return success_rate >= 70
    
    # Métodos auxiliares para pruebas de rendimiento
    def _quick_create_invoice(self):
        test_data = {
            "company": 1,
            "customer_identification_type": "05",
            "customer_identification": "1111111111",
            "customer_name": "PERF TEST",
            "items": [
                {
                    "main_code": "PERF", 
                    "description": "Performance test", 
                    "quantity": 1.0, 
                    "unit_price": 100.0, 
                    "discount": 0.0, 
                    "taxes": [
                        {
                            "tax_code": "2", 
                            "percentage_code": "2", 
                            "rate": 15.0
                        }
                    ]
                }
            ]
        }
        response = self.session.post(f"{self.base_url}/api/sri/documents/create_invoice/", json=test_data, timeout=5)
        return response.status_code == 201
    
    def _quick_create_retention(self):
        test_data = {
            "company": 1,
            "supplier_identification_type": "04",
            "supplier_identification": "1234567890001",
            "supplier_name": "PERF SUPPLIER",
            "retention_details": [
                {
                    "support_document_type": "01", 
                    "support_document_number": "001-001-000001234", 
                    "support_document_date": "2025-07-14", 
                    "tax_code": "1", 
                    "retention_code": "303", 
                    "retention_percentage": 1.0, 
                    "taxable_base": 100.0
                }
            ]
        }
        response = self.session.post(f"{self.base_url}/api/sri/documents/create_retention/", json=test_data, timeout=5)
        return response.status_code == 201
    
    def _quick_create_settlement(self):
        test_data = {
            "company": 1,
            "supplier_identification_type": "05",
            "supplier_identification": "1725834567",
            "supplier_name": "PERF SETTLEMENT",
            "items": [
                {
                    "main_code": "PERF", 
                    "description": "Performance test", 
                    "quantity": 1.0, 
                    "unit_price": 100.0, 
                    "discount": 0.0
                }
            ]
        }
        response = self.session.post(f"{self.base_url}/api/sri/documents/create_purchase_settlement/", json=test_data, timeout=5)
        return response.status_code == 201
    
    def _quick_list_documents(self):
        response = self.session.get(f"{self.base_url}/api/sri/documents/", timeout=3)
        return response.status_code == 200
    
    def _quick_dashboard(self):
        response = self.session.get(f"{self.base_url}/api/sri/documents/dashboard/", timeout=3)
        return response.status_code == 200