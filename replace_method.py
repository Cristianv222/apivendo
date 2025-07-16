import requests
import json

print('🔄 PROBANDO NOTA DE DÉBITO...')

data = {
    'company': 1,
    'original_invoice_id': 10,
    'reason_code': '01',
    'reason_description': 'Intereses por mora - Prueba automática',
    'amount': 25.00
}

response = requests.post(
    'http://localhost:8000/api/sri/documents/create_debit_note/',
    headers={'Content-Type': 'application/json'},
    json=data,
    timeout=30
)

print(f'Status: {response.status_code}')
if response.status_code == 201:
    result = response.json()
    debit_note_id = result.get('id')
    print(f'✅ Nota de débito creada: ID {debit_note_id}')
    print(f'   Número: {result.get("document_number")}')
    print(f'   Total: ${result.get("total_amount")}')

    # Probar flujo completo
    print('\n🔄 Probando flujo completo...')

    # Generar XML
    xml_response = requests.post(f'http://localhost:8000/api/sri/documents/{debit_note_id}/generate_xml/')
    print(f'📄 XML: {xml_response.status_code == 200}')

    # Firmar
    sign_response = requests.post(f'http://localhost:8000/api/sri/documents/{debit_note_id}/sign_document/')
    print(f'🔏 Firma: {sign_response.status_code == 200}')

    # Enviar al SRI
    sri_response = requests.post(f'http://localhost:8000/api/sri/documents/{debit_note_id}/send_to_sri/')
    print(f'📤 SRI: {sri_response.status_code == 200}')

    if sri_response.status_code == 200:
        print('🎉 NOTA DE DÉBITO 100% FUNCIONAL')
    else:
        print(f'❌ Error en SRI: {sri_response.text}')
else:
    print(f'❌ Error: {response.text}')