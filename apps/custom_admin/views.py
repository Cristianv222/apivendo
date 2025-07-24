# -*- coding: utf-8 -*-
"""
Custom Admin Views - VERSIÓN COMPLETA
apps/custom_admin/views.py
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Sum, Avg
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from functools import wraps
from django.conf import settings

# Import models
from apps.users.models import User, UserCompanyAssignment, AdminNotification
from apps.companies.models import Company
from apps.certificates.models import DigitalCertificate
from apps.core.models import AuditLog

# Import existing decorators
from apps.api.views.sri_views import audit_api_action

from django.db.models import Sum, Avg, Count, Q
from decimal import Decimal


def staff_required(view_func):
    """Decorator to require staff/admin access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Acceso denegado. Se requieren privilegios de administrador.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@staff_required
def dashboard(request):
    """Admin Dashboard with statistics"""
    context = {
        'page_title': 'Dashboard',
        
        # User Statistics
        'total_users': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'active_users': User.objects.filter(is_active=True, is_staff=False).count(),
        'pending_users': UserCompanyAssignment.objects.filter(status='waiting').count(),
        'new_users_today': User.objects.filter(
            date_joined__date=timezone.now().date()
        ).count(),
        
        # Company Statistics
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
        
        # Certificate Statistics
        'total_certificates': DigitalCertificate.objects.count(),
        'expiring_certificates': DigitalCertificate.objects.filter(
            valid_to__lte=timezone.now() + timedelta(days=30),
            valid_to__gte=timezone.now()
        ).count(),
        
        # Notifications
        'unread_notifications': AdminNotification.objects.filter(is_read=False).count(),
        'recent_notifications': AdminNotification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:5],
        
        # Recent Activity
        'recent_logs': AuditLog.objects.select_related('user').order_by('-created_at')[:10],
        
        # Charts Data
        'users_chart_data': get_users_chart_data(),
        'activity_chart_data': get_activity_chart_data(),
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


# ========== USERS CRUD ==========

@login_required
@staff_required
def users_list(request):
    """List all users with CRUD operations"""
    users = User.objects.all().select_related('company').order_by('-date_joined')
    
    # Filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    company_id = request.GET.get('company', '')
    
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if status:
        if status == 'active':
            users = users.filter(is_active=True)
        elif status == 'inactive':
            users = users.filter(is_active=False)
        elif status == 'staff':
            users = users.filter(is_staff=True)
        elif status == 'waiting':
            waiting_ids = UserCompanyAssignment.objects.filter(
                status='waiting'
            ).values_list('user_id', flat=True)
            users = users.filter(id__in=waiting_ids)
    
    if company_id:
        users = users.filter(company_id=company_id)
    
    # Pagination
    paginator = Paginator(users, 25)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Usuarios',
        'users': users_page,
        'total_count': paginator.count,
        'companies': Company.objects.filter(is_active=True),
        'filters': {
            'search': search,
            'status': status,
            'company': company_id,
        }
    }
    
    return render(request, 'custom_admin/users/list.html', context)
@login_required
@staff_required
def user_create(request):
    """Create user - Modal form"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        company_id = request.POST.get('company_id')
        is_staff = request.POST.get('is_staff') == 'on'
        user_status = request.POST.get('user_status', 'waiting')
        
        if User.objects.filter(email=email).exists():
            companies = Company.objects.filter(is_active=True).order_by('business_name')
            return render(request, 'custom_admin/users/form_modal.html', {
                'mode': 'create',
                'companies': companies,
                'error': 'Ya existe un usuario con este email'
            })
        
        try:
            # Crear usuario con estado inicial
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_staff=is_staff,
                is_active=True  # Por defecto activo, el status controla el acceso
            )
            
            # Asignar user_status si el modelo lo soporta
            if hasattr(user, 'user_status'):
                user.user_status = user_status
                user.save()
            
            if company_id:
                try:
                    company = Company.objects.get(id=company_id)
                    user.company = company
                    user.save()
                except Company.DoesNotExist:
                    pass
            
            # Log action
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='User',
                object_id=str(user.id),
                object_representation=str(user),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Usuario {user.email} creado exitosamente')
            return HttpResponse('<script>window.parent.location.reload();</script>')
            
        except Exception as e:
            companies = Company.objects.filter(is_active=True).order_by('business_name')
            return render(request, 'custom_admin/users/form_modal.html', {
                'mode': 'create',
                'companies': companies,
                'error': f'Error al crear usuario: {str(e)}'
            })
    
    # GET request
    try:
        companies = Company.objects.filter(is_active=True).order_by('business_name')
        context = {
            'mode': 'create',
            'companies': companies
        }
        return render(request, 'custom_admin/users/form_modal.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="alert alert-danger">Error al cargar el formulario: {str(e)}</div>')

@login_required
@staff_required
def user_edit(request, user_id):
    """Edit user - Modal form"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        if request.method == 'GET':
            companies = Company.objects.filter(is_active=True).order_by('business_name')
            context = {
                'user': user,
                'companies': companies,
                'mode': 'edit'
            }
            return render(request, 'custom_admin/users/form_modal.html', context)
        
        elif request.method == 'POST':
            # DEBUG: Ver qué datos llegan
            print("=== DATOS RECIBIDOS EN POST ===")
            for key, value in request.POST.items():
                print(f"{key}: {value}")
            print("================================")
            
            try:
                # Update basic info
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.phone = request.POST.get('phone', '')
                
                # Handle company assignment
                company_id = request.POST.get('company_id')
                if company_id:
                    user.company_id = company_id
                else:
                    user.company = None
                
                # Handle user status - SIEMPRE actualizar
                new_status = request.POST.get('user_status', 'waiting')
                old_status = getattr(user, 'user_status', 'waiting')
                
                print(f"[DEBUG] Estado anterior: {old_status}")
                print(f"[DEBUG] Nuevo estado: {new_status}")
                
                # IMPORTANTE: Asignar directamente sin verificar hasattr
                user.user_status = new_status
                
                # Handle reason for suspension/rejection
                reason = request.POST.get('reason', '')
                
                if new_status == 'suspended':
                    user.suspension_reason = reason
                    user.is_active = False
                    print("[DEBUG] Usuario suspendido - is_active = False")
                elif new_status == 'rejected':
                    user.rejection_reason = reason
                    user.is_active = False
                    print("[DEBUG] Usuario rechazado - is_active = False")
                elif new_status == 'active':
                    user.is_active = True
                    user.suspension_reason = None
                    user.rejection_reason = None
                    if old_status == 'waiting':
                        user.approved_by = request.user
                        user.approved_at = timezone.now()
                    print("[DEBUG] Usuario activado - is_active = True")
                elif new_status == 'waiting':
                    user.is_active = True
                    user.suspension_reason = None
                    user.rejection_reason = None
                    print("[DEBUG] Usuario en espera - is_active = True")
                
                # Handle is_staff
                user.is_staff = request.POST.get('is_staff') == 'on'
                
                # Update password if provided
                new_password = request.POST.get('password')
                if new_password:
                    user.set_password(new_password)
                
                # GUARDAR
                user.save()
                
                # VERIFICACIÓN ADICIONAL - Forzar actualización
                User.objects.filter(id=user.id).update(
                    user_status=new_status,
                    is_active=(new_status in ['active', 'waiting'])
                )
                
                # Verificar que se guardó correctamente
                user.refresh_from_db()
                print(f"[DEBUG] VERIFICACIÓN FINAL:")
                print(f"[DEBUG] - user_status: {user.user_status}")
                print(f"[DEBUG] - is_active: {user.is_active}")
                
                # Sincronizar con UserCompanyAssignment si existe
                try:
                    assignment = UserCompanyAssignment.objects.get(user=user)
                    
                    # Mapear estados
                    if new_status == 'active':
                        assignment.status = 'assigned'
                        assignment.assigned_by = request.user
                        assignment.assigned_at = timezone.now()
                        if user.company:
                            assignment.assigned_companies.add(user.company)
                    elif new_status == 'rejected':
                        assignment.status = 'rejected'
                        assignment.notes = reason
                    elif new_status == 'suspended':
                        assignment.status = 'suspended'
                        assignment.notes = reason
                    elif new_status == 'waiting':
                        assignment.status = 'waiting'
                    
                    assignment.save()
                    print(f"[DEBUG] UserCompanyAssignment actualizado: {assignment.status}")
                    
                except UserCompanyAssignment.DoesNotExist:
                    # Crear assignment si no existe y el usuario no es staff
                    if not user.is_staff:
                        assignment = UserCompanyAssignment.objects.create(
                            user=user,
                            status='assigned' if new_status == 'active' else new_status
                        )
                        if new_status == 'active' and user.company:
                            assignment.assigned_companies.add(user.company)
                            assignment.assigned_by = request.user
                            assignment.assigned_at = timezone.now()
                            assignment.save()
                        print(f"[DEBUG] UserCompanyAssignment creado")
                
                # Crear notificación si se aprobó
                if new_status == 'active' and old_status == 'waiting':
                    AdminNotification.objects.create(
                        notification_type='user_registered',
                        title=f'Usuario aprobado',
                        message=f'El usuario {user.email} ha sido aprobado por {request.user.get_full_name() or request.user.email}',
                        priority='normal',
                        related_user=user
                    )
                
                # Audit log con más detalle
                changes = f'Usuario actualizado'
                if old_status != new_status:
                    changes += f'. Estado cambiado de {old_status} a {new_status}'
                if reason:
                    changes += f'. Razón: {reason}'
                
                AuditLog.objects.create(
                    user=request.user,
                    model_name='User',
                    object_id=str(user.id),
                    action='UPDATE',
                    changes=changes,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Usuario {user.email} actualizado correctamente')
                return HttpResponse('<script>window.parent.location.reload();</script>')
                
            except Exception as e:
                print(f"[DEBUG] ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                
                companies = Company.objects.filter(is_active=True).order_by('business_name')
                context = {
                    'user': user,
                    'companies': companies,
                    'mode': 'edit',
                    'error': f'Error al actualizar: {str(e)}'
                }
                return render(request, 'custom_admin/users/form_modal.html', context)
    
    except Exception as e:
        print(f"[DEBUG] ERROR GENERAL: {str(e)}")
        return HttpResponse(f'<div class="alert alert-danger">Error: {str(e)}</div>')
        
@login_required
@staff_required
def user_view(request, user_id):
    """View user details - Modal"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user's activity logs
    user_logs = AuditLog.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get user's assignments
    try:
        assignment = UserCompanyAssignment.objects.get(user=user)
    except UserCompanyAssignment.DoesNotExist:
        assignment = None
    
    context = {
        'user': user,
        'user_logs': user_logs,
        'assignment': assignment
    }
    return render(request, 'custom_admin/users/view_modal.html', context)


@login_required
@staff_required
@require_http_methods(["POST"])
def user_delete(request, user_id):
    """Delete user"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'No se puede eliminar un superusuario'
            })
        
        if user.id == request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'No puedes eliminarte a ti mismo'
            })
        
        # Log before deletion
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='User',
            object_id=str(user.id),
            object_representation=str(user),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Usuario eliminado exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_required
@require_http_methods(["POST"])
def user_toggle_status(request, user_id):
    """Toggle user active status"""
    try:
        data = json.loads(request.body)
        user = get_object_or_404(User, id=user_id)
        
        if user.is_superuser and not data.get('is_active'):
            return JsonResponse({
                'success': False,
                'error': 'No se puede desactivar un superusuario'
            })
        
        if user.id == request.user.id and not data.get('is_active'):
            return JsonResponse({
                'success': False,
                'error': 'No puedes desactivarte a ti mismo'
            })
        
        user.is_active = data.get('is_active', False)
        user.save()
        
        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='UPDATE',
            model_name='User',
            object_id=str(user.id),
            object_representation=f'Status changed to {"active" if user.is_active else "inactive"}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Estado actualizado correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ========== COMPANIES CRUD ==========
# En views.py, busca la función companies_list y corrige esta parte:

@login_required
@staff_required
def companies_list(request):
    """List all companies"""
    companies = Company.objects.all().order_by('business_name')
    
    # Add related counts - CORREGIDO
    companies = companies.annotate(
        user_count=Count('users'),
        certificate_count=Count('digital_certificate')  # Cambiado de 'digitalcertificate' a 'digital_certificate'
    )
    
    # Filters
    search = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')
    plan = request.GET.get('plan', '')
    
    if search:
        companies = companies.filter(
            Q(business_name__icontains=search) |
            Q(ruc__icontains=search) |
            Q(trade_name__icontains=search)
        )
    
    if is_active:
        companies = companies.filter(is_active=(is_active == 'true'))
    
    if plan and hasattr(Company, 'plan'):
        companies = companies.filter(plan=plan)
    
    # Pagination
    paginator = Paginator(companies, 25)
    page = request.GET.get('page')
    companies_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Empresas',
        'companies': companies_page,
        'total_count': paginator.count,
        'filters': {
            'search': search,
            'is_active': is_active,
            'plan': plan,
        }
    }
    
    return render(request, 'custom_admin/companies/list.html', context)

@login_required
@staff_required
def company_create(request):
    """Create company - Modal form"""
    if request.method == 'POST':
        ruc = request.POST.get('ruc')
        business_name = request.POST.get('business_name')
        trade_name = request.POST.get('trade_name')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', 'Quito')
        province = request.POST.get('province', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if Company.objects.filter(ruc=ruc).exists():
            return render(request, 'custom_admin/companies/form_modal.html', {
                'mode': 'create',
                'error': 'Ya existe una empresa con este RUC'
            })
        
        try:
            company = Company.objects.create(
                ruc=ruc,
                business_name=business_name,
                trade_name=trade_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                province=province,
                is_active=is_active
            )
            
            # If plan field exists
            if hasattr(company, 'plan'):
                company.plan = request.POST.get('plan', 'basic')
                company.save()
            
            # Log action
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='Company',
                object_id=str(company.id),
                object_representation=str(company),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Empresa creada exitosamente')
            return HttpResponse('<script>window.parent.location.reload();</script>')
            
        except Exception as e:
            messages.error(request, f'Error al crear empresa: {str(e)}')
    
    context = {
        'mode': 'create'
    }
    return render(request, 'custom_admin/companies/form_modal.html', context)


@login_required
@staff_required
def company_edit(request, company_id):
    """Edit company - Modal form"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        company.business_name = request.POST.get('business_name', company.business_name)
        company.trade_name = request.POST.get('trade_name', company.trade_name)
        company.email = request.POST.get('email', company.email)
        company.phone = request.POST.get('phone', company.phone)
        company.address = request.POST.get('address', company.address)
        company.city = request.POST.get('city', company.city)
        company.province = request.POST.get('province', company.province)
        company.is_active = request.POST.get('is_active') == 'on'
        
        # If plan field exists
        if hasattr(company, 'plan'):
            company.plan = request.POST.get('plan', company.plan)
        
        try:
            company.save()
            
            # Log action
            AuditLog.objects.create(
                user=request.user,
                action='UPDATE',
                model_name='Company',
                object_id=str(company.id),
                object_representation=str(company),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Empresa actualizada exitosamente')
            return HttpResponse('<script>window.parent.location.reload();</script>')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    context = {
        'mode': 'edit',
        'company': company
    }
    return render(request, 'custom_admin/companies/form_modal.html', context)


@login_required
@staff_required
def company_view(request, company_id):
    """View company details - Modal"""
    company = get_object_or_404(Company, id=company_id)
    
    # Get related data
    users = User.objects.filter(company=company)
    certificates = DigitalCertificate.objects.filter(company=company)
    
    # Get company activity logs
    company_logs = AuditLog.objects.filter(
        model_name='Company',
        object_id=str(company.id)
    ).order_by('-created_at')[:10]
    
    context = {
        'company': company,
        'users': users,
        'certificates': certificates,
        'company_logs': company_logs,
        'user_count': users.count(),
        'certificate_count': certificates.count(),
    }
    return render(request, 'custom_admin/companies/view_modal.html', context)

@login_required
@staff_required
@require_http_methods(["POST"])
def company_delete(request, company_id):
    """Delete company"""
    try:
        company = get_object_or_404(Company, id=company_id)
        
        # Check if has related users
        if hasattr(company, 'users') and company.users.exists():
            return JsonResponse({
                'success': False,
                'error': 'No se puede eliminar una empresa con usuarios asociados'
            })
        
        # Log before deletion
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='Company',
            object_id=str(company.id),
            object_representation=str(company),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        company_name = company.trade_name or company.business_name
        company.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Empresa {company_name} eliminada exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_required
@require_http_methods(["POST"])
def company_toggle_status(request, company_id):
    """Toggle company active status"""
    try:
        data = json.loads(request.body)
        company = get_object_or_404(Company, id=company_id)
        
        company.is_active = data.get('is_active', False)
        company.save()
        
        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='UPDATE',
            model_name='Company',
            object_id=str(company.id),
            object_representation=f'Status changed to {"active" if company.is_active else "inactive"}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Estado actualizado correctamente',
            'is_active': company.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ========== CERTIFICATES CRUD ==========
@login_required
@staff_required
def certificates_list(request):
    """List all digital certificates"""
    certificates = DigitalCertificate.objects.all().select_related('company').order_by('-created_at')
    
    # Filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    company_id = request.GET.get('company', '')
    
    if search:
        certificates = certificates.filter(
            Q(subject_name__icontains=search) |
            Q(serial_number__icontains=search) |
            Q(issuer_name__icontains=search)
        )
    
    if company_id:
        certificates = certificates.filter(company_id=company_id)
    
    # Convertir a lista si necesitamos filtrar por status
    if status:
        certificate_list = list(certificates)
        
        if status == 'active':
            certificates = [
                cert for cert in certificate_list 
                if not cert.is_expired and cert.days_until_expiry > 30
            ]
        elif status == 'expired':
            certificates = [
                cert for cert in certificate_list 
                if cert.is_expired
            ]
        elif status == 'expiring':
            certificates = [
                cert for cert in certificate_list 
                if not cert.is_expired and cert.days_until_expiry <= 30
            ]
        
        # Calcular el total antes de paginar
        total_count = len(certificates)
    else:
        # Si no hay filtro de status, usar count() del queryset
        total_count = certificates.count()
    
    # Get companies for filter dropdown
    companies = Company.objects.all().order_by('business_name')
    
    # Pagination
    paginator = Paginator(certificates, 25)
    page = request.GET.get('page')
    certificates_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Certificados Digitales',
        'certificates': certificates_page,
        'companies': companies,
        'total_count': total_count,
        'filters': {
            'search': search,
            'status': status,
            'company': company_id,
        }
    }
    
    return render(request, 'custom_admin/certificates/list.html', context)

@login_required
@staff_required
def certificate_upload(request):
    """Upload new certificate - Modal form"""
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        certificate_file = request.FILES.get('certificate_file')
        password = request.POST.get('password')
        
        if not certificate_file:
            companies = Company.objects.filter(is_active=True)
            return render(request, 'custom_admin/certificates/upload_modal.html', {
                'companies': companies,
                'error': 'Debe seleccionar un archivo de certificado'
            })
        
        try:
            company = Company.objects.get(id=company_id)
            
            # Create certificate
            certificate = DigitalCertificate.objects.create(
                company=company,
                certificate_file=certificate_file,
                password=password,
                status='PENDING'
            )
            
            # Process certificate (this would typically extract cert info)
            # certificate.process_certificate()
            
            # Log action
            AuditLog.objects.create(
                user=request.user,
                action='CREATE',
                model_name='DigitalCertificate',
                object_id=str(certificate.id),
                object_representation=f'Certificate for {company}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Certificado cargado exitosamente')
            return HttpResponse('<script>window.parent.location.reload();</script>')
            
        except Exception as e:
            messages.error(request, f'Error al cargar certificado: {str(e)}')
    
    companies = Company.objects.filter(is_active=True)
    context = {
        'companies': companies
    }
    return render(request, 'custom_admin/certificates/upload_modal.html', context)

@login_required
@staff_required
def certificate_view(request, certificate_id):
    """View certificate details - Modal"""
    try:
        certificate = get_object_or_404(DigitalCertificate, id=certificate_id)
        
        # Calcular días hasta expiración
        days_until_expiry = 0
        is_expired = False
        try:
            if hasattr(certificate, 'valid_to') and certificate.valid_to:
                from datetime import datetime
                if timezone.is_aware(certificate.valid_to):
                    now = timezone.now()
                else:
                    now = datetime.now()
                days_until_expiry = (certificate.valid_to - now).days
                is_expired = certificate.valid_to < now
        except:
            pass
        
        # Calcular porcentaje de tiempo usado
        percentage = 70  # Default
        try:
            if hasattr(certificate, 'valid_from') and hasattr(certificate, 'valid_to'):
                total_days = (certificate.valid_to - certificate.valid_from).days
                used_days = (timezone.now() - certificate.valid_from).days
                if total_days > 0:
                    percentage = min(100, max(0, int((used_days / total_days) * 100)))
        except:
            pass
        
        # Devolver HTML directo mejorado
        html = f"""
        <style>
            .info-group {{
                padding: 0.75rem;
                background: #f8f9fa;
                border-radius: 0.25rem;
                margin-bottom: 0.75rem;
            }}
            .info-group label {{
                display: block;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 0.25rem;
                color: #6c757d;
            }}
            .info-group p {{
                margin-bottom: 0;
                font-weight: 500;
            }}
            .technical-details {{
                background: #f8f9fa;
                padding: 1rem;
                border-radius: 0.5rem;
            }}
            code {{
                background: #e9ecef;
                padding: 0.2rem 0.4rem;
                border-radius: 0.25rem;
                font-size: 0.875rem;
            }}
        </style>
        
        <div class="certificate-view-content">
            <div class="row">
                <!-- Información del Certificado -->
                <div class="col-md-6">
                    <h6 class="text-muted mb-3"><i class="fas fa-certificate me-2"></i>Información del Certificado</h6>
                    
                    <div class="info-group">
                        <label>Nombre del Sujeto</label>
                        <p><strong>{getattr(certificate, 'subject_name', 'N/A')}</strong></p>
                    </div>
                    
                    <div class="info-group">
                        <label>Número de Serie</label>
                        <p class="text-monospace"><code>{getattr(certificate, 'serial_number', 'N/A')}</code></p>
                    </div>
                    
                    <div class="info-group">
                        <label>Emisor</label>
                        <p>{getattr(certificate, 'issuer_name', 'N/A')}</p>
                    </div>
                    
                    <div class="info-group">
                        <label>Empresa</label>
                        <p>
                            {f'<span class="badge bg-info">{certificate.company.business_name}</span>' if hasattr(certificate, 'company') and certificate.company else '<span class="text-muted">Sin empresa asignada</span>'}
                        </p>
                    </div>
                    
                    <div class="info-group">
                        <label>Estado del Certificado</label>
                        <p>
                            {'<span class="badge bg-danger"><i class="fas fa-times-circle"></i> Expirado</span>' if is_expired else (f'<span class="badge bg-warning"><i class="fas fa-exclamation-triangle"></i> Por Expirar</span>' if days_until_expiry <= 30 else '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Activo</span>')}
                            <span class="badge bg-secondary ms-2">{getattr(certificate, 'status', 'N/A')}</span>
                        </p>
                    </div>
                    
                    <div class="info-group">
                        <label>Ambiente</label>
                        <p>
                            <span class="badge bg-{('danger' if getattr(certificate, 'environment', '') == 'PRODUCTION' else 'warning')}">
                                {getattr(certificate, 'environment', 'N/A')}
                            </span>
                        </p>
                    </div>
                </div>
                
                <!-- Información de Validez -->
                <div class="col-md-6">
                    <h6 class="text-muted mb-3"><i class="fas fa-calendar-alt me-2"></i>Información de Validez</h6>
                    
                    <div class="info-group">
                        <label>Válido Desde</label>
                        <p>
                            <i class="fas fa-calendar-check text-success"></i>
                            {certificate.valid_from.strftime('%d/%m/%Y %H:%M') if hasattr(certificate, 'valid_from') and certificate.valid_from else 'N/A'}
                        </p>
                    </div>
                    
                    <div class="info-group">
                        <label>Válido Hasta</label>
                        <p>
                            <i class="fas fa-calendar-times text-danger"></i>
                            {certificate.valid_to.strftime('%d/%m/%Y %H:%M') if hasattr(certificate, 'valid_to') and certificate.valid_to else 'N/A'}
                        </p>
                    </div>
                    
                    <div class="info-group">
                        <label>Días Restantes</label>
                        <p>
                            {'<span class="text-danger fw-bold">Expirado hace ' + str(abs(days_until_expiry)) + ' días</span>' if is_expired else (f'<span class="text-danger fw-bold">Expira hoy</span>' if days_until_expiry == 0 else (f'<span class="text-warning fw-bold">Expira mañana</span>' if days_until_expiry == 1 else (f'<span class="text-warning fw-bold">{days_until_expiry} días restantes</span>' if days_until_expiry <= 30 else f'<span class="text-success fw-bold">{days_until_expiry} días restantes</span>')))}
                        </p>
                    </div>
                    
                    <div class="info-group">
                        <label>Fecha de Carga</label>
                        <p>{certificate.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(certificate, 'created_at') and certificate.created_at else 'N/A'}</p>
                    </div>
                    
                    <div class="info-group">
                        <label>Fingerprint</label>
                        <p><code>{getattr(certificate, 'fingerprint', 'N/A')}</code></p>
                    </div>
                </div>
            </div>
            
            <hr>
            
            <!-- Detalles Técnicos -->
            <div class="row">
                <div class="col-12">
                    <h6 class="text-muted mb-3"><i class="fas fa-info-circle me-2"></i>Detalles Técnicos</h6>
                    
                    <div class="technical-details">
                        <p class="mb-2"><strong>CN (Common Name):</strong> {getattr(certificate, 'subject_name', 'N/A')}</p>
                        <p class="mb-2"><strong>Autoridad Certificadora:</strong> {getattr(certificate, 'issuer_name', 'N/A')}</p>
                        <p class="mb-2"><strong>Serial Completo:</strong></p>
                        <pre class="bg-white p-2 rounded text-monospace small" style="white-space: pre-wrap; word-break: break-all;">{getattr(certificate, 'serial_number', 'N/A')}</pre>
                        {f'<p class="mb-0"><strong>Archivo:</strong> <code>{certificate.certificate_file.name}</code></p>' if hasattr(certificate, 'certificate_file') and certificate.certificate_file else ''}
                    </div>
                </div>
            </div>
            
            <!-- Barra de Progreso -->
            <hr>
            <div class="row">
                <div class="col-12">
                    <h6 class="text-muted mb-3"><i class="fas fa-chart-line me-2"></i>Progreso de Validez</h6>
                    {'<div class="progress" style="height: 25px;"><div class="progress-bar bg-danger" role="progressbar" style="width: 100%">Certificado Expirado</div></div>' if is_expired else f'<div class="progress" style="height: 25px;"><div class="progress-bar {"bg-warning" if days_until_expiry <= 30 else "bg-success"}" role="progressbar" style="width: {percentage}%" aria-valuenow="{percentage}" aria-valuemin="0" aria-valuemax="100">Válido por {days_until_expiry} días más ({percentage}% usado)</div></div>'}
                    <small class="text-muted">
                        Período de validez: {certificate.valid_from.strftime('%d/%m/%Y') if hasattr(certificate, 'valid_from') and certificate.valid_from else 'N/A'} - {certificate.valid_to.strftime('%d/%m/%Y') if hasattr(certificate, 'valid_to') and certificate.valid_to else 'N/A'}
                    </small>
                </div>
            </div>
            
            <div class="modal-footer px-0 pb-0 mt-4">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="fas fa-times me-1"></i>Cerrar
                </button>
                {'<button class="btn btn-warning" onclick="validateCertFromView(' + str(certificate.id) + ')"><i class="fas fa-check me-1"></i>Validar Certificado</button>' if not is_expired else ''}
            </div>
        </div>
        
        <script>
        function validateCertFromView(certId) {{
            // Cerrar el modal actual
            bootstrap.Modal.getInstance(document.getElementById('certificateModal')).hide();
            
            // Trigger el click en el botón de validar
            setTimeout(function() {{
                $('.btn-validate[data-cert-id="' + certId + '"]').click();
            }}, 300);
        }}
        </script>
        """
        
        return HttpResponse(html)
        
    except DigitalCertificate.DoesNotExist:
        return HttpResponse("""
            <div class="p-4">
                <div class="alert alert-danger">
                    <h4>Error</h4>
                    <p>No se encontró el certificado</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                </div>
            </div>
        """)
    except Exception as e:
        return HttpResponse(f"""
            <div class="p-4">
                <div class="alert alert-danger">
                    <h4>Error</h4>
                    <p>{str(e)}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                </div>
            </div>
        """)
@login_required
@staff_required
@require_http_methods(["POST"])
def certificate_delete(request, certificate_id):
    """Delete certificate"""
    try:
        certificate = get_object_or_404(DigitalCertificate, id=certificate_id)
        
        # Log before deletion
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            model_name='DigitalCertificate',
            object_id=str(certificate.id),
            object_representation=str(certificate),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        certificate.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Certificado eliminado exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_required
@require_http_methods(["POST"])
def certificate_validate(request, certificate_id):
    """Validate certificate"""
    try:
        certificate = get_object_or_404(DigitalCertificate, id=certificate_id)
        
        # Here you would run actual validation
        # For now, just toggle status
        if certificate.status == 'ACTIVE':
            certificate.status = 'INACTIVE'
        else:
            certificate.status = 'ACTIVE'
        
        certificate.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Certificado validado exitosamente',
            'status': certificate.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
# En apps/custom_admin/views.py - Reemplaza la función certificate_edit con esta versión corregida

@login_required
@staff_required
def certificate_edit(request, certificate_id):
    """Edit certificate environment - Modal"""
    try:
        # Intenta convertir certificate_id a entero
        cert_id = int(certificate_id)
        certificate = get_object_or_404(DigitalCertificate, id=cert_id)
        
        if request.method == 'POST':
            new_environment = request.POST.get('environment')
            
            if new_environment in ['TEST', 'PRODUCTION']:
                old_environment = certificate.environment
                certificate.environment = new_environment
                certificate.save()
                
                # Log the change
                AuditLog.objects.create(
                    user=request.user,
                    action='UPDATE',
                    model_name='DigitalCertificate',
                    object_id=str(certificate.id),
                    object_representation=f'Certificate environment changed from {old_environment} to {new_environment}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Ambiente cambiado a {new_environment} exitosamente')
                return HttpResponse('<script>window.parent.location.reload();</script>')
            else:
                messages.error(request, 'Ambiente inválido')
        
        context = {
            'certificate': certificate
        }
        return render(request, 'custom_admin/certificates/edit_modal.html', context)
        
    except ValueError:
        # Si el certificate_id no es un número válido
        return HttpResponse("""
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle"></i> Error</h5>
                <p>ID de certificado inválido</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        """)
    except DigitalCertificate.DoesNotExist:
        # Si el certificado no existe
        return HttpResponse("""
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle"></i> Error</h5>
                <p>No se encontró el certificado solicitado</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        """)
    except Exception as e:
        # Para cualquier otro error
        return HttpResponse(f"""
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle"></i> Error</h5>
                <p>Error al cargar el formulario: {str(e)}</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        """)
# ========== INVOICES ==========
# Agrega estas funciones en views.py:
@login_required
@staff_required
def invoices_list(request):
    """List all invoices"""
    invoices = Invoice.objects.all().select_related('company', 'customer').order_by('-fecha_emision')
    
    # Filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    company_id = request.GET.get('company', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search:
        invoices = invoices.filter(
            Q(numero_completo__icontains=search) |
            Q(customer__business_name__icontains=search) |
            Q(customer__identification__icontains=search)
        )
    
    if status:
        invoices = invoices.filter(status=status)
    
    if company_id:
        invoices = invoices.filter(company_id=company_id)
    
    if date_from:
        invoices = invoices.filter(fecha_emision__gte=date_from)
    
    if date_to:
        invoices = invoices.filter(fecha_emision__lte=date_to)
    
    # Statistics
    stats = {
        'total_authorized': invoices.filter(status='AUTORIZADO').aggregate(
            total=Sum('total')
        )['total'] or Decimal('0.00'),
        'count_pending': invoices.filter(status='PENDIENTE').count(),
        'count_rejected': invoices.filter(status='RECHAZADO').count(),
        'avg_amount': invoices.aggregate(
            avg=Avg('total')
        )['avg'] or Decimal('0.00'),
    }
    
    # Get companies for filter
    companies = Company.objects.filter(is_active=True).order_by('trade_name')
    
    # Pagination
    paginator = Paginator(invoices, 25)
    page = request.GET.get('page')
    invoices_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Facturas',
        'invoices': invoices_page,
        'companies': companies,
        'total_count': paginator.count,
        'stats': stats,
        'filters': {
            'search': search,
            'status': status,
            'company': company_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'custom_admin/invoices/list.html', context)

@login_required
@staff_required
def invoice_view(request, invoice_id):
    """View invoice details - Modal"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    context = {
        'invoice': invoice,
    }
    return render(request, 'custom_admin/invoices/view_modal.html', context)

@login_required
@staff_required
def invoice_create(request):
    """Create new invoice - Full page"""
    # Esta sería una página completa, no un modal
    if request.method == 'GET':
        companies = Company.objects.filter(is_active=True).order_by('business_name')
        customers = Customer.objects.filter(is_active=True).order_by('business_name')
        
        context = {
            'page_title': 'Nueva Factura',
            'companies': companies,
            'customers': customers,
        }
        return render(request, 'custom_admin/invoices/create.html', context)
    
    elif request.method == 'POST':
        # Lógica para crear la factura
        try:
            # Aquí iría la lógica de creación
            messages.success(request, 'Factura creada correctamente')
            return redirect('custom_admin:invoices')
        except Exception as e:
            messages.error(request, f'Error al crear factura: {str(e)}')
            return redirect('custom_admin:invoice_create')

@login_required
@staff_required
def invoice_edit(request, invoice_id):
    """Edit invoice - Full page"""
    invoice = get_object_or_404(Invoice, id=invoice_id, status='PENDIENTE')
    
    if request.method == 'GET':
        companies = Company.objects.filter(is_active=True).order_by('business_name')
        customers = Customer.objects.filter(is_active=True).order_by('business_name')
        
        context = {
            'page_title': f'Editar Factura {invoice.numero_completo}',
            'invoice': invoice,
            'companies': companies,
            'customers': customers,
        }
        return render(request, 'custom_admin/invoices/edit.html', context)
    
    elif request.method == 'POST':
        # Lógica para actualizar la factura
        try:
            # Aquí iría la lógica de actualización
            messages.success(request, 'Factura actualizada correctamente')
            return redirect('custom_admin:invoices')
        except Exception as e:
            messages.error(request, f'Error al actualizar factura: {str(e)}')
            return redirect('custom_admin:invoice_edit', invoice_id=invoice_id)

@login_required
@staff_required
def invoice_authorize(request, invoice_id):
    """Authorize invoice with SRI"""
    if request.method == 'POST':
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id, status='PENDIENTE')
            
            # Aquí iría la lógica de autorización con el SRI
            # Por ahora, simulamos una autorización exitosa
            invoice.status = 'AUTORIZADO'
            invoice.numero_autorizacion = f'AUT{invoice_id:010d}'
            invoice.fecha_autorizacion = timezone.now()
            invoice.save()
            
            return JsonResponse({
                'success': True,
                'numero_autorizacion': invoice.numero_autorizacion
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

@login_required
@staff_required
def invoice_cancel(request, invoice_id):
    """Cancel an authorized invoice"""
    if request.method == 'POST':
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id, status='AUTORIZADO')
            
            # Aquí iría la lógica de anulación con el SRI
            invoice.status = 'ANULADO'
            invoice.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Factura anulada correctamente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

@login_required
@staff_required
def invoice_batch_authorize(request):
    """Authorize multiple invoices"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            invoice_ids = data.get('invoice_ids', [])
            
            authorized = 0
            errors = 0
            
            for invoice_id in invoice_ids:
                try:
                    invoice = Invoice.objects.get(id=invoice_id, status='PENDIENTE')
                    # Aquí iría la lógica de autorización
                    invoice.status = 'AUTORIZADO'
                    invoice.numero_autorizacion = f'AUT{invoice_id:010d}'
                    invoice.fecha_autorizacion = timezone.now()
                    invoice.save()
                    authorized += 1
                except:
                    errors += 1
            
            return JsonResponse({
                'success': True,
                'authorized': authorized,
                'errors': errors
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

@login_required
@staff_required
def invoice_pdf(request, invoice_id):
    """Generate and download invoice PDF"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Aquí iría la lógica para generar el PDF
    # Por ahora, solo un placeholder
    return HttpResponse('PDF generation not implemented yet', content_type='text/plain')

# ========== NOTIFICATIONS ==========

@login_required
@staff_required
def notifications_list(request):
    """List notifications"""
    notifications = AdminNotification.objects.all().order_by('-created_at')
    
    # Filters
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)
    
    if priority:
        notifications = notifications.filter(priority=priority)
    
    # Pagination
    paginator = Paginator(notifications, 25)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Notificaciones',
        'notifications': notifications_page,
        'total_count': paginator.count,
        'filters': {
            'status': status,
            'priority': priority,
        }
    }
    
    return render(request, 'custom_admin/notifications/list.html', context)


@login_required
@staff_required
@require_http_methods(["POST"])
def notification_mark_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = get_object_or_404(AdminNotification, id=notification_id)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notificación marcada como leída'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_required
@require_http_methods(["POST"])
def notifications_mark_all_read(request):
    """Mark all notifications as read"""
    try:
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'message': 'Todas las notificaciones marcadas como leídas'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ========== AUDIT LOGS ==========

@login_required
@staff_required
def audit_logs(request):
    """View audit logs"""
    logs = AuditLog.objects.all().select_related('user').order_by('-created_at')
    
    # Filters
    action = request.GET.get('action', '')
    model = request.GET.get('model', '')
    user_id = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if action:
        logs = logs.filter(action=action)
    
    if model:
        logs = logs.filter(model_name=model)
    
    if user_id:
        logs = logs.filter(user_id=user_id)
    
    if date_from:
        logs = logs.filter(created_at__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(created_at__date__lte=date_to)
    
    # Get unique values for filters
    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    models = AuditLog.objects.values_list('model_name', flat=True).distinct()
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    context = {
        'page_title': 'Logs de Auditoría',
        'logs': logs_page,
        'total_count': paginator.count,
        'actions': actions,
        'models': models,
        'users': User.objects.filter(is_staff=True),
        'filters': {
            'action': action,
            'model': model,
            'user': user_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'custom_admin/audit_logs.html', context)


# ========== SETTINGS ==========

@login_required
@staff_required
def settings_list(request):
    """Settings main page"""
    context = {
        'page_title': 'Configuraciones',
    }
    return render(request, 'custom_admin/settings/list.html', context)


@login_required
@staff_required
def system_settings(request):
    """System settings"""
    if request.method == 'POST':
        # Handle system settings update
        messages.success(request, 'Configuración actualizada exitosamente')
        return redirect('custom_admin:system_settings')
    
    context = {
        'page_title': 'Configuración del Sistema',
        'settings': {
            'site_name': getattr(settings, 'SITE_NAME', 'VENDO SRI'),
            'debug_mode': settings.DEBUG,
            'allowed_hosts': settings.ALLOWED_HOSTS,
            'time_zone': settings.TIME_ZONE,
            'language_code': settings.LANGUAGE_CODE,
        }
    }
    return render(request, 'custom_admin/settings/system.html', context)


@login_required
@staff_required
def company_settings(request):
    """Company default settings"""
    context = {
        'page_title': 'Configuración de Empresas',
    }
    return render(request, 'custom_admin/settings/companies.html', context)


# ========== PROFILE ==========

@login_required
@staff_required
def profile(request):
    """User profile"""
    context = {
        'page_title': 'Mi Perfil',
        'user': request.user
    }
    return render(request, 'custom_admin/profile.html', context)


@login_required
@staff_required
@require_http_methods(["POST"])
def profile_update(request):
    """Update user profile"""
    try:
        data = json.loads(request.body)
        user = request.user
        
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.phone = data.get('phone', user.phone)
        
        if data.get('password'):
            user.set_password(data['password'])
        
        user.save()
        
        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='UPDATE',
            model_name='User',
            object_id=str(user.id),
            object_representation='Profile Update',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Perfil actualizado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ========== HELPER FUNCTIONS ==========

def get_users_chart_data():
    """Get data for users chart"""
    last_30_days = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        count = User.objects.filter(date_joined__date=date).count()
        last_30_days.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return {
        'labels': [d['date'] for d in reversed(last_30_days)],
        'data': [d['count'] for d in reversed(last_30_days)]
    }


def get_activity_chart_data():
    """Get data for activity chart"""
    last_7_days = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        count = AuditLog.objects.filter(created_at__date=date).count()
        last_7_days.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return {
        'labels': [d['date'] for d in reversed(last_7_days)],
        'data': [d['count'] for d in reversed(last_7_days)]
    }


# ========== EXPORT FUNCTIONS ==========

@login_required
@staff_required
def export_data(request, model_name):
    """Export data to CSV"""
    import csv
    
    # Map model names to actual models
    model_map = {
        'users': User,
        'companies': Company,
        'certificates': DigitalCertificate,
        'audit_logs': AuditLog,
    }
    
    if model_name not in model_map:
        return JsonResponse({'error': 'Invalid model'}, status=400)
    
    model = model_map[model_name]
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers based on model
    if model_name == 'users':
        writer.writerow(['ID', 'Email', 'Nombre', 'Apellido', 'Teléfono', 'Empresa', 'Activo', 'Staff', 'Fecha Registro'])
        for obj in model.objects.all():
            writer.writerow([
                obj.id,
                obj.email,
                obj.first_name,
                obj.last_name,
                obj.phone,
                obj.company.business_name if obj.company else '',
                'Sí' if obj.is_active else 'No',
                'Sí' if obj.is_staff else 'No',
                obj.date_joined.strftime('%Y-%m-%d %H:%M')
            ])
    
    elif model_name == 'companies':
        writer.writerow(['ID', 'RUC', 'Razón Social', 'Nombre Comercial', 'Email', 'Teléfono', 'Activo', 'Fecha Creación'])
        for obj in model.objects.all():
            writer.writerow([
                obj.id,
                obj.ruc,
                obj.business_name,
                obj.trade_name,
                obj.email,
                obj.phone,
                'Sí' if obj.is_active else 'No',
                obj.created_at.strftime('%Y-%m-%d %H:%M')
            ])
    
    elif model_name == 'certificates':
        writer.writerow(['ID', 'Empresa', 'Sujeto', 'Serial', 'Válido Desde', 'Válido Hasta', 'Estado'])
        for obj in model.objects.all():
            writer.writerow([
                obj.id,
                obj.company.business_name if obj.company else '',
                obj.subject_name,
                obj.serial_number,
                obj.valid_from.strftime('%Y-%m-%d') if obj.valid_from else '',
                obj.valid_to.strftime('%Y-%m-%d') if obj.valid_to else '',
                obj.status
            ])
    
    # Log export
    AuditLog.objects.create(
        user=request.user,
        action='EXPORT',
        model_name=model_name,
        object_representation=f'Exported {model.objects.count()} records',
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return response


# ========== API ENDPOINTS ==========

@login_required
@staff_required
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics refresh"""
    stats = {
        'total_users': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'active_users': User.objects.filter(is_active=True, is_staff=False).count(),
        'pending_users': UserCompanyAssignment.objects.filter(status='waiting').count(),
        'new_users_today': User.objects.filter(date_joined__date=timezone.now().date()).count(),
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
        'total_certificates': DigitalCertificate.objects.count(),
        'expiring_certificates': DigitalCertificate.objects.filter(
            valid_to__lte=timezone.now() + timedelta(days=30),
            valid_to__gte=timezone.now()
        ).count(),
        'unread_notifications': AdminNotification.objects.filter(is_read=False).count(),
    }
    
    # Include updated chart data
    charts = {
        'users': get_users_chart_data(),
        'activity': get_activity_chart_data(),
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'charts': charts
    })


@login_required
@staff_required
def global_search(request):
    """Global search across models"""
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    results = []
    
    # Search users
    users = User.objects.filter(
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    )[:5]
    
    for user in users:
        results.append({
            'type': 'user',
            'id': user.id,
            'title': user.get_full_name() or user.email,
            'subtitle': user.email,
            'url': f'/admin-panel/users/{user.id}/edit/',
            'icon': 'fas fa-user'
        })
    
    # Search companies
    companies = Company.objects.filter(
        Q(business_name__icontains=query) |
        Q(ruc__icontains=query) |
        Q(trade_name__icontains=query)
    )[:5]
    
    for company in companies:
        results.append({
            'type': 'company',
            'id': company.id,
            'title': company.business_name,
            'subtitle': f'RUC: {company.ruc}',
            'url': f'/admin-panel/companies/{company.id}/edit/',
            'icon': 'fas fa-building'
        })
    
    # Search certificates
    certificates = DigitalCertificate.objects.filter(
        Q(subject_name__icontains=query) |
        Q(serial_number__icontains=query)
    ).select_related('company')[:5]
    
    for cert in certificates:
        results.append({
            'type': 'certificate',
            'id': cert.id,
            'title': cert.subject_name,
            'subtitle': f'Serial: {cert.serial_number}',
            'url': f'/admin-panel/certificates/{cert.id}/view/',
            'icon': 'fas fa-certificate'
        })
    
    return JsonResponse({
        'success': True,
        'results': results,
        'count': len(results)
    })


# ========== PLACEHOLDER VIEWS (Por implementar) ==========

@login_required
@staff_required
def invoices_list(request):
    """List invoices - Por implementar"""
    context = {
        'page_title': 'Facturas',
        'invoices': [],
        'total_count': 0,
    }
    return render(request, 'custom_admin/invoices/list.html', context)


@login_required
@staff_required
def customers_list(request):
    """List customers - Por implementar"""
    context = {
        'page_title': 'Clientes',
        'customers': [],
        'total_count': 0,
    }
    return render(request, 'custom_admin/customers/list.html', context)


@login_required
@staff_required
def products_list(request):
    """List products - Por implementar"""
    context = {
        'page_title': 'Productos',
        'products': [],
        'total_count': 0,
    }
    return render(request, 'custom_admin/products/list.html', context)


@login_required
@staff_required
def sri_documents_list(request):
    """List SRI documents - Por implementar"""
    context = {
        'page_title': 'Documentos SRI',
        'documents': [],
        'total_count': 0,
    }
    return render(request, 'custom_admin/sri_documents/list.html', context)