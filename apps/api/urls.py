# -*- coding: utf-8 -*-
"""
URLs for API app - VERSIÓN NUCLEAR CORREGIDA CON SEGURIDAD + AUTH TOKENS
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

# 🔥🔥🔥 IMPORTAR VIEWSET NUCLEAR CORRECTO 🔥🔥🔥
from apps.api.views.company_views import CompanyViewSet as NuclearCompanyViewSet

# 🔑🔑🔑 IMPORTAR AUTH VIEWS PARA TOKENS 🔑🔑🔑
from apps.api.views.auth_views import token_login, token_logout, token_profile, auth_status


def api_status(request):
    """Status de la API"""
    return JsonResponse({
        'status': 'OK', 
        'message': 'VENDO_SRI API funcionando con SEGURIDAD NUCLEAR + TOKEN AUTH',
        'version': 'v1-nuclear-tokens',
        'sri_enabled': SRI_AVAILABLE,
        'security_level': 'NUCLEAR_MAXIMUM',
        'authentication': 'Dual Token System (User + Company tokens)',
        'token_endpoints': {
            'login': '/api/auth/login/',
            'logout': '/api/auth/logout/',
            'profile': '/api/auth/profile/',
            'status': '/api/auth/status/'
        }
    })


def api_root(request):
    """Endpoint raíz con información completa"""
    endpoints = {
        'companies': '/api/companies/',
        'companies_mine': '/api/companies/my_companies/',
        'customers': '/api/customers/',
        'products': '/api/products/',
        'status': '/api/status/',
        # Auth endpoints
        'auth_login': '/api/auth/login/',
        'auth_logout': '/api/auth/logout/',
        'auth_profile': '/api/auth/profile/',
        'auth_status': '/api/auth/status/'
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
        'message': 'VENDO_SRI API v1 - NUCLEAR SECURITY + DUAL TOKEN AUTHENTICATION',
        'sri_integration': SRI_AVAILABLE,
        'security_method': 'UserCompanyAssignment + Nuclear Protection + Dual Tokens',
        'authentication_types': {
            'user_tokens': 'Multi-company access with company_id required',
            'company_tokens': 'Single company access, no company_id needed',
            'session_auth': 'Browser-based authentication for web interface'
        },
        'endpoints': endpoints
    })


# 🔥🔥🔥 NOTA: CompanyViewSet REMOVIDO - AHORA USAMOS EL NUCLEAR 🔥🔥🔥
# El CompanyViewSet original que estaba aquí ha sido reemplazado por
# el ViewSet nuclear con seguridad máxima desde apps.api.views.company_views


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

# 🔥🔥🔥 REGISTRAR VIEWSET NUCLEAR CON SEGURIDAD MÁXIMA 🔥🔥🔥
router.register(r'companies', NuclearCompanyViewSet, basename='company')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')

# Registrar ViewSets SRI si están disponibles
if SRI_AVAILABLE:
    router.register(r'sri/documents', SRIDocumentViewSet, basename='sri-documents')
    router.register(r'sri/configuration', SRIConfigurationViewSet, basename='sri-configuration')
    router.register(r'sri/responses', SRIResponseViewSet, basename='sri-responses')

# ========== URLs DE AUTENTICACIÓN CON TOKENS ==========

auth_urlpatterns = [
    path('auth/login/', token_login, name='token-login'),
    path('auth/logout/', token_logout, name='token-logout'),
    path('auth/profile/', token_profile, name='token-profile'),
    path('auth/status/', auth_status, name='auth-status'),
]

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
    
    # 🔑 URLs de autenticación con tokens
    path('', include(auth_urlpatterns)),
    
    # Router con ViewSets (incluye SRI si está disponible)
    path('', include(router.urls)),
    
    # URLs específicas SRI
    path('', include(sri_urlpatterns)),
    
    # Auth para browsable API (DRF tradicional)
    path('auth/', include('rest_framework.urls')),
]

# ========== DOCUMENTACIÓN DE ENDPOINTS NUCLEAR + TOKENS ==========

"""
ENDPOINTS DISPONIBLES CON SEGURIDAD NUCLEAR + DUAL TOKEN AUTHENTICATION:

=== AUTENTICACIÓN CON TOKENS ===
POST /api/auth/login/                             # Login → Retorna tokens disponibles
POST /api/auth/logout/                            # Logout → Invalida token actual
GET  /api/auth/profile/                           # Info del token/usuario actual
GET  /api/auth/status/                            # Estado de autenticación

=== BÁSICOS CON SEGURIDAD NUCLEAR ===
GET  /api/                                        # Info de la API (Nuclear + Tokens)
GET  /api/status/                                 # Estado de la API (Nuclear + Tokens)
GET  /api/companies/                              # Listar empresas (SEGÚN TIPO DE TOKEN)
GET  /api/companies/{id}/                         # Obtener empresa (CON BLOQUEO NUCLEAR)
GET  /api/companies/my_companies/                 # Empresas del usuario (SEGURO)
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

=== TIPOS DE AUTENTICACIÓN DISPONIBLES ===
🔑 TOKEN DE USUARIO:
   - Formato: Token 372a72b56b8bdf7b2d626d3a0df82c37c1600804
   - Acceso: Múltiples empresas asignadas al usuario
   - Uso: Dashboard web, aplicaciones multi-empresa
   - Requisito: Debe especificar company_id en requests de documentos

🏢 TOKEN DE EMPRESA:
   - Formato: Token vsr_ABC123456789...
   - Acceso: Solo la empresa específica del token
   - Uso: APIs externas, sistemas POS, integraciones
   - Ventaja: NO necesita company_id (implícito en token)

🍪 SESIÓN (NAVEGADOR):
   - Autenticación tradicional con cookies
   - Uso: Interfaz web browsable de DRF
   - Acceso: Según empresas asignadas al usuario

=== SEGURIDAD NUCLEAR + TOKENS IMPLEMENTADA ===
🔥 SOLO empresas asignadas via UserCompanyAssignment o token específico
🔥 Bloqueo NUCLEAR de acceso no autorizado (403 NUCLEAR_BLOCK/COMPANY_TOKEN_BLOCK)
🔥 Logs de seguridad 🔥🔥🔥 NUCLEAR en cada request
🔥 Autenticación dual automática (detecta tipo de token)
🔥 Sin bypass de permisos - seguridad máxima
🔥 Validación estricta de acceso en cada endpoint
🔥 Estadísticas de uso por token de empresa
🔥 Permisos granulares por token

=== CÓDIGOS DE RESPUESTA NUCLEAR + TOKENS ===
200 OK                     - Operación exitosa y autorizada
201 Created               - Recurso creado exitosamente
400 Bad Request           - Datos inválidos en el request
401 Unauthorized          - Token inválido o ausente
403 NUCLEAR_BLOCK         - ⚠️  ACCESO NUCLEAR BLOQUEADO (usuario) ⚠️
403 COMPANY_TOKEN_BLOCK   - ⚠️  ACCESO TOKEN EMPRESA BLOQUEADO ⚠️
404 Not Found             - Recurso no encontrado
422 Unprocessable Entity  - Error de validación de datos
500 Internal Server Error - Error interno del servidor

=== EJEMPLOS DE USO ===

# Login y obtener tokens
POST /api/auth/login/
{
    "email": "usuario@empresa.com",
    "password": "password123"
}

# Usar token de usuario (múltiples empresas)
Authorization: Token 372a72b56b8bdf7b2d626d3a0df82c37c1600804
GET /api/companies/                               # Ve todas sus empresas
POST /api/sri/documents/create_invoice/
{
    "company_id": 1,
    "customer": {...},
    "items": [...]
}

# Usar token de empresa (empresa específica)
Authorization: Token vsr_ABC123456789...
GET /api/companies/                               # Ve solo SU empresa
POST /api/sri/documents/create_invoice/           # NO necesita company_id
{
    "customer": {...},
    "items": [...]
}

=== CAMBIOS APLICADOS ===
✅ Dual Token Authentication system implementado
✅ CompanyViewSet nuclear con soporte para ambos tipos de token
✅ Auth endpoints para login/logout/profile/status
✅ Detección automática de tipo de token (user vs company)
✅ Seguridad nuclear aplicada a ambos tipos de autenticación
✅ Logs nucleares 🔥🔥🔥 activos para detectar accesos no autorizados
✅ URLs limpias para tokens de empresa (sin company_id)
✅ Compatibilidad total con sistema existente
"""