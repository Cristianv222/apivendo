# -*- coding: utf-8 -*-
"""
Views for sri_integration app - COMPLETAMENTE CORREGIDO
"""

from rest_framework import viewsets, filters, status, permissions
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
    permission_classes = [permissions.AllowAny]  # Para pruebas
    
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
    permission_classes = [permissions.AllowAny]  # Para pruebas
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ElectronicDocumentListSerializer
        return ElectronicDocumentSerializer
    
    @action(detail=False, methods=['post'])
    def create_invoice(self, request):
        """Crear factura completa con items - VERSIÓN CORREGIDA"""
        serializer = CreateInvoiceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from django.utils import timezone
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                # Obtener datos validados
                validated_data = serializer.validated_data
                items_data = validated_data.pop('items')
                
                # Obtener empresa
                company = Company.objects.get(id=validated_data['company'])
                
                # Obtener configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {'error': 'Company does not have SRI configuration'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('INVOICE')
                document_number = sri_config.get_full_document_number('INVOICE', sequence)
                
                # Crear documento electrónico
                document = ElectronicDocument.objects.create(
                    company=company,
                    document_type='INVOICE',
                    document_number=document_number,
                    issue_date=validated_data.get('issue_date', timezone.now().date()),
                    customer_identification_type=validated_data['customer_identification_type'],
                    customer_identification=validated_data['customer_identification'],
                    customer_name=validated_data['customer_name'],
                    customer_address=validated_data.get('customer_address', ''),
                    customer_email=validated_data.get('customer_email', ''),
                    customer_phone=validated_data.get('customer_phone', ''),
                    status='DRAFT'
                )
                
                # Función para redondear decimales correctamente
                def fix_decimal_places(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Crear items
                total_subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')
                
                for item_data in items_data:
                    # Convertir a Decimal y calcular subtotal
                    quantity = fix_decimal_places(Decimal(str(item_data['quantity'])), 6)
                    unit_price = fix_decimal_places(Decimal(str(item_data['unit_price'])), 6)
                    discount = fix_decimal_places(Decimal(str(item_data.get('discount', 0))), 2)
                    
                    # Calcular subtotal con redondeo correcto
                    raw_subtotal = (quantity * unit_price) - discount
                    subtotal = fix_decimal_places(raw_subtotal, 2)
                    
                    # Crear item usando método seguro
                    item = DocumentItem(
                        document=document,
                        main_code=item_data['main_code'],
                        auxiliary_code=item_data.get('auxiliary_code', ''),
                        description=item_data['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=discount,
                        subtotal=subtotal
                    )
                    
                    # Guardar usando BaseModel.save() para evitar problemas
                    from apps.core.models import BaseModel
                    BaseModel.save(item)
                    
                    # Calcular impuesto (IVA 15% por defecto)
                    tax_rate = Decimal('15.00')
                    tax_amount = fix_decimal_places(subtotal * tax_rate / 100, 2)
                    
                    # Crear impuesto
                    DocumentTax.objects.create(
                        document=document,
                        item=item,
                        tax_code='2',  # IVA
                        percentage_code='2',  # 12%
                        rate=tax_rate,
                        taxable_base=subtotal,
                        tax_amount=tax_amount
                    )
                    
                    total_subtotal += subtotal
                    total_tax += tax_amount
                
                # Actualizar totales del documento
                total_amount = total_subtotal + total_tax
                
                document.subtotal_without_tax = fix_decimal_places(total_subtotal, 2)
                document.total_tax = fix_decimal_places(total_tax, 2)
                document.total_amount = fix_decimal_places(total_amount, 2)
                document.status = 'GENERATED'
                document.save()
                
                # Serializar respuesta
                response_serializer = ElectronicDocumentSerializer(document)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': f'Error creating invoice: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_xml(self, request, pk=None):
        """Generar XML del documento según normas SRI"""
        document = self.get_object()
        
        try:
            from .services.xml_generator import XMLGenerator
            
            xml_generator = XMLGenerator(document)
            
            if document.document_type == 'INVOICE':
                xml_content = xml_generator.generate_invoice_xml()
            elif document.document_type == 'CREDIT_NOTE':
                xml_content = xml_generator.generate_credit_note_xml()
            elif document.document_type == 'DEBIT_NOTE':
                xml_content = xml_generator.generate_debit_note_xml()
            else:
                return Response({
                    'status': 'ERROR',
                    'message': f'Tipo de documento no soportado: {document.document_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Guardar XML en archivo temporal
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(xml_content)
                xml_path = f.name
            
            document.xml_file = xml_path
            document.status = 'GENERATED'
            document.save()
            
            return Response({
                'status': 'XML generated successfully',
                'document_number': document.document_number,
                'xml_size': len(xml_content),
                'xml_path': xml_path,
                'access_key': document.access_key,
                'message': 'XML generado según estructura oficial del SRI'
            })
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e),
                'message': 'Failed to generate XML'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def sign_document(self, request, pk=None):
        """Firmar documento digitalmente con certificado P12"""
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
                    'message': 'No digital certificate found for this company'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener contraseña del request
            cert_password = request.data.get('password')
            if not cert_password:
                return Response({
                    'status': 'ERROR',
                    'message': 'Certificate password is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Procesar firma usando el document processor
            from .services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            
            # Leer XML a firmar
            with open(str(document.xml_file), 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Firmar XML
            success, signed_xml = processor._sign_xml(document, xml_content, cert_password)
            
            if success:
                return Response({
                    'status': 'Document signed successfully',
                    'document_number': document.document_number,
                    'certificate_serial': certificate.serial_number,
                    'certificate_subject': certificate.subject_name,
                    'signature_algorithm': 'XAdES-BES',
                    'message': 'Document signed with digital certificate'
                })
            else:
                return Response({
                    'status': 'ERROR',
                    'message': f'Signing failed: {signed_xml}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def send_to_sri(self, request, pk=None):
        """Enviar documento al SRI"""
        document = self.get_object()
        
        try:
            # Verificar que esté firmado
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
            
            # Procesar envío usando document processor
            from .services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            
            # Leer XML firmado
            with open(str(document.signed_xml_file), 'r', encoding='utf-8') as f:
                signed_xml = f.read()
            
            # Enviar al SRI
            success, sri_result = processor._send_to_sri(document, signed_xml)
            
            if success:
                # Consultar autorización automáticamente
                auth_success, auth_result = processor._check_authorization(document, max_attempts=3)
                
                if auth_success:
                    return Response({
                        'status': 'Document authorized by SRI',
                        'document_number': document.document_number,
                        'authorization_code': document.sri_authorization_code,
                        'authorization_date': document.sri_authorization_date,
                        'access_key': document.access_key,
                        'message': 'Document sent and authorized by SRI'
                    })
                else:
                    return Response({
                        'status': 'Sent to SRI, authorization pending',
                        'document_number': document.document_number,
                        'message': f'Sent successfully, authorization: {auth_result}'
                    })
            else:
                return Response({
                    'status': 'ERROR',
                    'message': f'Failed to send to SRI: {sri_result}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Generar PDF del documento"""
        document = self.get_object()
        
        try:
            from .services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            
            # Generar PDF
            success, pdf_result = processor._generate_pdf(document)
            
            if success:
                return Response({
                    'status': 'PDF generated successfully',
                    'document_number': document.document_number,
                    'pdf_path': str(document.pdf_file),
                    'message': 'PDF file created successfully'
                })
            else:
                return Response({
                    'status': 'ERROR',
                    'message': f'PDF generation failed: {pdf_result}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def process_complete(self, request, pk=None):
        """Procesar documento completo: XML + Firma + SRI + PDF"""
        document = self.get_object()
        
        cert_password = request.data.get('password')
        if not cert_password:
            return Response({
                'status': 'ERROR',
                'message': 'Certificate password is required for complete processing'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            
            # Procesar completamente
            success, message = processor.process_document(document, cert_password, send_email=False)
            
            if success:
                return Response({
                    'status': 'Document processed completely',
                    'document_number': document.document_number,
                    'document_status': document.status,
                    'authorization_code': document.sri_authorization_code,
                    'authorization_date': document.sri_authorization_date,
                    'files_generated': {
                        'xml': bool(document.xml_file),
                        'signed_xml': bool(document.signed_xml_file),
                        'pdf': bool(document.pdf_file)
                    },
                    'message': message
                })
            else:
                return Response({
                    'status': 'ERROR',
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'status': 'ERROR',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentItemViewSet(viewsets.ModelViewSet):
    queryset = DocumentItem.objects.all()
    serializer_class = DocumentItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['document']
    search_fields = ['description', 'main_code']
    permission_classes = [permissions.AllowAny]  # Para pruebas


class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SRIResponse.objects.all()
    serializer_class = SRIResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'operation_type', 'response_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]  # Para pruebas