# -*- coding: utf-8 -*-
"""
Views completas para SRI integration - VERSIÓN ACTUALIZADA CON GlobalCertificateManager
apps/api/views/sri_views.py - ECOSISTEMA PERFECTO SIN PASSWORDS MANUALES
VERSION FINAL - USANDO GlobalCertificateManager para máximo rendimiento
"""

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
import logging
import os

from apps.sri_integration.models import (
    SRIConfiguration, ElectronicDocument, DocumentItem,
    DocumentTax, SRIResponse, CreditNote, DebitNote, 
    Retention, RetentionDetail, PurchaseSettlement, PurchaseSettlementItem
)
from apps.api.serializers.sri_serializers import (
    SRIConfigurationSerializer, ElectronicDocumentSerializer,
    ElectronicDocumentCreateSerializer, DocumentItemSerializer,
    DocumentTaxSerializer, SRIResponseSerializer, 
    CreateCreditNoteSerializer, CreateDebitNoteSerializer, CreateRetentionSerializer,
    CreatePurchaseSettlementSerializer, CreditNoteResponseSerializer,
    DebitNoteResponseSerializer, RetentionResponseSerializer, PurchaseSettlementResponseSerializer,
    DocumentProcessRequestSerializer, DocumentStatusSerializer
)
from apps.sri_integration.services.global_certificate_manager import get_certificate_manager

logger = logging.getLogger(__name__)


# ========== FUNCIONES AUXILIARES ==========

def sync_document_to_electronic_document(document, document_type):
    """
    Sincroniza cualquier tipo de documento con ElectronicDocument
    """
    try:
        # Verificar si ya existe ElectronicDocument
        try:
            existing = ElectronicDocument.objects.get(access_key=document.access_key)
            logger.info(f'ElectronicDocument already exists for {document_type} {document.id}')
            return existing
        except ElectronicDocument.DoesNotExist:
            pass
        
        # Mapear campos según el tipo de documento
        base_data = {
            'company': document.company,
            'document_type': document_type,
            'document_number': document.document_number,
            'access_key': document.access_key,
            'issue_date': document.issue_date,
            'status': document.status,
            'xml_file': '',
            'signed_xml_file': '',
        }
        
        # Campos específicos según el tipo
        if document_type in ['CREDIT_NOTE', 'DEBIT_NOTE']:
            base_data.update({
                'customer_identification_type': document.customer_identification_type,
                'customer_identification': document.customer_identification,
                'customer_name': document.customer_name,
                'customer_address': document.customer_address,
                'customer_email': document.customer_email,
                'subtotal_without_tax': document.subtotal_without_tax,
                'total_tax': document.total_tax,
                'total_amount': document.total_amount,
            })
        elif document_type == 'RETENTION':
            base_data.update({
                'customer_identification_type': document.supplier_identification_type,
                'customer_identification': document.supplier_identification,
                'customer_name': document.supplier_name,
                'customer_address': getattr(document, 'supplier_address', ''),
                'customer_email': '',
                'subtotal_without_tax': 0,
                'total_tax': 0,
                'total_amount': document.total_retained,
            })
        elif document_type == 'PURCHASE_SETTLEMENT':
            base_data.update({
                'customer_identification_type': document.supplier_identification_type,
                'customer_identification': document.supplier_identification,
                'customer_name': document.supplier_name,
                'customer_address': getattr(document, 'supplier_address', ''),
                'customer_email': '',
                'subtotal_without_tax': document.subtotal_without_tax,
                'total_tax': document.total_tax,
                'total_amount': document.total_amount,
            })
        
        # Crear ElectronicDocument
        electronic_doc = ElectronicDocument.objects.create(**base_data)
        
        logger.info(f'ElectronicDocument {electronic_doc.id} created for {document_type} {document.id}')
        return electronic_doc
        
    except Exception as e:
        logger.error(f'Error syncing {document_type} {document.id} to ElectronicDocument: {e}')
        return None


def find_document_by_id(pk):
    """
    Busca un documento por ID en todas las tablas posibles
    """
    document = None
    document_type = None
    electronic_doc = None
    
    # Buscar en orden de prioridad
    search_order = [
        (CreditNote, 'CREDIT_NOTE'),
        (DebitNote, 'DEBIT_NOTE'),
        (Retention, 'RETENTION'),
        (PurchaseSettlement, 'PURCHASE_SETTLEMENT'),
        (ElectronicDocument, 'INVOICE')
    ]
    
    for model, doc_type in search_order:
        try:
            document = model.objects.get(id=pk)
            document_type = doc_type
            logger.info(f'Found document {pk} as {doc_type}')
            break
        except model.DoesNotExist:
            continue
    
    if not document:
        return None, None, None
    
    # Si encontramos un documento específico, sincronizar con ElectronicDocument
    if document_type != 'INVOICE':
        electronic_doc = sync_document_to_electronic_document(document, document_type)
    else:
        electronic_doc = document
    
    return document, document_type, electronic_doc


def validate_company_certificate(company_id):
    """
    Valida que la empresa tenga certificado disponible en el GlobalCertificateManager
    """
    try:
        cert_manager = get_certificate_manager()
        cert_data = cert_manager.get_certificate(company_id)
        
        if not cert_data:
            return False, "Certificate not available in GlobalCertificateManager. Please configure certificate."
        
        is_valid, message = cert_manager.validate_certificate(company_id)
        if not is_valid:
            return False, f"Certificate validation failed: {message}"
        
        if "expires in" in message:
            logger.warning(f"Certificate warning for company {company_id}: {message}")
        
        return True, "Certificate is available and valid"
        
    except Exception as e:
        logger.error(f"Error validating certificate for company {company_id}: {str(e)}")
        return False, f"Error validating certificate: {str(e)}"


# ========== CLASE PRINCIPAL ==========

class SRIDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal para todos los documentos SRI - VERSIÓN ACTUALIZADA
    SIN REQUERIMIENTO DE PASSWORDS - Usando GlobalCertificateManager
    """
    queryset = ElectronicDocument.objects.all()
    serializer_class = ElectronicDocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'document_type', 'status', 'issue_date', 'customer_identification_type']
    search_fields = ['document_number', 'customer_name', 'customer_identification', 'access_key']
    ordering_fields = ['issue_date', 'created_at', 'total_amount', 'document_number']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]  # Para pruebas, cambiar en producción
    
    def get_queryset(self):
        """
        Filtra documentos por empresa del usuario
        """
        user = self.request.user
        
        if hasattr(user, 'is_superuser') and user.is_superuser:
            return ElectronicDocument.objects.all()
        
        # Si hay usuario autenticado, filtrar por empresas
        if hasattr(user, 'companies'):
            companies = user.companies.filter(is_active=True)
            return ElectronicDocument.objects.filter(company__in=companies)
        
        # Para pruebas sin autenticación
        return ElectronicDocument.objects.all()
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción
        """
        if self.action == 'create':
            return ElectronicDocumentCreateSerializer
        elif self.action == 'list':
            return ElectronicDocumentSerializer
        return ElectronicDocumentSerializer
    
    def handle_exception(self, exc):
        """
        Manejo centralizado de excepciones
        """
        if isinstance(exc, ValueError):
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': str(exc),
                    'code': 'INVALID_DATA'
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        elif isinstance(exc, PermissionError):
            return Response(
                {
                    'error': 'PERMISSION_DENIED',
                    'message': 'Insufficient permissions to perform this action',
                    'code': 'FORBIDDEN'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        return super().handle_exception(exc)
    
    # ========== CREACIÓN DE DOCUMENTOS ==========
    
    @action(detail=False, methods=['post'])
    def create_invoice(self, request):
        """
        Crear factura electrónica usando ElectronicDocument directamente
        """
        try:
            with transaction.atomic():
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                data = request.data
                
                # Validar campos requeridos
                required_fields = ['company', 'customer_identification_type', 'customer_identification', 
                                 'customer_name', 'issue_date', 'items']
                
                for field in required_fields:
                    if field not in data:
                        return Response(
                            {
                                'error': 'VALIDATION_ERROR',
                                'message': f'Field {field} is required',
                                'missing_field': field
                            },
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY
                        )
                
                # Verificar empresa
                try:
                    company = Company.objects.get(id=data['company'])
                except Company.DoesNotExist:
                    return Response(
                        {
                            'error': 'COMPANY_NOT_FOUND',
                            'message': f"Company with ID {data['company']} not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar certificado en GlobalCertificateManager
                cert_valid, cert_message = validate_company_certificate(company.id)
                if not cert_valid:
                    return Response(
                        {
                            'error': 'CERTIFICATE_NOT_AVAILABLE',
                            'message': cert_message,
                            'suggestion': 'Please configure digital certificate for this company'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {
                            'error': 'SRI_CONFIGURATION_MISSING',
                            'message': 'Company does not have SRI configuration'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('INVOICE')
                document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
                
                # Función para manejar decimales
                def fix_decimal(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Crear ElectronicDocument directamente (como Invoice)
                electronic_doc = ElectronicDocument.objects.create(
                    company=company,
                    document_type='INVOICE',
                    document_number=document_number,
                    issue_date=data['issue_date'],
                    customer_identification_type=data['customer_identification_type'],
                    customer_identification=data['customer_identification'],
                    customer_name=data['customer_name'],
                    customer_address=data.get('customer_address', ''),
                    customer_email=data.get('customer_email', ''),
                    customer_phone=data.get('customer_phone', ''),
                    status='DRAFT'
                )
                
                # Generar clave de acceso
                electronic_doc.access_key = electronic_doc._generate_access_key()
                
                # Crear items y calcular totales
                total_subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')
                
                items_data = data.get('items', [])
                for item_data in items_data:
                    quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
                    unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
                    discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
                    
                    subtotal = fix_decimal((quantity * unit_price) - discount, 2)
                    
                    # Crear item de documento
                    DocumentItem.objects.create(
                        document=electronic_doc,
                        main_code=item_data['main_code'],
                        auxiliary_code=item_data.get('auxiliary_code', ''),
                        description=item_data['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=discount,
                        subtotal=subtotal
                    )
                    
                    # Calcular impuesto (IVA 15%)
                    tax_amount = fix_decimal(subtotal * Decimal('15.00') / 100, 2)
                    
                    total_subtotal += subtotal
                    total_tax += tax_amount
                
                # Actualizar totales
                total_amount = total_subtotal + total_tax
                
                electronic_doc.subtotal_without_tax = fix_decimal(total_subtotal, 2)
                electronic_doc.total_tax = fix_decimal(total_tax, 2)
                electronic_doc.total_amount = fix_decimal(total_amount, 2)
                electronic_doc.status = 'GENERATED'
                electronic_doc.save()
                
                logger.info(f'🎉 Invoice ElectronicDocument {electronic_doc.id} created successfully')
                
                # Respuesta con datos de la factura
                response_data = {
                    'id': electronic_doc.id,
                    'company': electronic_doc.company.id,
                    'company_name': electronic_doc.company.business_name,
                    'document_type': electronic_doc.document_type,
                    'document_number': electronic_doc.document_number,
                    'access_key': electronic_doc.access_key,
                    'issue_date': electronic_doc.issue_date,
                    'customer_identification_type': electronic_doc.customer_identification_type,
                    'customer_identification': electronic_doc.customer_identification,
                    'customer_name': electronic_doc.customer_name,
                    'customer_address': electronic_doc.customer_address,
                    'customer_email': electronic_doc.customer_email,
                    'subtotal_without_tax': str(electronic_doc.subtotal_without_tax),
                    'total_tax': str(electronic_doc.total_tax),
                    'total_amount': str(electronic_doc.total_amount),
                    'status': electronic_doc.status,
                    'status_display': electronic_doc.get_status_display(),
                    'sri_authorization_code': electronic_doc.sri_authorization_code,
                    'sri_authorization_date': electronic_doc.sri_authorization_date,
                    'created_at': electronic_doc.created_at,
                    'updated_at': electronic_doc.updated_at,
                    'certificate_ready': True,
                    'processing_method': 'GlobalCertificateManager'
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating invoice: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_credit_note(self, request):
        """
        Crear nota de crédito con sincronización automática
        """
        serializer = CreateCreditNoteSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': 'Invalid credit note data provided',
                    'details': serializer.errors
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        try:
            with transaction.atomic():
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                validated_data = serializer.validated_data
                items_data = validated_data.pop('items', [])
                
                # Verificar empresa
                try:
                    company = Company.objects.get(id=validated_data['company'])
                except Company.DoesNotExist:
                    return Response(
                        {
                            'error': 'COMPANY_NOT_FOUND',
                            'message': f"Company with ID {validated_data['company']} not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar certificado
                cert_valid, cert_message = validate_company_certificate(company.id)
                if not cert_valid:
                    return Response(
                        {
                            'error': 'CERTIFICATE_NOT_AVAILABLE',
                            'message': cert_message
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar factura original
                try:
                    original_invoice = ElectronicDocument.objects.get(
                        id=validated_data['original_invoice_id'],
                        document_type='INVOICE'
                    )
                except ElectronicDocument.DoesNotExist:
                    return Response(
                        {
                            'error': 'ORIGINAL_INVOICE_NOT_FOUND',
                            'message': 'Original invoice not found'
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {
                            'error': 'SRI_CONFIGURATION_MISSING',
                            'message': 'Company does not have SRI configuration'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('CREDIT_NOTE')
                document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
                
                # Función para manejar decimales
                def fix_decimal(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Calcular totales
                total_subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')
                
                for item_data in items_data:
                    quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
                    unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
                    discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
                    
                    subtotal = fix_decimal((quantity * unit_price) - discount, 2)
                    tax_amount = fix_decimal(subtotal * Decimal('15.00') / 100, 2)
                    
                    total_subtotal += subtotal
                    total_tax += tax_amount
                
                # Generar clave de acceso
                temp_document = ElectronicDocument(
                    company=company,
                    document_type='CREDIT_NOTE',
                    document_number=document_number,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    customer_identification_type=original_invoice.customer_identification_type,
                    customer_identification=original_invoice.customer_identification,
                    customer_name=original_invoice.customer_name
                )
                access_key = temp_document._generate_access_key()
                
                # Crear nota de crédito
                credit_note = CreditNote.objects.create(
                    company=company,
                    original_document=original_invoice,
                    document_number=document_number,
                    access_key=access_key,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    reason_code=validated_data['reason_code'],
                    reason_description=validated_data['reason_description'],
                    customer_identification_type=original_invoice.customer_identification_type,
                    customer_identification=original_invoice.customer_identification,
                    customer_name=original_invoice.customer_name,
                    customer_address=original_invoice.customer_address,
                    customer_email=original_invoice.customer_email,
                    subtotal_without_tax=fix_decimal(total_subtotal, 2),
                    total_tax=fix_decimal(total_tax, 2),
                    total_amount=fix_decimal(total_subtotal + total_tax, 2),
                    status='GENERATED'
                )
                
                # Sincronización automática
                electronic_doc = sync_document_to_electronic_document(credit_note, 'CREDIT_NOTE')
                
                if electronic_doc:
                    logger.info(f'🎉 CreditNote {credit_note.id} synced with ElectronicDocument {electronic_doc.id}')
                
                response_serializer = CreditNoteResponseSerializer(credit_note)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating credit note: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating credit note: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_debit_note(self, request):
        """
        Crear nota de débito con sincronización automática
        """
        serializer = CreateDebitNoteSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': 'Invalid debit note data provided',
                    'details': serializer.errors
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        try:
            with transaction.atomic():
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                validated_data = serializer.validated_data
                
                # Verificar empresa
                try:
                    company = Company.objects.get(id=validated_data['company'])
                except Company.DoesNotExist:
                    return Response(
                        {
                            'error': 'COMPANY_NOT_FOUND',
                            'message': f"Company with ID {validated_data['company']} not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar certificado
                cert_valid, cert_message = validate_company_certificate(company.id)
                if not cert_valid:
                    return Response(
                        {
                            'error': 'CERTIFICATE_NOT_AVAILABLE',
                            'message': cert_message
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar factura original
                try:
                    original_invoice = ElectronicDocument.objects.get(
                        id=validated_data['original_invoice_id'],
                        document_type='INVOICE'
                    )
                except ElectronicDocument.DoesNotExist:
                    return Response(
                        {
                            'error': 'ORIGINAL_INVOICE_NOT_FOUND',
                            'message': 'Original invoice not found'
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {
                            'error': 'SRI_CONFIGURATION_MISSING',
                            'message': 'Company does not have SRI configuration'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('DEBIT_NOTE')
                document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
                
                # Función para manejar decimales
                def fix_decimal(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Calcular totales
                total_amount = fix_decimal(validated_data.get('amount', 0), 2)
                total_tax = fix_decimal(total_amount * Decimal('15.00') / 100, 2)
                
                # Generar clave de acceso
                temp_document = ElectronicDocument(
                    company=company,
                    document_type='DEBIT_NOTE',
                    document_number=document_number,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    customer_identification_type=original_invoice.customer_identification_type,
                    customer_identification=original_invoice.customer_identification,
                    customer_name=original_invoice.customer_name
                )
                access_key = temp_document._generate_access_key()
                
                # Crear nota de débito
                debit_note = DebitNote.objects.create(
                    company=company,
                    original_document=original_invoice,
                    document_number=document_number,
                    access_key=access_key,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    reason_code=validated_data['reason_code'],
                    reason_description=validated_data['reason_description'],
                    customer_identification_type=original_invoice.customer_identification_type,
                    customer_identification=original_invoice.customer_identification,
                    customer_name=original_invoice.customer_name,
                    customer_address=original_invoice.customer_address,
                    customer_email=original_invoice.customer_email,
                    subtotal_without_tax=fix_decimal(total_amount, 2),
                    total_tax=fix_decimal(total_tax, 2),
                    total_amount=fix_decimal(total_amount + total_tax, 2),
                    status='GENERATED'
                )
                
                # Sincronización
                electronic_doc = sync_document_to_electronic_document(debit_note, 'DEBIT_NOTE')
                
                if electronic_doc:
                    logger.info(f'🎉 DebitNote {debit_note.id} synced with ElectronicDocument {electronic_doc.id}')
                
                response_serializer = DebitNoteResponseSerializer(debit_note)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating debit note: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating debit note: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_retention(self, request):
        """
        Crear comprobante de retención con sincronización automática
        """
        serializer = CreateRetentionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': 'Invalid retention data provided',
                    'details': serializer.errors
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        try:
            with transaction.atomic():
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                validated_data = serializer.validated_data
                retention_details_data = validated_data.pop('retention_details', [])
                
                # Verificar empresa
                try:
                    company = Company.objects.get(id=validated_data['company'])
                except Company.DoesNotExist:
                    return Response(
                        {
                            'error': 'COMPANY_NOT_FOUND',
                            'message': f"Company with ID {validated_data['company']} not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar certificado
                cert_valid, cert_message = validate_company_certificate(company.id)
                if not cert_valid:
                    return Response(
                        {
                            'error': 'CERTIFICATE_NOT_AVAILABLE',
                            'message': cert_message
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {
                            'error': 'SRI_CONFIGURATION_MISSING',
                            'message': 'Company does not have SRI configuration'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('RETENTION')
                document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
                
                # Función para manejar decimales
                def fix_decimal(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Calcular total retenido
                total_retained = Decimal('0.00')
                for detail_data in retention_details_data:
                    taxable_base = fix_decimal(detail_data['taxable_base'], 2)
                    percentage = fix_decimal(detail_data['retention_percentage'], 2)
                    retained_amount = fix_decimal(taxable_base * percentage / 100, 2)
                    total_retained += retained_amount
                
                # Generar clave de acceso
                temp_document = ElectronicDocument(
                    company=company,
                    document_type='RETENTION',
                    document_number=document_number,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    customer_identification_type=validated_data['supplier_identification_type'],
                    customer_identification=validated_data['supplier_identification'],
                    customer_name=validated_data['supplier_name']
                )
                access_key = temp_document._generate_access_key()
                
                # Crear comprobante de retención
                retention = Retention.objects.create(
                    company=company,
                    document_number=document_number,
                    access_key=access_key,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    supplier_identification_type=validated_data['supplier_identification_type'],
                    supplier_identification=validated_data['supplier_identification'],
                    supplier_name=validated_data['supplier_name'],
                    supplier_address=validated_data.get('supplier_address', ''),
                    fiscal_period=validated_data.get('fiscal_period', timezone.now().strftime('%m/%Y')),
                    total_retained=fix_decimal(total_retained, 2),
                    status='GENERATED'
                )
                
                # Crear detalles de retención
                for detail_data in retention_details_data:
                    taxable_base = fix_decimal(detail_data['taxable_base'], 2)
                    percentage = fix_decimal(detail_data['retention_percentage'], 2)
                    retained_amount = fix_decimal(taxable_base * percentage / 100, 2)
                    
                    RetentionDetail.objects.create(
                        retention=retention,
                        support_document_type=detail_data['support_document_type'],
                        support_document_number=detail_data['support_document_number'],
                        support_document_date=detail_data['support_document_date'],
                        tax_code=detail_data['tax_code'],
                        retention_code=detail_data['retention_code'],
                        retention_percentage=percentage,
                        taxable_base=taxable_base,
                        retained_amount=retained_amount
                    )
                
                # Sincronización
                electronic_doc = sync_document_to_electronic_document(retention, 'RETENTION')
                
                if electronic_doc:
                    logger.info(f'🎉 Retention {retention.id} synced with ElectronicDocument {electronic_doc.id}')
                
                response_serializer = RetentionResponseSerializer(retention)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating retention: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating retention: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_purchase_settlement(self, request):
        """
        Crear liquidación de compra con sincronización automática
        """
        serializer = CreatePurchaseSettlementSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': 'Invalid purchase settlement data provided',
                    'details': serializer.errors
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        try:
            with transaction.atomic():
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                validated_data = serializer.validated_data
                items_data = validated_data.pop('items', [])
                
                # Verificar empresa
                try:
                    company = Company.objects.get(id=validated_data['company'])
                except Company.DoesNotExist:
                    return Response(
                        {
                            'error': 'COMPANY_NOT_FOUND',
                            'message': f"Company with ID {validated_data['company']} not found"
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Verificar certificado
                cert_valid, cert_message = validate_company_certificate(company.id)
                if not cert_valid:
                    return Response(
                        {
                            'error': 'CERTIFICATE_NOT_AVAILABLE',
                            'message': cert_message
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {
                            'error': 'SRI_CONFIGURATION_MISSING',
                            'message': 'Company does not have SRI configuration'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence('PURCHASE_SETTLEMENT')
                document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
                
                # Función para manejar decimales
                def fix_decimal(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal('0.' + '0' * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Generar clave de acceso
                temp_document = ElectronicDocument(
                    company=company,
                    document_type='PURCHASE_SETTLEMENT',
                    document_number=document_number,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    customer_identification_type=validated_data['supplier_identification_type'],
                    customer_identification=validated_data['supplier_identification'],
                    customer_name=validated_data['supplier_name']
                )
                access_key = temp_document._generate_access_key()
                
                # Crear liquidación de compra
                settlement = PurchaseSettlement.objects.create(
                    company=company,
                    document_number=document_number,
                    access_key=access_key,
                    issue_date=validated_data.get('issue_date', timezone.now().strftime('%Y-%m-%d')),
                    supplier_identification_type=validated_data['supplier_identification_type'],
                    supplier_identification=validated_data['supplier_identification'],
                    supplier_name=validated_data['supplier_name'],
                    supplier_address=validated_data.get('supplier_address', ''),
                    status='DRAFT'
                )
                
                # Crear items y calcular totales
                total_subtotal = Decimal('0.00')
                total_tax = Decimal('0.00')
                
                for item_data in items_data:
                    quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
                    unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
                    discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
                    
                    subtotal = fix_decimal((quantity * unit_price) - discount, 2)
                    
                    # Crear item de liquidación
                    PurchaseSettlementItem.objects.create(
                        settlement=settlement,
                        main_code=item_data['main_code'],
                        description=item_data['description'],
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=discount,
                        subtotal=subtotal
                    )
                    
                    # Calcular impuesto (IVA 15%)
                    tax_amount = fix_decimal(subtotal * Decimal('15.00') / 100, 2)
                    
                    total_subtotal += subtotal
                    total_tax += tax_amount
                
                # Actualizar totales
                total_amount = total_subtotal + total_tax
                
                settlement.subtotal_without_tax = fix_decimal(total_subtotal, 2)
                settlement.total_tax = fix_decimal(total_tax, 2)
                settlement.total_amount = fix_decimal(total_amount, 2)
                settlement.status = 'GENERATED'
                settlement.save()
                
                # Sincronización
                electronic_doc = sync_document_to_electronic_document(settlement, 'PURCHASE_SETTLEMENT')
                
                if electronic_doc:
                    logger.info(f'🎉 PurchaseSettlement {settlement.id} synced with ElectronicDocument {electronic_doc.id}')
                
                response_serializer = PurchaseSettlementResponseSerializer(settlement)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating purchase settlement: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating purchase settlement: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ========== PROCESAMIENTO CON GlobalCertificateManager (SIN PASSWORDS) ==========
    
    @action(detail=True, methods=['post'])
    def generate_xml(self, request, pk=None):
        """
        Generar XML del documento usando XMLGenerator REAL
        """
        logger.info(f"🚀 Generando XML para documento ID: {pk}")
        
        # Buscar documento en todas las tablas
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar certificado disponible
        cert_valid, cert_message = validate_company_certificate(document.company.id)
        if not cert_valid:
            logger.warning(f"Certificate not ready for company {document.company.id}: {cert_message}")
            # No bloqueamos la generación de XML por el certificado
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Usar DocumentProcessor real
            processor = DocumentProcessor(document.company)
            success, result = processor._generate_xml(electronic_doc or document)
            
            if not success:
                return Response(
                    {
                        'error': 'XML_GENERATION_ERROR',
                        'message': f'Failed to generate XML: {result}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            xml_content = result
            
            # Actualizar ambos documentos
            if electronic_doc:
                electronic_doc.status = 'GENERATED'
                electronic_doc.save()
                logger.info(f'✅ ElectronicDocument {electronic_doc.id} updated with XML')
            
            document.status = 'GENERATED'
            document.save()
            logger.info(f'✅ {document_type} {document.id} status updated to GENERATED')
            
            return Response(
                {
                    'success': True,
                    'message': 'XML generated successfully using real XMLGenerator',
                    'data': {
                        'document_number': document.document_number,
                        'document_type': document_type,
                        'xml_size': len(xml_content),
                        'xml_file': str(electronic_doc.xml_file) if electronic_doc and electronic_doc.xml_file else None,
                        'access_key': document.access_key,
                        'status': document.status,
                        'ready_for_signing': cert_valid
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating XML for document {pk}: {str(e)}")
            return Response(
                {
                    'error': 'XML_GENERATION_ERROR',
                    'message': f'Failed to generate XML: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def sign_document(self, request, pk=None):
        """
        Firmar documento usando GlobalCertificateManager (SIN PASSWORD REQUERIDO)
        """
        logger.info(f"🔐 Firmando documento ID: {pk}")
        
        # Buscar documento en todas las tablas
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not electronic_doc:
            return Response(
                {
                    'error': 'SYNC_ERROR',
                    'message': 'Could not sync document for signing'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Verificar que existe XML para firmar
        if not electronic_doc.xml_file:
            return Response(
                {
                    'error': 'XML_FILE_NOT_FOUND',
                    'message': 'XML file must be generated before signing. Call generate_xml first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar certificado en GlobalCertificateManager
        cert_valid, cert_message = validate_company_certificate(document.company.id)
        if not cert_valid:
            return Response(
                {
                    'error': 'CERTIFICATE_NOT_AVAILABLE',
                    'message': cert_message,
                    'company_id': document.company.id,
                    'suggestion': 'Please configure digital certificate for this company'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Leer contenido XML existente
            with open(electronic_doc.xml_file.path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Usar DocumentProcessor ACTUALIZADO (sin password)
            processor = DocumentProcessor(document.company)
            success, result = processor._sign_xml_with_global_manager(electronic_doc, xml_content)
            
            if not success:
                return Response(
                    {
                        'error': 'SIGNING_ERROR',
                        'message': f'Failed to sign document: {result}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            signed_xml = result
            
            # Actualizar documento original también
            document.status = 'SIGNED'
            document.save()
            logger.info(f'✅ {document_type} {document.id} signed successfully using GlobalCertificateManager')
            
            # Información del certificado del gestor global
            cert_manager = get_certificate_manager()
            cert_info = cert_manager.get_company_certificate_info(document.company.id)
            
            return Response(
                {
                    'success': True,
                    'message': 'Document signed successfully with GlobalCertificateManager (NO PASSWORD REQUIRED)',
                    'data': {
                        'document_number': document.document_number,
                        'document_type': document_type,
                        'certificate_info': cert_info,
                        'signature_method': 'GlobalCertificateManager with XAdES-BES',
                        'status': electronic_doc.status,
                        'signed_xml_file': str(electronic_doc.signed_xml_file) if electronic_doc.signed_xml_file else None,
                        'processing_method': 'Automatic Certificate Management',
                        'password_required': False
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"❌ Error signing {document_type} {pk}: {str(e)}")
            return Response(
                {
                    'error': 'SIGNING_ERROR',
                    'message': f'Error during document signing: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def send_to_sri(self, request, pk=None):
        """
        Enviar documento al SRI usando SRISOAPClient REAL
        """
        logger.info(f"📤 Enviando documento ID: {pk} al SRI")
        
        # Buscar documento en todas las tablas
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not electronic_doc:
            return Response(
                {
                    'error': 'SYNC_ERROR',
                    'message': 'Could not sync document for SRI submission'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Verificar que esté firmado
        if electronic_doc.status != 'SIGNED' or not electronic_doc.signed_xml_file:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_SIGNED',
                    'message': 'Document must be signed before sending to SRI',
                    'current_status': electronic_doc.status,
                    'has_signed_file': bool(electronic_doc.signed_xml_file),
                    'suggestion': 'Call sign_document endpoint first'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Leer XML firmado
            with open(electronic_doc.signed_xml_file.path, 'r', encoding='utf-8') as f:
                signed_xml = f.read()
            
            # Usar DocumentProcessor real para envío al SRI
            processor = DocumentProcessor(document.company)
            
            # Enviar al SRI
            success, message = processor._send_to_sri(electronic_doc, signed_xml)
            
            if not success:
                return Response(
                    {
                        'error': 'SRI_SUBMISSION_ERROR',
                        'message': f'Failed to send to SRI: {message}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Consultar autorización
            auth_success, auth_message = processor._check_authorization(electronic_doc)
            
            # Actualizar documento original también
            document.status = electronic_doc.status
            document.save()
            
            logger.info(f"✅ {document_type} {pk} sent to SRI successfully")
            
            return Response(
                {
                    'success': True,
                    'message': 'Document sent to SRI successfully using real SOAP client',
                    'data': {
                        'document_number': document.document_number,
                        'document_type': document_type,
                        'sri_status': electronic_doc.status,
                        'sri_message': auth_message if auth_success else message,
                        'authorization_code': electronic_doc.sri_authorization_code,
                        'authorization_date': electronic_doc.sri_authorization_date,
                        'access_key': electronic_doc.access_key,
                        'status': electronic_doc.status,
                        'authorized': auth_success,
                        'processing_method': 'GlobalCertificateManager + Real SOAP Client'
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"❌ Error sending {document_type} {pk} to SRI: {str(e)}")
            return Response(
                {
                    'error': 'SRI_SUBMISSION_ERROR',
                    'message': f'Error sending to SRI: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def process_complete(self, request, pk=None):
        """
        Proceso completo usando DocumentProcessor ACTUALIZADO con GlobalCertificateManager
        ¡SIN REQUERIR PASSWORD!
        """
        logger.info(f"🚀 Procesamiento completo para documento ID: {pk}")
        
        # Buscar documento
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not electronic_doc:
            return Response(
                {
                    'error': 'SYNC_ERROR',
                    'message': 'Could not sync document for complete processing'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Verificar certificado en GlobalCertificateManager
        cert_valid, cert_message = validate_company_certificate(document.company.id)
        if not cert_valid:
            return Response(
                {
                    'error': 'CERTIFICATE_NOT_AVAILABLE',
                    'message': cert_message,
                    'company_id': document.company.id,
                    'suggestion': 'Please configure digital certificate for this company'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener parámetros opcionales
        send_email = request.data.get('send_email', True)
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Usar DocumentProcessor ACTUALIZADO (SIN password requerido)
            processor = DocumentProcessor(document.company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            # Actualizar documento original también
            document.status = electronic_doc.status
            document.save()
            
            if success:
                # Obtener información detallada del estado
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': 'Document processed completely using GlobalCertificateManager with real SRI integration',
                        'password_required': False,
                        'processing_method': 'GlobalCertificateManager',
                        'steps_completed': [
                            'CERTIFICATE_LOADED_FROM_CACHE',
                            'XML_GENERATED',
                            'DOCUMENT_SIGNED_AUTOMATICALLY', 
                            'SENT_TO_SRI',
                            'AUTHORIZATION_CHECKED'
                        ],
                        'data': {
                            'document_id': pk,
                            'document_type': document_type,
                            'final_status': electronic_doc.status,
                            'status_info': status_info,
                            'has_xml': bool(electronic_doc.xml_file),
                            'has_signed_xml': bool(electronic_doc.signed_xml_file),
                            'has_pdf': bool(electronic_doc.pdf_file),
                            'email_sent': electronic_doc.email_sent,
                            'authorization_code': electronic_doc.sri_authorization_code,
                            'authorization_date': electronic_doc.sri_authorization_date,
                            'certificate_cached': True,
                            'user_friendly': True
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'message': f'Error in complete process: {message}',
                        'data': {
                            'document_id': pk,
                            'document_type': document_type,
                            'current_status': electronic_doc.status,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            logger.error(f"❌ Error in complete process for document {pk}: {str(e)}")
            return Response(
                {
                    'error': 'PROCESS_ERROR',
                    'message': f'Error in complete process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reprocess_document(self, request, pk=None):
        """
        Reprocesar un documento que falló anteriormente usando DocumentProcessor ACTUALIZADO
        """
        logger.info(f"🔄 Reprocesando documento ID: {pk}")
        
        # Buscar documento
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not electronic_doc:
            return Response(
                {
                    'error': 'SYNC_ERROR',
                    'message': 'Could not sync document for reprocessing'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Verificar certificado
        cert_valid, cert_message = validate_company_certificate(document.company.id)
        if not cert_valid:
            return Response(
                {
                    'error': 'CERTIFICATE_NOT_AVAILABLE',
                    'message': cert_message,
                    'company_id': document.company.id
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Usar DocumentProcessor ACTUALIZADO (sin password)
            processor = DocumentProcessor(document.company)
            success, message = processor.reprocess_document(electronic_doc)
            
            # Actualizar documento original también
            document.status = electronic_doc.status
            document.save()
            
            if success:
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': 'Document reprocessed successfully using GlobalCertificateManager',
                        'password_required': False,
                        'data': {
                            'document_id': pk,
                            'document_type': document_type,
                            'final_status': electronic_doc.status,
                            'status_info': status_info,
                            'processing_method': 'GlobalCertificateManager'
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'message': f'Error reprocessing document: {message}',
                        'data': {
                            'document_id': pk,
                            'current_status': electronic_doc.status
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            logger.error(f"❌ Error reprocessing document {pk}: {str(e)}")
            return Response(
                {
                    'error': 'REPROCESS_ERROR',
                    'message': f'Error reprocessing document: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ========== GESTIÓN DEL GlobalCertificateManager ==========
    
    @action(detail=False, methods=['get'])
    def certificate_manager_status(self, request):
        """
        Estado del GlobalCertificateManager
        """
        try:
            cert_manager = get_certificate_manager()
            stats = cert_manager.get_stats()
            
            # Agregar información adicional
            stats['endpoints_info'] = {
                'password_required': False,
                'automatic_certificate_loading': True,
                'cache_enabled': True,
                'multi_company_support': True
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting certificate manager status: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def preload_certificates(self, request):
        """
        Precarga certificados en el GlobalCertificateManager
        """
        try:
            cert_manager = get_certificate_manager()
            company_ids = request.data.get('company_ids', None)
            
            result = cert_manager.preload_certificates(company_ids)
            
            return Response(
                {
                    'success': True,
                    'message': 'Certificate preloading completed',
                    'result': result
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error preloading certificates: {str(e)}")
            return Response(
                {
                    'error': 'PRELOAD_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def reload_company_certificate(self, request):
        """
        Recarga certificado de una empresa específica
        """
        try:
            company_id = request.data.get('company_id')
            
            if not company_id:
                return Response(
                    {
                        'error': 'VALIDATION_ERROR',
                        'message': 'company_id is required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cert_manager = get_certificate_manager()
            success = cert_manager.reload_certificate(company_id)
            
            if success:
                return Response(
                    {
                        'success': True,
                        'message': f'Certificate reloaded for company {company_id}'
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'message': f'Failed to reload certificate for company {company_id}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except Exception as e:
            logger.error(f"Error reloading certificate: {str(e)}")
            return Response(
                {
                    'error': 'RELOAD_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def clear_certificate_cache(self, request):
        """
        Limpia el cache de certificados
        """
        try:
            cert_manager = get_certificate_manager()
            cleared_count = cert_manager.clear_cache()
            
            return Response(
                {
                    'success': True,
                    'message': f'Certificate cache cleared: {cleared_count} certificates removed'
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error clearing certificate cache: {str(e)}")
            return Response(
                {
                    'error': 'CLEAR_CACHE_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def company_certificate_info(self, request):
        """
        Información del certificado de una empresa
        """
        try:
            company_id = request.query_params.get('company_id')
            
            if not company_id:
                return Response(
                    {
                        'error': 'VALIDATION_ERROR',
                        'message': 'company_id parameter is required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cert_manager = get_certificate_manager()
            cert_info = cert_manager.get_company_certificate_info(int(company_id))
            
            if cert_info:
                return Response(cert_info, status=status.HTTP_200_OK)
            else:
                return Response(
                    {
                        'error': 'CERTIFICATE_NOT_FOUND',
                        'message': f'Certificate not found for company {company_id}'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
        except Exception as e:
            logger.error(f"Error getting company certificate info: {str(e)}")
            return Response(
                {
                    'error': 'CERTIFICATE_INFO_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ========== MÉTODOS ADICIONALES ==========
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """
        Reenvía el documento por email
        """
        # Buscar documento en todas las tablas
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener email del cliente
        customer_email = None
        if hasattr(document, 'customer_email'):
            customer_email = document.customer_email
        elif hasattr(document, 'supplier_email'):
            customer_email = getattr(document, 'supplier_email', None)
        
        if not customer_email:
            return Response({
                'success': False,
                'message': 'Customer email not provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            success, message = processor._send_email(electronic_doc or document)
            
            logger.info(f"📧 Email sent for {document_type} {pk}")
            
            return Response({
                'success': success,
                'message': message,
                'data': {
                    'document_type': document_type,
                    'document_number': document.document_number,
                    'email': customer_email,
                    'sent_date': timezone.now() if success else None
                }
            }, status=status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"❌ Error sending email for {document_type} {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """
        Verificar estado detallado de un documento
        """
        # Buscar en todas las tablas
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            if electronic_doc:
                processor = DocumentProcessor(document.company)
                status_info = processor.get_document_status(electronic_doc)
            else:
                # Información básica si no está sincronizado
                status_info = {
                    'document_id': pk,
                    'document_type': document_type,
                    'found_in_specialized_table': True,
                    'found_in_electronic_document': False,
                    'synchronized': False,
                    'document_number': document.document_number,
                    'access_key': document.access_key,
                    'current_status': document.status,
                    'issue_date': document.issue_date,
                    'total_amount': str(getattr(document, 'total_amount', 'N/A')),
                    'created_at': document.created_at,
                    'updated_at': document.updated_at,
                    'processing_method': 'GlobalCertificateManager',
                    'password_required': False
                }
            
            # Agregar información del certificado
            cert_valid, cert_message = validate_company_certificate(document.company.id)
            status_info['certificate_status'] = {
                'available': cert_valid,
                'message': cert_message,
                'cached': cert_valid
            }
            
            return Response(status_info, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error getting document status {pk}: {str(e)}")
            return Response(
                {
                    'error': 'STATUS_CHECK_ERROR',
                    'message': f'Error checking document status: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Dashboard con estadísticas de documentos y GlobalCertificateManager
        """
        try:
            queryset = self.get_queryset()
            cert_manager = get_certificate_manager()
            
            # Estadísticas por estado
            status_stats = {}
            for choice in ElectronicDocument.STATUS_CHOICES:
                status_key = choice[0]
                count = queryset.filter(status=status_key).count()
                status_stats[status_key] = {
                    'count': count,
                    'label': choice[1]
                }
            
            # Estadísticas por tipo
            type_stats = {}
            for choice in ElectronicDocument.DOCUMENT_TYPES:
                type_key = choice[0]
                count = queryset.filter(document_type=type_key).count()
                type_stats[type_key] = {
                    'count': count,
                    'label': choice[1]
                }
            
            # Estadísticas del ecosistema
            ecosystem_stats = {
                'total_documents': queryset.count(),
                'signed_documents': queryset.filter(status='SIGNED').count(),
                'sent_to_sri': queryset.filter(status='SENT').count(),
                'authorized_documents': queryset.filter(status='AUTHORIZED').count(),
                'with_xml': queryset.exclude(xml_file='').count(),
                'with_signed_xml': queryset.exclude(signed_xml_file='').count(),
                'with_pdf': queryset.exclude(pdf_file='').count(),
                'email_sent': queryset.filter(email_sent=True).count(),
                'processing_method': 'GlobalCertificateManager',
                'password_required': False,
                'automatic_processing': True
            }
            
            # Estadísticas del gestor de certificados
            cert_stats = cert_manager.get_stats()
            
            # Documentos recientes
            recent_documents = queryset.order_by('-created_at')[:10]
            recent_serializer = ElectronicDocumentSerializer(
                recent_documents,
                many=True,
                context={'request': request}
            )
            
            return Response({
                'status_stats': status_stats,
                'type_stats': type_stats,
                'ecosystem_stats': ecosystem_stats,
                'certificate_manager_stats': cert_stats,
                'recent_documents': recent_serializer.data,
                'total_documents': queryset.count(),
                'system_info': {
                    'version': 'GlobalCertificateManager v1.0',
                    'password_required': False,
                    'multi_company_support': True,
                    'certificate_caching': True,
                    'automatic_processing': True
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error getting dashboard data: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def generate_pdf(self, request, pk=None):
        """
        Generar PDF del documento usando PDFGenerator REAL
        """
        # Buscar documento
        document, document_type, electronic_doc = find_document_by_id(pk)
        
        if not document:
            return Response(
                {
                    'error': 'DOCUMENT_NOT_FOUND',
                    'message': f'Document with ID {pk} not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not electronic_doc:
            return Response(
                {
                    'error': 'SYNC_ERROR',
                    'message': 'Could not sync document for PDF generation'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            success, message = processor._generate_pdf(electronic_doc)
            
            if success:
                return Response(
                    {
                        'success': True,
                        'message': 'PDF generated successfully using real PDFGenerator',
                        'data': {
                            'pdf_file': str(electronic_doc.pdf_file) if electronic_doc.pdf_file else None,
                            'document_number': document.document_number,
                            'document_type': document_type,
                        }
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'success': False,
                        'message': f'Failed to generate PDF: {message}'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            logger.error(f"❌ Error generating PDF for {document_type} {pk}: {str(e)}")
            return Response(
                {
                    'error': 'PDF_GENERATION_ERROR',
                    'message': f'Failed to generate PDF: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ========== VALIDACIONES Y CONFIGURACIÓN ==========
    
    @action(detail=False, methods=['post'])
    def validate_company_setup(self, request):
        """
        Valida la configuración completa de una empresa
        """
        try:
            company_id = request.data.get('company_id')
            
            if not company_id:
                return Response(
                    {
                        'error': 'VALIDATION_ERROR',
                        'message': 'company_id is required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from apps.companies.models import Company
            
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return Response(
                    {
                        'error': 'COMPANY_NOT_FOUND',
                        'message': f'Company with ID {company_id} not found'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(company)
            is_valid, validation_result = processor.validate_company_setup()
            
            # Verificar certificado en GlobalCertificateManager
            cert_valid, cert_message = validate_company_certificate(company_id)
            
            return Response(
                {
                    'company_id': company_id,
                    'company_name': company.business_name,
                    'is_valid': is_valid and cert_valid,
                    'sri_configuration': {
                        'valid': is_valid,
                        'details': validation_result
                    },
                    'certificate_manager': {
                        'valid': cert_valid,
                        'message': cert_message,
                        'method': 'GlobalCertificateManager'
                    },
                    'ready_for_processing': is_valid and cert_valid,
                    'password_required': False
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"❌ Error validating company setup: {str(e)}")
            return Response(
                {
                    'error': 'VALIDATION_ERROR',
                    'message': f'Error validating company setup: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def processing_stats(self, request):
        """
        Estadísticas de procesamiento por empresa
        """
        try:
            company_id = request.query_params.get('company_id')
            
            if company_id:
                from apps.companies.models import Company
                company = Company.objects.get(id=company_id)
                from apps.sri_integration.services.document_processor import DocumentProcessor
                
                processor = DocumentProcessor(company)
                stats = processor.get_processing_stats()
                
                return Response(stats, status=status.HTTP_200_OK)
            else:
                # Estadísticas globales
                cert_manager = get_certificate_manager()
                global_stats = cert_manager.get_stats()
                
                # Agregar estadísticas de documentos
                total_docs = ElectronicDocument.objects.count()
                authorized_docs = ElectronicDocument.objects.filter(status='AUTHORIZED').count()
                
                global_stats['global_document_stats'] = {
                    'total_documents': total_docs,
                    'authorized_documents': authorized_docs,
                    'success_rate': (authorized_docs / total_docs * 100) if total_docs > 0 else 0,
                    'processing_method': 'GlobalCertificateManager'
                }
                
                return Response(global_stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error getting processing stats: {str(e)}")
            return Response(
                {
                    'error': 'STATS_ERROR',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========== VIEWSETS ADICIONALES ==========

class SRIConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuración SRI
    """
    queryset = SRIConfiguration.objects.all()
    serializer_class = SRIConfigurationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'environment']
    permission_classes = [permissions.AllowAny]


class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para respuestas del SRI (solo lectura)
    """
    queryset = SRIResponse.objects.all()
    serializer_class = SRIResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'operation_type', 'response_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]


# ========== DOCUMENTACIÓN DE LA API ==========

class DocumentationViewSet(viewsets.ViewSet):
    """
    Documentación de la API actualizada con GlobalCertificateManager
    """
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'])
    def api_info(self, request):
        """
        Información general de la API
        """
        return Response({
            'api_name': 'SRI Integration API v2.0',
            'description': 'API completa para integración con SRI Ecuador',
            'version': '2.0.0',
            'certificate_manager': 'GlobalCertificateManager',
            'password_required': False,
            'features': [
                'Automatic certificate management',
                'Multi-company support',
                'Certificate caching',
                'Real-time SRI integration',
                'Automatic document processing',
                'PDF generation',
                'Email notifications'
            ],
            'endpoints': {
                'document_creation': [
                    'POST /api/sri/documents/create_invoice/',
                    'POST /api/sri/documents/create_credit_note/',
                    'POST /api/sri/documents/create_debit_note/',
                    'POST /api/sri/documents/create_retention/',
                    'POST /api/sri/documents/create_purchase_settlement/'
                ],
                'document_processing': [
                    'POST /api/sri/documents/{id}/generate_xml/',
                    'POST /api/sri/documents/{id}/sign_document/',
                    'POST /api/sri/documents/{id}/send_to_sri/',
                    'POST /api/sri/documents/{id}/process_complete/',
                    'POST /api/sri/documents/{id}/reprocess_document/'
                ],
                'certificate_management': [
                    'GET /api/sri/documents/certificate_manager_status/',
                    'POST /api/sri/documents/preload_certificates/',
                    'POST /api/sri/documents/reload_company_certificate/',
                    'POST /api/sri/documents/clear_certificate_cache/',
                    'GET /api/sri/documents/company_certificate_info/'
                ],
                'utilities': [
                    'GET /api/sri/documents/{id}/status_check/',
                    'GET /api/sri/documents/dashboard/',
                    'GET /api/sri/documents/{id}/generate_pdf/',
                    'POST /api/sri/documents/{id}/send_email/',
                    'POST /api/sri/documents/validate_company_setup/',
                    'GET /api/sri/documents/processing_stats/'
                ]
            },
            'migration_notes': {
                'breaking_changes': [
                    'certificate_password parameter is now optional',
                    'Automatic certificate loading from GlobalCertificateManager',
                    'process_complete endpoint no longer requires password'
                ],
                'improvements': [
                    'Faster processing with certificate caching',
                    'Better error handling and validation',
                    'Multi-company certificate management',
                    'Real-time certificate status monitoring'
                ]
            }
        })


# ========== FUNCIONES AUXILIARES ADICIONALES ==========

def calculate_document_totals(items_data):
    """
    Calcula totales de documento de forma segura
    """
    from decimal import Decimal, ROUND_HALF_UP
    
    def fix_decimal(value, places=2):
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        quantizer = Decimal('0.' + '0' * places)
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    total_subtotal = Decimal('0.00')
    total_tax = Decimal('0.00')
    
    for item_data in items_data:
        quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
        unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
        discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
        
        subtotal = fix_decimal((quantity * unit_price) - discount, 2)
        tax_amount = fix_decimal(subtotal * Decimal('15.00') / 100, 2)
        
        total_subtotal += subtotal
        total_tax += tax_amount
    
    return {
        'subtotal_without_tax': fix_decimal(total_subtotal, 2),
        'total_tax': fix_decimal(total_tax, 2),
        'total_amount': fix_decimal(total_subtotal + total_tax, 2)
    }


def validate_company_sri_config(company):
    """
    Valida que la empresa tenga configuración SRI válida
    """
    try:
        sri_config = company.sri_configuration
        
        # Validaciones básicas
        if not sri_config.is_active:
            return False, "SRI configuration is not active"
        
        if not sri_config.establishment_code:
            return False, "Establishment code not configured"
        
        if not sri_config.emission_point:
            return False, "Emission point not configured"
        
        return True, "Configuration is valid"
        
    except Exception as e:
        return False, f"Error validating SRI configuration: {str(e)}"


def generate_document_number(company, document_type):
    """
    Genera número de documento de forma segura
    """
    try:
        sri_config = company.sri_configuration
        sequence = sri_config.get_next_sequence(document_type)
        return f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
    except Exception as e:
        logger.error(f"Error generating document number: {e}")
        # Fallback con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"001-001-{timestamp[-9:]}"


def process_document_items(document, items_data, item_model):
    """
    Procesa los items de un documento de forma genérica
    """
    from decimal import Decimal, ROUND_HALF_UP
    
    def fix_decimal(value, places=2):
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        quantizer = Decimal('0.' + '0' * places)
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    created_items = []
    
    for item_data in items_data:
        quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
        unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
        discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
        subtotal = fix_decimal((quantity * unit_price) - discount, 2)
        
        # Campos específicos según el modelo
        if item_model == PurchaseSettlementItem:
            item = PurchaseSettlementItem.objects.create(
                settlement=document,
                main_code=item_data['main_code'],
                description=item_data['description'],
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                subtotal=subtotal
            )
        else:
            # Para DocumentItem genérico
            item = DocumentItem.objects.create(
                document=document,
                main_code=item_data['main_code'],
                description=item_data['description'],
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                subtotal=subtotal
            )
        
        created_items.append(item)
    
    return created_items


def log_document_creation(document, document_type, user=None):
    """
    Log de creación de documentos para auditoría
    """
    logger.info(f"""
    ========== DOCUMENT CREATION LOG ==========
    Document Type: {document_type}
    Document ID: {document.id}
    Document Number: {document.document_number}
    Access Key: {document.access_key}
    Company: {document.company.business_name}
    User: {user.username if user else 'System'}
    Created At: {timezone.now()}
    Status: {document.status}
    Processing Method: GlobalCertificateManager
    Password Required: False
    ==========================================
    """)


def handle_document_error(document, error_message, document_type):
    """
    Manejo centralizado de errores de documentos
    """
    logger.error(f"❌ Error in {document_type} {document.id}: {error_message}")
    
    # Actualizar estado del documento
    document.status = 'ERROR'
    document.save()
    
    # Si existe documento electrónico sincronizado, también actualizarlo
    try:
        electronic_doc = ElectronicDocument.objects.get(access_key=document.access_key)
        electronic_doc.status = 'ERROR'
        electronic_doc.save()
    except ElectronicDocument.DoesNotExist:
        pass
    
    return {
        'error': 'DOCUMENT_ERROR',
        'message': error_message,
        'document_id': document.id,
        'document_type': document_type,
        'processing_method': 'GlobalCertificateManager'
    }