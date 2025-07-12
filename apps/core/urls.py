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