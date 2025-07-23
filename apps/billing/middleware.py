# -*- coding: utf-8 -*-
"""
Middleware para control de límites de facturación
apps/billing/middleware.py
"""

import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from apps.companies.models import CompanyAPIToken
from apps.billing.models import CompanyBillingProfile, InvoiceConsumption

logger = logging.getLogger(__name__)


class BillingLimitMiddleware(MiddlewareMixin):
    """
    Middleware que controla los límites de facturación antes de crear documentos SRI
    """
    
    # Endpoints que consumen facturas
    INVOICE_CREATION_ENDPOINTS = [
        '/api/sri/documents/create_invoice/',
        '/api/sri/documents/create_credit_note/',
        '/api/sri/documents/create_debit_note/',
        '/api/sri/documents/create_retention/',
        '/api/sri/documents/create_purchase_settlement/',
    ]
    
    def process_request(self, request):
        """
        Verificar límites antes de procesar endpoints de creación de documentos
        """
        # Solo aplicar a endpoints de creación de documentos
        if not any(request.path.startswith(endpoint) for endpoint in self.INVOICE_CREATION_ENDPOINTS):
            return None
        
        # Solo aplicar a métodos POST (creación)
        if request.method != 'POST':
            return None
        
        # Obtener la empresa del request
        company = self._get_company_from_request(request)
        if not company:
            return JsonResponse({
                'error': 'BILLING_ERROR',
                'message': 'No se pudo identificar la empresa para verificar límites de facturación',
                'code': 'COMPANY_NOT_FOUND'
            }, status=400)
        
        # Obtener o crear perfil de facturación
        billing_profile, created = CompanyBillingProfile.objects.get_or_create(
            company=company,
            defaults={
                'available_invoices': 0,
                'total_invoices_purchased': 0,
                'total_invoices_consumed': 0,
            }
        )
        
        # Verificar si tiene facturas disponibles
        if billing_profile.available_invoices <= 0:
            logger.warning(f"🚫 BILLING LIMIT: Company {company.business_name} has no invoices remaining")
            
            return JsonResponse({
                'error': 'BILLING_LIMIT_EXCEEDED',
                'message': 'No tienes facturas disponibles. Debes comprar un plan para continuar.',
                'details': {
                    'company': company.business_name,
                    'available_invoices': billing_profile.available_invoices,
                    'total_purchased': billing_profile.total_invoices_purchased,
                    'total_consumed': billing_profile.total_invoices_consumed,
                },
                'actions': {
                    'buy_plan_url': '/dashboard/billing/plans/',
                    'contact_admin': 'Contacta al administrador para activar tu plan',
                },
                'code': 'NO_INVOICES_REMAINING'
            }, status=402)  # 402 Payment Required
        
        # Verificar alerta de saldo bajo
        if billing_profile.is_low_balance:
            logger.warning(f"⚠️ BILLING WARNING: Company {company.business_name} has low balance: {billing_profile.available_invoices} invoices remaining")
        
        # Agregar información de facturación al request para uso posterior
        request.billing_profile = billing_profile
        request.billing_company = company
        
        return None
    
    def process_response(self, request, response):
        """
        Consumir factura si la creación fue exitosa
        """
        # Solo procesar si es un endpoint de creación
        if not any(request.path.startswith(endpoint) for endpoint in self.INVOICE_CREATION_ENDPOINTS):
            return response
        
        # Solo procesar si fue POST exitoso
        if request.method != 'POST' or response.status_code not in [200, 201]:
            return response
        
        # Verificar si tenemos la información de facturación
        if not hasattr(request, 'billing_profile') or not hasattr(request, 'billing_company'):
            return response
        
        try:
            # Obtener información del documento creado
            invoice_id = self._extract_invoice_id_from_response(response)
            invoice_type = self._extract_document_type_from_path(request.path)
            
            # Registrar el consumo antes de descontar
            balance_before = request.billing_profile.available_invoices
            
            # Consumir una factura
            if request.billing_profile.consume_invoice():
                balance_after = request.billing_profile.available_invoices
                
                # Registrar en auditoría
                InvoiceConsumption.objects.create(
                    company=request.billing_company,
                    invoice_id=invoice_id or f"unknown_{request.path.split('/')[-2]}",
                    invoice_type=invoice_type,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    ip_address=self._get_client_ip(request),
                    api_endpoint=request.path,
                )
                
                logger.info(f"✅ BILLING CONSUMED: Company {request.billing_company.business_name} consumed 1 invoice. Remaining: {balance_after}")
                
                # Agregar headers informativos a la respuesta
                response['X-Billing-Invoices-Remaining'] = str(balance_after)
                response['X-Billing-Invoices-Consumed'] = str(request.billing_profile.total_invoices_consumed)
                
                # Alerta si se está agotando el saldo
                if balance_after <= request.billing_profile.low_balance_threshold:
                    response['X-Billing-Warning'] = f'Quedan solo {balance_after} facturas. Considera comprar un nuevo plan.'
                
            else:
                logger.error(f"❌ BILLING ERROR: Failed to consume invoice for {request.billing_company.business_name}")
        
        except Exception as e:
            logger.error(f"❌ BILLING MIDDLEWARE ERROR: {e}")
            # No interferir con la respuesta si hay errores en el billing
        
        return response
    
    def _get_company_from_request(self, request):
        """
        Extraer la empresa del request (desde token o parámetros)
        """
        try:
            # Intentar obtener desde token de autenticación
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Token '):
                token_key = auth_header.split(' ')[1]
                
                # Verificar si es token de empresa
                if token_key.startswith('vsr_'):
                    try:
                        company_token = CompanyAPIToken.objects.get(key=token_key, is_active=True)
                        return company_token.company
                    except CompanyAPIToken.DoesNotExist:
                        pass
            
            # Intentar obtener desde parámetros del request
            if hasattr(request, 'data') and 'company_id' in request.data:
                from apps.companies.models import Company
                try:
                    return Company.objects.get(id=request.data['company_id'])
                except Company.DoesNotExist:
                    pass
            
            # Intentar obtener desde usuario autenticado (para tokens de usuario)
            if request.user.is_authenticated:
                from apps.api.user_company_helper import get_user_companies_exact
                user_companies = get_user_companies_exact(request.user)
                if user_companies.exists():
                    # Si hay company_id en los datos, usarlo
                    if hasattr(request, 'data') and 'company_id' in request.data:
                        company_id = request.data['company_id']
                        return user_companies.filter(id=company_id).first()
                    else:
                        # Usar la primera empresa del usuario
                        return user_companies.first()
            
        except Exception as e:
            logger.error(f"Error extracting company from request: {e}")
        
        return None
    
    def _extract_invoice_id_from_response(self, response):
        """
        Extraer ID del documento de la respuesta
        """
        try:
            if hasattr(response, 'content'):
                import json
                data = json.loads(response.content.decode('utf-8'))
                return data.get('id') or data.get('document_id') or data.get('invoice_id')
        except:
            pass
        return None
    
    def _extract_document_type_from_path(self, path):
        """
        Extraer tipo de documento del path
        """
        type_mapping = {
            'create_invoice': 'invoice',
            'create_credit_note': 'credit_note',
            'create_debit_note': 'debit_note',
            'create_retention': 'retention',
            'create_purchase_settlement': 'purchase_settlement',
        }
        
        for endpoint, doc_type in type_mapping.items():
            if endpoint in path:
                return doc_type
        
        return 'unknown'
    
    def _get_client_ip(self, request):
        """
        Obtener IP del cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip