# -*- coding: utf-8 -*-
"""
URLs principales para VENDO_SRI con OAuth
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse
from apps.users.views import dashboard_view

def home_redirect(request):
    """Redirección inteligente desde la raíz"""
    if request.user.is_authenticated:
        if request.user.is_pending_approval():
            return redirect('users:waiting_room')
        elif request.user.is_rejected():
            return redirect('users:account_rejected')
        elif request.user.is_approved():
            return redirect('dashboard')
    
    return redirect('account_login')

def health_check(request):
    """Endpoint de salud para monitoreo"""
    return HttpResponse("OK - VENDO_SRI", content_type='text/plain')

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
    # DASHBOARD
    # ==========================================
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # ==========================================
    # AUTENTICACIÓN (ALLAUTH + CUSTOM)
    # ==========================================
    
    # URLs de allauth (incluye OAuth con Google)
    path('accounts/', include('allauth.urls')),
    
    # URLs personalizadas de users (sala de espera, etc.)
    path('accounts/', include('apps.users.urls')),
    
    # ==========================================
    # APLICACIONES LOCALES
    # ==========================================
    path('api/', include('apps.api.urls')),
    # path('companies/', include('apps.companies.urls')),
    # path('invoicing/', include('apps.invoicing.urls')),
    # path('certificates/', include('apps.certificates.urls')),
    # path('notifications/', include('apps.notifications.urls')),
    # path('settings/', include('apps.settings.urls')),
    # path('sri/', include('apps.sri_integration.urls')),
    
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
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        print("  - /__debug__/ (Django Debug Toolbar)")

print("✅ CONFIGURACIÓN DE URLs COMPLETA")

print("\n=== RUTAS DE AUTENTICACIÓN DISPONIBLES ===")
print("📧 Login con email: /accounts/login/")
print("🔗 Login con Google: /accounts/google/login/")
print("🚪 Logout: /accounts/logout/")
print("⏳ Sala de espera: /accounts/waiting-room/")
print("❌ Cuenta rechazada: /accounts/account-rejected/")
print("👥 Gestión usuarios (admin): /accounts/pending-approval/")
print("🏠 Dashboard: /dashboard/")
print("===============================================")