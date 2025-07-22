# -*- coding: utf-8 -*-
"""
Core views - VERSIÓN SEGURA CON DECORADORES Y TOKENS
Todas las vistas validadas con decoradores personalizados
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from functools import wraps

from apps.companies.models import Company
from apps.users.models import User

# ========== IMPORTAR DECORADORES DEL SISTEMA ==========
from apps.api.views.sri_views import (
    audit_api_action,
    get_user_company_by_id
)

logger = logging.getLogger(__name__)

# ========== DECORADORES PARA VISTAS HTML ==========

def require_company_access_html(view_func):
    """
    Decorador para vistas HTML que requieren validación de empresa
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Obtener company_id del parámetro GET o kwargs
        company_id = request.GET.get('company') or kwargs.get('company_id')
        
        if company_id:
            # 🔒 VALIDACIÓN CRÍTICA: Solo empresas del usuario
            company = get_user_company_by_id(company_id, request.user)
            
            if not company:
                logger.warning(f"🚫 HTML SECURITY: User {request.user.username} denied access to company {company_id}")
                messages.error(request, f'You do not have access to company {company_id}.')
                
                # Redirigir a dashboard sin company parameter
                return redirect('core:dashboard')
            
            # Agregar empresa validada al request
            request.validated_company = company
            logger.info(f"✅ HTML: User {request.user.username} validated access to company {company_id}")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def audit_html_action(action_type):
    """
    Decorador de auditoría para vistas HTML
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = timezone.now()
            
            logger.info(f"🌐 [{action_type}] User {request.user.username} - {view_func.__name__} - Started")
            
            try:
                response = view_func(request, *args, **kwargs)
                execution_time = (timezone.now() - start_time).total_seconds()
                logger.info(f"✅ [{action_type}] User {request.user.username} - SUCCESS - {execution_time:.2f}s")
                return response
            except Exception as e:
                execution_time = (timezone.now() - start_time).total_seconds()
                logger.error(f"❌ [{action_type}] User {request.user.username} - ERROR: {str(e)} - {execution_time:.2f}s")
                raise
        return wrapper
    return decorator


def get_user_companies_secure(user):
    """
    Función auxiliar SEGURA CORREGIDA - USA EL HELPER QUE FUNCIONA
    """
    from apps.api.user_company_helper import get_user_companies_exact
    return get_user_companies_exact(user)


# ========== VISTAS PRINCIPALES CON DECORADORES ==========

@login_required
@audit_html_action('VIEW_DASHBOARD')
@require_company_access_html
def dashboard_view(request):
    """
    🔒 DASHBOARD SEGURO CON DECORADORES
    """
    user = request.user
    
    # Si es admin/staff, mostrar dashboard administrativo
    if user.is_staff or user.is_superuser:
        return admin_dashboard_view(request)
    
    # Obtener empresas del usuario de forma SEGURA
    user_companies = get_user_companies_secure(user)
    
    # Si no tiene empresas, mostrar mensaje
    if not user_companies.exists():
        logger.warning(f"User {user.username} has no accessible companies")
        return render(request, 'dashboard/no_companies.html', {'user': user})
    
    # Empresa seleccionada (ya validada por decorador)
    selected_company = getattr(request, 'validated_company', None)
    
    # Si no hay empresa seleccionada, usar la primera
    if not selected_company:
        selected_company = user_companies.first()
        logger.info(f"Using default company {selected_company.id} for user {user.username}")
    
    # Verificar si el modelo Invoice existe
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
        logger.warning("Invoice model not available")
    
    if INVOICES_AVAILABLE:
        # 🔒 FILTRAR FACTURAS SOLO DE EMPRESAS DEL USUARIO
        if selected_company:
            invoices = Invoice.objects.filter(company=selected_company)
        else:
            invoices = Invoice.objects.filter(company__in=user_companies)
        
        # Filtros adicionales
        status_filter = request.GET.get('status')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                invoices = invoices.filter(created_at__date__gte=date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                invoices = invoices.filter(created_at__date__lte=date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        # Estadísticas
        stats = {
            'total_invoices': invoices.count(),
            'pending_invoices': invoices.filter(status='pending').count(),
            'authorized_invoices': invoices.filter(status='authorized').count(),
            'rejected_invoices': invoices.filter(status='rejected').count(),
            'total_amount': invoices.aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        # Estadísticas por estado
        status_stats = invoices.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('status')
        
        # Facturas recientes (últimas 10)
        recent_invoices = invoices.order_by('-created_at')[:10]
        
        # Paginación
        paginator = Paginator(invoices.order_by('-created_at'), 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
    else:
        # Datos ficticios si no existe Invoice
        stats = {
            'total_invoices': 0,
            'pending_invoices': 0,
            'authorized_invoices': 0,
            'rejected_invoices': 0,
            'total_amount': 0,
        }
        status_stats = []
        recent_invoices = []
        page_obj = None
    
    # Estados disponibles para el filtro
    INVOICE_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('authorized', 'Autorizada'),
        ('rejected', 'Rechazada'),
        ('cancelled', 'Cancelada'),
        ('sent', 'Enviada'),
    ]
    
    context = {
        'user_companies': user_companies,
        'selected_company': selected_company,
        'stats': stats,
        'status_stats': status_stats,
        'recent_invoices': recent_invoices,
        'page_obj': page_obj,
        'status_choices': INVOICE_STATUS_CHOICES,
        'invoices_exist': INVOICES_AVAILABLE,
        'is_admin': False,
        'current_filters': {
            'company': selected_company.id if selected_company else None,
            'status': request.GET.get('status'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        },
        'security_validation': {
            'validated_by_decorator': True,
            'user_access_confirmed': True,
            'companies_filtered_by_user': True
        }
    }
    
    return render(request, 'dashboard/user_dashboard.html', context)


@login_required
@audit_html_action('VIEW_ADMIN_DASHBOARD')
def admin_dashboard_view(request):
    """
    🔒 DASHBOARD ADMINISTRATIVO SEGURO
    """
    if not (request.user.is_staff or request.user.is_superuser):
        logger.warning(f"Non-admin user {request.user.username} tried to access admin dashboard")
        messages.error(request, 'Access denied. Administrator privileges required.')
        return redirect('core:dashboard')
    
    # Estadísticas generales para admins
    total_users = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_companies = Company.objects.count()
    
    try:
        from apps.users.models import UserCompanyAssignment, AdminNotification
        ASSIGNMENTS_AVAILABLE = True
        
        waiting_users = UserCompanyAssignment.objects.filter(status='waiting').count()
        assigned_users = UserCompanyAssignment.objects.filter(status='assigned').count()
        unread_notifications = AdminNotification.objects.filter(is_read=False).count()
        recent_notifications = AdminNotification.objects.filter(is_read=False)[:5]
        recent_waiting = UserCompanyAssignment.objects.filter(
            status='waiting'
        ).select_related('user').order_by('-created_at')[:10]
        
    except ImportError:
        ASSIGNMENTS_AVAILABLE = False
        waiting_users = 0
        assigned_users = total_users
        unread_notifications = 0
        recent_notifications = []
        recent_waiting = []
    
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
        total_invoices = Invoice.objects.count()
        pending_invoices = Invoice.objects.filter(status='pending').count()
    except ImportError:
        INVOICES_AVAILABLE = False
        total_invoices = 0
        pending_invoices = 0
    
    admin_stats = {
        'total_users': total_users,
        'waiting_users': waiting_users,
        'assigned_users': assigned_users,
        'total_companies': total_companies,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'unread_notifications': unread_notifications,
    }
    
    context = {
        'is_admin': True,
        'admin_stats': admin_stats,
        'recent_notifications': recent_notifications,
        'recent_waiting': recent_waiting,
        'assignments_available': ASSIGNMENTS_AVAILABLE,
        'invoices_available': INVOICES_AVAILABLE,
        'security_validation': {
            'admin_access_confirmed': True,
            'user': request.user.username
        }
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@audit_html_action('API_COMPANY_INVOICES')
@require_company_access_html
def company_invoices_api(request, company_id):
    """
    🔒 API SEGURA para obtener facturas de empresa (AJAX)
    """
    # La empresa ya está validada por el decorador
    company = request.validated_company
    
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
    
    if INVOICES_AVAILABLE:
        # 🔒 FILTRAR SOLO FACTURAS DE LA EMPRESA VALIDADA
        invoices = Invoice.objects.filter(company=company).order_by('-created_at')
        
        invoices_data = []
        for invoice in invoices[:50]:  # Limitar para performance
            invoices_data.append({
                'id': invoice.id,
                'invoice_number': getattr(invoice, 'invoice_number', ''),
                'total_amount': float(invoice.total_amount or 0),
                'status': invoice.status,
                'status_display': invoice.get_status_display() if hasattr(invoice, 'get_status_display') else invoice.status,
                'created_at': invoice.created_at.strftime('%d/%m/%Y %H:%M'),
                'client_name': getattr(invoice, 'client_name', ''),
            })
        
        return JsonResponse({
            'success': True,
            'company_name': getattr(company, 'business_name', company.trade_name),
            'invoices': invoices_data,
            'total_count': invoices.count(),
            'security_validation': {
                'validated_by_decorator': True,
                'user_access_confirmed': True
            }
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'El módulo de facturación no está disponible',
            'company_name': getattr(company, 'business_name', company.trade_name),
            'invoices': [],
            'total_count': 0,
            'security_validation': {
                'validated_by_decorator': True,
                'user_access_confirmed': True
            }
        })


@login_required
@audit_html_action('VIEW_INVOICE_DETAIL')
def invoice_detail_view(request, invoice_id):
    """
    🔒 VISTA SEGURA de detalle de factura
    """
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        from django.http import Http404
        raise Http404("La funcionalidad de facturas no está disponible")
    
    # 🔒 VALIDACIÓN CRÍTICA: Solo facturas de empresas del usuario
    user_companies = get_user_companies_secure(request.user)
    
    if user_companies.exists():
        try:
            invoice = Invoice.objects.select_related('company').get(
                id=invoice_id,
                company__in=user_companies
            )
            logger.info(f"✅ User {request.user.username} accessing invoice {invoice_id}")
        except Invoice.DoesNotExist:
            logger.warning(f"❌ User {request.user.username} denied access to invoice {invoice_id}")
            from django.http import Http404
            raise Http404("Invoice not found or access denied")
    else:
        logger.warning(f"❌ User {request.user.username} has no companies for invoice access")
        from django.http import Http404
        raise Http404("No accessible companies")
    
    context = {
        'invoice': invoice,
        'company': invoice.company,
        'is_admin': request.user.is_staff or request.user.is_superuser,
        'security_validation': {
            'validated_by_query_filter': True,
            'user_access_confirmed': True
        }
    }
    
    return render(request, 'dashboard/invoice_detail.html', context)


@login_required
@audit_html_action('API_DASHBOARD_STATS')
def dashboard_stats_api(request):
    """
    🔒 API SEGURA para estadísticas del dashboard
    """
    # Obtener empresas del usuario de forma SEGURA
    user_companies = get_user_companies_secure(request.user)
    
    if not user_companies.exists():
        return JsonResponse({
            'error': 'No accessible companies',
            'security_validation': {
                'user_access_confirmed': False,
                'companies_count': 0
            }
        })
    
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
    
    if INVOICES_AVAILABLE:
        # 🔒 ESTADÍSTICAS SOLO DE EMPRESAS DEL USUARIO
        last_30_days = timezone.now() - timedelta(days=30)
        invoices_last_30 = Invoice.objects.filter(
            company__in=user_companies,
            created_at__gte=last_30_days
        )
        
        # Facturas por día (últimos 7 días)
        daily_stats = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = invoices_last_30.filter(created_at__date=date).count()
            daily_stats.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })
        
        # Facturas por estado
        status_distribution = invoices_last_30.values('status').annotate(
            count=Count('id')
        )
        
        # Facturas por empresa (solo empresas del usuario)
        company_stats = invoices_last_30.values('company__trade_name').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('-count')[:5]
        
        return JsonResponse({
            'daily_stats': list(reversed(daily_stats)),
            'status_distribution': list(status_distribution),
            'company_stats': list(company_stats),
            'total_last_30': invoices_last_30.count(),
            'security_validation': {
                'filtered_by_user_companies': True,
                'companies_count': user_companies.count(),
                'user': request.user.username
            }
        })
        
    else:
        return JsonResponse({
            'daily_stats': [],
            'status_distribution': [],
            'company_stats': [],
            'total_last_30': 0,
            'error': 'Módulo de facturación no disponible',
            'security_validation': {
                'filtered_by_user_companies': True,
                'companies_count': user_companies.count(),
                'user': request.user.username
            }
        })
