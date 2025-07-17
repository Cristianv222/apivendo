from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # APIs para AJAX
    path('api/company/<int:company_id>/invoices/', views.company_invoices_api, name='company_invoices_api'),
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # Vista detallada de factura
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
]

# Verificar si session_views existe antes de importar
try:
    from . import session_views
    
    # Si existe, agregar las URLs de sesión
    session_urlpatterns = [
        path('api/session/heartbeat/', session_views.session_heartbeat, name='session_heartbeat'),
        path('api/session/check/', session_views.check_session_status, name='check_session'),
        path('api/session/extend/', session_views.extend_session, name='extend_session'),
        path('api/session/info/', session_views.get_session_info, name='session_info'),
    ]
    
    urlpatterns.extend(session_urlpatterns)
    
except ImportError:
    # Si no existe session_views, continuar sin esas URLs
    print("Advertencia: session_views no encontrado. URLs de sesión no disponibles.")
    pass