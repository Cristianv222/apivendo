#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT PARA PROBAR FLUJO COMPLETO DE DOCUMENTOS SRI
Crea cada tipo de documento y ejecuta todo el flujo: Crear → XML → Firmar → Enviar SRI → PDF
"""

import os
import sys
import requests
import json
from datetime import datetime, date
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
import django
django.setup()

class SRICompleteFlowTester:
    """Probador de flujo completo SRI: Crear → XML → Firmar → Enviar → PDF"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {}
        self.created_docs = {}
        
    def test_complete_flow(self):
        """Ejecutar flujo completo para todos los tipos de documentos"""
        
        print("🚀 PRUEBA DE FLUJO COMPLETO SRI - TODOS LOS DOCUMENTOS")
        print("=" * 80)
        print(f"🕐 Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Objetivo: Probar flujo completo de cada tipo de documento")
        print()
        
        # Primero crear una factura base para notas de crédito/débito
        base_invoice_id = self._create_base_invoice()
        
        # Documentos a probar con flujo completo
        documents_to_test = [
            ("NOTA DE CRÉDITO", self._create_credit_note, base_invoice_id),
            ("NOTA DE DÉBITO", self._create_debit_note, base_invoice_id),
            ("RETENCIÓN", self._create_retention, None),
            ("LIQUIDACIÓN", self._create_settlement, None)
        ]
        
        for doc_name, create_func, extra_param in documents_to_test:
            print(f"\n{'🔸' * 80}")
            print(f"🧪 PROBANDO FLUJO COMPLETO: {doc_name}")
            print(f"{'🔸' * 80}")
            
            # PASO 1: Crear documento
            doc_id = create_func(extra_param)
            
            if doc_id:
                self.created_docs[doc_name] = doc_id
                
                # PASO 2: Ejecutar flujo completo
                flow_results = self._execute_complete_flow(doc_name, doc_id)
                self.test_results[doc_name] = flow_results
                
                # PASO 3: Mostrar resumen del documento
                self._show_document_summary(doc_name, doc_id, flow_results)
            else:
                print(f"❌ No se pudo crear {doc_name}, saltando flujo completo")
                self.test_results[doc_name] = {
                    'creation': False, 'xml': False, 'signature': False, 
                    'sri_submission': False, 'pdf': False
                }
        
        # Mostrar resumen final
        self._show_final_summary()
    
    def _create_base_invoice(self):
        """Crear factura base para notas de crédito/débito"""
        print("📄 CREANDO FACTURA BASE (para notas de crédito/débito)...")
        
        invoice_data = {
            "company": 1,
            "issue_date": date.today().strftime('%Y-%m-%d'),
            "customer_identification_type": "05",
            "customer_identification": "1234567890",
            "customer_name": "CLIENTE BASE PARA NOTAS",
            "customer_address": "Dirección Base",
            "customer_email": "base@test.com",
            "customer_phone": "0999999999",
            "items": [
                {
                    "main_code": "BASE001",
                    "auxiliary_code": "",
                    "description": "Producto base para notas",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "discount": 0.0,
                    "additional_details": {}
                }
            ],
            "additional_data": {}
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_invoice/",
                json=invoice_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                invoice_id = result.get('id')
                print(f"✅ Factura base creada: ID {invoice_id}")
                return invoice_id
            else:
                print(f"❌ Error creando factura base: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción creando factura base: {e}")
            return None
    
    def _create_credit_note(self, base_invoice_id):
        """Crear nota de crédito"""
        print("\n📝 PASO 1: CREANDO NOTA DE CRÉDITO...")
        
        if not base_invoice_id:
            print("❌ No hay factura base para nota de crédito")
            return None
        
        credit_note_data = {
            "company": 1,
            "original_invoice_id": base_invoice_id,
            "reason_code": "01",
            "reason_description": "Devolución de producto defectuoso",
            "issue_date": date.today().strftime('%Y-%m-%d'),
            "items": [
                {
                    "main_code": "DEV001",
                    "auxiliary_code": "",
                    "description": "Producto devuelto defectuoso",
                    "quantity": 1.0,
                    "unit_price": 25.0,
                    "discount": 0.0
                }
            ]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_credit_note/",
                json=credit_note_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                doc_id = result.get('id')
                print(f"✅ Nota de crédito creada: ID {doc_id}")
                print(f"   📋 Número: {result.get('document_number')}")
                print(f"   💰 Total: ${result.get('total_amount')}")
                return doc_id
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {e}")
            return None
    
    def _create_debit_note(self, base_invoice_id):
        """Crear nota de débito"""
        print("\n📈 PASO 1: CREANDO NOTA DE DÉBITO...")
        
        if not base_invoice_id:
            print("❌ No hay factura base para nota de débito")
            return None
        
        debit_note_data = {
            "company": 1,
            "original_invoice_id": base_invoice_id,
            "reason_code": "01",
            "reason_description": "Intereses por pago tardío",
            "issue_date": date.today().strftime('%Y-%m-%d'),
            "motives": [
                {
                    "reason": "Intereses de mora por pago tardío",
                    "amount": 15.0
                }
            ]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_debit_note/",
                json=debit_note_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                doc_id = result.get('id')
                print(f"✅ Nota de débito creada: ID {doc_id}")
                print(f"   📋 Número: {result.get('document_number')}")
                print(f"   💰 Total: ${result.get('total_amount')}")
                return doc_id
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {e}")
            return None
    
    def _create_retention(self, _):
        """Crear retención"""
        print("\n📊 PASO 1: CREANDO RETENCIÓN...")
        
        retention_data = {
            "company": 1,
            "supplier_identification_type": "04",
            "supplier_identification": "1234567890001",
            "supplier_name": "PROVEEDOR FLUJO COMPLETO S.A.",
            "supplier_address": "Av. Flujo Completo 123",
            "issue_date": date.today().strftime('%Y-%m-%d'),
            "fiscal_period": f"{date.today().month:02d}/{date.today().year}",
            "retention_details": [
                {
                    "support_document_type": "01",
                    "support_document_number": "001-001-000005555",
                    "support_document_date": date.today().strftime('%Y-%m-%d'),
                    "tax_code": "1",
                    "retention_code": "303",
                    "retention_percentage": 2.0,
                    "taxable_base": 500.0
                }
            ]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_retention/",
                json=retention_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                doc_id = result.get('id')
                print(f"✅ Retención creada: ID {doc_id}")
                print(f"   📋 Número: {result.get('document_number')}")
                print(f"   💰 Total retenido: ${result.get('total_retained')}")
                return doc_id
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {e}")
            return None
    
    def _create_settlement(self, _):
        """Crear liquidación de compra"""
        print("\n📋 PASO 1: CREANDO LIQUIDACIÓN...")
        
        settlement_data = {
            "company": 1,
            "supplier_identification_type": "05",
            "supplier_identification": "1725834567",
            "supplier_name": "PROVEEDOR INDIVIDUAL FLUJO",
            "supplier_address": "Calle Flujo 789",
            "issue_date": date.today().strftime('%Y-%m-%d'),
            "items": [
                {
                    "main_code": "FLUJO001",
                    "description": "Servicios de prueba completa",
                    "quantity": 2.0,
                    "unit_price": 75.0,
                    "discount": 10.0
                }
            ]
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/create_purchase_settlement/",
                json=settlement_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                doc_id = result.get('id')
                print(f"✅ Liquidación creada: ID {doc_id}")
                print(f"   📋 Número: {result.get('document_number')}")
                print(f"   💰 Total: ${result.get('total_amount')}")
                return doc_id
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {e}")
            return None
    
    def _execute_complete_flow(self, doc_name, doc_id):
        """Ejecutar flujo completo: XML → Firma → Envío SRI → PDF"""
        
        flow_results = {
            'creation': True,  # Ya se creó
            'xml': False,
            'signature': False,
            'sri_submission': False,
            'pdf': False
        }
        
        print(f"\n🔄 EJECUTANDO FLUJO COMPLETO PARA {doc_name} (ID: {doc_id})")
        print("-" * 60)
        
        # PASO 2: Generar XML
        print("📄 PASO 2: Generando XML...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/{doc_id}/generate_xml/",
                json={}, timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                xml_size = result.get('data', {}).get('xml_size', 'N/A')
                print(f"   ✅ XML generado exitosamente: {xml_size} caracteres")
                flow_results['xml'] = True
            else:
                print(f"   ❌ Error generando XML: {response.status_code}")
                print(f"   📝 Respuesta: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Excepción en XML: {e}")
        
        # PASO 3: Firmar documento
        print("\n🔐 PASO 3: Firmando con certificado digital...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/{doc_id}/sign_document/",
                json={"password": "Jheymie10"}, timeout=25
            )
            
            if response.status_code == 200:
                result = response.json()
                cert_subject = result.get('data', {}).get('certificate_subject', 'N/A')
                print(f"   ✅ Documento firmado exitosamente")
                print(f"   🏢 Certificado: {cert_subject[:80]}...")
                flow_results['signature'] = True
            else:
                print(f"   ❌ Error firmando: {response.status_code}")
                print(f"   📝 Respuesta: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Excepción en firma: {e}")
        
        # PASO 4: Enviar al SRI
        print("\n📤 PASO 4: Enviando al SRI...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/{doc_id}/send_to_sri/",
                json={}, timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result.get('message', 'N/A')
                print(f"   ✅ Enviado al SRI exitosamente")
                print(f"   📝 Respuesta SRI: {message}")
                flow_results['sri_submission'] = True
            else:
                print(f"   ⚠️ Error enviando al SRI: {response.status_code}")
                print(f"   📝 Respuesta: {response.text[:300]}")
                
        except Exception as e:
            print(f"   ❌ Excepción en envío SRI: {e}")
        
        # PASO 5: Generar PDF
        print("\n📑 PASO 5: Generando PDF...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/sri/documents/{doc_id}/generate_pdf/",
                json={}, timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                pdf_path = result.get('data', {}).get('pdf_path', 'N/A')
                print(f"   ✅ PDF generado exitosamente")
                print(f"   📁 Ruta: {pdf_path}")
                flow_results['pdf'] = True
            else:
                print(f"   ❌ Error generando PDF: {response.status_code}")
                if response.status_code == 404:
                    print(f"   📝 Endpoint PDF no implementado")
                else:
                    print(f"   📝 Respuesta: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Excepción en PDF: {e}")
        
        # PASO 6: Verificar archivos generados
        print(f"\n🔍 PASO 6: Verificando archivos generados...")
        self._verify_generated_files(doc_id)
        
        return flow_results
    
    def _verify_generated_files(self, doc_id):
        """Verificar qué archivos se generaron para el documento"""
        
        # Buscar archivos relacionados con este documento
        try:
            import subprocess
            
            # Buscar archivos XML
            xml_search = subprocess.run(
                ['docker-compose', 'exec', '-T', 'web', 'find', '/app', '-name', f'*{doc_id}*'],
                capture_output=True, text=True, timeout=10
            )
            
            if xml_search.returncode == 0 and xml_search.stdout.strip():
                files = xml_search.stdout.strip().split('\n')
                print(f"   📁 Archivos encontrados: {len(files)}")
                for file in files[:3]:  # Mostrar solo los primeros 3
                    print(f"      📄 {file}")
            else:
                print(f"   📁 No se encontraron archivos específicos para ID {doc_id}")
                
        except Exception as e:
            print(f"   ⚠️ No se pudo verificar archivos: {e}")
    
    def _show_document_summary(self, doc_name, doc_id, flow_results):
        """Mostrar resumen del flujo del documento"""
        
        total_steps = len(flow_results)
        successful_steps = sum(flow_results.values())
        success_rate = (successful_steps / total_steps) * 100
        
        print(f"\n📊 RESUMEN {doc_name} (ID: {doc_id}):")
        print("-" * 40)
        print(f"   🎯 Pasos completados: {successful_steps}/{total_steps} ({success_rate:.0f}%)")
        
        step_names = {
            'creation': 'Creación',
            'xml': 'Generación XML',
            'signature': 'Firma Digital',
            'sri_submission': 'Envío SRI',
            'pdf': 'Generación PDF'
        }
        
        for step, success in flow_results.items():
            status = "✅" if success else "❌"
            step_name = step_names.get(step, step)
            print(f"   {status} {step_name}")
        
        # Evaluación del documento
        if success_rate >= 80:
            print(f"   🟢 EXCELENTE - Flujo mayormente exitoso")
        elif success_rate >= 60:
            print(f"   🟡 BUENO - Flujo parcialmente exitoso")
        else:
            print(f"   🔴 PROBLEMÁTICO - Múltiples fallas")
    
    def _show_final_summary(self):
        """Mostrar resumen final de todas las pruebas"""
        
        print(f"\n{'🎯' * 80}")
        print("📊 RESUMEN FINAL - FLUJO COMPLETO SRI")
        print(f"{'🎯' * 80}")
        
        if not self.test_results:
            print("❌ No se ejecutaron pruebas")
            return
        
        # Calcular estadísticas generales
        total_docs = len(self.test_results)
        total_steps = sum(len(results) for results in self.test_results.values())
        successful_steps = sum(sum(results.values()) for results in self.test_results.values())
        
        overall_success_rate = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
        
        print(f"📈 ESTADÍSTICAS GENERALES:")
        print(f"   • Documentos probados: {total_docs}")
        print(f"   • Pasos totales: {total_steps}")
        print(f"   • Pasos exitosos: {successful_steps}")
        print(f"   • Tasa de éxito general: {overall_success_rate:.1f}%")
        
        print(f"\n📋 RESULTADOS POR DOCUMENTO:")
        for doc_name, flow_results in self.test_results.items():
            successful = sum(flow_results.values())
            total = len(flow_results)
            rate = (successful / total) * 100 if total > 0 else 0
            
            status_icon = "🟢" if rate >= 80 else "🟡" if rate >= 60 else "🔴"
            print(f"   {status_icon} {doc_name}: {successful}/{total} ({rate:.0f}%)")
        
        print(f"\n📋 RESULTADOS POR PROCESO:")
        # Agregar estadísticas por proceso
        process_stats = {}
        for doc_results in self.test_results.values():
            for process, success in doc_results.items():
                if process not in process_stats:
                    process_stats[process] = {'total': 0, 'successful': 0}
                process_stats[process]['total'] += 1
                if success:
                    process_stats[process]['successful'] += 1
        
        process_names = {
            'creation': 'Creación de documentos',
            'xml': 'Generación XML',
            'signature': 'Firma digital',
            'sri_submission': 'Envío al SRI',
            'pdf': 'Generación PDF'
        }
        
        for process, stats in process_stats.items():
            rate = (stats['successful'] / stats['total']) * 100 if stats['total'] > 0 else 0
            process_name = process_names.get(process, process)
            status_icon = "✅" if rate == 100 else "⚠️" if rate >= 50 else "❌"
            print(f"   {status_icon} {process_name}: {stats['successful']}/{stats['total']} ({rate:.0f}%)")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        if overall_success_rate >= 80:
            print(f"   🚀 Sistema en buen estado para producción")
            print(f"   🔧 Corregir problemas menores identificados")
        elif overall_success_rate >= 60:
            print(f"   🔧 Sistema requiere correcciones antes de producción")
            print(f"   🎯 Enfocar en problemas de envío SRI y PDF")
        else:
            print(f"   🚨 Sistema requiere trabajo significativo")
            print(f"   🔧 Revisar configuración completa")
        
        print(f"\n🕐 Prueba completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'🎯' * 80}")

def main():
    """Función principal"""
    print("🔥 INICIANDO PRUEBA DE FLUJO COMPLETO SRI")
    print("🎯 Objetivo: Verificar flujo completo de cada tipo de documento")
    print()
    
    tester = SRICompleteFlowTester()
    tester.test_complete_flow()

if __name__ == "__main__":
    main()