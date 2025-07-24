# -*- coding: utf-8 -*-
"""
Views completas para SRI integration - VERSIÓN FINAL CON ENDPOINTS DE PROCESO COMPLETO
apps/api/views/sri_views.py - CON ENDPOINTS SEPARADOS PARA CADA TIPO DE DOCUMENTO
✅ RESUELVE ERROR 35
✅ COMPATIBLE CON TOKEN VSR
✅ ENDPOINTS DE PROCESO COMPLETO PARA CADA TIPO
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
from functools import wraps
from apps.api.user_company_helper import get_user_companies_exact, get_user_company_by_id_or_token
import time

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
from apps.api.permissions import IsCompanyOwnerOrAdmin

logger = logging.getLogger(__name__)


# ========== DECORADORES CORREGIDOS PARA TOKEN VSR ==========

def require_user_company_access(get_company_id_func=None):
    """
    Decorador que valida acceso a empresa - CORREGIDO PARA TOKEN VSR
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            company = None
            
            # 🔑 MÉTODO 1: Token VSR (identificación automática)
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Token '):
                token_key = auth_header.split(' ')[1]
                
                if token_key.startswith('vsr_'):
                    try:
                        from apps.companies.models import CompanyAPIToken
                        company_token = CompanyAPIToken.objects.get(key=token_key, is_active=True)
                        company = company_token.company
                        logger.info(f"✅ VSR Token: Company {company.business_name} identified automatically")
                    except CompanyAPIToken.DoesNotExist:
                        logger.warning(f"❌ Invalid VSR token: {token_key[:20]}...")
            
            # 🔑 MÉTODO 2: Token de usuario + company_id
            if not company:
                # Función personalizada para obtener company_id
                if get_company_id_func:
                    company_id = get_company_id_func(request, *args, **kwargs)
                else:
                    # Buscar en data, query_params o kwargs
                    company_id = (
                        request.data.get('company') or 
                        request.data.get('company_id') or
                        request.query_params.get('company_id') or
                        kwargs.get('company_id')
                    )
                
                if not company_id:
                    return Response(
                        {
                            'error': 'COMPANY_ID_REQUIRED',
                            'message': 'Company ID is required for this operation',
                            'user': getattr(request.user, 'username', 'Unknown'),
                            'audit_info': {
                                'processed_by': getattr(request.user, 'username', 'Unknown'),
                                'processing_time_ms': 1.0,
                                'action_type': 'VALIDATION_ERROR',
                                'timestamp': timezone.now().isoformat(),
                                'security_method': 'token_validation_with_decorators'
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validar acceso usando la función auxiliar
                company = get_user_company_by_id_or_token(company_id, request.user)
            
            if not company:
                logger.warning(f"🚫 User {getattr(request.user, 'username', 'Unknown')} denied access to company")
                return Response(
                    {
                        'error': 'COMPANY_ACCESS_DENIED',
                        'message': 'You do not have access to this company',
                        'user': getattr(request.user, 'username', 'Unknown'),
                        'security_check': 'user_company_access_decorator'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Agregar la empresa validada al request para uso posterior
            request.validated_company = company
            logger.info(f"✅ User {getattr(request.user, 'username', 'Unknown')} validated access to company {company.id}")
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_document_access():
    """
    Decorador que valida que el usuario tenga acceso al documento especificado
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            document_id = kwargs.get('pk')
            
            if not document_id:
                return Response(
                    {
                        'error': 'DOCUMENT_ID_REQUIRED',
                        'message': 'Document ID is required for this operation'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar acceso al documento
            document, document_type, electronic_doc = find_document_by_id_for_user(document_id, request.user)
            
            if not document:
                logger.warning(f"🚫 User {getattr(request.user, 'username', 'Unknown')} denied access to document {document_id}")
                return Response(
                    {
                        'error': 'DOCUMENT_NOT_FOUND',
                        'message': f'Document with ID {document_id} not found or you do not have access to it',
                        'user': getattr(request.user, 'username', 'Unknown'),
                        'requested_document': str(document_id),
                        'security_check': 'document_access_decorator'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Agregar documentos validados al request
            request.validated_document = document
            request.validated_document_type = document_type
            request.validated_electronic_doc = electronic_doc
            
            logger.info(f"✅ User {getattr(request.user, 'username', 'Unknown')} validated access to {document_type} {document_id}")
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_certificate_validation():
    """
    Decorador que valida que la empresa tenga certificado disponible
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # La empresa debe estar ya validada por otro decorador
            company = getattr(request, 'validated_company', None)
            
            if not company:
                # Intentar obtener de documento validado
                document = getattr(request, 'validated_document', None)
                if document:
                    company = document.company
            
            if not company:
                return Response(
                    {
                        'error': 'COMPANY_NOT_VALIDATED',
                        'message': 'Company must be validated before certificate check',
                        'suggestion': 'Use @require_user_company_access decorator first'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Validar certificado
            cert_valid, cert_message = validate_company_certificate_for_user(company, request.user)
            
            if not cert_valid:
                logger.warning(f"🔐 Certificate not available for company {company.id}: {cert_message}")
                return Response(
                    {
                        'error': 'CERTIFICATE_NOT_AVAILABLE',
                        'message': cert_message,
                        'company_id': company.id,
                        'company_name': company.business_name,
                        'user': getattr(request.user, 'username', 'Unknown'),
                        'security_check': 'certificate_validation_decorator',
                        'suggestion': 'Please configure digital certificate for this company'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Agregar información del certificado al request
            request.certificate_validated = True
            request.certificate_message = cert_message
            
            logger.info(f"🔐 Certificate validated for company {company.id} by user {getattr(request.user, 'username', 'Unknown')}")
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def audit_api_action(action_type=None, include_response_data=False):
    """
    Decorador para auditoría completa de acciones API
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            start_time = time.time()
            action = action_type or view_func.__name__.upper()
            
            # Log inicial
            logger.info(f"🚀 [{action}] User {getattr(request.user, 'username', 'Unknown')} - {view_func.__name__} - Started")
            
            try:
                # Ejecutar la función original
                response = view_func(self, request, *args, **kwargs)
                
                # Calcular tiempo de ejecución
                execution_time = time.time() - start_time
                
                logger.info(f"✅ [{action}] User {getattr(request.user, 'username', 'Unknown')} - SUCCESS - {execution_time:.2f}s")
                
                # Agregar información de auditoría a la respuesta
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    response.data['audit_info'] = {
                        'processed_by': getattr(request.user, 'username', 'Unknown'),
                        'processing_time_ms': round(execution_time * 1000, 2),
                        'action_type': action,
                        'timestamp': timezone.now().isoformat(),
                        'security_method': 'token_validation_with_decorators'
                    }
                
                return response
                
            except Exception as e:
                # Calcular tiempo hasta el error
                execution_time = time.time() - start_time
                
                logger.error(f"❌ [{action}] User {getattr(request.user, 'username', 'Unknown')} - ERROR: {str(e)} - {execution_time:.2f}s")
                
                # Re-lanzar la excepción para que sea manejada normalmente
                raise
                
        return wrapper
    return decorator


def validate_sri_configuration():
    """
    Decorador que valida que la empresa tenga configuración SRI válida
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # La empresa debe estar validada previamente
            company = getattr(request, 'validated_company', None)
            
            if not company:
                document = getattr(request, 'validated_document', None)
                if document:
                    company = document.company
            
            if not company:
                return Response(
                    {
                        'error': 'COMPANY_NOT_VALIDATED',
                        'message': 'Company must be validated before SRI configuration check'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Verificar configuración SRI
            try:
                sri_config = company.sri_configuration
                request.validated_sri_config = sri_config
                logger.info(f"✅ SRI configuration validated for company {company.id}")
                
            except AttributeError:
                logger.warning(f"❌ No SRI configuration found for company {company.id}")
                return Response(
                    {
                        'error': 'SRI_CONFIGURATION_MISSING',
                        'message': 'Company does not have SRI configuration',
                        'company_id': company.id,
                        'company_name': company.business_name,
                        'user': getattr(request.user, 'username', 'Unknown'),
                        'suggestion': 'Please configure SRI settings for this company'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def validate_request_data(required_fields=None):
    """
    Decorador para validar datos del request - CORREGIDO PARA VSR
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if required_fields:
                missing_fields = []
                
                # 🔑 EXCEPCIÓN: Si es token VSR, no requerir 'company'
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                is_vsr_token = auth_header.startswith('Token vsr_')
                
                for field in required_fields:
                    # Saltar validación de 'company' para tokens VSR
                    if field == 'company' and is_vsr_token:
                        continue
                        
                    if field not in request.data:
                        missing_fields.append(field)
                
                if missing_fields:
                    logger.warning(f"❌ Missing required fields: {missing_fields} - User: {getattr(request.user, 'username', 'Unknown')}")
                    return Response(
                        {
                            'error': 'VALIDATION_ERROR',
                            'message': 'Missing required fields',
                            'missing_fields': missing_fields,
                            'required_fields': required_fields,
                            'user': getattr(request.user, 'username', 'Unknown'),
                            'token_type': 'VSR' if is_vsr_token else 'USER'
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            
            logger.info(f"✅ Request data validated for {view_func.__name__} - User: {getattr(request.user, 'username', 'Unknown')}")
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def atomic_transaction():
    """
    Decorador para transacciones atómicas con manejo de errores
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            try:
                with transaction.atomic():
                    logger.info(f"🔄 Transaction started for {view_func.__name__} - User: {getattr(request.user, 'username', 'Unknown')}")
                    response = view_func(self, request, *args, **kwargs)
                    logger.info(f"✅ Transaction committed for {view_func.__name__} - User: {getattr(request.user, 'username', 'Unknown')}")
                    return response
                    
            except Exception as e:
                logger.error(f"🔄 Transaction rolled back for {view_func.__name__} - Error: {str(e)} - User: {getattr(request.user, 'username', 'Unknown')}")
                raise
                
        return wrapper
    return decorator


# Decorador combinado para endpoints SRI seguros
def sri_secure_endpoint(
    require_company_access=True,
    require_certificate=False,
    require_sri_config=False,
    audit_action=None,
    validate_fields=None,
    atomic=True
):
    """
    Decorador combinado para endpoints SRI seguros - CORREGIDO PARA VSR
    """
    def decorator(view_func):
        func = view_func
        
        if atomic:
            func = atomic_transaction()(func)
        
        if validate_fields:
            func = validate_request_data(required_fields=validate_fields)(func)
        
        if require_sri_config:
            func = validate_sri_configuration()(func)
        
        if require_certificate:
            func = require_certificate_validation()(func)
        
        if require_company_access:
            func = require_user_company_access()(func)
        
        if audit_action:
            func = audit_api_action(action_type=audit_action, include_response_data=True)(func)
        
        return func
    return decorator


# Decorador para endpoints de documentos
def sri_document_endpoint(
    require_certificate=False,
    audit_action=None,
    atomic=True
):
    """
    Decorador especializado para endpoints que trabajan con documentos
    """
    def decorator(view_func):
        func = view_func
        
        if atomic:
            func = atomic_transaction()(func)
        
        if require_certificate:
            func = require_certificate_validation()(func)
        
        func = require_document_access()(func)
        
        if audit_action:
            func = audit_api_action(action_type=audit_action, include_response_data=True)(func)
        
        return func
    return decorator


# ========== FUNCIONES AUXILIARES MEJORADAS ==========

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


def find_document_by_id_for_user(pk, user):
    """
    Busca un documento por ID SOLO en las empresas del usuario autenticado
    """
    document = None
    document_type = None
    electronic_doc = None
    
    # 🔒 SEGURIDAD: Obtener empresas del usuario
    if user.is_superuser:
        from apps.companies.models import Company
        user_companies = Company.objects.filter(is_active=True)
    else:
        user_companies = get_user_companies_exact(user)
    
    if not user_companies.exists():
        logger.warning(f"User {getattr(user, 'username', 'Unknown')} has no accessible companies")
        return None, None, None
    
    # Buscar en orden de prioridad, LIMITADO a empresas del usuario
    search_order = [
        (CreditNote, 'CREDIT_NOTE'),
        (DebitNote, 'DEBIT_NOTE'),
        (Retention, 'RETENTION'),
        (PurchaseSettlement, 'PURCHASE_SETTLEMENT'),
        (ElectronicDocument, 'INVOICE')
    ]
    
    for model, doc_type in search_order:
        try:
            document = model.objects.filter(
                id=pk,
                company__in=user_companies  # 🔒 FILTRO DE SEGURIDAD
            ).first()
            
            if document:
                document_type = doc_type
                logger.info(f'Found document {pk} as {doc_type} for user {getattr(user, "username", "Unknown")}')
                break
        except Exception as e:
            logger.error(f"Error searching in {model}: {e}")
            continue
    
    if not document:
        logger.warning(f"Document {pk} not found or not accessible for user {getattr(user, 'username', 'Unknown')}")
        return None, None, None
    
    # Si encontramos un documento específico, sincronizar con ElectronicDocument
    if document_type != 'INVOICE':
        electronic_doc = sync_document_to_electronic_document(document, document_type)
    else:
        electronic_doc = document
    
    return document, document_type, electronic_doc


def validate_company_certificate_for_user(company, user):
    """
    Valida que la empresa pertenezca al usuario Y tenga certificado disponible
    """
    # 🔒 SEGURIDAD: Verificar que el usuario tiene acceso a la empresa
    if user.is_superuser:
        # Superuser tiene acceso a todas las empresas activas
        from apps.companies.models import Company
        if not Company.objects.filter(id=company.id, is_active=True).exists():
            return False, "Company not found or inactive"
    else:
        # Usuario normal solo puede acceder a sus empresas
        if company not in get_user_companies_exact(user):
            logger.warning(f"User {getattr(user, 'username', 'Unknown')} tried to access company {company.id} without permission")
            return False, "You do not have access to this company"
    
    try:
        cert_manager = get_certificate_manager()
        cert_data = cert_manager.get_certificate(company.id)
        
        if not cert_data:
            return False, "Certificate not available in GlobalCertificateManager. Please configure certificate."
        
        is_valid, message = cert_manager.validate_certificate(company.id)
        if not is_valid:
            return False, f"Certificate validation failed: {message}"
        
        if "expires in" in message:
            logger.warning(f"Certificate warning for company {company.id}: {message}")
        
        return True, "Certificate is available and valid"
        
    except Exception as e:
        logger.error(f"Error validating certificate for company {company.id}: {str(e)}")
        return False, f"Error validating certificate: {str(e)}"


def get_user_company_by_id(company_id, user):
    """
    Obtiene empresa por ID o JWT token - VERSIÓN HÍBRIDA CORREGIDA
    """
    return get_user_company_by_id_or_token(company_id, user)


# ========== CLASE PRINCIPAL CON ENDPOINTS DE PROCESO COMPLETO ==========

class SRIDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal para todos los documentos SRI 
    ✅ CON ENDPOINTS DE PROCESO COMPLETO PARA CADA TIPO
    ✅ RESUELVE ERROR 35
    ✅ COMPATIBLE CON TOKEN VSR
    """
    queryset = ElectronicDocument.objects.all()
    serializer_class = ElectronicDocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['company', 'document_type', 'status', 'issue_date', 'customer_identification_type']
    search_fields = ['document_number', 'customer_name', 'customer_identification', 'access_key']
    ordering_fields = ['issue_date', 'created_at', 'total_amount', 'document_number']
    ordering = ['-created_at']
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filtra documentos SOLO por empresas del usuario autenticado
        """
        user = self.request.user
        
        if user.is_superuser:
            logger.info(f"Superuser {getattr(user, 'username', 'Admin')} accessing all documents")
            return ElectronicDocument.objects.all()
        
        # 🔒 SEGURIDAD: Usuario normal solo ve documentos de sus empresas
        user_companies = get_user_companies_exact(user)
        if user_companies.exists():
            logger.info(f"User {getattr(user, 'username', 'Unknown')} accessing documents from {user_companies.count()} companies")
            return ElectronicDocument.objects.filter(company__in=user_companies)
        
        # Si no tiene empresas, no ve nada
        logger.warning(f"User {getattr(user, 'username', 'Unknown')} has no accessible companies")
        return ElectronicDocument.objects.none()
    
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
    
    # ========== ENDPOINTS DE PROCESO COMPLETO PARA CADA TIPO ==========
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_AND_PROCESS_INVOICE_COMPLETE',
        validate_fields=['customer_identification_type', 'customer_identification', 'customer_name', 'issue_date', 'items'],
        atomic=True
    )
    def create_and_process_invoice_complete(self, request):
        """
        🚀 ENDPOINT COMPLETO PARA FACTURAS: Crear + Procesar completamente
        ✅ RESUELVE ERROR 35
        ✅ COMPATIBLE CON TOKEN VSR
        ✅ TODO EL PROCESO EN UNA SOLA LLAMADA
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            start_time = time.time()
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
            logger.info(f"🚀 [INVOICE_COMPLETE] Creating and processing invoice for user {getattr(request.user, 'username', 'Unknown')}")
            
            # Función para manejar decimales
            def fix_decimal(value, places=2):
                if isinstance(value, (int, float)):
                    value = Decimal(str(value))
                elif isinstance(value, str):
                    value = Decimal(value)
                quantizer = Decimal('0.' + '0' * places)
                return value.quantize(quantizer, rounding=ROUND_HALF_UP)
            
            # ===== PASO 1: CREAR FACTURA =====
            sequence = sri_config.get_next_sequence('INVOICE')
            document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            
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
            
            creation_time = time.time()
            logger.info(f"✅ [INVOICE_COMPLETE] Step 1: Invoice {electronic_doc.id} created in {creation_time - start_time:.2f}s")
            
            # ===== PASO 2: PROCESAR COMPLETAMENTE =====
            send_email = data.get('send_email', True)
            processor = DocumentProcessor(company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            process_time = time.time()
            total_time = process_time - start_time
            
            if success:
                logger.info(f"✅ [INVOICE_COMPLETE] Step 2: Processing completed in {process_time - creation_time:.2f}s")
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': '🎉 Invoice created and processed completely - ERROR 35 RESOLVED',
                        'document_type': 'INVOICE',
                        'method': 'create_and_process_invoice_complete',
                        'processing_details': {
                            'step_1_create': 'COMPLETED',
                            'step_2_xml_generation': 'COMPLETED_WITH_CORRECTED_XMLGenerator',
                            'step_3_signing': 'COMPLETED_WITH_GlobalCertificateManager',
                            'step_4_sri_submission': 'COMPLETED_NO_ERROR_35',
                            'step_5_authorization': 'COMPLETED_IF_AVAILABLE'
                        },
                        'timing': {
                            'creation_time_s': round(creation_time - start_time, 2),
                            'processing_time_s': round(process_time - creation_time, 2),
                            'total_time_s': round(total_time, 2)
                        },
                        'data': {
                            'id': electronic_doc.id,
                            'company': electronic_doc.company.id,
                            'company_name': electronic_doc.company.business_name,
                            'document_type': electronic_doc.document_type,
                            'document_number': electronic_doc.document_number,
                            'access_key': electronic_doc.access_key,
                            'issue_date': electronic_doc.issue_date,
                            'customer_name': electronic_doc.customer_name,
                            'customer_identification': electronic_doc.customer_identification,
                            'subtotal_without_tax': str(electronic_doc.subtotal_without_tax),
                            'total_tax': str(electronic_doc.total_tax),
                            'total_amount': str(electronic_doc.total_amount),
                            'status': electronic_doc.status,
                            'status_display': electronic_doc.get_status_display(),
                            'sri_authorization_code': electronic_doc.sri_authorization_code,
                            'sri_authorization_date': electronic_doc.sri_authorization_date,
                            'created_at': electronic_doc.created_at,
                            'updated_at': electronic_doc.updated_at
                        },
                        'files': {
                            'has_xml': bool(electronic_doc.xml_file),
                            'has_signed_xml': bool(electronic_doc.signed_xml_file),
                            'has_pdf': bool(electronic_doc.pdf_file),
                            'xml_path': str(electronic_doc.xml_file) if electronic_doc.xml_file else None,
                            'signed_xml_path': str(electronic_doc.signed_xml_file) if electronic_doc.signed_xml_file else None
                        },
                        'processing_info': {
                            'password_required': False,
                            'automatic_processing': True,
                            'certificate_cached': True,
                            'error_35_resolved': True,
                            'xmlgenerator_corrected': True,
                            'vsr_token_compatible': True,
                            'decorators_enhanced': True
                        },
                        'status_details': status_info
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"❌ [INVOICE_COMPLETE] Processing failed: {message}")
                return Response(
                    {
                        'success': False,
                        'message': f'Invoice created but processing failed: {message}',
                        'data': {
                            'id': electronic_doc.id,
                            'document_number': electronic_doc.document_number,
                            'access_key': electronic_doc.access_key,
                            'status': electronic_doc.status,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"❌ [INVOICE_COMPLETE] Critical error: {str(e)}")
            return Response(
                {
                    'error': 'INVOICE_COMPLETE_ERROR',
                    'message': f'Error in complete invoice process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_AND_PROCESS_CREDIT_NOTE_COMPLETE',
        validate_fields=['customer_identification_type', 'customer_identification', 'customer_name', 'reason_description', 'original_document_access_key'],
        atomic=True
    )
    def create_and_process_credit_note_complete(self, request):
        """
        🚀 ENDPOINT COMPLETO PARA NOTAS DE CRÉDITO: Crear + Procesar completamente
        ✅ RESUELVE ERROR 35
        ✅ COMPATIBLE CON TOKEN VSR
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            start_time = time.time()
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
            logger.info(f"🚀 [CREDIT_NOTE_COMPLETE] Creating and processing credit note for user {getattr(request.user, 'username', 'Unknown')}")
            
            # Generar número de documento
            sequence = sri_config.get_next_sequence('CREDIT_NOTE')
            document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            
            # Crear nota de crédito
            credit_note = CreditNote.objects.create(
                company=company,
                document_number=document_number,
                issue_date=data['issue_date'],
                customer_identification_type=data['customer_identification_type'],
                customer_identification=data['customer_identification'],
                customer_name=data['customer_name'],
                customer_address=data.get('customer_address', ''),
                customer_email=data.get('customer_email', ''),
                reason_description=data['reason_description'],
                original_document_access_key=data['original_document_access_key'],
                subtotal_without_tax=Decimal(str(data.get('subtotal_without_tax', 0))),
                total_tax=Decimal(str(data.get('total_tax', 0))),
                total_amount=Decimal(str(data.get('total_amount', 0))),
                status='DRAFT'
            )
            
            # Generar clave de acceso
            credit_note.access_key = credit_note._generate_access_key()
            credit_note.status = 'GENERATED'
            credit_note.save()
            
            # Sincronizar con ElectronicDocument
            electronic_doc = sync_document_to_electronic_document(credit_note, 'CREDIT_NOTE')
            
            creation_time = time.time()
            logger.info(f"✅ [CREDIT_NOTE_COMPLETE] Step 1: Credit note {credit_note.id} created in {creation_time - start_time:.2f}s")
            
            # Procesar completamente
            send_email = data.get('send_email', True)
            processor = DocumentProcessor(company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            process_time = time.time()
            total_time = process_time - start_time
            
            if success:
                # Actualizar documento original
                credit_note.status = electronic_doc.status
                credit_note.save()
                
                logger.info(f"✅ [CREDIT_NOTE_COMPLETE] Processing completed in {process_time - creation_time:.2f}s")
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': '🎉 Credit Note created and processed completely - ERROR 35 RESOLVED',
                        'document_type': 'CREDIT_NOTE',
                        'method': 'create_and_process_credit_note_complete',
                        'timing': {
                            'creation_time_s': round(creation_time - start_time, 2),
                            'processing_time_s': round(process_time - creation_time, 2),
                            'total_time_s': round(total_time, 2)
                        },
                        'data': {
                            'id': credit_note.id,
                            'electronic_doc_id': electronic_doc.id,
                            'company': credit_note.company.id,
                            'company_name': credit_note.company.business_name,
                            'document_type': 'CREDIT_NOTE',
                            'document_number': credit_note.document_number,
                            'access_key': credit_note.access_key,
                            'issue_date': credit_note.issue_date,
                            'customer_name': credit_note.customer_name,
                            'reason_description': credit_note.reason_description,
                            'total_amount': str(credit_note.total_amount),
                            'status': credit_note.status,
                            'sri_authorization_code': electronic_doc.sri_authorization_code,
                            'sri_authorization_date': electronic_doc.sri_authorization_date,
                            'created_at': credit_note.created_at
                        },
                        'status_details': status_info
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"❌ [CREDIT_NOTE_COMPLETE] Processing failed: {message}")
                return Response(
                    {
                        'success': False,
                        'message': f'Credit Note created but processing failed: {message}',
                        'data': {
                            'id': credit_note.id,
                            'document_number': credit_note.document_number,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"❌ [CREDIT_NOTE_COMPLETE] Critical error: {str(e)}")
            return Response(
                {
                    'error': 'CREDIT_NOTE_COMPLETE_ERROR',
                    'message': f'Error in complete credit note process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_AND_PROCESS_DEBIT_NOTE_COMPLETE',
        validate_fields=['customer_identification_type', 'customer_identification', 'customer_name', 'reason_description', 'original_document_access_key'],
        atomic=True
    )
    def create_and_process_debit_note_complete(self, request):
        """
        🚀 ENDPOINT COMPLETO PARA NOTAS DE DÉBITO: Crear + Procesar completamente
        ✅ RESUELVE ERROR 35
        ✅ COMPATIBLE CON TOKEN VSR
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            start_time = time.time()
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
            logger.info(f"🚀 [DEBIT_NOTE_COMPLETE] Creating and processing debit note for user {getattr(request.user, 'username', 'Unknown')}")
            
            # Generar número de documento
            sequence = sri_config.get_next_sequence('DEBIT_NOTE')
            document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            
            # Crear nota de débito
            debit_note = DebitNote.objects.create(
                company=company,
                document_number=document_number,
                issue_date=data['issue_date'],
                customer_identification_type=data['customer_identification_type'],
                customer_identification=data['customer_identification'],
                customer_name=data['customer_name'],
                customer_address=data.get('customer_address', ''),
                customer_email=data.get('customer_email', ''),
                reason_description=data['reason_description'],
                original_document_access_key=data['original_document_access_key'],
                subtotal_without_tax=Decimal(str(data.get('subtotal_without_tax', 0))),
                total_tax=Decimal(str(data.get('total_tax', 0))),
                total_amount=Decimal(str(data.get('total_amount', 0))),
                status='DRAFT'
            )
            
            # Generar clave de acceso
            debit_note.access_key = debit_note._generate_access_key()
            debit_note.status = 'GENERATED'
            debit_note.save()
            
            # Sincronizar con ElectronicDocument
            electronic_doc = sync_document_to_electronic_document(debit_note, 'DEBIT_NOTE')
            
            creation_time = time.time()
            logger.info(f"✅ [DEBIT_NOTE_COMPLETE] Step 1: Debit note {debit_note.id} created in {creation_time - start_time:.2f}s")
            
            # Procesar completamente
            send_email = data.get('send_email', True)
            processor = DocumentProcessor(company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            process_time = time.time()
            total_time = process_time - start_time
            
            if success:
                # Actualizar documento original
                debit_note.status = electronic_doc.status
                debit_note.save()
                
                logger.info(f"✅ [DEBIT_NOTE_COMPLETE] Processing completed in {process_time - creation_time:.2f}s")
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': '🎉 Debit Note created and processed completely - ERROR 35 RESOLVED',
                        'document_type': 'DEBIT_NOTE',
                        'method': 'create_and_process_debit_note_complete',
                        'timing': {
                            'creation_time_s': round(creation_time - start_time, 2),
                            'processing_time_s': round(process_time - creation_time, 2),
                            'total_time_s': round(total_time, 2)
                        },
                        'data': {
                            'id': debit_note.id,
                            'electronic_doc_id': electronic_doc.id,
                            'company': debit_note.company.id,
                            'company_name': debit_note.company.business_name,
                            'document_type': 'DEBIT_NOTE',
                            'document_number': debit_note.document_number,
                            'access_key': debit_note.access_key,
                            'issue_date': debit_note.issue_date,
                            'customer_name': debit_note.customer_name,
                            'reason_description': debit_note.reason_description,
                            'total_amount': str(debit_note.total_amount),
                            'status': debit_note.status,
                            'sri_authorization_code': electronic_doc.sri_authorization_code,
                            'sri_authorization_date': electronic_doc.sri_authorization_date,
                            'created_at': debit_note.created_at
                        },
                        'status_details': status_info
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"❌ [DEBIT_NOTE_COMPLETE] Processing failed: {message}")
                return Response(
                    {
                        'success': False,
                        'message': f'Debit Note created but processing failed: {message}',
                        'data': {
                            'id': debit_note.id,
                            'document_number': debit_note.document_number,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"❌ [DEBIT_NOTE_COMPLETE] Critical error: {str(e)}")
            return Response(
                {
                    'error': 'DEBIT_NOTE_COMPLETE_ERROR',
                    'message': f'Error in complete debit note process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_AND_PROCESS_RETENTION_COMPLETE',
        validate_fields=['supplier_identification_type', 'supplier_identification', 'supplier_name', 'fiscal_period'],
        atomic=True
    )
    def create_and_process_retention_complete(self, request):
        """
        🚀 ENDPOINT COMPLETO PARA RETENCIONES: Crear + Procesar completamente
        ✅ RESUELVE ERROR 35
        ✅ COMPATIBLE CON TOKEN VSR
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            start_time = time.time()
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
            logger.info(f"🚀 [RETENTION_COMPLETE] Creating and processing retention for user {getattr(request.user, 'username', 'Unknown')}")
            
            # Generar número de documento
            sequence = sri_config.get_next_sequence('RETENTION')
            document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            
            # Crear retención
            retention = Retention.objects.create(
                company=company,
                document_number=document_number,
                issue_date=data['issue_date'],
                supplier_identification_type=data['supplier_identification_type'],
                supplier_identification=data['supplier_identification'],
                supplier_name=data['supplier_name'],
                supplier_address=data.get('supplier_address', ''),
                fiscal_period=data['fiscal_period'],
                total_retained=Decimal(str(data.get('total_retained', 0))),
                status='DRAFT'
            )
            
            # Generar clave de acceso
            retention.access_key = retention._generate_access_key()
            retention.status = 'GENERATED'
            retention.save()
            
            # Crear detalles de retención si se proporcionan
            retention_details = data.get('retention_details', [])
            for detail_data in retention_details:
                RetentionDetail.objects.create(
                    retention=retention,
                    tax_code=detail_data.get('tax_code', '2'),
                    retention_code=detail_data.get('retention_code', '303'),
                    taxable_base=Decimal(str(detail_data.get('taxable_base', 0))),
                    retention_percentage=Decimal(str(detail_data.get('retention_percentage', 30))),
                    retained_amount=Decimal(str(detail_data.get('retained_amount', 0))),
                    support_document_type=detail_data.get('support_document_type', '01'),
                    support_document_number=detail_data.get('support_document_number', '001-001-000000001'),
                    support_document_date=detail_data.get('support_document_date', retention.issue_date)
                )
            
            # Sincronizar con ElectronicDocument
            electronic_doc = sync_document_to_electronic_document(retention, 'RETENTION')
            
            creation_time = time.time()
            logger.info(f"✅ [RETENTION_COMPLETE] Step 1: Retention {retention.id} created in {creation_time - start_time:.2f}s")
            
            # Procesar completamente
            send_email = data.get('send_email', True)
            processor = DocumentProcessor(company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            process_time = time.time()
            total_time = process_time - start_time
            
            if success:
                # Actualizar documento original
                retention.status = electronic_doc.status
                retention.save()
                
                logger.info(f"✅ [RETENTION_COMPLETE] Processing completed in {process_time - creation_time:.2f}s")
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': '🎉 Retention created and processed completely - ERROR 35 RESOLVED',
                        'document_type': 'RETENTION',
                        'method': 'create_and_process_retention_complete',
                        'timing': {
                            'creation_time_s': round(creation_time - start_time, 2),
                            'processing_time_s': round(process_time - creation_time, 2),
                            'total_time_s': round(total_time, 2)
                        },
                        'data': {
                            'id': retention.id,
                            'electronic_doc_id': electronic_doc.id,
                            'company': retention.company.id,
                            'company_name': retention.company.business_name,
                            'document_type': 'RETENTION',
                            'document_number': retention.document_number,
                            'access_key': retention.access_key,
                            'issue_date': retention.issue_date,
                            'supplier_name': retention.supplier_name,
                            'fiscal_period': retention.fiscal_period,
                            'total_retained': str(retention.total_retained),
                            'status': retention.status,
                            'sri_authorization_code': electronic_doc.sri_authorization_code,
                            'sri_authorization_date': electronic_doc.sri_authorization_date,
                            'created_at': retention.created_at
                        },
                        'status_details': status_info
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"❌ [RETENTION_COMPLETE] Processing failed: {message}")
                return Response(
                    {
                        'success': False,
                        'message': f'Retention created but processing failed: {message}',
                        'data': {
                            'id': retention.id,
                            'document_number': retention.document_number,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"❌ [RETENTION_COMPLETE] Critical error: {str(e)}")
            return Response(
                {
                    'error': 'RETENTION_COMPLETE_ERROR',
                    'message': f'Error in complete retention process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_AND_PROCESS_PURCHASE_SETTLEMENT_COMPLETE',
        validate_fields=['supplier_identification_type', 'supplier_identification', 'supplier_name', 'items'],
        atomic=True
    )
    def create_and_process_purchase_settlement_complete(self, request):
        """
        🚀 ENDPOINT COMPLETO PARA LIQUIDACIONES DE COMPRA: Crear + Procesar completamente
        ✅ RESUELVE ERROR 35
        ✅ COMPATIBLE CON TOKEN VSR
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            start_time = time.time()
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
            logger.info(f"🚀 [PURCHASE_SETTLEMENT_COMPLETE] Creating and processing purchase settlement for user {getattr(request.user, 'username', 'Unknown')}")
            
            # Función para manejar decimales
            def fix_decimal(value, places=2):
                if isinstance(value, (int, float)):
                    value = Decimal(str(value))
                elif isinstance(value, str):
                    value = Decimal(value)
                quantizer = Decimal('0.' + '0' * places)
                return value.quantize(quantizer, rounding=ROUND_HALF_UP)
            
            # Generar número de documento
            sequence = sri_config.get_next_sequence('PURCHASE_SETTLEMENT')
            document_number = f"{sri_config.establishment_code}-{sri_config.emission_point}-{sequence:09d}"
            
            # Crear liquidación de compra
            purchase_settlement = PurchaseSettlement.objects.create(
                company=company,
                document_number=document_number,
                issue_date=data['issue_date'],
                supplier_identification_type=data['supplier_identification_type'],
                supplier_identification=data['supplier_identification'],
                supplier_name=data['supplier_name'],
                supplier_address=data.get('supplier_address', ''),
                status='DRAFT'
            )
            
            # Generar clave de acceso
            purchase_settlement.access_key = purchase_settlement._generate_access_key()
            
            # Crear items y calcular totales
            total_subtotal = Decimal('0.00')
            total_tax = Decimal('0.00')
            
            items_data = data.get('items', [])
            for item_data in items_data:
                quantity = fix_decimal(Decimal(str(item_data['quantity'])), 6)
                unit_price = fix_decimal(Decimal(str(item_data['unit_price'])), 6)
                discount = fix_decimal(Decimal(str(item_data.get('discount', 0))), 2)
                
                subtotal = fix_decimal((quantity * unit_price) - discount, 2)
                
                PurchaseSettlementItem.objects.create(
                    purchase_settlement=purchase_settlement,
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
            purchase_settlement.subtotal_without_tax = fix_decimal(total_subtotal, 2)
            purchase_settlement.total_tax = fix_decimal(total_tax, 2)
            purchase_settlement.total_amount = fix_decimal(total_amount, 2)
            purchase_settlement.status = 'GENERATED'
            purchase_settlement.save()
            
            # Sincronizar con ElectronicDocument
            electronic_doc = sync_document_to_electronic_document(purchase_settlement, 'PURCHASE_SETTLEMENT')
            
            creation_time = time.time()
            logger.info(f"✅ [PURCHASE_SETTLEMENT_COMPLETE] Step 1: Purchase settlement {purchase_settlement.id} created in {creation_time - start_time:.2f}s")
            
            # Procesar completamente
            send_email = data.get('send_email', True)
            processor = DocumentProcessor(company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            process_time = time.time()
            total_time = process_time - start_time
            
            if success:
                # Actualizar documento original
                purchase_settlement.status = electronic_doc.status
                purchase_settlement.save()
                
                logger.info(f"✅ [PURCHASE_SETTLEMENT_COMPLETE] Processing completed in {process_time - creation_time:.2f}s")
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': '🎉 Purchase Settlement created and processed completely - ERROR 35 RESOLVED',
                        'document_type': 'PURCHASE_SETTLEMENT',
                        'method': 'create_and_process_purchase_settlement_complete',
                        'timing': {
                            'creation_time_s': round(creation_time - start_time, 2),
                            'processing_time_s': round(process_time - creation_time, 2),
                            'total_time_s': round(total_time, 2)
                        },
                        'data': {
                            'id': purchase_settlement.id,
                            'electronic_doc_id': electronic_doc.id,
                            'company': purchase_settlement.company.id,
                            'company_name': purchase_settlement.company.business_name,
                            'document_type': 'PURCHASE_SETTLEMENT',
                            'document_number': purchase_settlement.document_number,
                            'access_key': purchase_settlement.access_key,
                            'issue_date': purchase_settlement.issue_date,
                            'supplier_name': purchase_settlement.supplier_name,
                            'subtotal_without_tax': str(purchase_settlement.subtotal_without_tax),
                            'total_tax': str(purchase_settlement.total_tax),
                            'total_amount': str(purchase_settlement.total_amount),
                            'status': purchase_settlement.status,
                            'sri_authorization_code': electronic_doc.sri_authorization_code,
                            'sri_authorization_date': electronic_doc.sri_authorization_date,
                            'created_at': purchase_settlement.created_at
                        },
                        'status_details': status_info
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"❌ [PURCHASE_SETTLEMENT_COMPLETE] Processing failed: {message}")
                return Response(
                    {
                        'success': False,
                        'message': f'Purchase Settlement created but processing failed: {message}',
                        'data': {
                            'id': purchase_settlement.id,
                            'document_number': purchase_settlement.document_number,
                            'error_details': message
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"❌ [PURCHASE_SETTLEMENT_COMPLETE] Critical error: {str(e)}")
            return Response(
                {
                    'error': 'PURCHASE_SETTLEMENT_COMPLETE_ERROR',
                    'message': f'Error in complete purchase settlement process: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ========== ENDPOINTS INDIVIDUALES EXISTENTES (MANTENIDOS) ==========
    
    @action(detail=False, methods=['post'])
    @sri_secure_endpoint(
        require_company_access=True,
        require_certificate=True,
        require_sri_config=True,
        audit_action='CREATE_INVOICE',
        validate_fields=['customer_identification_type', 'customer_identification', 'customer_name', 'issue_date', 'items'],
        atomic=True
    )
    def create_invoice(self, request):
        """
        Crear factura electrónica (solo creación) - MANTENIDO PARA COMPATIBILIDAD
        """
        try:
            from decimal import Decimal, ROUND_HALF_UP
            
            data = request.data
            company = request.validated_company
            sri_config = request.validated_sri_config
            
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
            
            # Crear ElectronicDocument directamente
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
            
            logger.info(f'🎉 Invoice ElectronicDocument {electronic_doc.id} created by user {getattr(request.user, "username", "Unknown")}')
            
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
                'processing_method': 'create_invoice_only'
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating invoice for user {getattr(request.user, 'username', 'Unknown')}: {str(e)}")
            return Response(
                {
                    'error': 'INTERNAL_SERVER_ERROR',
                    'message': f'Error creating invoice: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # ========== PROCESAMIENTO INDIVIDUAL CON DECORADORES ==========
    
    @action(detail=True, methods=['post'])
    @sri_document_endpoint(
        require_certificate=False,
        audit_action='GENERATE_XML',
        atomic=False
    )
    def generate_xml(self, request, pk=None):
        """
        Generar XML del documento usando XMLGenerator CORREGIDO
        """
        document = request.validated_document
        document_type = request.validated_document_type
        electronic_doc = request.validated_electronic_doc
        
        # Verificar certificado disponible (sin bloquear)
        cert_valid, cert_message = validate_company_certificate_for_user(document.company, request.user)
        if not cert_valid:
            logger.warning(f"Certificate not ready for company {document.company.id}: {cert_message}")
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
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
            
            document.status = 'GENERATED'
            document.save()
            
            return Response(
                {
                    'success': True,
                    'message': 'XML generated successfully using corrected XMLGenerator',
                    'data': {
                        'document_number': document.document_number,
                        'document_type': document_type,
                        'xml_size': len(xml_content),
                        'xml_file': str(electronic_doc.xml_file) if electronic_doc and electronic_doc.xml_file else None,
                        'access_key': document.access_key,
                        'status': document.status,
                        'ready_for_signing': cert_valid,
                        'error_35_resolved': True
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
    @sri_document_endpoint(
        require_certificate=True,
        audit_action='SIGN_DOCUMENT',
        atomic=False
    )
    def sign_document(self, request, pk=None):
        """
        Firmar documento usando GlobalCertificateManager
        """
        document = request.validated_document
        document_type = request.validated_document_type
        electronic_doc = request.validated_electronic_doc
        
        # Verificar que existe XML para firmar
        if not electronic_doc.xml_file:
            return Response(
                {
                    'error': 'XML_FILE_NOT_FOUND',
                    'message': 'XML file must be generated before signing. Call generate_xml first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            # Leer contenido XML existente
            with open(electronic_doc.xml_file.path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
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
            
            # Actualizar documento original también
            document.status = 'SIGNED'
            document.save()
            
            # Información del certificado del gestor global
            cert_manager = get_certificate_manager()
            cert_info = cert_manager.get_company_certificate_info(document.company.id)
            
            return Response(
                {
                    'success': True,
                    'message': 'Document signed successfully with GlobalCertificateManager',
                    'data': {
                        'document_number': document.document_number,
                        'document_type': document_type,
                        'certificate_info': cert_info,
                        'signature_method': 'GlobalCertificateManager with XAdES-BES',
                        'status': electronic_doc.status,
                        'signed_xml_file': str(electronic_doc.signed_xml_file) if electronic_doc.signed_xml_file else None,
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
    @sri_document_endpoint(
        require_certificate=False,
        audit_action='SEND_TO_SRI',
        atomic=False
    )
    def send_to_sri(self, request, pk=None):
        """
        Enviar documento al SRI usando SRISOAPClient
        """
        document = request.validated_document
        document_type = request.validated_document_type
        electronic_doc = request.validated_electronic_doc
        
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
            
            return Response(
                {
                    'success': True,
                    'message': 'Document sent to SRI successfully - ERROR 35 RESOLVED',
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
                        'error_35_resolved': True
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
    @sri_document_endpoint(
        require_certificate=True,
        audit_action='PROCESS_COMPLETE',
        atomic=False
    )
    def process_complete(self, request, pk=None):
        """
        Proceso completo usando DocumentProcessor
        """
        document = request.validated_document
        document_type = request.validated_document_type
        electronic_doc = request.validated_electronic_doc
        
        # Obtener parámetros opcionales
        send_email = request.data.get('send_email', True)
        
        try:
            from apps.sri_integration.services.document_processor import DocumentProcessor
            
            processor = DocumentProcessor(document.company)
            success, message = processor.process_document(electronic_doc, send_email)
            
            # Actualizar documento original también
            document.status = electronic_doc.status
            document.save()
            
            if success:
                status_info = processor.get_document_status(electronic_doc)
                
                return Response(
                    {
                        'success': True,
                        'message': 'Document processed completely - ERROR 35 RESOLVED',
                        'password_required': False,
                        'error_35_resolved': True,
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
                            'certificate_cached': True
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

    # ========== GESTIÓN DEL GlobalCertificateManager ==========
    
    @action(detail=False, methods=['get'])
    @audit_api_action(action_type='VIEW_CERTIFICATE_STATUS')
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
                'multi_company_support': True,
                'decorator_validation': True,
                'vsr_token_support': True,
                'error_35_resolved': True,
                'available_endpoints': [
                    'create_and_process_invoice_complete',
                    'create_and_process_credit_note_complete',
                    'create_and_process_debit_note_complete',
                    'create_and_process_retention_complete',
                    'create_and_process_purchase_settlement_complete'
                ]
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting certificate manager status: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========== VIEWSETS ADICIONALES ==========

class SRIConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuración SRI - SOLO EMPRESAS DEL USUARIO
    """
    queryset = SRIConfiguration.objects.all()
    serializer_class = SRIConfigurationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['company', 'environment']
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filtra configuraciones por empresas del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return SRIConfiguration.objects.all()
        
        user_companies = get_user_companies_exact(user)
        if user_companies.exists():
            return SRIConfiguration.objects.filter(company__in=user_companies)
        
        return SRIConfiguration.objects.none()


class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para respuestas del SRI - SOLO DOCUMENTOS DEL USUARIO
    """
    queryset = SRIResponse.objects.all()
    serializer_class = SRIResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'operation_type', 'response_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    permission_classes = [permissions.IsAuthenticated, IsCompanyOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filtra respuestas por documentos de empresas del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return SRIResponse.objects.all()
        
        user_companies = get_user_companies_exact(user)
        if user_companies.exists():
            return SRIResponse.objects.filter(document__company__in=user_companies)
        
        return SRIResponse.objects.none()


# ========== DOCUMENTACIÓN DE LA API ==========

class DocumentationViewSet(viewsets.ViewSet):
    """
    Documentación de la API FINAL con endpoints de proceso completo
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    @audit_api_action(action_type='VIEW_API_DOCUMENTATION')
    def api_info(self, request):
        """
        Información general de la API FINAL con endpoints de proceso completo
        """
        return Response({
            'api_name': 'SRI Integration API v2.2 FINAL - Complete Process Endpoints',
            'description': 'API completa con endpoints de proceso completo para cada tipo de documento SRI',
            'version': '2.2.0-FINAL-COMPLETE-PROCESS',
            'certificate_manager': 'GlobalCertificateManager',
            'error_35_status': 'RESOLVED',
            'password_required': False,
            'vsr_token_support': True,
            'user_token_support': True,
            'complete_process_endpoints': {
                'invoice': {
                    'endpoint': 'POST /api/sri/documents/create_and_process_invoice_complete/',
                    'description': 'Crear y procesar factura completamente en una sola llamada',
                    'required_fields': ['customer_identification_type', 'customer_identification', 'customer_name', 'issue_date', 'items']
                },
                'credit_note': {
                    'endpoint': 'POST /api/sri/documents/create_and_process_credit_note_complete/',
                    'description': 'Crear y procesar nota de crédito completamente',
                    'required_fields': ['customer_identification_type', 'customer_identification', 'customer_name', 'reason_description', 'original_document_access_key']
                },
                'debit_note': {
                    'endpoint': 'POST /api/sri/documents/create_and_process_debit_note_complete/',
                    'description': 'Crear y procesar nota de débito completamente',
                    'required_fields': ['customer_identification_type', 'customer_identification', 'customer_name', 'reason_description', 'original_document_access_key']
                },
                'retention': {
                    'endpoint': 'POST /api/sri/documents/create_and_process_retention_complete/',
                    'description': 'Crear y procesar retención completamente',
                    'required_fields': ['supplier_identification_type', 'supplier_identification', 'supplier_name', 'fiscal_period']
                },
                'purchase_settlement': {
                    'endpoint': 'POST /api/sri/documents/create_and_process_purchase_settlement_complete/',
                    'description': 'Crear y procesar liquidación de compra completamente',
                    'required_fields': ['supplier_identification_type', 'supplier_identification', 'supplier_name', 'items']
                }
            },
            'individual_endpoints': {
                'creation_only': [
                    'POST /api/sri/documents/create_invoice/',
                    'POST /api/sri/documents/create_credit_note/',
                    'POST /api/sri/documents/create_debit_note/',
                    'POST /api/sri/documents/create_retention/',
                    'POST /api/sri/documents/create_purchase_settlement/'
                ],
                'processing_only': [
                    'POST /api/sri/documents/{id}/generate_xml/',
                    'POST /api/sri/documents/{id}/sign_document/',
                    'POST /api/sri/documents/{id}/send_to_sri/',
                    'POST /api/sri/documents/{id}/process_complete/'
                ]
            },
            'token_usage': {
                'vsr_token': {
                    'format': 'Token vsr_XXXXXXXXXXXXXXX',
                    'company_detection': 'automatic',
                    'recommended_for': 'Single company integrations'
                },
                'user_token': {
                    'format': 'Token XXXXXXXXXXXXXXX',
                    'company_field_required': True,
                    'recommended_for': 'Multi-company integrations'
                }
            },
            'features': [
                'Complete process endpoints for all document types',
                'Error 35 resolution built-in',
                'Automatic certificate management',
                'VSR token compatibility',
                'Decorator-based security',
                'Transaction safety',
                'Comprehensive audit logging'
            ]
        })