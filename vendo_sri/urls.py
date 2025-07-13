# -*- coding: utf-8 -*-
"""
URLs principales para VENDO_SRI con OAuth
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse

# ==========================================
# VISTAS PRINCIPALES
# ==========================================

def home_redirect(request):
    """Redirección inteligente desde la raíz"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')  # Actualizado para usar el nuevo dashboard
    return redirect('account_login')

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
                <span class="navbar-brand">VENDO SRI</span>
                <div>
                    <span class="text-white me-3">Hola, {request.user.email}</span>
                    <a href="/accounts/logout/" class="btn btn-outline-light btn-sm">Salir</a>
                </div>
            </div>
        </nav>
        <div class="container mt-4">
            <div class="row">
                <div class="col-12">
                    <div class="alert alert-success">
                        <h4>¡Sistema funcionando correctamente!</h4>
                        <p>Usuario: <strong>{request.user.email}</strong></p>
                        <p>Las migraciones y configuración están listas.</p>
                        <div class="mt-3">
                            <a href="/dashboard/" class="btn btn-primary me-2">Nuevo Dashboard</a>
                            <a href="/admin/" class="btn btn-secondary">Admin</a>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Panel de Administración</h5>
                        </div>
                        <div class="card-body">
                            <p>Accede al panel de administración para gestionar usuarios, empresas y configuración.</p>
                            <a href="/admin/" class="btn btn-primary">Ir al Admin</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Información del Usuario</h5>
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
        'database': 'connected',
        'authenticated_user': request.user.is_authenticated
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
    # REDIRECCIÓN DE RAÍZ
    # ==========================================
    path('', home_redirect, name='home'),
    
    # ==========================================
    # DASHBOARD - NUEVO SISTEMA COMPLETO
    # ==========================================
    
    # Dashboard principal y funcionalidades completas
    path('dashboard/', include('apps.core.urls')),
    
    # Dashboard legacy (temporal) - puedes eliminarlo después
    path('dashboard-legacy/', dashboard_view_legacy, name='dashboard_legacy'),
    
    # ==========================================
    # AUTENTICACIÓN (ALLAUTH)
    # ==========================================
    
    # URLs de allauth (incluye OAuth con Google)
    path('accounts/', include('allauth.urls')),
    
    # URLs personalizadas de users (cuando las necesites)
    path('users/', include('apps.users.urls')),
    
    # ==========================================
    # APLICACIONES LOCALES - ACTIVADAS GRADUALMENTE
    # ==========================================
<<<<<<< Updated upstream
    
    # API - Ya puedes activar esto
    # path('api/', include('apps.api.urls')),
    
    # Empresas - Necesario para el dashboard
    # path('companies/', include('apps.companies.urls')),
    
    # Facturación - Necesario para el dashboard
    # path('invoicing/', include('apps.invoicing.urls')),
    
    # Otras apps (activar según necesites)
    # path('certificates/', include('apps.certificates.urls')),
    # path('notifications/', include('apps.notifications.urls')),
    # path('settings/', include('apps.settings.urls')),
    # path('sri/', include('apps.sri_integration.urls')),
=======
    path('api/', include('apps.api.urls')),
    path('companies/', include('apps.companies.urls')),
    path('invoicing/', include('apps.invoicing.urls')),
    path('certificates/', include('apps.certificates.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('settings/', include('apps.settings.urls')),
    path('sri/', include('apps.sri_integration.urls')),
>>>>>>> Stashed changes
    
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

admin.site.site_header = 'VENDO_SRI - Administración'
admin.site.site_title = 'VENDO_SRI Admin'
<<<<<<< Updated upstream
admin.site.index_title = 'Panel de Administración'

# ==========================================
# INFORMACIÓN DE CONFIGURACIÓN
# ==========================================

print("=== CONFIGURACIÓN DE URLs VENDO_SRI ===")
print(f"URLs totales configuradas: {len(urlpatterns)}")
print(f"Modo DEBUG: {settings.DEBUG}")

auth_urls = len([url for url in urlpatterns if any(pattern in str(url.pattern) for pattern in ['accounts/', 'auth/'])])
api_urls = len([url for url in urlpatterns if 'api/' in str(url.pattern)])

print(f"URLs de autenticación: {auth_urls}")
print(f"URLs de API: {api_urls}")

if settings.DEBUG:
    print("Endpoints de desarrollo disponibles:")
    print("  - /health/ (health check)")
    print("  - /dashboard/ (nuevo dashboard completo)")
    print("  - /dashboard-legacy/ (dashboard temporal)")
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        print("  - /__debug__/ (Django Debug Toolbar)")

print("✅ CONFIGURACIÓN DE URLs COMPLETA")

print("\n=== RUTAS DE AUTENTICACIÓN DISPONIBLES ===")
print("📧 Login con email: /accounts/login/")
print("🔗 Login con Google: /accounts/google/login/")
print("🚪 Logout: /accounts/logout/")
print("🏠 Dashboard: /dashboard/")
print("🔧 Admin: /admin/")
print("💚 Health check: /health/")
print("===============================================")
=======
admin.site.index_title = 'Panel de Administración'
>>>>>>> Stashed changes
