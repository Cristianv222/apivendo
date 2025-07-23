# apps/custom_admin/urls.py
from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Users CRUD
    path('users/', views.users_list, name='users'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/view/', views.user_view, name='user_view'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:user_id>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    
    # Companies CRUD
    path('companies/', views.companies_list, name='companies'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<int:company_id>/edit/', views.company_edit, name='company_edit'),
    path('companies/<int:company_id>/view/', views.company_view, name='company_view'),
    path('companies/<int:company_id>/delete/', views.company_delete, name='company_delete'),
    path('companies/<int:company_id>/toggle-status/', views.company_toggle_status, name='company_toggle_status'),
    
    # Certificates CRUD
    path('certificates/', views.certificates_list, name='certificates'),
    path('certificates/upload/', views.certificate_upload, name='certificate_upload'),
    path('certificates/<int:certificate_id>/view/', views.certificate_view, name='certificate_view'),
    path('certificates/<int:certificate_id>/delete/', views.certificate_delete, name='certificate_delete'),
    path('certificates/<int:certificate_id>/validate/', views.certificate_validate, name='certificate_validate'),
    
    # Invoices (placeholder)
    path('invoices/', views.invoices_list, name='invoices'),
        # Invoice URLs
    path('invoices/', views.invoices_list, name='invoices'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:invoice_id>/view/', views.invoice_view, name='invoice_view'),
    path('invoices/<int:invoice_id>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:invoice_id>/authorize/', views.invoice_authorize, name='invoice_authorize'),
    path('invoices/<int:invoice_id>/cancel/', views.invoice_cancel, name='invoice_cancel'),
    path('invoices/<int:invoice_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/batch-authorize/', views.invoice_batch_authorize, name='invoice_batch_authorize'),
    
    
    # Customers (placeholder)
    path('customers/', views.customers_list, name='customers'),
    
    # Products (placeholder)
    path('products/', views.products_list, name='products'),
    
    # SRI Documents (placeholder)
    path('sri-documents/', views.sri_documents_list, name='sri_documents'),
    
    # Settings
    path('settings/', views.settings_list, name='settings'),
    path('settings/system/', views.system_settings, name='system_settings'),
    path('settings/companies/', views.company_settings, name='company_settings'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # Export
    path('export/<str:model_name>/', views.export_data, name='export_data'),
    
    # API endpoints
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/search/', views.global_search, name='global_search'),
]