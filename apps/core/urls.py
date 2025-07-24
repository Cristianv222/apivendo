# -*- coding: utf-8 -*-
"""
Core URLs - VERSIÓN COMPLETA CON TOKENS Y EDICIÓN DE EMPRESA
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
    # 🏢 GESTIÓN DE EMPRESAS Y CERTIFICADOS
    # ==========================================
    
    # 🔑 Actualización de empresa (requiere company_id por seguridad)
    path('company/<int:company_id>/update/', views.company_update, name='company_update'),
    
    # 🔑 Carga de certificado digital
    path('company/<int:company_id>/certificate/upload/', views.certificate_upload, name='certificate_upload'),
    
    # 🔑 Información de empresa para modal (AJAX)
    path('company/<int:company_id>/info/', views.company_info_modal, name='company_info_modal'),
    
    # Selección de empresa (redirección)
    path('company/<int:company_id>/select/', views.company_select, name='company_select'),
    
    # Dashboard específico de empresa
    path('company/<int:company_id>/dashboard/', views.company_dashboard, name='company_dashboard'),
    
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

=== 🏢 GESTIÓN DE EMPRESAS Y CERTIFICADOS (NUEVO) ===
POST /dashboard/company/<id>/update/              # Actualizar información de empresa
     Requiere: Formulario multipart con datos de empresa
     
POST /dashboard/company/<id>/certificate/upload/  # Subir certificado digital
     Requiere: certificate_file, certificate_password, alias (opcional)
     
GET  /dashboard/company/<id>/info/                # Info de empresa para modal (AJAX)
GET  /dashboard/company/<id>/select/              # Seleccionar empresa (redirección)
GET  /dashboard/company/<id>/dashboard/           # Dashboard específico de empresa

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

=== EJEMPLOS DE USO CON TOKENS Y EDICIÓN ===

# Acceso al dashboard con token específico
http://localhost:8000/dashboard/?token=vsr_J--XtSkkiM0XvhAwYqG1Lt3A-Ex35PN3pzk-569c4ktm

# Actualización de empresa vía AJAX
const formData = new FormData();
formData.append('business_name', 'Nueva Razón Social');
formData.append('email', 'nuevo@email.com');
// ... otros campos

fetch('/dashboard/company/123/update/', {
    method: 'POST',
    headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: formData
})

# Carga de certificado digital
const certForm = new FormData();
certForm.append('certificate_file', fileInput.files[0]);
certForm.append('certificate_password', 'contraseña123');
certForm.append('certificate_alias', 'Certificado Principal');

fetch('/dashboard/company/123/certificate/upload/', {
    method: 'POST',
    headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: certForm
})

# Cambio de empresa vía AJAX con token
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

=== VENTAJAS DEL SISTEMA INTEGRADO ===
✅ URLs seguras sin exposer IDs internos (tokens)
✅ Edición completa de empresa con validación SRI
✅ Gestión segura de certificados digitales
✅ Compatibilidad con API externa
✅ Consistencia entre dashboard y API
✅ Fácil integración con sistemas externos
✅ Trazabilidad y auditoría por token
✅ Escalabilidad para múltiples integraciones

=== SEGURIDAD MEJORADA ===
🔒 Tokens validados por decorador @require_company_access_html_token
🔒 Solo tokens de empresas asignadas al usuario
🔒 Certificados encriptados con PBKDF2
🔒 Validación de permisos en cada operación
🔒 Logs de auditoría en cada acceso
🔒 Auto-creación controlada de tokens
🔒 Invalidación de tokens comprometidos
🔒 Compatibilidad con autenticación dual (usuario + empresa)

=== MIGRACIÓN GRADUAL ===
- URLs con tokens: Recomendadas y activas
- URLs con IDs: Para operaciones sensibles (update, certificate)
- Redirección automática: Dashboard sin parámetros -> primera empresa del usuario
- Auto-creación de tokens: Si empresa no tiene token, se crea automáticamente
"""