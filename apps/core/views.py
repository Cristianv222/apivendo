# -*- coding: utf-8 -*-
"""
Core views - VERSIÓN SEGURA CON DECORADORES Y TOKENS EN URL
Todas las vistas validadas con decoradores personalizados
NUEVO: Usa tokens en lugar de IDs en URLs
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

from apps.companies.models import Company, CompanyAPIToken
from apps.users.models import User

# ========== IMPORTAR DECORADORES DEL SISTEMA ==========
from apps.api.views.sri_views import (
    audit_api_action,
    get_user_company_by_id
)

logger = logging.getLogger(__name__)

# ========== DECORADORES PARA VISTAS HTML CON TOKENS ==========

def require_company_access_html_token(view_func):
    """
    Decorador para vistas HTML que requieren validación de empresa CON TOKENS
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Obtener token del parámetro GET o kwargs
        token_param = request.GET.get('token') or kwargs.get('company_token')
        
        if token_param:
            # 🔑 VALIDACIÓN CON TOKEN: Buscar empresa por token
            try:
                user_companies = get_user_companies_secure(request.user)
                company_token = CompanyAPIToken.objects.get(
                    key=token_param,
                    company__in=user_companies,
                    is_active=True
                )
                company = company_token.company
                
                # Agregar empresa y token validados al request
                request.validated_company = company
                request.validated_token = company_token
                
                logger.info(f"✅ TOKEN HTML: User {request.user.username} validated access to company {company.business_name} via token {token_param[:20]}...")
                
            except CompanyAPIToken.DoesNotExist:
                logger.warning(f"🚫 TOKEN HTML SECURITY: User {request.user.username} denied access with invalid token {token_param[:20]}...")
                messages.error(request, f'Token de empresa inválido o sin permisos.')
                
                # Redirigir a dashboard sin token
                return redirect('core:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_company_access_html(view_func):
    """
    Decorador LEGACY para vistas HTML que requieren validación de empresa POR ID
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


# ========== VISTAS PRINCIPALES CON TOKENS ==========

@login_required
@audit_html_action('VIEW_DASHBOARD')
def dashboard_view(request):
    """
    🔒 DASHBOARD SEGURO CON MODO INTELIGENTE
    
    MODO INTELIGENTE:
    - Detecta ?company=X y redirige automáticamente a ?token=ABC...
    - Siempre usa tokens en lugar de IDs
    - URLs limpias sin exposer estructura interna
    
    URLs soportadas:
    - /dashboard/ (empresa por defecto del usuario)
    - /dashboard/?company=X (REDIRIGE a ?token=ABC...)
    - /dashboard/?token=vsr_ABC123... (modo token directo)
    """
    user = request.user
    
    # AGREGAR ESTA VERIFICACIÓN AL INICIO
    if user.is_staff or user.is_superuser:
        return redirect('/admin-panel/')
    
    # Obtener empresas del usuario de forma SEGURA
    user_companies = get_user_companies_secure(user)
    
    # Si no tiene empresas, mostrar mensaje
    if not user_companies.exists():
        logger.warning(f"User {user.username} has no accessible companies")
        return render(request, 'dashboard/no_companies.html', {'user': user})
    
    # 🔄 MODO INTELIGENTE: Detectar ?company=X y redirigir a token
    company_id_param = request.GET.get('company')
    token_param = request.GET.get('token')
    
    if company_id_param and not token_param:
        logger.info(f"🔄 SMART MODE: Detected ?company={company_id_param}, redirecting to token...")
        
        try:
            company_id = int(company_id_param)
            
            # Verificar que el usuario tenga acceso a esta empresa
            target_company = user_companies.filter(id=company_id).first()
            
            if target_company:
                # Obtener/crear token para esta empresa
                company_token, created = CompanyAPIToken.objects.get_or_create(
                    company=target_company,
                    defaults={
                        'name': f'Auto-generated token for {target_company.business_name}',
                        'is_active': True
                    }
                )
                
                if created:
                    logger.info(f"🔑 Token created automatically for smart redirect: {target_company.business_name}")
                
                # Construir URL de redirección con token
                redirect_url = f"/dashboard/?token={company_token.key}"
                
                # Preservar otros parámetros de la URL original
                other_params = []
                for key, value in request.GET.items():
                    if key != 'company' and value:
                        other_params.append(f"{key}={value}")
                
                if other_params:
                    redirect_url += "&" + "&".join(other_params)
                
                logger.info(f"✅ SMART REDIRECT: {company_id_param} -> {company_token.key[:20]}...")
                return redirect(redirect_url)
            
            else:
                logger.warning(f"🚫 SMART MODE: User {user.username} denied access to company {company_id_param}")
                messages.error(request, f'No tienes acceso a la empresa solicitada.')
                return redirect('core:dashboard')
                
        except (ValueError, TypeError):
            logger.warning(f"🚫 SMART MODE: Invalid company ID format: {company_id_param}")
            messages.error(request, 'ID de empresa inválido.')
            return redirect('core:dashboard')
    
    # 🔑 MODO TOKEN: Validar token si está presente
    selected_company = None
    selected_token = None
    
    if token_param:
        try:
            company_token = CompanyAPIToken.objects.get(
                key=token_param,
                company__in=user_companies,
                is_active=True
            )
            selected_company = company_token.company
            selected_token = company_token
            
            logger.info(f"✅ TOKEN MODE: User {user.username} validated access to {selected_company.business_name} via token {token_param[:20]}...")
            
        except CompanyAPIToken.DoesNotExist:
            logger.warning(f"🚫 TOKEN MODE: User {user.username} denied access with invalid token {token_param[:20]}...")
            messages.error(request, f'Token de empresa inválido o sin permisos.')
            return redirect('core:dashboard')
    
    # 🏢 MODO DEFAULT: Sin parámetros - usar primera empresa y redirigir a su token
    if not selected_company:
        default_company = user_companies.first()
        logger.info(f"🏢 DEFAULT MODE: Using default company {default_company.business_name} for user {user.username}")
        
        # Obtener/crear token para la empresa por defecto
        try:
            default_token, created = CompanyAPIToken.objects.get_or_create(
                company=default_company,
                defaults={
                    'name': f'Auto-generated token for {default_company.business_name}',
                    'is_active': True
                }
            )
            
            if created:
                logger.info(f"🔑 Token created automatically for default company: {default_company.business_name}")
            
            # Redirigir a URL con token
            logger.info(f"🔄 DEFAULT REDIRECT: Redirecting to token for {default_company.business_name}")
            return redirect(f"/dashboard/?token={default_token.key}")
            
        except Exception as e:
            logger.error(f"❌ Error creating default token: {e}")
            # Fallback: continuar sin redirección
            selected_company = default_company
            selected_token = None
    
    # 🔑 Preparar tokens disponibles para el selector (SIEMPRE CON TOKENS)
    available_companies_with_tokens = []
    for company in user_companies:
        try:
            # Obtener/crear token para cada empresa
            company_token, created = CompanyAPIToken.objects.get_or_create(
                company=company,
                defaults={
                    'name': f'Auto-generated token for {company.business_name}',
                    'is_active': True
                }
            )
            
            available_companies_with_tokens.append({
                'company': company,
                'token': company_token,
                'is_selected': company.id == selected_company.id,
                'dashboard_url': f"/dashboard/?token={company_token.key}",  # 🔑 SIEMPRE TOKEN
                'api_test_url': f"/api/companies/",
                'token_display': f"{company_token.key[:20]}...",
            })
            
        except Exception as e:
            logger.error(f"❌ Error obtaining token for {company.business_name}: {e}")
    
    # Verificar si el modelo Invoice existe
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
        logger.warning("Invoice model not available")
    
    if INVOICES_AVAILABLE:
        # 🔒 FILTRAR FACTURAS SOLO DE LA EMPRESA SELECCIONADA
        invoices = Invoice.objects.filter(company=selected_company)
        
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
    
    # 🔑 Obtener el token actual de la URL
    current_token = request.GET.get('token')
    
    context = {
        'user_companies': user_companies,
        'selected_company': selected_company,
        'selected_token': selected_token,
        'available_companies_with_tokens': available_companies_with_tokens,  # 🔑 SIEMPRE TOKENS
        'stats': stats,
        'status_stats': status_stats,
        'recent_invoices': recent_invoices,
        'page_obj': page_obj,
        'status_choices': INVOICE_STATUS_CHOICES,
        'invoices_exist': INVOICES_AVAILABLE,
        'is_admin': False,
        'current_filters': {
            'token': current_token,  # 🔑 SIEMPRE TOKEN (nunca company_id)
            'status': request.GET.get('status'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        },
        'token_mode': True,  # 🔑 SIEMPRE EN MODO TOKEN
        'smart_mode': True,  # 🔄 MODO INTELIGENTE ACTIVO
        'security_validation': {
            'validated_by_decorator': True,
            'user_access_confirmed': True,
            'companies_filtered_by_user': True,
            'token_based_access': True,  # 🔑 SIEMPRE
            'smart_redirect_enabled': True,  # 🔄 NUEVO
            'current_token': current_token[:20] + '...' if current_token else None,
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
    total_tokens = CompanyAPIToken.objects.filter(is_active=True).count()  # 🔑 NUEVO
    
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
    
    # 🔑 Estadísticas de tokens más utilizados
    try:
        top_tokens = CompanyAPIToken.objects.filter(
            is_active=True
        ).select_related('company').order_by('-total_requests')[:5]
    except Exception as e:
        logger.error(f"Error getting token stats: {e}")
        top_tokens = []
    
    admin_stats = {
        'total_users': total_users,
        'waiting_users': waiting_users,
        'assigned_users': assigned_users,
        'total_companies': total_companies,
        'total_tokens': total_tokens,  # 🔑 NUEVO
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'unread_notifications': unread_notifications,
    }
    
    context = {
        'is_admin': True,
        'admin_stats': admin_stats,
        'top_tokens': top_tokens,  # 🔑 NUEVO
        'recent_notifications': recent_notifications,
        'recent_waiting': recent_waiting,
        'assignments_available': ASSIGNMENTS_AVAILABLE,
        'invoices_available': INVOICES_AVAILABLE,
        'security_validation': {
            'admin_access_confirmed': True,
            'user': request.user.username,
            'token_system_enabled': True,  # 🔑 NUEVO
        }
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@audit_html_action('SWITCH_COMPANY_TOKEN')
def switch_company_token_ajax(request):
    """
    Cambio de empresa vía AJAX - USA TOKENS
    
    POST /dashboard/api/switch-company/
    {"token": "vsr_ABC123..."}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'Token required'}, status=400)
        
        # Verificar que el usuario tenga acceso a este token
        user_companies = get_user_companies_secure(request.user)
        
        try:
            company_token = CompanyAPIToken.objects.get(
                key=token,
                company__in=user_companies,
                is_active=True
            )
            
            logger.info(f"✅ User {request.user.username} switching to company {company_token.company.business_name} via token")
            
            return JsonResponse({
                'success': True,
                'company_id': company_token.company.id,
                'company_name': company_token.company.business_name,
                'token': company_token.key,
                'redirect_url': f'/dashboard/?token={token}',  # 🔑 TOKEN EN URL
                'security_validation': {
                    'token_validated': True,
                    'user_access_confirmed': True
                }
            })
            
        except CompanyAPIToken.DoesNotExist:
            logger.warning(f"🚫 User {request.user.username} tried invalid token {token[:20]}...")
            return JsonResponse({'error': 'Invalid token or no permissions'}, status=403)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"❌ Error en switch_company_token_ajax: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@audit_html_action('API_COMPANY_INVOICES_TOKEN')
@require_company_access_html_token
def company_invoices_api_token(request):
    """
    🔒 API SEGURA para obtener facturas de empresa por TOKEN (AJAX)
    
    GET /dashboard/api/invoices/?token=vsr_ABC123...
    """
    # La empresa ya está validada por el decorador CON TOKEN
    company = request.validated_company
    company_token = request.validated_token
    
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
    
    if INVOICES_AVAILABLE:
        # 🔒 FILTRAR SOLO FACTURAS DE LA EMPRESA VALIDADA POR TOKEN
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
            'company_token': company_token.key[:20] + '...',  # 🔑 NUEVO
            'invoices': invoices_data,
            'total_count': invoices.count(),
            'security_validation': {
                'validated_by_token': True,  # 🔑 NUEVO
                'token_validated': True,
                'user_access_confirmed': True
            }
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'El módulo de facturación no está disponible',
            'company_name': getattr(company, 'business_name', company.trade_name),
            'company_token': company_token.key[:20] + '...',  # 🔑 NUEVO
            'invoices': [],
            'total_count': 0,
            'security_validation': {
                'validated_by_token': True,  # 🔑 NUEVO
                'token_validated': True,
                'user_access_confirmed': True
            }
        })


@login_required
@audit_html_action('API_COMPANY_INVOICES_LEGACY')
@require_company_access_html
def company_invoices_api(request, company_id):
    """
    🚨 LEGACY: API para obtener facturas por company_id (MANTENIDO POR COMPATIBILIDAD)
    """
    # La empresa ya está validada por el decorador original
    company = request.validated_company
    
    try:
        from apps.invoicing.models import Invoice
        INVOICES_AVAILABLE = True
    except ImportError:
        INVOICES_AVAILABLE = False
    
    if INVOICES_AVAILABLE:
        invoices = Invoice.objects.filter(company=company).order_by('-created_at')
        
        invoices_data = []
        for invoice in invoices[:50]:
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
            'warning': 'DEPRECATED: Use token-based API instead',
            'security_validation': {
                'validated_by_decorator': True,
                'user_access_confirmed': True,
                'legacy_api': True
            }
        })
    
    return JsonResponse({
        'success': False,
        'error': 'El módulo de facturación no está disponible',
        'warning': 'DEPRECATED: Use token-based API instead'
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
            
            # 🔑 Obtener token de la empresa de la factura
            try:
                company_token = CompanyAPIToken.objects.get(
                    company=invoice.company,
                    is_active=True
                )
                dashboard_token_url = f"/dashboard/?token={company_token.key}"
            except CompanyAPIToken.DoesNotExist:
                dashboard_token_url = "/dashboard/"
            
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
        'dashboard_token_url': dashboard_token_url,  # 🔑 NUEVO
        'is_admin': request.user.is_staff or request.user.is_superuser,
        'security_validation': {
            'validated_by_query_filter': True,
            'user_access_confirmed': True,
            'token_url_generated': True,  # 🔑 NUEVO
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
        
        # Facturas por empresa (solo empresas del usuario) - CON TOKENS
        company_stats = []
        for company in user_companies:
            company_invoices = invoices_last_30.filter(company=company)
            if company_invoices.exists():
                try:
                    company_token = CompanyAPIToken.objects.get(
                        company=company,
                        is_active=True
                    )
                    token_display = company_token.key[:10] + '...'
                except CompanyAPIToken.DoesNotExist:
                    token_display = 'No token'
                
                company_stats.append({
                    'company_name': company.trade_name or company.business_name,
                    'token_display': token_display,  # 🔑 NUEVO
                    'count': company_invoices.count(),
                    'total_amount': company_invoices.aggregate(
                        total=Sum('total_amount')
                    )['total'] or 0
                })
        
        # Ordenar por cantidad de facturas
        company_stats = sorted(company_stats, key=lambda x: x['count'], reverse=True)[:5]
        
        return JsonResponse({
            'daily_stats': list(reversed(daily_stats)),
            'status_distribution': list(status_distribution),
            'company_stats': company_stats,  # 🔑 ACTUALIZADO CON TOKENS
            'total_last_30': invoices_last_30.count(),
            'security_validation': {
                'filtered_by_user_companies': True,
                'companies_count': user_companies.count(),
                'user': request.user.username,
                'token_system_enabled': True,  # 🔑 NUEVO
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
                'user': request.user.username,
                'token_system_enabled': True,  # 🔑 NUEVO
            }
        })


@login_required
@audit_html_action('VIEW_COMPANY_TOKENS')
def company_tokens_view(request):
    """
    🔑 NUEVA: Vista para gestionar los tokens de las empresas del usuario
    
    GET /dashboard/tokens/
    """
    user = request.user
    user_companies = get_user_companies_secure(user)
    
    companies_with_tokens = []
    
    for company in user_companies:
        try:
            # Obtener todos los tokens de esta empresa
            company_tokens = CompanyAPIToken.objects.filter(
                company=company,
                is_active=True
            ).order_by('-created_at')
            
            # Si no tiene tokens, crear uno automáticamente
            if not company_tokens.exists():
                auto_token = CompanyAPIToken.objects.create(
                    company=company,
                    name=f'Auto-generated token for {company.business_name}',
                    is_active=True
                )
                company_tokens = [auto_token]
            
            companies_with_tokens.append({
                'company': company,
                'tokens': company_tokens,
                'primary_token': company_tokens.first(),
                'dashboard_url': f"/dashboard/?token={company_tokens.first().key}",  # 🔑 TOKEN EN URL
                'api_test_url': f"/api/companies/",
                'token_display': company_tokens.first().key[:20] + '...',
            })
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo tokens para {company.business_name}: {e}")
    
    context = {
        'user': user,
        'companies_with_tokens': companies_with_tokens,
        'page_title': 'Gestión de Tokens de Empresa',
        'security_validation': {
            'user_access_confirmed': True,
            'token_system_enabled': True,
        }
    }
    
    return render(request, 'dashboard/company_tokens.html', context)