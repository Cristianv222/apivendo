import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

from apps.sri_integration.models import ElectronicDocument

print('📄 GENERANDO XML...')

document = ElectronicDocument.objects.filter(
    company_id=1,
    document_number='001-001-000000001',
    document_type='INVOICE'
).first()

if document:
    print('✅ DOCUMENTO ENCONTRADO')
    print('   ID:', document.id)
    print('   Número:', document.document_number)
    
    # Crear XML simple línea por línea
    xml_lines = [
        '<?xml version=" 1.0\
