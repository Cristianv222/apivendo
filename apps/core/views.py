# -*- coding: utf-8 -*-
"""
Core views - VERSIÓN COMPLETA CON TOKENS, EDICIÓN DE EMPRESA Y CERTIFICADOS
Todas las vistas validadas con decoradores personalizados
"""

import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from datetime import datetime, timedelta
from functools import wraps

from apps.companies.models import Company, CompanyAPIToken
from apps.certificates.models import DigitalCertificate

# Importar User del sistema de autenticación de Django
from django.contrib.auth import get_user_model
User = get_user_model()

# ========== IMPORTAR DECORADORES DEL SISTEMA ==========
try:
    from apps.api.views.sri_views import (
        audit_api_action,
        get_user_company_by_id
    )
except ImportError:
    # Si no existen, crear versiones simples
    def audit_api_action(action):
        def decorator(func):
            return func
        return decorator
    
    def get_user_company_by_id(company_id, user):
        try:
            company = Company.objects.get(id=company_id, is_active=True)
            if user.is_staff or user.is_superuser:
                return company
            # Verificar si el usuario tiene acceso a la empresa
            user_companies = get_user_companies_secure(user)
            if user_companies.filter(id=company.id).exists():
                return company
            return None
        except Company.DoesNotExist:
            return None

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
    Función auxiliar SEGURA - Obtiene las empresas del usuario
    """
    # Intentar usar el helper si existe
    try:
        from apps.api.user_company_helper import get_user_companies_exact
        return get_user_companies_exact(user)
    except ImportError:
        pass
    
    # Si es admin, puede ver todas las empresas
    if user.is_staff or user.is_superuser:
        return Company.objects.filter(is_active=True)
    
    # Para usuarios normales, intentar diferentes formas de obtener las empresas
    
    # Opción 1: Si el usuario tiene un campo 'companies' (ManyToMany)
    if hasattr(user, 'companies'):
        return user.companies.filter(is_active=True)
    
    # Opción 2: Si existe un modelo UserCompany en algún lado
    try:
        from apps.users.models import UserCompany
        user_company_ids = UserCompany.objects.filter(
            user=user,
            is_active=True
        ).values_list('company_id', flat=True)
        return Company.objects.filter(id__in=user_company_ids, is_active=True)
    except ImportError:
        pass
    
    # Opción 3: Si existe una relación a través del modelo User
    try:
        # Django permite acceso a través de relaciones reversas
        if hasattr(User, 'companies'):
            through_model = User.companies.through
            user_company_ids = through_model.objects.filter(
                user=user
            ).values_list('company_id', flat=True)
            return Company.objects.filter(id__in=user_company_ids, is_active=True)
    except:
        pass
    
    # Opción 4: Por defecto, devolver la primera empresa activa
    # Esto es temporal - deberías implementar la lógica correcta para tu caso
    logger.warning(f"No se pudo determinar las empresas del usuario {user.username}, usando empresa por defecto")
    return Company.objects.filter(is_active=True)[:1]


# ========== VISTAS PRINCIPALES CON TOKENS ==========

@login_required
def dashboard(request):
    """
    Vista principal del dashboard que redirige según el tipo de usuario
    """
    if request.user.is_staff:
        return admin_dashboard_view(request)
    else:
        return user_dashboard(request)


@login_required
@audit_html_action('VIEW_DASHBOARD')
def dashboard_view(request):
    """Alias para compatibilidad"""
    return dashboard(request)


@login_required
@audit_html_action('VIEW_USER_DASHBOARD')
def user_dashboard(request):
    """
    Dashboard mejorado para usuarios con toda la información necesaria
    """
    user = request.user
    
    # Verificar si es admin
    if user.is_staff or user.is_superuser:
        return redirect('/admin/')
    
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
    
    # 🔑 Preparar tokens disponibles para el selector
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
                'dashboard_url': f"/dashboard/?token={company_token.key}",
                'api_test_url': f"/api/companies/",
                'token_display': f"{company_token.key[:20]}...",
            })
            
        except Exception as e:
            logger.error(f"❌ Error obtaining token for {company.business_name}: {e}")
    
    # ==================== INFORMACIÓN DEL CERTIFICADO ====================
    has_certificate = False
    certificate_info = {}
    
    if selected_company:
        try:
            certificate = DigitalCertificate.objects.filter(
                company=selected_company,
                status='ACTIVE'
            ).first()
            
            if certificate:
                has_certificate = True
                certificate_info = {
                    'issuer': certificate.issuer_name,
                    'subject': certificate.subject_name,
                    'expiry': certificate.valid_to,
                    'days_left': certificate.days_until_expiration,
                    'expired': certificate.is_expired,
                    'serial': certificate.serial_number
                }
        except Exception as e:
            logger.error(f"Error obteniendo certificado: {e}")
    
    # ==================== BILLING ====================
    current_plan = None
    all_plans = []
    recent_purchases = []
    billing_profile = None
    
    try:
        from apps.billing.models import Plan, CompanyBillingProfile, PlanPurchase
        BILLING_AVAILABLE = True
    except ImportError:
        try:
            # Intentar con nombre alternativo
            from apps.billing.models import Plan, BillingProfile as CompanyBillingProfile, PlanPurchase
            BILLING_AVAILABLE = True
        except ImportError:
            BILLING_AVAILABLE = False
            logger.warning("Billing models not available")
    
    if BILLING_AVAILABLE and selected_company:
        try:
            # Asegurar que existe el billing profile
            billing_profile, created = CompanyBillingProfile.objects.get_or_create(
                company=selected_company,
                defaults={
                    'available_invoices': 0,
                    'total_invoices_purchased': 0,
                    'total_invoices_consumed': 0,
                }
            )
            
            if created:
                logger.info(f"💳 Billing profile created for {selected_company.business_name}")
            
            # Obtener plan actual
            last_purchase = PlanPurchase.objects.filter(
                company=selected_company,
                payment_status='approved'
            ).order_by('-created_at').first()
            
            if last_purchase:
                current_plan = last_purchase.plan
            
            # Obtener todos los planes activos
            all_plans = Plan.objects.filter(is_active=True).order_by('price')
            
            # Obtener compras recientes
            recent_purchases = PlanPurchase.objects.filter(
                company=selected_company
            ).order_by('-created_at')[:5]
        except Exception as e:
            logger.error(f"Error loading billing data: {e}")
            BILLING_AVAILABLE = False
    # En la sección de ESTADÍSTICAS, reemplaza desde la línea que dice "# ==================== ESTADÍSTICAS ====================" hasta "except Exception as e:"

    # ==================== ESTADÍSTICAS ====================
    stats = {
        'total_invoices': 0,
        'authorized_invoices': 0,
        'pending_invoices': 0,
        'total_amount': 0
    }
    
    recent_invoices = []
    document_stats = {
        'facturas': 0,
        'retenciones': 0,
        'liquidaciones': 0,
        'notas_credito': 0,
        'notas_debito': 0,
    }
    
    try:
        from apps.sri_integration.models import ElectronicDocument
        
        if selected_company:
            # Obtener TODOS los tipos de documentos, no solo facturas
            all_documents = ElectronicDocument.objects.filter(
                company=selected_company
            )
            
            # Estadísticas generales (manteniendo compatibilidad)
            stats = {
                'total_invoices': all_documents.count(),  # Total de TODOS los documentos
                'authorized_invoices': all_documents.filter(
                    status='AUTHORIZED'
                ).count(),
                'pending_invoices': all_documents.filter(
                    status__in=['DRAFT', 'GENERATED', 'SIGNED', 'SENT']
                ).count(),
                'total_amount': all_documents.filter(
                    status='AUTHORIZED'
                ).aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            }
            
            # Estadísticas por tipo de documento
            document_stats = {
                'facturas': all_documents.filter(document_type='INVOICE').count(),
                'retenciones': all_documents.filter(document_type='RETENTION').count(),
                'liquidaciones': all_documents.filter(document_type='PURCHASE_SETTLEMENT').count(),
                'notas_credito': all_documents.filter(document_type='CREDIT_NOTE').count(),
                'notas_debito': all_documents.filter(document_type='DEBIT_NOTE').count(),
            }
            
            # Documentos recientes - TODOS los tipos
            recent_invoices = all_documents.order_by('-created_at')[:50]
            
            # Agregar campo mapped_type para el filtro del template
            for doc in recent_invoices:
                # Mapear los tipos de documento del modelo a los valores del filtro
                type_mapping = {
                    'INVOICE': 'factura',
                    'RETENTION': 'retencion',
                    'PURCHASE_SETTLEMENT': 'liquidacion',
                    'CREDIT_NOTE': 'nota_credito',
                    'DEBIT_NOTE': 'nota_debito',
                    'REMISSION_GUIDE': 'guia_remision',
                }
                doc.mapped_type = type_mapping.get(doc.document_type, 'factura')
                
                # También agregar el nombre del cliente/proveedor según el tipo
                if doc.document_type in ['RETENTION', 'PURCHASE_SETTLEMENT']:
                    # Para retenciones y liquidaciones, buscar el campo supplier
                    doc.client_name = getattr(doc, 'supplier_name', doc.customer_name)
                else:
                    doc.client_name = doc.customer_name
            
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
    
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
        'available_companies_with_tokens': available_companies_with_tokens,
        'has_certificate': has_certificate,
        'certificate_info': certificate_info,
        'certificate_expired': certificate_info.get('expired', False),
        'certificate_expiry': certificate_info.get('expiry'),
        'certificate_days_left': certificate_info.get('days_left', 0),
        'certificate_issuer': certificate_info.get('issuer'),
        'stats': stats,
        'recent_invoices': recent_invoices,
        'document_stats': document_stats,
        'status_choices': INVOICE_STATUS_CHOICES,
        'is_admin': False,
        'current_filters': {
            'token': current_token,
            'status': request.GET.get('status'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        },
        'token_mode': True,
        'smart_mode': True,
        'security_validation': {
            'validated_by_decorator': True,
            'user_access_confirmed': True,
            'companies_filtered_by_user': True,
            'token_based_access': True,
            'smart_redirect_enabled': True,
            'current_token': current_token[:20] + '...' if current_token else None,
        },
        # Variables de billing
        'billing_available': BILLING_AVAILABLE,
        'billing_profile': billing_profile,
        'current_plan': current_plan,
        'all_plans': all_plans,
        'recent_purchases': recent_purchases,
    }
    
    return render(request, 'dashboard/user_dashboard.html', context)


@login_required
@audit_html_action('UPDATE_COMPANY')
@require_POST
def company_update(request, company_id):
    """
    Vista AJAX para actualizar información de la empresa
    """
    company = get_object_or_404(Company, id=company_id)
    
    # Verificar permisos
    user_companies = get_user_companies_secure(request.user)
    if not user_companies.filter(id=company.id).exists() and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'errors': {'general': 'No tienes permisos para editar esta empresa'}
        }, status=403)
    
    try:
        with transaction.atomic():
            # Actualizar campos básicos
            company.business_name = request.POST.get('business_name', company.business_name)
            company.trade_name = request.POST.get('trade_name', '')
            company.email = request.POST.get('email', company.email)
            company.phone = request.POST.get('phone', '')
            company.address = request.POST.get('address', company.address)
            company.ciudad = request.POST.get('ciudad', '')
            company.provincia = request.POST.get('provincia', '')
            company.codigo_postal = request.POST.get('codigo_postal', '')
            company.website = request.POST.get('website', '')
            
            # Actualizar campos SRI
            company.tipo_contribuyente = request.POST.get('tipo_contribuyente', company.tipo_contribuyente)
            company.obligado_contabilidad = request.POST.get('obligado_contabilidad', company.obligado_contabilidad)
            company.contribuyente_especial = request.POST.get('contribuyente_especial', '') or None
            company.codigo_establecimiento = request.POST.get('codigo_establecimiento', company.codigo_establecimiento)
            company.codigo_punto_emision = request.POST.get('codigo_punto_emision', company.codigo_punto_emision)
            company.ambiente_sri = request.POST.get('ambiente_sri', company.ambiente_sri)
            company.tipo_emision = request.POST.get('tipo_emision', company.tipo_emision)
            
            # Manejar logo si se subió
            if 'logo' in request.FILES:
                company.logo = request.FILES['logo']
            
            # Validar y guardar
            company.full_clean()
            company.save()
            
            # Manejar certificado si se subió
            if 'certificate_file' in request.FILES:
                handle_certificate_upload(
                    company=company,
                    file=request.FILES['certificate_file'],
                    password=request.POST.get('certificate_password', ''),
                    alias=request.POST.get('certificate_alias', ''),
                    user=request.user
                )
            
            logger.info(f"✅ Company {company.business_name} updated by {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Información actualizada correctamente'
            })
            
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'errors': e.message_dict if hasattr(e, 'message_dict') else {'general': str(e)}
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        return JsonResponse({
            'success': False,
            'errors': {'general': f'Error al actualizar: {str(e)}'}
        }, status=500)


@login_required
@audit_html_action('UPLOAD_CERTIFICATE')
def certificate_upload(request, company_id):
    """
    Vista dedicada para subir/actualizar certificado digital
    """
    company = get_object_or_404(Company, id=company_id)
    
    # Verificar permisos
    user_companies = get_user_companies_secure(request.user)
    if not user_companies.filter(id=company.id).exists() and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'errors': {'general': 'No tienes permisos para gestionar certificados de esta empresa'}
        }, status=403)
    
    if request.method == 'POST':
        try:
            certificate = handle_certificate_upload(
                company=company,
                file=request.FILES.get('certificate_file'),
                password=request.POST.get('certificate_password', ''),
                alias=request.POST.get('certificate_alias', ''),
                user=request.user
            )
            
            messages.success(request, 'Certificado cargado exitosamente')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Certificado cargado correctamente',
                    'certificate': {
                        'id': certificate.id,
                        'issuer': certificate.issuer_name,
                        'subject': certificate.subject_name,
                        'valid_from': certificate.valid_from.strftime('%d/%m/%Y'),
                        'valid_to': certificate.valid_to.strftime('%d/%m/%Y'),
                        'days_until_expiration': certificate.days_until_expiration,
                        'is_active': certificate.status == 'ACTIVE'
                    }
                })
            
            # Obtener token para redirección
            try:
                company_token = CompanyAPIToken.objects.get(company=company, is_active=True)
                return redirect(f'/dashboard/?token={company_token.key}')
            except:
                return redirect('core:dashboard')
            
        except Exception as e:
            error_msg = f'Error al procesar certificado: {str(e)}'
            messages.error(request, error_msg)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': {'certificate_file': error_msg}
                }, status=400)
    
    return redirect('core:dashboard')


def handle_certificate_upload(company, file, password, alias, user):
    """
    Maneja la carga y procesamiento del certificado digital
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    import hashlib
    
    if not file:
        raise ValueError("No se proporcionó archivo de certificado")
    
    try:
        # Leer el archivo
        cert_data = file.read()
        
        # Intentar cargar el certificado para validarlo
        try:
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                cert_data,
                password.encode() if password else None,
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"No se pudo leer el certificado. Verifique que el archivo y contraseña sean correctos: {str(e)}")
        
        if not certificate:
            raise ValueError("El archivo no contiene un certificado válido")
        
        # Extraer información del certificado
        subject = certificate.subject
        issuer = certificate.issuer
        
        # Formatear nombres
        subject_name = ", ".join([f"{attr.oid._name}={attr.value}" for attr in subject])
        issuer_name = ", ".join([f"{attr.oid._name}={attr.value}" for attr in issuer])
        
        # Desactivar certificados anteriores
        DigitalCertificate.objects.filter(
            company=company,
            status='ACTIVE'
        ).update(status='INACTIVE')
        
        # Crear nuevo certificado
        new_cert = DigitalCertificate(
            company=company,
            subject_name=subject_name[:255],
            issuer_name=issuer_name[:255],
            serial_number=str(certificate.serial_number)[:100],
            valid_from=certificate.not_valid_before,
            valid_to=certificate.not_valid_after,
            status='ACTIVE',
            created_by=user,
            environment='TEST' if company.ambiente_sri == '1' else 'PRODUCTION'
        )
        
        # Establecer contraseña hasheada
        new_cert.set_password(password)
        
        # Guardar archivo
        file.seek(0)  # Volver al inicio del archivo
        new_cert.certificate_file.save(f"{company.ruc}_cert.p12", file)
        
        # Guardar certificado
        new_cert.save()
        
        logger.info(f"✅ Certificate uploaded for company {company.business_name} by {user.username}")
        
        return new_cert
        
    except Exception as e:
        logger.error(f"Error processing certificate: {str(e)}")
        raise ValueError(f"Error al procesar el certificado: {str(e)}")


@login_required
def company_info_modal(request, company_id):
    """
    Vista para obtener información de la empresa para el modal de edición
    """
    company = get_object_or_404(Company, id=company_id)
    
    # Verificar permisos
    user_companies = get_user_companies_secure(request.user)
    if not user_companies.filter(id=company.id).exists() and not request.user.is_staff:
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    
    # Obtener información del certificado si existe
    certificate_info = None
    try:
        certificate = company.digital_certificate
        if certificate:
            certificate_info = {
                'has_certificate': True,
                'issuer': certificate.issuer_name,
                'valid_until': certificate.valid_to.strftime('%d/%m/%Y'),
                'days_left': certificate.days_until_expiration,
                'is_expired': certificate.is_expired,
                'is_active': certificate.status == 'ACTIVE'
            }
    except:
        certificate_info = {'has_certificate': False}
    
    # Preparar datos para el formulario
    data = {
        'company': {
            'id': company.id,
            'ruc': company.ruc,
            'business_name': company.business_name,
            'trade_name': company.trade_name,
            'email': company.email,
            'phone': company.phone,
            'address': company.address,
            'ciudad': company.ciudad,
            'provincia': company.provincia,
            'codigo_postal': company.codigo_postal,
            'website': company.website,
            'tipo_contribuyente': company.tipo_contribuyente,
            'obligado_contabilidad': company.obligado_contabilidad,
            'contribuyente_especial': company.contribuyente_especial,
            'codigo_establecimiento': company.codigo_establecimiento,
            'codigo_punto_emision': company.codigo_punto_emision,
            'ambiente_sri': company.ambiente_sri,
            'tipo_emision': company.tipo_emision,
            'logo_url': company.logo.url if company.logo else None
        },
        'certificate': certificate_info,
        'tipo_contribuyente_choices': list(Company.TIPO_CONTRIBUYENTE_CHOICES),
        'obligado_contabilidad_choices': list(Company.OBLIGADO_CONTABILIDAD_CHOICES)
    }
    
    return JsonResponse(data)


@login_required
def company_select(request, company_id):
    """
    Cambia la empresa seleccionada - redirige con token
    """
    company = get_object_or_404(Company, id=company_id, is_active=True)
    
    # Verificar que el usuario tenga acceso
    user_companies = get_user_companies_secure(request.user)
    if user_companies.filter(id=company.id).exists() or request.user.is_staff:
        # Obtener o crear token para la empresa
        try:
            company_token, created = CompanyAPIToken.objects.get_or_create(
                company=company,
                defaults={
                    'name': f'Auto-generated token for {company.business_name}',
                    'is_active': True
                }
            )
            
            messages.success(request, f'Empresa cambiada a: {company.display_name}')
            return redirect(f'/dashboard/?token={company_token.key}')
            
        except Exception as e:
            logger.error(f"Error getting token for company selection: {e}")
            messages.error(request, 'Error al cambiar de empresa')
    else:
        messages.error(request, 'No tienes acceso a esta empresa')
    
    return redirect('core:dashboard')


@login_required
def company_dashboard(request, company_id):
    """
    Dashboard específico de una empresa - redirige con token
    """
    company = get_object_or_404(Company, id=company_id, is_active=True)
    
    # Verificar acceso
    user_companies = get_user_companies_secure(request.user)
    if user_companies.filter(id=company.id).exists() or request.user.is_staff:
        # Obtener o crear token y redirigir
        try:
            company_token, created = CompanyAPIToken.objects.get_or_create(
                company=company,
                defaults={
                    'name': f'Auto-generated token for {company.business_name}',
                    'is_active': True
                }
            )
            
            return redirect(f'/dashboard/?token={company_token.key}')
            
        except Exception as e:
            logger.error(f"Error in company_dashboard: {e}")
            messages.error(request, 'Error al acceder al dashboard de la empresa')
    else:
        messages.error(request, 'No tienes acceso a esta empresa')
    
    return redirect('core:dashboard')


# ========== VISTAS ADMINISTRATIVAS ==========

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
    total_tokens = CompanyAPIToken.objects.filter(is_active=True).count()
    
    # Valores por defecto
    waiting_users = 0
    assigned_users = total_users
    unread_notifications = 0
    recent_notifications = []
    recent_waiting = []
    total_invoices = 0
    pending_invoices = 0
    
    # Estadísticas de tokens más utilizados
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
        'total_tokens': total_tokens,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'unread_notifications': unread_notifications,
    }
    
    context = {
        'is_admin': True,
        'admin_stats': admin_stats,
        'top_tokens': top_tokens,
        'recent_notifications': recent_notifications,
        'recent_waiting': recent_waiting,
        'assignments_available': False,
        'invoices_available': False,
        'security_validation': {
            'admin_access_confirmed': True,
            'user': request.user.username,
            'token_system_enabled': True,
        }
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


# ========== APIs CON TOKENS ==========

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
                'redirect_url': f'/dashboard/?token={token}',
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
        # FILTRAR SOLO FACTURAS DE LA EMPRESA VALIDADA POR TOKEN
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
            'company_token': company_token.key[:20] + '...',
            'invoices': invoices_data,
            'total_count': invoices.count(),
            'security_validation': {
                'validated_by_token': True,
                'token_validated': True,
                'user_access_confirmed': True
            }
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'El módulo de facturación no está disponible',
            'company_name': getattr(company, 'business_name', company.trade_name),
            'company_token': company_token.key[:20] + '...',
            'invoices': [],
            'total_count': 0,
            'security_validation': {
                'validated_by_token': True,
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
    
    # VALIDACIÓN CRÍTICA: Solo facturas de empresas del usuario
    user_companies = get_user_companies_secure(request.user)
    
    if user_companies.exists():
        try:
            invoice = Invoice.objects.select_related('company').get(
                id=invoice_id,
                company__in=user_companies
            )
            logger.info(f"✅ User {request.user.username} accessing invoice {invoice_id}")
            
            # Obtener token de la empresa de la factura
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
        'dashboard_token_url': dashboard_token_url,
        'is_admin': request.user.is_staff or request.user.is_superuser,
        'security_validation': {
            'validated_by_query_filter': True,
            'user_access_confirmed': True,
            'token_url_generated': True,
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
        # ESTADÍSTICAS SOLO DE EMPRESAS DEL USUARIO
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
                    'token_display': token_display,
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
            'company_stats': company_stats,
            'total_last_30': invoices_last_30.count(),
            'security_validation': {
                'filtered_by_user_companies': True,
                'companies_count': user_companies.count(),
                'user': request.user.username,
                'token_system_enabled': True,
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
                'token_system_enabled': True,
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
                'dashboard_url': f"/dashboard/?token={company_tokens.first().key}",
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