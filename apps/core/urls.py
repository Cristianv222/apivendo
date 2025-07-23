# -*- coding: utf-8 -*-
"""
Core URLs - VERSIÓN COMPLETA CON TOKENS
apps/core/urls.py
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ==========================================
    # DASHBOARD PRINCIPAL CON TOKENS
    # ==========================================
    
    # Dashboard principal con validación automática de tokens
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # ==========================================
    # 🔑 NUEVAS APIs CON TOKENS (REEMPLAZA LAS DE IDs)
    # ==========================================
    
    # 🔑 API para cambio de empresa con tokens (AJAX)
    path('api/switch-company/', views.switch_company_token_ajax, name='switch_company_token'),
    
    # 🔑 API para obtener facturas por token (AJAX)
    path('api/invoices/', views.company_invoices_api_token, name='company_invoices_api_token'),
    
    # API para estadísticas del dashboard (actualizada con soporte tokens)
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # ==========================================
    # 🔑 GESTIÓN DE TOKENS
    # ==========================================
    
    # Vista para ver y gestionar tokens de empresas
    path('tokens/', views.company_tokens_view, name='company_tokens'),
    
    # ==========================================
    # APIs LEGACY CON IDs (MANTENIDAS PARA COMPATIBILIDAD)
    # ==========================================
    
    # 🚨 DEPRECATED: API con company_id (mantener por compatibilidad)
    path('api/company/<int:company_id>/invoices/', views.company_invoices_api, name='company_invoices_api'),
    
    # ==========================================
    # VISTAS DE DETALLE
    # ==========================================
    
    # Vista detallada de factura con validación
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
]

# ==========================================
# Session URLs si están disponibles
# ==========================================
try:
    from . import session_views
    
    session_urlpatterns = [
        path('api/session/heartbeat/', session_views.session_heartbeat, name='session_heartbeat'),
        path('api/session/check/', session_views.check_session_status, name='check_session'),
        path('api/session/extend/', session_views.extend_session, name='extend_session'),
        path('api/session/info/', session_views.get_session_info, name='session_info'),
    ]
    
    urlpatterns.extend(session_urlpatterns)
    
except ImportError:
    pass

# ==========================================
# DOCUMENTACIÓN DE URLs CON TOKENS
# ==========================================

"""
ENDPOINTS DISPONIBLES CON SISTEMA DE TOKENS:

=== 📊 DASHBOARD CON TOKENS ===
GET  /dashboard/                                  # Dashboard principal
GET  /dashboard/?token=vsr_ABC123...              # Dashboard empresa específica por token

=== 🔑 APIs CON TOKENS (NUEVAS) ===
POST /dashboard/api/switch-company/               # Cambiar empresa por token
     Body: {"token": "vsr_ABC123..."}
     
GET  /dashboard/api/invoices/?token=vsr_ABC123... # Facturas por token
GET  /dashboard/api/dashboard/stats/              # Estadísticas (con soporte tokens)

=== 🛠️ GESTIÓN DE TOKENS ===
GET  /dashboard/tokens/                           # Ver/gestionar tokens de empresas

=== 📄 VISTAS DE DETALLE ===
GET  /dashboard/invoice/<id>/                     # Detalle de factura (con token_url generado)

=== 🔄 SESIÓN (Si disponible) ===
GET  /dashboard/api/session/heartbeat/            # Heartbeat de sesión  
GET  /dashboard/api/session/check/                # Estado de sesión
POST /dashboard/api/session/extend/               # Extender sesión
GET  /dashboard/api/session/info/                 # Info de sesión

=== 🚨 DEPRECATED (Mantenido por compatibilidad) ===
GET  /dashboard/api/company/<id>/invoices/        # Facturas por company_id (legacy)

=== EJEMPLOS DE USO CON TOKENS ===

# Acceso al dashboard con token específico
http://localhost:8000/dashboard/?token=vsr_J--XtSkkiM0XvhAwYqG1Lt3A-Ex35PN3pzk-569c4ktm

# Cambio de empresa vía AJAX
fetch('/dashboard/api/switch-company/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
        'token': 'vsr_vMixnpkhwTx-N6PLyBiEPsCf5UB4Cxv5x3ZRy5gEETbK'
    })
})

# Obtener facturas por token
fetch('/dashboard/api/invoices/?token=vsr_ABC123...', {
    method: 'GET',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
})

=== VENTAJAS DEL SISTEMA DE TOKENS ===
✅ URLs seguras sin exposer IDs internos
✅ Tokens como identificadores públicos
✅ Compatibilidad con API externa
✅ Consistencia entre dashboard y API
✅ Fácil integración con sistemas externos
✅ Trazabilidad y auditoría por token
✅ Escalabilidad para múltiples integraciones

=== MIGRACIÓN GRADUAL ===
- URLs con tokens: Recomendadas y activas
- URLs con IDs: Mantenidas por compatibilidad (deprecated)
- Redirección automática: Dashboard sin parámetros -> primera empresa del usuario
- Auto-creación de tokens: Si empresa no tiene token, se crea automáticamente

=== SEGURIDAD ===
🔒 Tokens validados por decorador @require_company_access_html_token
🔒 Solo tokens de empresas asignadas al usuario
🔒 Logs de auditoría en cada acceso
🔒 Auto-creación controlada de tokens
🔒 Invalidación de tokens comprometidos
🔒 Compatibilidad con autenticación dual (usuario + empresa)
"""