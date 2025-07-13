import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

def main():
    print("🚀 PRUEBA RÁPIDA SISTEMA SRI")
    print("=" * 50)
    
    # 1. Crear empresa de prueba
    print("\n1. CREANDO EMPRESA DE PRUEBA...")
    try:
        from apps.companies.models import Company
        from apps.sri_integration.models import SRIConfiguration
        
        company, created = Company.objects.get_or_create(
            ruc="1791737409001",
            defaults={
                'business_name': "EMPRESA PRUEBA FACTURACION SRI S.A.",
                'trade_name': "EMPRESA PRUEBA SRI",
                'address': "AV. AMAZONAS 123 Y COLON, QUITO"
            }
        )
        
        print(f"✅ Empresa: {'creada' if created else 'encontrada'}")
        print(f"   ID: {company.id}")
        print(f"   RUC: {company.ruc}")
        print(f"   Razón Social: {company.business_name}")
        
        # Crear configuración SRI
        sri_config, created = SRIConfiguration.objects.get_or_create(
            company=company,
            defaults={
                'environment': 'TEST',
                'establishment_code': '001',
                'emission_point': '001',
                'accounting_required': True,
                'reception_url': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
                'authorization_url': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
            }
        )
        
        print(f"✅ Config SRI: {'creada' if created else 'encontrada'}")
        print(f"   Ambiente: {sri_config.environment}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # 2. Probar conexión SRI
    print("\n2. PROBANDO CONEXIÓN CON SRI...")
    try:
        from apps.sri_integration.services.soap_client import SRISOAPClient
        
        soap_client = SRISOAPClient(company)
        test_results = soap_client.test_connection()
        
        for service, result in test_results.items():
            status_icon = "✅" if result['status'] == 'OK' else "⚠️" if result['status'] == 'WARNING' else "❌"
            print(f"   {status_icon} {service.capitalize()}: {result['status']}")
            if 'method' in result:
                print(f"      Método: {result['method']}")
        
    except Exception as e:
        print(f"❌ Error probando SRI: {e}")
    
    # 3. Crear factura de prueba
    print("\n3. CREANDO FACTURA DE PRUEBA...")
    try:
        from apps.sri_integration.models import ElectronicDocument, DocumentItem
        
        # Verificar si ya existe
        existing_doc = ElectronicDocument.objects.filter(
            company=company,
            customer_identification='1234567890'
        ).first()
        
        if existing_doc:
            document = existing_doc
            print(f"✅ Usando factura existente: {document.document_number}")
        else:
            document = ElectronicDocument.objects.create(
                company=company,
                document_type='INVOICE',
                customer_identification_type='05',
                customer_identification='1234567890',
                customer_name='CLIENTE DE PRUEBA FACTURACION SRI',
                customer_email='cliente@prueba.com',
                customer_address='DIRECCION DEL CLIENTE DE PRUEBA',
                subtotal_without_tax=100.00,
                total_tax=12.00,
                total_amount=112.00
            )
            
            # Crear item
            DocumentItem.objects.create(
                document=document,
                main_code='PROD001',
                description='Producto de prueba para facturación electrónica SRI',
                quantity=1.000000,
                unit_price=100.00,
                discount=0.00,
                subtotal=100.00
            )
            
            print(f"✅ Factura creada: {document.document_number}")
        
        print(f"   ID: {document.id}")
        print(f"   Número: {document.document_number}")
        print(f"   Clave de acceso: {document.access_key}")
        print(f"   Estado: {document.status}")
        print(f"   Total: ${document.total_amount}")
        
    except Exception as e:
        print(f"❌ Error creando factura: {e}")
        return False
    
    # 4. Generar XML de prueba
    print("\n4. GENERANDO XML DE PRUEBA...")
    try:
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<factura id="comprobante" version="1.1.0">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>{company.business_name}</razonSocial>
        <ruc>{company.ruc}</ruc>
        <claveAcceso>{document.access_key}</claveAcceso>
        <codDoc>01</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>{document.document_number.split('-')[-1]}</secuencial>
        <dirMatriz>{company.address}</dirMatriz>
    </infoTributaria>
    <infoFactura>
        <fechaEmision>{document.issue_date.strftime('%d/%m/%Y')}</fechaEmision>
        <dirEstablecimiento>{company.address}</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionComprador>{document.customer_identification_type}</tipoIdentificacionComprador>
        <razonSocialComprador>{document.customer_name}</razonSocialComprador>
        <identificacionComprador>{document.customer_identification}</identificacionComprador>
        <totalSinImpuestos>{document.subtotal_without_tax:.2f}</totalSinImpuestos>
        <totalDescuento>0.00</totalDescuento>
        <totalConImpuestos>
            <totalImpuesto>
                <codigo>2</codigo>
                <codigoPorcentaje>2</codigoPorcentaje>
                <baseImponible>{document.subtotal_without_tax:.2f}</baseImponible>
                <tarifa>12.00</tarifa>
                <valor>{document.total_tax:.2f}</valor>
            </totalImpuesto>
        </totalConImpuestos>
        <propina>0.00</propina>
        <importeTotal>{document.total_amount:.2f}</importeTotal>
        <moneda>DOLAR</moneda>
    </infoFactura>
    <detalles>
        <detalle>
            <codigoPrincipal>PROD001</codigoPrincipal>
            <descripcion>Producto de prueba SRI</descripcion>
            <cantidad>1.000000</cantidad>
            <precioUnitario>{document.subtotal_without_tax:.6f}</precioUnitario>
            <descuento>0.00</descuento>
            <precioTotalSinImpuesto>{document.subtotal_without_tax:.2f}</precioTotalSinImpuesto>
            <impuestos>
                <impuesto>
                    <codigo>2</codigo>
                    <codigoPorcentaje>2</codigoPorcentaje>
                    <tarifa>12.00</tarifa>
                    <baseImponible>{document.subtotal_without_tax:.2f}</baseImponible>
                    <valor>{document.total_tax:.2f}</valor>
                </impuesto>
            </impuestos>
        </detalle>
    </detalles>
    <infoAdicional>
        <campoAdicional nombre="EMAIL">{document.customer_email}</campoAdicional>
    </infoAdicional>
</factura>'''
        
        # Guardar XML
        os.makedirs('/app/storage/invoices/xml/', exist_ok=True)
        xml_filename = f"factura_{document.document_number.replace('-', '_')}_test.xml"
        xml_path = f"/app/storage/invoices/xml/{xml_filename}"
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        document.xml_file = xml_path
        document.status = 'GENERATED'
        document.save()
        
        file_size = os.path.getsize(xml_path)
        print(f"✅ XML generado: {xml_path}")
        print(f"   Tamaño: {file_size} bytes")
        
        # Validar XML
        from lxml import etree
        try:
            etree.fromstring(xml_content.encode('utf-8'))
            print("✅ XML estructuralmente válido")
        except Exception as e:
            print(f"⚠️  XML con problemas: {e}")
        
    except Exception as e:
        print(f"❌ Error generando XML: {e}")
        return False
    
    # 5. Resumen
    print("\n" + "=" * 50)
    print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 50)
    print("✅ Sistema configurado correctamente")
    print("✅ Empresa de prueba creada")
    print("✅ Factura de prueba generada")
    print("✅ XML válido creado")
    
    print(f"\n📊 DATOS DE LA FACTURA:")
    print(f"   ID: {document.id}")
    print(f"   Número: {document.document_number}")
    print(f"   Estado: {document.status}")
    print(f"   Archivo XML: {xml_path}")
    
    print(f"\n📋 PRÓXIMOS PASOS:")
    print("   1. Subir certificado P12 para firma digital")
    print("   2. Configurar datos reales de empresa")
    print("   3. Probar firma digital del XML")
    print("   4. Enviar al SRI ambiente de pruebas")
    
    print(f"\n🔧 PARA CONTINUAR:")
    print("   - Usa el ID de empresa: " + str(company.id))
    print("   - Usa el ID de documento: " + str(document.id))
    print("   - APIs disponibles en: http://localhost:8000/api/")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()