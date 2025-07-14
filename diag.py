#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT PARA VER DETALLES DE DOCUMENTOS SRI CREADOS
Muestra información completa de notas de crédito, débito, retenciones y liquidaciones
"""

import os
import sys
import django
from datetime import datetime

# CONFIGURAR DJANGO PRIMERO (OBLIGATORIO)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

# AHORA SÍ IMPORTAR LOS MODELOS
from apps.sri_integration.models import (
    CreditNote, 
    DebitNote, 
    Retention, 
    RetentionDetail,
    PurchaseSettlement, 
    PurchaseSettlementItem,
    ElectronicDocument
)

def ver_documentos_sri():
    """Ver todos los documentos SRI creados con detalles completos"""
    
    print("🎯 DOCUMENTOS SRI CREADOS - DETALLES COMPLETOS")
    print("=" * 70)
    print(f"🕐 Consultado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # ====================================================================
    # 📝 NOTAS DE CRÉDITO
    # ====================================================================
    print("📝 NOTAS DE CRÉDITO")
    print("-" * 50)
    
    try:
        credit_notes = CreditNote.objects.all().order_by('-id')
        print(f"Total encontradas: {credit_notes.count()}")
        
        for credit in credit_notes:
            print(f"\n✅ Nota de Crédito ID: {credit.id}")
            print(f"   📋 Número: {credit.document_number}")
            print(f"   🔑 Clave de acceso: {credit.access_key}")
            print(f"   🏢 Empresa: {credit.company}")
            print(f"   📄 Documento original: {credit.original_document}")
            print(f"   📅 Fecha creación: {credit.created_at}")
            print(f"   💰 Total: ${getattr(credit, 'total_amount', 'N/A')}")
            print(f"   📝 Razón: {getattr(credit, 'reason_description', 'N/A')}")
            print(f"   🔄 Estado: {getattr(credit, 'status', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error consultando notas de crédito: {e}")
    
    # ====================================================================
    # 📈 NOTAS DE DÉBITO
    # ====================================================================
    print("\n📈 NOTAS DE DÉBITO")
    print("-" * 50)
    
    try:
        debit_notes = DebitNote.objects.all().order_by('-id')
        print(f"Total encontradas: {debit_notes.count()}")
        
        for debit in debit_notes:
            print(f"\n✅ Nota de Débito ID: {debit.id}")
            print(f"   📋 Número: {debit.document_number}")
            print(f"   🔑 Clave de acceso: {debit.access_key}")
            print(f"   🏢 Empresa: {debit.company}")
            print(f"   📄 Documento original: {debit.original_document}")
            print(f"   📅 Fecha creación: {debit.created_at}")
            print(f"   💰 Total: ${getattr(debit, 'total_amount', 'N/A')}")
            print(f"   📝 Razón: {getattr(debit, 'reason_description', 'N/A')}")
            print(f"   🔄 Estado: {getattr(debit, 'status', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error consultando notas de débito: {e}")
    
    # ====================================================================
    # 📊 RETENCIONES
    # ====================================================================
    print("\n📊 RETENCIONES")
    print("-" * 50)
    
    try:
        retentions = Retention.objects.all().order_by('-id')
        print(f"Total encontradas: {retentions.count()}")
        
        for retention in retentions:
            print(f"\n✅ Retención ID: {retention.id}")
            print(f"   📋 Número: {retention.document_number}")
            print(f"   🔑 Clave de acceso: {retention.access_key}")
            print(f"   🏢 Empresa: {retention.company}")
            print(f"   📅 Fecha emisión: {retention.issue_date}")
            print(f"   📅 Fecha creación: {retention.created_at}")
            print(f"   📊 Período fiscal: {getattr(retention, 'fiscal_period', 'N/A')}")
            print(f"   👤 Proveedor: {getattr(retention, 'supplier_name', 'N/A')}")
            print(f"   🆔 RUC/CI Proveedor: {getattr(retention, 'supplier_identification', 'N/A')}")
            print(f"   💰 Total retenido: ${getattr(retention, 'total_retained', 'N/A')}")
            print(f"   🔄 Estado: {getattr(retention, 'status', 'N/A')}")
            
            # Mostrar detalles de retención
            try:
                details = RetentionDetail.objects.filter(retention=retention)
                if details.exists():
                    print(f"   📋 Detalles de retención: {details.count()}")
                    for detail in details:
                        print(f"      📄 Doc. soporte: {detail.support_document_number}")
                        print(f"      💰 Base imponible: ${detail.taxable_base}")
                        print(f"      📊 Porcentaje: {detail.retention_percentage}%")
                        print(f"      💵 Valor retenido: ${getattr(detail, 'retained_amount', 'N/A')}")
                        print(f"      🏷️ Código retención: {detail.retention_code}")
            except Exception as e:
                print(f"      ⚠️ Error en detalles: {e}")
                
    except Exception as e:
        print(f"❌ Error consultando retenciones: {e}")
    
    # ====================================================================
    # 📋 LIQUIDACIONES DE COMPRA
    # ====================================================================
    print("\n📋 LIQUIDACIONES DE COMPRA")
    print("-" * 50)
    
    try:
        settlements = PurchaseSettlement.objects.all().order_by('-id')
        print(f"Total encontradas: {settlements.count()}")
        
        for settlement in settlements:
            print(f"\n✅ Liquidación ID: {settlement.id}")
            print(f"   📋 Número: {settlement.document_number}")
            print(f"   🔑 Clave de acceso: {settlement.access_key}")
            print(f"   🏢 Empresa: {settlement.company}")
            print(f"   📅 Fecha emisión: {settlement.issue_date}")
            print(f"   📅 Fecha creación: {settlement.created_at}")
            print(f"   👤 Proveedor: {getattr(settlement, 'supplier_name', 'N/A')}")
            print(f"   🆔 RUC/CI Proveedor: {getattr(settlement, 'supplier_identification', 'N/A')}")
            print(f"   💰 Total: ${getattr(settlement, 'total_amount', 'N/A')}")
            print(f"   🔄 Estado: {getattr(settlement, 'status', 'N/A')}")
            
            # Mostrar items de liquidación
            try:
                items = PurchaseSettlementItem.objects.filter(settlement=settlement)
                if items.exists():
                    print(f"   📦 Items: {items.count()}")
                    for item in items:
                        total_item = item.quantity * item.unit_price - getattr(item, 'discount', 0)
                        print(f"      📦 {item.description}")
                        print(f"      🔢 Cantidad: {item.quantity}")
                        print(f"      💰 Precio unit.: ${item.unit_price}")
                        print(f"      💵 Total item: ${total_item:.2f}")
            except Exception as e:
                print(f"      ⚠️ Error en items: {e}")
                
    except Exception as e:
        print(f"❌ Error consultando liquidaciones: {e}")
    
    # ====================================================================
    # 📄 RESUMEN GENERAL
    # ====================================================================
    print("\n📊 RESUMEN GENERAL DE DOCUMENTOS")
    print("-" * 50)
    
    try:
        # Contar todos los documentos electrónicos
        total_docs = ElectronicDocument.objects.count()
        recent_docs = ElectronicDocument.objects.filter(
            created_at__date=datetime.now().date()
        ).count()
        
        print(f"📄 Total documentos electrónicos: {total_docs}")
        print(f"📅 Documentos creados hoy: {recent_docs}")
        print(f"📝 Notas de crédito: {CreditNote.objects.count()}")
        print(f"📈 Notas de débito: {DebitNote.objects.count()}")
        print(f"📊 Retenciones: {Retention.objects.count()}")
        print(f"📋 Liquidaciones: {PurchaseSettlement.objects.count()}")
        
        # Últimos documentos creados
        print(f"\n🕐 ÚLTIMOS 5 DOCUMENTOS CREADOS:")
        recent = ElectronicDocument.objects.all().order_by('-id')[:5]
        for doc in recent:
            print(f"   📄 {doc.document_type} {doc.document_number} - {doc.created_at}")
            
    except Exception as e:
        print(f"❌ Error en resumen: {e}")
    
    # ====================================================================
    # 🗂️ UBICACIÓN DE ARCHIVOS
    # ====================================================================
    print("\n🗂️ UBICACIÓN DE ARCHIVOS GENERADOS")
    print("-" * 50)
    
    # Buscar directorios comunes donde se guardan archivos
    possible_dirs = [
        '/app/media/',
        '/app/static/',
        '/app/documents/',
        '/app/sri_documents/',
        '/app/temp/',
        '/app/storage/'
    ]
    
    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            try:
                files = os.listdir(dir_path)
                if files:
                    print(f"✅ {dir_path} - {len(files)} archivos")
                    # Mostrar algunos archivos XML/PDF
                    xml_files = [f for f in files if f.endswith('.xml')]
                    pdf_files = [f for f in files if f.endswith('.pdf')]
                    if xml_files:
                        print(f"   📄 Archivos XML: {len(xml_files)}")
                    if pdf_files:
                        print(f"   📑 Archivos PDF: {len(pdf_files)}")
                else:
                    print(f"📁 {dir_path} - (vacío)")
            except Exception as e:
                print(f"❌ {dir_path} - Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ CONSULTA COMPLETADA")
    print(f"🕐 Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

def ver_documento_especifico():
    """Ver detalles de documentos específicos por ID"""
    
    print("\n🎯 DOCUMENTOS ESPECÍFICOS DE LA PRUEBA:")
    print("-" * 50)
    
    # IDs específicos de la prueba
    target_docs = [
        ('Credit Note', CreditNote, 1),
        ('Debit Note', DebitNote, 1),
        ('Retention', Retention, 11),
        ('Settlement', PurchaseSettlement, 10)
    ]
    
    for doc_name, model_class, doc_id in target_docs:
        try:
            doc = model_class.objects.get(id=doc_id)
            print(f"\n🎯 {doc_name} ID {doc_id}:")
            print(f"   📋 Número: {doc.document_number}")
            print(f"   🔑 Clave: {doc.access_key}")
            print(f"   📅 Creado: {doc.created_at}")
            
        except model_class.DoesNotExist:
            print(f"\n❌ {doc_name} ID {doc_id}: No encontrado")
        except Exception as e:
            print(f"\n❌ {doc_name} ID {doc_id}: Error - {e}")

if __name__ == "__main__":
    try:
        print("🚀 INICIANDO CONSULTA DE DOCUMENTOS SRI...")
        ver_documentos_sri()
        ver_documento_especifico()
        
    except Exception as e:
        print(f"💥 Error crítico: {e}")
        sys.exit(1)