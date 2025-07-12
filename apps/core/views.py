from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from apps.companies.models import Company
from apps.users.models import User

# Intentar importar Invoice, si no existe, crear una clase temporal
try:
    from apps.invoicing.models import Invoice
    INVOICES_AVAILABLE = True
except ImportError:
    INVOICES_AVAILABLE = False

# Importar modelos de asignación
try:
    from apps.users.models import UserCompanyAssignment, AdminNotification
    ASSIGNMENTS_AVAILABLE = True
except ImportError:
    ASSIGNMENTS_AVAILABLE = False


@login_required
def dashboard_view(request):
    """Dashboard principal para usuarios - con control de asignaciones"""
    user = request.user
    
    # Si es admin/staff, mostrar dashboard administrativo
    if user.is_staff or user.is_superuser:
        return admin_dashboard_view(request)
    
    # Verificar asignación del usuario
    if ASSIGNMENTS_AVAILABLE:
        try:
            assignment = UserCompanyAssignment.objects.get(user=user)
            
            # Si no está asignado, redirigir a sala de espera
            if not assignment.is_assigned():
                return redirect('users:waiting_room')
            
            # Obtener empresas asignadas
            user_companies = assignment.get_assigned_companies()
            
        except UserCompanyAssignment.DoesNotExist:
            # Si no tiene asignación, redirigir a sala de espera
            return redirect('users:waiting_room')
    else:
        # Fallback: usar el sistema original de empresas
        user_companies = user.companies.all() if hasattr(user, 'companies') else Company.objects.filter(users=user)
        
        # Si no hay relación directa, crear empresas de ejemplo
        if not user_companies.exists():
            user_companies = Company.objects.all()[:5]  # Limitar a 5 para demo
    
    # Si no tiene empresas asignadas
    if not user_companies.exists():
        return render(request, 'dashboard/no_companies.html', {'user': user})
    
    # Filtro por empresa si se selecciona una específica
    selected_company_id = request.GET.get('company')
    selected_company = None
    
    if selected_company_id:
        selected_company = get_object_or_404(
            Company, 
            id=selected_company_id, 
            id__in=user_companies.values_list('id', flat=True)
        )
    
    # Verificar si el modelo Invoice existe
    if INVOICES_AVAILABLE:
        if selected_company:
            invoices = Invoice.objects.filter(company=selected_company)
        else:
            # Mostrar facturas de todas las empresas asignadas
            invoices = Invoice.objects.filter(company__in=user_companies)
        
        # Filtros adicionales
        status_filter = request.GET.get('status')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            invoices = invoices.filter(created_at__date__gte=date_from)
        
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            invoices = invoices.filter(created_at__date__lte=date_to)
        
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
        
        # Paginación para todas las facturas
        paginator = Paginator(invoices.order_by('-created_at'), 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
    else:
        # Si no existe el modelo Invoice, crear datos ficticios
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
            'company': selected_company_id,
            'status': request.GET.get('status'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        }
    }
    
    return render(request, 'dashboard/user_dashboard.html', context)


@login_required
def admin_dashboard_view(request):
    """Dashboard especial para administradores"""
    
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('core:dashboard')
    
    # Estadísticas generales
    total_users = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_companies = Company.objects.count()
    
    if ASSIGNMENTS_AVAILABLE:
        waiting_users = UserCompanyAssignment.objects.filter(status='waiting').count()
        assigned_users = UserCompanyAssignment.objects.filter(status='assigned').count()
        
        # Notificaciones no leídas
        unread_notifications = AdminNotification.objects.filter(is_read=False).count()
        recent_notifications = AdminNotification.objects.filter(is_read=False)[:5]
        
        # Usuarios recientes en espera
        recent_waiting = UserCompanyAssignment.objects.filter(
            status='waiting'
        ).select_related('user').order_by('-created_at')[:10]
        
    else:
        waiting_users = 0
        assigned_users = total_users
        unread_notifications = 0
        recent_notifications = []
        recent_waiting = []
    
    if INVOICES_AVAILABLE:
        total_invoices = Invoice.objects.count()
        pending_invoices = Invoice.objects.filter(status='pending').count()
    else:
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
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def company_invoices_api(request, company_id):
    """API para obtener facturas de una empresa específica (AJAX)"""
    user = request.user
    
    # Verificar acceso del usuario a la empresa
    if user.is_staff or user.is_superuser:
        # Admins pueden ver todas las empresas
        company = get_object_or_404(Company, id=company_id)
    else:
        # Usuarios normales solo ven empresas asignadas
        if ASSIGNMENTS_AVAILABLE:
            try:
                assignment = UserCompanyAssignment.objects.get(user=user)
                user_companies = assignment.get_assigned_companies()
            except UserCompanyAssignment.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'No autorizado'})
        else:
            # Fallback al sistema original
            user_companies = user.companies.all() if hasattr(user, 'companies') else Company.objects.filter(users=user)
        
        company = get_object_or_404(Company, id=company_id, id__in=user_companies.values_list('id', flat=True))
    
    if INVOICES_AVAILABLE:
        invoices = Invoice.objects.filter(company=company).order_by('-created_at')
        
        invoices_data = []
        for invoice in invoices[:50]:  # Limitar a 50 para performance
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
            'total_count': invoices.count()
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'El módulo de facturación no está disponible',
            'company_name': getattr(company, 'business_name', company.trade_name),
            'invoices': [],
            'total_count': 0
        })


@login_required
def invoice_detail_view(request, invoice_id):
    """Vista detallada de una factura"""
    user = request.user
    
    if not INVOICES_AVAILABLE:
        from django.http import Http404
        raise Http404("La funcionalidad de facturas no está disponible")
    
    from apps.invoicing.models import Invoice
    
    # Verificar acceso del usuario a la factura
    if user.is_staff or user.is_superuser:
        # Admins pueden ver todas las facturas
        invoice = get_object_or_404(Invoice, id=invoice_id)
    else:
        # Usuarios normales solo ven facturas de empresas asignadas
        if ASSIGNMENTS_AVAILABLE:
            try:
                assignment = UserCompanyAssignment.objects.get(user=user)
                user_companies = assignment.get_assigned_companies()
            except UserCompanyAssignment.DoesNotExist:
                from django.http import Http404
                raise Http404("No autorizado")
        else:
            # Fallback al sistema original
            user_companies = user.companies.all() if hasattr(user, 'companies') else Company.objects.filter(users=user)
        
        invoice = get_object_or_404(
            Invoice, 
            id=invoice_id, 
            company__in=user_companies
        )
    
    context = {
        'invoice': invoice,
        'company': invoice.company,
        'is_admin': user.is_staff or user.is_superuser,
    }
    
    return render(request, 'dashboard/invoice_detail.html', context)


@login_required
def dashboard_stats_api(request):
    """API para estadísticas del dashboard (para gráficos)"""
    user = request.user
    
    # Obtener empresas según permisos del usuario
    if user.is_staff or user.is_superuser:
        user_companies = Company.objects.all()
    elif ASSIGNMENTS_AVAILABLE:
        try:
            assignment = UserCompanyAssignment.objects.get(user=user)
            user_companies = assignment.get_assigned_companies()
        except UserCompanyAssignment.DoesNotExist:
            return JsonResponse({'error': 'No autorizado'})
    else:
        # Fallback al sistema original
        user_companies = user.companies.all() if hasattr(user, 'companies') else Company.objects.filter(users=user)
    
    if INVOICES_AVAILABLE:
        from apps.invoicing.models import Invoice
        
        # Estadísticas de los últimos 30 días
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
        
        # Facturas por empresa
        company_stats = invoices_last_30.values('company__trade_name').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount')
        ).order_by('-count')[:5]  # Top 5 empresas
        
        return JsonResponse({
            'daily_stats': list(reversed(daily_stats)),
            'status_distribution': list(status_distribution),
            'company_stats': list(company_stats),
            'total_last_30': invoices_last_30.count(),
        })
        
    else:
        return JsonResponse({
            'daily_stats': [],
            'status_distribution': [],
            'company_stats': [],
            'total_last_30': 0,
            'error': 'Módulo de facturación no disponible'
        })