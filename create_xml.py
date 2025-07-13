import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

from apps.sri_integration.models import ElectronicDocument

print('📄 CREANDO XML...')

try:
    document = ElectronicDocument.objects.filter(
        company_id=1,
        document_number='001-001-000000001'
    ).first()
    
    if document:
        print(' DOCUMENTO ENCONTRADO')
        print('   ID:', document.id)
        print('   Número:', document.document_number)
        
        # Crear directorio
        os.makedirs('/app/storage/invoices/xml/', exist_ok=True)
        
        # Datos para el XML
        company_name = document.company.business_name
        company_ruc = document.company.ruc
        access_key = document.access_key
        sequence = document.document_number.split('-')[-1]
        issue_date = document.issue_date.strftime('%d/%m/%Y')
        customer_name = document.customer_name
        customer_id = document.customer_identification
        subtotal = str(document.subtotal_without_tax)
        total = str(document.total_amount)
        
        # Crear XML usando concatenación simple
        xml_lines = []
        xml_lines.append('<?xml version=" 1.0\
