from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard principal con validación automática
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # APIs AJAX con validación de empresa
    path('api/company/<int:company_id>/invoices/', views.company_invoices_api, name='company_invoices_api'),
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # Vista detallada de factura con validación
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
    
]

# Session URLs si están disponibles
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