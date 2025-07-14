# -*- coding: utf-8 -*-
"""
URLs for API app - Versión completa con integración SRI
apps/api/urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

# Importar SRI ViewSets si están disponibles
try:
    from apps.api.views.sri_views import (
        SRIDocumentViewSet, 
        SRIConfigurationViewSet, 
        SRIResponseViewSet
    )
    SRI_AVAILABLE = True
except ImportError:
    SRI_AVAILABLE = False
    print("SRI views not available - basic API only")


def api_status(request):
    """Status de la API"""
    return JsonResponse({
        'status': 'OK', 
        'message': 'VENDO_SRI API funcionando',
        'version': 'v1',
        'sri_enabled': SRI_AVAILABLE
    })


def api_root(request):
    """Endpoint raíz con información completa"""
    endpoints = {
        'companies': '/api/companies/',
        'companies_mine': '/api/companies/my_companies/',
        'customers': '/api/customers/',
        'products': '/api/products/',
        'status': '/api/status/'
    }
    
    # Agregar endpoints SRI si están disponibles
    if SRI_AVAILABLE:
        endpoints.update({
            'sri_documents': '/api/sri/documents/',
            'sri_configuration': '/api/sri/configuration/',
            'sri_responses': '/api/sri/responses/',
            'create_invoice': '/api/sri/documents/create_invoice/',
            'create_credit_note': '/api/sri/documents/create_credit_note/',
            'create_debit_note': '/api/sri/documents/create_debit_note/',
            'create_retention': '/api/sri/documents/create_retention/',
            'create_purchase_settlement': '/api/sri/documents/create_purchase_settlement/',
        })
    
    return JsonResponse({
        'message': 'VENDO_SRI API v1',
        'sri_integration': SRI_AVAILABLE,
        'endpoints': endpoints
    })


class CompanyViewSet(viewsets.ViewSet):
    """ViewSet simple para empresas"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar empresas"""
        try:
            from apps.companies.models import Company
            companies = Company.objects.filter(is_active=True)
            
            data = []
            for company in companies:
                company_data = {
                    'id': company.id,
                    'ruc': company.ruc,
                    'business_name': company.business_name,
                    'trade_name': company.trade_name,
                    'display_name': company.trade_name or company.business_name,
                    'email': company.email,
                    'phone': company.phone,
                    'address': company.address,
                    'is_active': company.is_active,
                    'created_at': company.created_at.isoformat() if company.created_at else None,
                    'updated_at': company.updated_at.isoformat() if company.updated_at else None
                }
                
                # Agregar información SRI si está disponible
                if SRI_AVAILABLE:
                    try:
                        sri_config = company.sri_configuration
                        company_data['sri_configured'] = True
                        company_data['sri_environment'] = sri_config.environment
                    except:
                        company_data['sri_configured'] = False
                        company_data['sri_environment'] = None
                
                data.append(company_data)
            
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def retrieve(self, request, pk=None):
        """Obtener empresa específica"""
        try:
            from apps.companies.models import Company
            company = Company.objects.get(id=pk, is_active=True)
            
            data = {
                'id': company.id,
                'ruc': company.ruc,
                'business_name': company.business_name,
                'trade_name': company.trade_name,
                'display_name': company.trade_name or company.business_name,
                'email': company.email,
                'phone': company.phone,
                'address': company.address,
                'is_active': company.is_active,
                'created_at': company.created_at.isoformat() if company.created_at else None,
                'updated_at': company.updated_at.isoformat() if company.updated_at else None
            }
            
            # Agregar información detallada SRI
            if SRI_AVAILABLE:
                try:
                    sri_config = company.sri_configuration
                    data['sri_configuration'] = {
                        'configured': True,
                        'environment': sri_config.environment,
                        'establishment_code': sri_config.establishment_code,
                        'emission_point': sri_config.emission_point,
                        'special_taxpayer': sri_config.special_taxpayer,
                        'accounting_required': sri_config.accounting_required
                    }
                except:
                    data['sri_configuration'] = {
                        'configured': False
                    }
            
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=404)
    
    @action(detail=False, methods=['get'])
    def my_companies(self, request):
        """Empresas del usuario - endpoint principal"""
        try:
            from apps.companies.models import Company
            
            # Por ahora devolver todas las empresas activas
            # TODO: Filtrar por usuario cuando configures la relación
            companies = Company.objects.filter(is_active=True)
            
            data = []
            for company in companies:
                company_data = {
                    'id': company.id,
                    'ruc': company.ruc,
                    'business_name': company.business_name,
                    'trade_name': company.trade_name,
                    'display_name': company.trade_name or company.business_name,
                    'email': company.email,
                    'phone': company.phone,
                    'address': company.address,
                    'is_active': company.is_active,
                    'created_at': company.created_at.isoformat() if company.created_at else None,
                    'updated_at': company.updated_at.isoformat() if company.updated_at else None
                }
                
                # Agregar estado SRI
                if SRI_AVAILABLE:
                    try:
                        sri_config = company.sri_configuration
                        company_data['sri_configured'] = True
                        company_data['sri_environment'] = sri_config.environment
                    except:
                        company_data['sri_configured'] = False
                
                data.append(company_data)
            
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class CustomerViewSet(viewsets.ViewSet):
    """ViewSet simple para clientes"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar clientes"""
        try:
            from apps.invoicing.models import Customer
            
            # Filtros opcionales
            company_id = request.query_params.get('company')
            limit = int(request.query_params.get('limit', 20))
            
            queryset = Customer.objects.filter(is_active=True)
            if company_id:
                queryset = queryset.filter(company_id=company_id)
            
            customers = queryset[:limit]
            
            data = []
            for customer in customers:
                data.append({
                    'id': customer.id,
                    'identification_type': customer.identification_type,
                    'identification': customer.identification,
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'address': customer.address,
                    'company_id': customer.company.id,
                    'company_name': customer.company.business_name
                })
            
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def create(self, request):
        """Crear cliente"""
        try:
            from apps.invoicing.models import Customer
            from apps.companies.models import Company
            
            data = request.data
            
            # Validar datos requeridos
            required_fields = ['company', 'identification', 'name']
            for field in required_fields:
                if field not in data:
                    return Response({'error': f'Field {field} is required'}, status=400)
            
            # Obtener empresa
            company = Company.objects.get(id=data['company'])
            
            # Verificar que no exista cliente con misma identificación
            if Customer.objects.filter(
                company=company, 
                identification=data['identification']
            ).exists():
                return Response({
                    'error': 'Customer with this identification already exists for this company'
                }, status=400)
            
            # Crear cliente
            customer = Customer.objects.create(
                company=company,
                identification_type=data.get('identification_type', '05'),
                identification=data['identification'],
                name=data['name'],
                email=data.get('email', ''),
                phone=data.get('phone', ''),
                address=data.get('address', ''),
                city=data.get('city', ''),
                province=data.get('province', '')
            )
            
            return Response({
                'id': customer.id,
                'identification_type': customer.identification_type,
                'identification': customer.identification,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'company_id': customer.company.id,
                'company_name': customer.company.business_name
            }, status=201)
        except Company.DoesNotExist:
            return Response({'error': 'Company not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class ProductViewSet(viewsets.ViewSet):
    """ViewSet simple para productos"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar productos"""
        try:
            from apps.invoicing.models import ProductTemplate
            
            # Filtros opcionales
            company_id = request.query_params.get('company')
            limit = int(request.query_params.get('limit', 20))
            
            queryset = ProductTemplate.objects.filter(is_active=True)
            if company_id:
                queryset = queryset.filter(company_id=company_id)
            
            products = queryset[:limit]
            
            data = []
            for product in products:
                data.append({
                    'id': product.id,
                    'main_code': product.main_code,
                    'name': product.name,
                    'description': product.description,
                    'unit_price': str(product.unit_price),
                    'tax_rate': str(product.tax_rate),
                    'unit_of_measure': product.unit_of_measure,
                    'tax_code': product.tax_code,
                    'company_id': product.company.id,
                    'company_name': product.company.business_name
                })
            
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def create(self, request):
        """Crear producto"""
        try:
            from apps.invoicing.models import ProductTemplate
            from apps.companies.models import Company
            from decimal import Decimal
            
            data = request.data
            
            # Validar datos requeridos
            required_fields = ['company', 'main_code', 'name', 'unit_price']
            for field in required_fields:
                if field not in data:
                    return Response({'error': f'Field {field} is required'}, status=400)
            
            # Obtener empresa
            company = Company.objects.get(id=data['company'])
            
            # Verificar que no exista producto con mismo código
            if ProductTemplate.objects.filter(
                company=company, 
                main_code=data['main_code']
            ).exists():
                return Response({
                    'error': 'Product with this code already exists for this company'
                }, status=400)
            
            # Crear producto
            product = ProductTemplate.objects.create(
                company=company,
                main_code=data['main_code'],
                name=data['name'],
                description=data.get('description', ''),
                unit_of_measure=data.get('unit_of_measure', 'u'),
                unit_price=Decimal(str(data['unit_price'])),
                tax_rate=Decimal(str(data.get('tax_rate', 15.00))),
                tax_code=data.get('tax_code', '2')
            )
            
            return Response({
                'id': product.id,
                'main_code': product.main_code,
                'name': product.name,
                'description': product.description,
                'unit_price': str(product.unit_price),
                'tax_rate': str(product.tax_rate),
                'unit_of_measure': product.unit_of_measure,
                'company_id': product.company.id,
                'company_name': product.company.business_name
            }, status=201)
        except Company.DoesNotExist:
            return Response({'error': 'Company not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ========== CONFIGURACIÓN DE ROUTERS ==========

# Router principal
router = DefaultRouter()

# Registrar ViewSets básicos
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')

# Registrar ViewSets SRI si están disponibles
if SRI_AVAILABLE:
    router.register(r'sri/documents', SRIDocumentViewSet, basename='sri-documents')
    router.register(r'sri/configuration', SRIConfigurationViewSet, basename='sri-configuration')
    router.register(r'sri/responses', SRIResponseViewSet, basename='sri-responses')

# ========== URLs ESPECÍFICAS SRI ==========

sri_urlpatterns = []

if SRI_AVAILABLE:
    sri_urlpatterns = [
        # Creación de documentos electrónicos
        path('sri/documents/create_invoice/', 
             SRIDocumentViewSet.as_view({'post': 'create_invoice'}), 
             name='sri-create-invoice'),
        
        path('sri/documents/create_credit_note/', 
             SRIDocumentViewSet.as_view({'post': 'create_credit_note'}), 
             name='sri-create-credit-note'),
        
        path('sri/documents/create_debit_note/', 
             SRIDocumentViewSet.as_view({'post': 'create_debit_note'}), 
             name='sri-create-debit-note'),
        
        path('sri/documents/create_retention/', 
             SRIDocumentViewSet.as_view({'post': 'create_retention'}), 
             name='sri-create-retention'),
        
        path('sri/documents/create_purchase_settlement/', 
             SRIDocumentViewSet.as_view({'post': 'create_purchase_settlement'}), 
             name='sri-create-purchase-settlement'),
        
        # Procesamiento de documentos
        path('sri/documents/<int:pk>/process/', 
             SRIDocumentViewSet.as_view({'post': 'process'}), 
             name='sri-process-document'),
        
        path('sri/documents/<int:pk>/generate_xml/', 
             SRIDocumentViewSet.as_view({'post': 'generate_xml'}), 
             name='sri-generate-xml'),
        
        path('sri/documents/<int:pk>/sign_document/', 
             SRIDocumentViewSet.as_view({'post': 'sign_document'}), 
             name='sri-sign-document'),
        
        path('sri/documents/<int:pk>/send_to_sri/', 
             SRIDocumentViewSet.as_view({'post': 'send_to_sri'}), 
             name='sri-send-to-sri'),
        
        path('sri/documents/<int:pk>/send_email/', 
             SRIDocumentViewSet.as_view({'post': 'send_email'}), 
             name='sri-send-email'),
        
        # Consultas y estado
        path('sri/documents/<int:pk>/status_check/', 
             SRIDocumentViewSet.as_view({'get': 'status_check'}), 
             name='sri-status-check'),
        
        path('sri/documents/dashboard/', 
             SRIDocumentViewSet.as_view({'get': 'dashboard'}), 
             name='sri-dashboard'),
        
        # Configuración SRI
        path('sri/configuration/<int:pk>/get_next_sequence/', 
             SRIConfigurationViewSet.as_view({'post': 'get_next_sequence'}), 
             name='sri-get-next-sequence'),
        
        path('sri/configuration/<int:pk>/reset_sequences/', 
             SRIConfigurationViewSet.as_view({'post': 'reset_sequences'}), 
             name='sri-reset-sequences'),
    ]

# ========== CONFIGURACIÓN PRINCIPAL DE URLs ==========

app_name = 'api'

urlpatterns = [
    # Endpoints básicos
    path('', api_root, name='api_root'),
    path('v1/', api_root, name='api_root_v1'),
    path('v1/status/', api_status, name='status'),
    path('status/', api_status, name='status_simple'),
    
    # Router con ViewSets (incluye SRI si está disponible)
    path('', include(router.urls)),
    
    # URLs específicas SRI
    path('', include(sri_urlpatterns)),
    
    # Auth para browsable API
    path('auth/', include('rest_framework.urls')),
]

# ========== DOCUMENTACIÓN DE ENDPOINTS ==========

"""
ENDPOINTS DISPONIBLES:

=== BÁSICOS ===
GET  /api/                                        # Info de la API
GET  /api/status/                                 # Estado de la API
GET  /api/companies/                              # Listar empresas
GET  /api/companies/{id}/                         # Obtener empresa
GET  /api/companies/my_companies/                 # Empresas del usuario
GET  /api/customers/                              # Listar clientes
POST /api/customers/                              # Crear cliente
GET  /api/products/                               # Listar productos
POST /api/products/                               # Crear producto

=== SRI (Solo si está disponible) ===
POST /api/sri/documents/create_invoice/           # Crear factura
POST /api/sri/documents/create_credit_note/       # Crear nota de crédito  
POST /api/sri/documents/create_debit_note/        # Crear nota de débito
POST /api/sri/documents/create_retention/         # Crear retención
POST /api/sri/documents/create_purchase_settlement/ # Crear liquidación

POST /api/sri/documents/{id}/process/             # Procesar documento completo
POST /api/sri/documents/{id}/generate_xml/        # Generar XML
POST /api/sri/documents/{id}/sign_document/       # Firmar documento
POST /api/sri/documents/{id}/send_to_sri/         # Enviar al SRI
POST /api/sri/documents/{id}/send_email/          # Enviar por email
GET  /api/sri/documents/{id}/status_check/        # Estado del documento
GET  /api/sri/documents/dashboard/                # Dashboard SRI

GET  /api/sri/documents/                          # Listar documentos
GET  /api/sri/configuration/                      # Configuraciones SRI
GET  /api/sri/responses/                          # Respuestas del SRI

=== PARÁMETROS DE CONSULTA ===
?company={id}      # Filtrar por empresa
?limit={number}    # Limitar resultados
?document_type=    # Filtrar por tipo de documento (SRI)
?status=           # Filtrar por estado (SRI)

=== CÓDIGOS DE RESPUESTA ===
200 OK                     - Operación exitosa
201 Created               - Recurso creado
400 Bad Request           - Datos inválidos
404 Not Found             - Recurso no encontrado
422 Unprocessable Entity  - Error de validación
500 Internal Server Error - Error del servidor
"""