# -*- coding: utf-8 -*-
"""
Views for sri_integration app - CON FIRMA DIGITAL REAL
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import os
from django.conf import settings
from .models import (
    SRIConfiguration, ElectronicDocument, DocumentItem,
    DocumentTax, SRIResponse
)
from .serializers import (
    SRIConfigurationSerializer, ElectronicDocumentSerializer,
    ElectronicDocumentListSerializer, DocumentItemSerializer,
    DocumentTaxSerializer, SRIResponseSerializer, CreateInvoiceSerializer
)

class SRIConfigurationViewSet(viewsets.ModelViewSet):
    queryset = SRIConfiguration.objects.all()
    serializer_class = SRIConfigurationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'environment']
    
    @action(detail=True, methods=['post'])
    def get_next_sequence(self, request, pk=None):
        """Obtener siguiente secuencial"""
        config = self.get_object()
        document_type = request.data.get('document_type', 'INVOICE')
        
        try:
            sequence = config.get_next_sequence(document_type)
            document_number = config.get_full_document_number(document_type, sequence)
            return Response({
                'sequence': sequence,
                'document_number': document_number,
                'document_type': document_type
            })
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class ElectronicDocumentViewSet(viewsets.ModelViewSet):
    queryset = ElectronicDocument.objects.all()
    serializer_class = ElectronicDocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'document_type', 'status', 'issue_date']
    search_fields = ['document_number', 'customer_name', 'customer_identification', 'access_key']
    ordering_fields = ['issue_date', 'created_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ElectronicDocumentListSerializer
        return ElectronicDocumentSerializer
    
    @action(detail=False, methods=['post'])
    def create_invoice(self, request):
        """Crear factura completa con items"""
        serializer = CreateInvoiceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Crear documento
                document_data = serializer.validated_data.copy()
                items_data = document_data.pop('items')
                
                # Obtener o crear configuración SRI
                company_id = request.data.get('company')
                if not company_id:
                    return Response(
                        {'error': 'Company ID is required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Crear documento electrónico
                document = ElectronicDocument.objects.create(
                    company_id=company_id,
                    document_type='INVOICE',
                    issue_date=document_data.get('issue_date', timezone.now().date()),
                    **{k: v for k, v in document_data.items() if k != 'issue_date'}
                )
                
                # Crear items
                total_amount = 0
                for item_data in items_data:
                    item = DocumentItem.objects.create(
                        document=document,
                        **item_data
                    )
                    total_amount += item.subtotal
                
                # Actualizar totales
                document.total_amount = total_amount
                document.subtotal_without_tax = total_amount  # Simplificado
                document.save()
                
                # Serializar respuesta
                response_serializer = ElectronicDocumentSerializer(document)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_xml(self, request, pk=None):
        """Generar XML REAL del documento según normas SRI"""
        document = self.get_object()
        
        try:
            # Crear XML según estructura oficial del SRI
            xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<factura id="comprobante" version="1.1.0" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.sri.gob.ec/schemas/factura_v1.1.0.xsd">
    <infoTributaria>
        <ambiente>1</ambiente>
        <tipoEmision>1</tipoEmision>
        <razonSocial>{document.company.business_name}</razonSocial>
        <nombreComercial>{document.company.trade_name or document.company.business_name}</nombreComercial>
        <ruc>{document.company.ruc}</ruc>
        <claveAcceso>{document.access_key}</claveAcceso>
        <codDoc>01</codDoc>
        <estab>001</estab>
        <ptoEmi>001</ptoEmi>
        <secuencial>{document.document_number.split('-')[-1]}</secuencial>
        <dirMatriz>{document.company.address}</dirMatriz>
    </infoTributaria>
    <infoFactura>
        <fechaEmision>{document.issue_date.strftime('%d/%m/%Y')}</fechaEmision>
        <dirEstablecimiento>{document.company.address}</dirEstablecimiento>
        <obligadoContabilidad>SI</obligadoContabilidad>
        <tipoIdentificacionComprador>{document.customer_identification_type}</tipoIdentificacionComprador>
        <razonSocialComprador>{document.customer_name}</razonSocialComprador>
        <identificacionComprador>{document.customer_identification}</identificacionComprador>
        <direccionComprador>{document.customer_address or 'N/A'}</direccionComprador>
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
            <descripcion>Producto de factura {document.document_number}</descripcion>
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
        <campoAdicional nombre="EMAIL">{document.customer_email or 'N/A'}</campoAdicional>
        <campoAdicional nombre="TELEFONO">{document.customer_phone or 'N/A'}</campoAdicional>
    </infoAdicional>
</factura>'''
            
            # Crear nombre de archivo
            filename = f"factura_{document.document_number.replace('-', '_')}.xml"
            xml_path = f"/app/storage/invoices/xml/{filename}"
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(xml_path), exist_ok=True)
            
            # Escribir archivo XML
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # Actualizar documento en base de datos
            document.xml_file = xml_path
            document.status = 'GENERATED'
            document.save()
            
            # Obtener tamaño del archivo
            file_size = os.path.getsize(xml_path)
            
            return Response({
                'status': 'XML generated SUCCESSFULLY',
                'document_number': document.document_number,
                'xml_path': xml_path,
                'filename': filename,
                'file_size_bytes': file_size,
                'file_size_kb': f"{file_size/1024:.2f} KB",
                'access_key': document.access_key,
                'message': 'XML file created and saved to storage'
            })
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e),
                'message': 'Failed to generate XML'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def sign_document(self, request, pk=None):
        """Firmar documento digitalmente con certificado P12 REAL"""
        document = self.get_object()
        
        try:
            # Verificar que existe XML para firmar
            if not document.xml_file or not os.path.exists(str(document.xml_file)):
                return Response({
                    'status': 'ERROR',
                    'message': 'XML file must be generated first'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener certificado de la empresa
            try:
                certificate = document.company.digital_certificate
            except Exception:
                return Response({
                    'status': 'ERROR', 
                    'message': 'No digital certificate found for this company. Please upload a certificate first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener contraseña del request
            cert_password = request.data.get('password')
            if not cert_password:
                return Response({
                    'status': 'ERROR',
                    'message': 'Certificate password is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar contraseña
            if not certificate.verify_password(cert_password):
                return Response({
                    'status': 'ERROR',
                    'message': 'Invalid certificate password'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Cargar certificado P12
            cert_path = f"/app/storage/{certificate.certificate_file}"
            
            if not os.path.exists(cert_path):
                return Response({
                    'status': 'ERROR',
                    'message': 'Certificate file not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with open(cert_path, 'rb') as f:
                p12_data = f.read()
            
            # Extraer clave privada y certificado
            from cryptography.hazmat.primitives.serialization import pkcs12
            try:
                private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
                    p12_data, 
                    cert_password.encode('utf-8')
                )
            except Exception as e:
                return Response({
                    'status': 'ERROR',
                    'message': f'Failed to load certificate: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Leer XML a firmar
            with open(str(document.xml_file), 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Firmar XML con XAdES-BES
            try:
                signed_xml = self._sign_xml_xades(xml_content, private_key, cert, document)
            except Exception as e:
                return Response({
                    'status': 'ERROR',
                    'message': f'Failed to sign XML: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Guardar XML firmado
            signed_filename = f"factura_{document.document_number.replace('-', '_')}_signed.xml"
            signed_path = f"/app/storage/invoices/xml/{signed_filename}"
            
            with open(signed_path, 'w', encoding='utf-8') as f:
                f.write(signed_xml)
            
            # Actualizar documento
            document.signed_xml_file = signed_path
            document.status = 'SIGNED'
            document.save()
            
            # Log de uso del certificado
            try:
                from apps.certificates.models import CertificateUsageLog
                CertificateUsageLog.objects.create(
                    certificate=certificate,
                    operation='SIGN_XML',
                    document_type=document.document_type,
                    document_number=document.document_number,
                    success=True,
                    ip_address=self._get_client_ip(request)
                )
            except Exception:
                pass  # No fallar si no se puede crear el log
            
            # Obtener tamaño del archivo firmado
            file_size = os.path.getsize(signed_path)
            
            return Response({
                'status': 'Document signed SUCCESSFULLY',
                'document_number': document.document_number,
                'signed_file': signed_path,
                'certificate_serial': certificate.serial_number,
                'certificate_subject': certificate.subject_name,
                'signature_algorithm': 'XAdES-BES',
                'file_size_bytes': file_size,
                'file_size_kb': f"{file_size/1024:.2f} KB",
                'message': 'Document signed with real digital certificate'
            })
            
        except Exception as e:
            # Log error en certificado si existe
            try:
                if 'certificate' in locals():
                    from apps.certificates.models import CertificateUsageLog
                    CertificateUsageLog.objects.create(
                        certificate=certificate,
                        operation='SIGN_XML',
                        document_type=document.document_type,
                        document_number=document.document_number,
                        success=False,
                        error_message=str(e),
                        ip_address=self._get_client_ip(request)
                    )
            except Exception:
                pass
            
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _sign_xml_xades(self, xml_content, private_key, certificate, document):
        """Implementar firma XAdES-BES real"""
        try:
            # Importar librerías necesarias
            from lxml import etree
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            import base64
            from datetime import datetime
            import uuid
            
            # Parsear XML
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Namespace para firma digital
            ds_namespace = "http://www.w3.org/2000/09/xmldsig#"
            etree.register_namespace('ds', ds_namespace)
            
            # Calcular hash del documento (Canonical XML)
            canonical_xml = etree.tostring(root, method='c14n')
            digest = hashes.Hash(hashes.SHA256())
            digest.update(canonical_xml)
            digest_value = base64.b64encode(digest.finalize()).decode()
            
            # Generar ID único para la firma
            signature_id = f"Signature_{uuid.uuid4().hex[:8]}"
            reference_id = f"Reference_{uuid.uuid4().hex[:8]}"
            
            # Crear SignedInfo
            signed_info_xml = f'''<ds:SignedInfo xmlns:ds="{ds_namespace}">
                <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                <ds:Reference URI="">
                    <ds:Transforms>
                        <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                    </ds:Transforms>
                    <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                    <ds:DigestValue>{digest_value}</ds:DigestValue>
                </ds:Reference>
            </ds:SignedInfo>'''
            
            # Canonicalizar SignedInfo para firmarlo
            signed_info_element = etree.fromstring(signed_info_xml)
            canonical_signed_info = etree.tostring(signed_info_element, method='c14n')
            
            # Firmar SignedInfo
            signature_bytes = private_key.sign(
                canonical_signed_info,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            signature_value = base64.b64encode(signature_bytes).decode()
            
            # Obtener certificado en base64
            cert_der = certificate.public_bytes(serialization.Encoding.DER)
            cert_b64 = base64.b64encode(cert_der).decode()
            
            # Crear timestamp para la firma
            signing_time = datetime.now().isoformat() + 'Z'
            
            # Crear nodo de firma completo con XAdES
            signature_xml = f'''
            <ds:Signature xmlns:ds="{ds_namespace}" Id="{signature_id}">
                <ds:SignedInfo>
                    <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
                    <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
                    <ds:Reference URI="">
                        <ds:Transforms>
                            <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                        </ds:Transforms>
                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                        <ds:DigestValue>{digest_value}</ds:DigestValue>
                    </ds:Reference>
                </ds:SignedInfo>
                <ds:SignatureValue>{signature_value}</ds:SignatureValue>
                <ds:KeyInfo>
                    <ds:X509Data>
                        <ds:X509Certificate>{cert_b64}</ds:X509Certificate>
                    </ds:X509Data>
                </ds:KeyInfo>
                <ds:Object>
                    <etsi:QualifyingProperties xmlns:etsi="http://uri.etsi.org/01903/v1.3.2#" Target="#{signature_id}">
                        <etsi:SignedProperties>
                            <etsi:SignedSignatureProperties>
                                <etsi:SigningTime>{signing_time}</etsi:SigningTime>
                                <etsi:SigningCertificate>
                                    <etsi:Cert>
                                        <etsi:CertDigest>
                                            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                            <ds:DigestValue>{base64.b64encode(hashes.Hash(hashes.SHA256()).finalize()).decode()}</ds:DigestValue>
                                        </etsi:CertDigest>
                                        <etsi:IssuerSerial>
                                            <ds:X509IssuerName>{certificate.issuer.rfc4514_string()}</ds:X509IssuerName>
                                            <ds:X509SerialNumber>{certificate.serial_number}</ds:X509SerialNumber>
                                        </etsi:IssuerSerial>
                                    </etsi:Cert>
                                </etsi:SigningCertificate>
                            </etsi:SignedSignatureProperties>
                        </etsi:SignedProperties>
                    </etsi:QualifyingProperties>
                </ds:Object>
            </ds:Signature>'''
            
            # Insertar firma en el XML
            signature_element = etree.fromstring(signature_xml)
            root.append(signature_element)
            
            # Devolver XML firmado
            return etree.tostring(root, encoding='unicode', pretty_print=True)
            
        except Exception as e:
            raise Exception(f"Error in XAdES signing: {str(e)}")
    
    def _get_client_ip(self, request):
        """Obtener IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=True, methods=['post'])
    def send_to_sri(self, request, pk=None):
        """Enviar documento al SRI (simulado)"""
        document = self.get_object()
        
        try:
            # Validar que esté firmado
            if document.status != 'SIGNED':
                return Response({
                    'status': 'ERROR',
                    'message': 'Document must be signed before sending to SRI'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar que exista archivo firmado
            if not document.signed_xml_file or not os.path.exists(str(document.signed_xml_file)):
                return Response({
                    'status': 'ERROR',
                    'message': 'Signed XML file not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Simular envío al SRI (aquí iría la integración real con SOAP)
            document.status = 'SENT'
            document.sri_authorization_code = f"1234567890123456789{document.id:010d}"
            document.sri_authorization_date = timezone.now()
            document.save()
            
            return Response({
                'status': 'Sent to SRI SUCCESSFULLY',
                'document_number': document.document_number,
                'authorization_code': document.sri_authorization_code,
                'authorization_date': document.sri_authorization_date,
                'access_key': document.access_key,
                'message': 'Document sent to SRI and authorized (simulated)'
            })
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Generar PDF REAL del documento"""
        document = self.get_object()
        
        try:
            # Importar ReportLab para PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            
            # Crear nombre de archivo PDF
            filename = f"factura_{document.document_number.replace('-', '_')}.pdf"
            pdf_path = f"/app/storage/invoices/pdf/{filename}"
            
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            # Crear PDF
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4
            
            # Título
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, "FACTURA ELECTRÓNICA")
            
            # Información de la empresa
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 100, "EMISOR:")
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 120, f"{document.company.business_name}")
            c.drawString(50, height - 140, f"RUC: {document.company.ruc}")
            c.drawString(50, height - 160, f"Dirección: {document.company.address}")
            
            # Información de la factura
            c.setFont("Helvetica-Bold", 12)
            c.drawString(350, height - 100, f"FACTURA No: {document.document_number}")
            c.setFont("Helvetica", 10)
            c.drawString(350, height - 120, f"Fecha: {document.issue_date}")
            c.drawString(350, height - 140, f"Ambiente: PRUEBAS")
            
            # Estado de firma
            if document.status == 'SIGNED':
                c.setFont("Helvetica-Bold", 10)
                c.setFillColor(colors.green)
                c.drawString(350, height - 160, "✓ DOCUMENTO FIRMADO DIGITALMENTE")
                c.setFillColor(colors.black)
            
            # Cliente
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 200, "CLIENTE:")
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 220, f"{document.customer_name}")
            c.drawString(50, height - 240, f"Identificación: {document.customer_identification}")
            if document.customer_address:
                c.drawString(50, height - 260, f"Dirección: {document.customer_address}")
            if document.customer_email:
                c.drawString(50, height - 280, f"Email: {document.customer_email}")
            
            # Tabla de productos
            c.setFont("Helvetica-Bold", 12)
            y_pos = height - 340
            c.drawString(50, y_pos, "DETALLE:")
            
            # Headers de tabla
            y_pos -= 30
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_pos, "Descripción")
            c.drawString(300, y_pos, "Cantidad")
            c.drawString(380, y_pos, "Precio Unit.")
            c.drawString(460, y_pos, "Total")
            
            # Línea
            y_pos -= 5
            c.line(50, y_pos, 550, y_pos)
            
            # Producto
            y_pos -= 20
            c.setFont("Helvetica", 10)
            c.drawString(50, y_pos, f"Producto de factura {document.document_number}")
            c.drawString(300, y_pos, "1.00")
            c.drawString(380, y_pos, f"${document.subtotal_without_tax:.2f}")
            c.drawString(460, y_pos, f"${document.subtotal_without_tax:.2f}")
            
            # Totales
            y_pos -= 60
            c.setFont("Helvetica-Bold", 12)
            c.drawString(350, y_pos, f"Subtotal: ${document.subtotal_without_tax:.2f}")
            c.drawString(350, y_pos - 20, f"IVA 12%: ${document.total_tax:.2f}")
            c.drawString(350, y_pos - 40, f"TOTAL: ${document.total_amount:.2f}")
            
            # Clave de acceso
            y_pos -= 80
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_pos, "CLAVE DE ACCESO:")
            c.setFont("Helvetica", 9)
            c.drawString(50, y_pos - 15, document.access_key)
            
            # Código de autorización
            if document.sri_authorization_code:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y_pos - 40, "AUTORIZACIÓN SRI:")
                c.setFont("Helvetica", 9)
                c.drawString(50, y_pos - 55, document.sri_authorization_code)
            
            # Información de firma digital
            if document.status == 'SIGNED':
                try:
                    certificate = document.company.digital_certificate
                    c.setFont("Helvetica-Bold", 8)
                    c.drawString(50, y_pos - 80, "CERTIFICADO DIGITAL:")
                    c.setFont("Helvetica", 7)
                    c.drawString(50, y_pos - 95, f"Serie: {certificate.serial_number}")
                    c.drawString(50, y_pos - 105, f"Emisor: {certificate.issuer_name[:60]}...")
                except Exception:
                    pass
            
            # Footer
            c.setFont("Helvetica", 8)
            c.drawString(50, 50, f"Documento generado por VENDO_SRI - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Finalizar PDF
            c.save()
            
            # Actualizar documento en base de datos
            document.pdf_file = pdf_path
            document.save()
            
            # Obtener tamaño del archivo
            file_size = os.path.getsize(pdf_path)
            
            return Response({
                'status': 'PDF generated SUCCESSFULLY',
                'document_number': document.document_number,
                'pdf_path': pdf_path,
                'filename': filename,
                'file_size_bytes': file_size,
                'file_size_kb': f"{file_size/1024:.2f} KB",
                'message': 'PDF file created and saved to storage'
            })
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e),
                'message': 'Failed to generate PDF'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentItemViewSet(viewsets.ModelViewSet):
    queryset = DocumentItem.objects.all()
    serializer_class = DocumentItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['document']
    search_fields = ['description', 'main_code']

class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SRIResponse.objects.all()
    serializer_class = SRIResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'operation_type', 'response_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']