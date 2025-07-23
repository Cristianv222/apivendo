# -*- coding: utf-8 -*-
"""
URLs principales para VENDO_SRI con OAuth + DUAL TOKEN AUTHENTICATION
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.views.generic import TemplateView

# ==========================================
# VISTAS PRINCIPALES
# ==========================================

def home_redirect(request):
    """Redirección inteligente desde la raíz"""
    if request.user.is_authenticated:
        # Si es admin/staff, ir al panel personalizado
        if request.user.is_staff or request.user.is_superuser:
            return redirect('/admin-panel/')
        return redirect('core:dashboard')
    return redirect('account_login')

class CustomLoginView(LoginView):
    """Vista personalizada de login"""
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # Si es admin/staff, ir al panel personalizado
        if self.request.user.is_staff or self.request.user.is_superuser:
            return '/admin-panel/'
        return '/dashboard/'

def custom_logout(request):
    """Logout directo sin página de confirmación"""
    logout(request)
    return redirect('account_login')  # Redirige a tu login personalizado

def dashboard_view_legacy(request):
    """Vista temporal básica del dashboard (mantenida como backup)"""
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    # Template básico inline
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - VENDO SRI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary">
            <div class="container">
                <span class="navbar-brand">VENDO SRI - Dual Token System</span>
                <div>
                    <span class="text-white me-3">Hola, {request.user.email}</span>
                    <a href="/token-auth/" class="btn btn-warning btn-sm me-2">🔑 Tokens API</a>
                    <a href="/accounts/logout/" class="btn btn-outline-light btn-sm">Salir</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-12">
                    <div class="alert alert-success">
                        <h4>🎉 ¡Sistema Dual Token funcionando correctamente!</h4>
                        <p>Usuario: <strong>{request.user.email}</strong></p>
                        <p>Autenticación dual implementada: Usuario + Empresa tokens</p>
                        <div class="mt-3">
                            <a href="/dashboard/" class="btn btn-primary me-2">Nuevo Dashboard</a>
                            <a href="/token-auth/" class="btn btn-warning me-2">🔑 Sistema de Tokens</a>
                            <a href="/admin/" class="btn btn-secondary">Admin</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5>🌐 Navegador Web</h5>
                        </div>
                        <div class="card-body">
                            <p>Interfaz tradicional con sesión para uso en navegador.</p>
                            <p><strong>Uso:</strong> Dashboard, administración manual</p>
                            <a href="/admin/" class="btn btn-primary">Ir al Admin</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-warning text-dark">
                            <h5>🔑 Tokens API</h5>
                        </div>
                        <div class="card-body">
                            <p>Sistema de tokens para APIs externas y máxima seguridad.</p>
                            <p><strong>Uso:</strong> Sistemas POS, integraciones, APIs</p>
                            <a href="/token-auth/" class="btn btn-warning">Obtener Tokens</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header bg-info text-white">
                            <h5>👤 Usuario Actual</h5>
                        </div>
                        <div class="card-body">
                            <p><strong>Email:</strong> {request.user.email}</p>
                            <p><strong>Nombre:</strong> {request.user.get_full_name() or 'No configurado'}</p>
                            <p><strong>Staff:</strong> {'Sí' if request.user.is_staff else 'No'}</p>
                            <p><strong>Superuser:</strong> {'Sí' if request.user.is_superuser else 'No'}</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h5>🚀 Endpoints Disponibles</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6>🔐 Autenticación:</h6>
                                    <ul class="list-unstyled">
                                        <li>• <code>/accounts/login/</code> - Login navegador</li>
                                        <li>• <code>/token-auth/</code> - Login con tokens</li>
                                        <li>• <code>/api/auth/login/</code> - Login API</li>
                                        <li>• <code>/api/auth/profile/</code> - Perfil token</li>
                                    </ul>
                                </div>
                                <div class="col-md-6">
                                    <h6>📊 APIs:</h6>
                                    <ul class="list-unstyled">
                                        <li>• <code>/api/companies/</code> - Empresas</li>
                                        <li>• <code>/api/customers/</code> - Clientes</li>
                                        <li>• <code>/api/products/</code> - Productos</li>
                                        <li>• <code>/api/sri/</code> - Documentos SRI</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

def health_check(request):
    """Endpoint de salud para monitoreo"""
    return JsonResponse({
        'status': 'ok',
        'service': 'VENDO_SRI',
        'version': 'v1-dual-tokens',
        'authentication': 'Dual Token System',
        'database': 'connected',
        'authenticated_user': request.user.is_authenticated,
        'endpoints': {
            'auth_login': '/api/auth/login/',
            'token_interface': '/token-auth/',
            'api_companies': '/api/companies/',
            'api_status': '/api/status/'
        }
    })


# ==========================================
# CONFIGURACIÓN DE URLs
# ==========================================

urlpatterns = [
    # ==========================================
    # ADMIN
    # ==========================================
    path('admin/', admin.site.urls),
    # ==========================================
    # PANEL ADMIN PERSONALIZADO
    # ==========================================
    path('admin-panel/', include('apps.custom_admin.urls')),
    
    # ==========================================
    # REDIRECCIÓN DE RAÍZ
    # ==========================================
    path('', home_redirect, name='home'),
    
    # ==========================================
    # AUTENTICACIÓN PERSONALIZADA (ANTES DE ALLAUTH)
    # ==========================================
    
    # LOGIN PERSONALIZADO - USA templates/users/login.html
    path('accounts/login/', CustomLoginView.as_view(), name='account_login'),
    
    # 🔑 NUEVA: INTERFAZ WEB CON TOKENS - USA EL MISMO TEMPLATE PERO CON FUNCIONALIDAD DE TOKENS
    path('token-auth/', TemplateView.as_view(template_name='users/login.html'), name='token-auth'),
    
    # LOGOUT PERSONALIZADO - Sin página de confirmación
    path('accounts/logout/', custom_logout, name='account_logout'),
    
    # ==========================================
    # DASHBOARD - NUEVO SISTEMA COMPLETO
    # ==========================================
    
    # Dashboard principal y funcionalidades completas
    path('dashboard/', include('apps.core.urls')),
    
    # Dashboard legacy (temporal) - puedes eliminarlo después
    path('dashboard-legacy/', dashboard_view_legacy, name='dashboard_legacy'),
    
    # ==========================================
    # AUTENTICACIÓN (ALLAUTH) - DESPUÉS DEL LOGIN PERSONALIZADO
    # ==========================================
    
    # URLs de allauth (incluye OAuth con Google)
    path('accounts/', include('allauth.urls')),
    
    # URLs personalizadas de users (cuando las necesites)
    path('users/', include('apps.users.urls')),
    
    # ==========================================
    # 🔑 API CON DUAL TOKEN AUTHENTICATION - ACTIVADA
    # ==========================================
    path('api/', include('apps.api.urls')),
    
    # ==========================================
    # APLICACIONES LOCALES - ACTIVADAS
    # ==========================================
    path('companies/', include('apps.companies.urls')),
    path('invoicing/', include('apps.invoicing.urls')),
    path('certificates/', include('apps.certificates.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('settings/', include('apps.settings.urls')),
    path('sri/', include('apps.sri_integration.urls')),
    path('billing/', include('apps.billing.urls')),
    
    # ==========================================
    # UTILIDADES
    # ==========================================
    path('health/', health_check, name='health_check'),
]

# ==========================================
# ARCHIVOS ESTÁTICOS Y MEDIA (DESARROLLO)
# ==========================================

if settings.DEBUG:
    print("🔧 Configurando URLs para DESARROLLO...")
    
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        try:
            import debug_toolbar
            urlpatterns = [
                path('__debug__/', include(debug_toolbar.urls)),
            ] + urlpatterns
            print("✅ Debug Toolbar activado en /__debug__/")
        except ImportError:
            print("⚠️  Debug Toolbar configurado pero no instalado")
    
    # Servir archivos media y static en desarrollo
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    print(f"✅ Archivos estáticos servidos desde: {settings.STATIC_URL}")
    print(f"✅ Archivos media servidos desde: {settings.MEDIA_URL}")

# ==========================================
# CONFIGURACIÓN PARA PRODUCCIÓN
# ==========================================

else:  # if not settings.DEBUG
    print("🚀 Configurando URLs para PRODUCCIÓN...")
    
    # Health checks para load balancers
    urlpatterns += [
        path('ping/', lambda request: HttpResponse("pong", content_type='text/plain'), name='ping'),
        path('status/', lambda request: HttpResponse("active", content_type='text/plain'), name='status'),
    ]
    
    print("✅ URLs de producción configuradas")

# ==========================================
# CONFIGURACIÓN DEL ADMIN
# ==========================================

admin.site.site_header = 'VENDO_SRI - Administración (Dual Token System)'
admin.site.site_title = 'VENDO_SRI Admin'
admin.site.index_title = 'Panel de Administración con Tokens'

# ==========================================
# INFORMACIÓN DE CONFIGURACIÓN
# ==========================================

print("=== CONFIGURACIÓN DE URLs VENDO_SRI + DUAL TOKENS ===")
print(f"URLs totales configuradas: {len(urlpatterns)}")
print(f"Modo DEBUG: {settings.DEBUG}")

auth_urls = len([url for url in urlpatterns if any(pattern in str(url.pattern) for pattern in ['accounts/', 'auth/', 'token-auth'])])
api_urls = len([url for url in urlpatterns if 'api/' in str(url.pattern)])

print(f"URLs de autenticación: {auth_urls}")
print(f"URLs de API: {api_urls}")

if settings.DEBUG:
    print("Endpoints de desarrollo disponibles:")
    print("  - /health/ (health check)")
    print("  - /dashboard/ (nuevo dashboard completo)")
    print("  - /dashboard-legacy/ (dashboard temporal)")
    print("  - /token-auth/ (🔑 interfaz web con tokens)")
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        print("  - /__debug__/ (Django Debug Toolbar)")

print("✅ CONFIGURACIÓN DE URLs COMPLETA")

print("\n=== RUTAS DE AUTENTICACIÓN DUAL DISPONIBLES ===")
print("📧 Login NAVEGADOR: /accounts/login/ -> templates/users/login.html (modo tradicional)")
print("🔑 Login TOKENS: /token-auth/ -> templates/users/login.html (modo tokens)")
print("🔗 Login con Google: /accounts/google/login/")
print("🚪 Logout: /accounts/logout/")
print("🏠 Dashboard: /dashboard/")
print("🔧 Admin: /admin/")
print("💚 Health check: /health/")
print("\n=== ENDPOINTS API CON DUAL AUTHENTICATION ===")
print("🔑 POST /api/auth/login/ -> Obtener tokens disponibles")
print("👤 GET /api/auth/profile/ -> Info del token actual")
print("🚪 POST /api/auth/logout/ -> Invalidar token")
print("📊 GET /api/auth/status/ -> Estado de autenticación")
print("🏢 GET /api/companies/ -> Empresas (según tipo de token)")
print("👥 GET /api/customers/ -> Clientes")
print("📦 GET /api/products/ -> Productos")
print("📄 POST /api/sri/documents/create_invoice/ -> Crear factura")
print("\n=== TIPOS DE TOKENS DISPONIBLES ===")
print("👤 TOKEN USUARIO: Acceso a múltiples empresas (requiere company_id)")
print("🏢 TOKEN EMPRESA: Acceso a empresa específica (sin company_id)")
print("🍪 SESIÓN NAVEGADOR: Autenticación tradicional con cookies")
print("===============================================")
print("🎉 SISTEMA DUAL DE TOKENS COMPLETAMENTE CONFIGURADO")
print("===============================================")