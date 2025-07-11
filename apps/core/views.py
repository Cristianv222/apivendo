# -*- coding: utf-8 -*-
"""
Vistas del módulo Users para VENDO_SRI
Sistema de autenticación con OAuth y sala de espera
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView, FormView, CreateView, View
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings

from .models import UserProfile, UserSession

User = get_user_model()


class CustomLoginView(FormView):
    """
    Vista personalizada de login con gestión de sala de espera
    """
    template_name = 'users/login.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        # Si ya está autenticado, verificar su estado de aprobación
        if request.user.is_authenticated:
            if request.user.is_pending_approval():
                return redirect('users:waiting_room')
            elif request.user.is_rejected():
                return redirect('users:account_rejected')
            elif request.user.is_approved():
                return redirect(self.get_success_url())
            else:
                # Estado desconocido, cerrar sesión y continuar con login
                logout(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        user = authenticate(self.request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                # Verificar estado de aprobación ANTES de hacer login completo
                if user.is_pending_approval():
                    # Hacer login temporal para que pueda ver la sala de espera
                    login(self.request, user)
                    
                    # Configurar sesión temporal (más corta)
                    self.request.session.set_expiry(3600)  # 1 hora
                    
                    # Registrar la sesión
                    self.register_user_session(user)
                    
                    messages.info(
                        self.request, 
                        _('Tu cuenta está pendiente de aprobación. Te notificaremos cuando sea revisada.')
                    )
                    return redirect('users:waiting_room')
                
                elif user.is_rejected():
                    # Hacer login temporal para que pueda ver la página de rechazo
                    login(self.request, user)
                    
                    # Configurar sesión temporal (más corta)
                    self.request.session.set_expiry(3600)  # 1 hora
                    
                    # Registrar la sesión
                    self.register_user_session(user)
                    
                    messages.warning(
                        self.request, 
                        _('Tu cuenta ha sido rechazada. Contacta al administrador para más información.')
                    )
                    return redirect('users:account_rejected')
                
                elif not user.is_approved():
                    # Estado desconocido - no permitir login
                    messages.error(
                        self.request, 
                        _('Tu cuenta tiene un estado desconocido. Contacta al administrador.')
                    )
                    return self.form_invalid(form)
                
                # Usuario aprobado - login normal
                login(self.request, user)
                
                # Configurar duración de sesión
                remember_me = form.cleaned_data.get('remember_me', False)
                if not remember_me:
                    self.request.session.set_expiry(0)  # Expirar al cerrar navegador
                else:
                    self.request.session.set_expiry(30 * 24 * 60 * 60)  # 30 días
                
                # Registrar la sesión
                self.register_user_session(user)
                
                # Actualizar última actividad
                user.last_activity = timezone.now()
                user.save(update_fields=['last_activity'])
                
                # Mensaje de bienvenida
                messages.success(
                    self.request, 
                    _('Bienvenido %(name)s') % {'name': user.get_full_name()}
                )
                
                return redirect(self.get_success_url())
            else:
                messages.error(self.request, _('Su cuenta está desactivada'))
        else:
            messages.error(self.request, _('Credenciales incorrectas'))
        
        return self.form_invalid(form)
    
    def register_user_session(self, user):
        """Registra la sesión del usuario"""
        try:
            UserSession.objects.create(
                user=user,
                session_key=self.request.session.session_key,
                ip_address=self.get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception:
            pass  # No fallar el login por problemas de registro de sesión
    
    def get_client_ip(self):
        """Obtiene la IP del cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional"""
        context = super().get_context_data(**kwargs)
        
        # Agregar información para debugging en desarrollo
        if settings.DEBUG:
            context.update({
                'debug_info': {
                    'pending_users': User.objects.filter(approval_status='pending').count(),
                    'total_users': User.objects.count(),
                }
            })
        
        return context


class WaitingRoomView(TemplateView):
    """
    Vista para usuarios que están en espera de aprobación
    """
    template_name = 'users/waiting_room.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Solo usuarios autenticados pueden acceder
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        # Si el usuario ya está aprobado, redirigir al dashboard
        if request.user.is_approved():
            return redirect('dashboard')
        
        # Si el usuario está rechazado, mostrar página de rechazo
        if request.user.is_rejected():
            return redirect('users:account_rejected')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        context.update({
            'user': user,
            'approval_status': user.approval_status,
            'created_at': user.created_at,
            'waiting_time': timezone.now() - user.created_at,
            'contact_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@vendo-sri.com'),
        })
        
        return context


class AccountRejectedView(TemplateView):
    """
    Vista para usuarios cuya cuenta ha sido rechazada
    """
    template_name = 'users/account_rejected.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        # Solo usuarios rechazados pueden ver esta página
        if not request.user.is_rejected():
            if request.user.is_approved():
                return redirect('dashboard')
            else:
                return redirect('users:waiting_room')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        context.update({
            'user': user,
            'rejection_reason': user.rejection_reason,
            'rejected_at': user.approved_at,
            'rejected_by': user.approved_by,
            'contact_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@vendo-sri.com'),
        })
        
        return context


@method_decorator([login_required, staff_member_required], name='dispatch')
class PendingUsersView(TemplateView):
    """
    Vista para administradores para gestionar usuarios pendientes
    """
    template_name = 'users/pending_users.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener usuarios pendientes
        pending_users = User.objects.filter(approval_status='pending').order_by('-created_at')
        
        # Paginación
        paginator = Paginator(pending_users, 25)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Estadísticas
        stats = {
            'pending_count': pending_users.count(),
            'approved_today': User.objects.filter(
                approval_status='approved',
                approved_at__date=timezone.now().date()
            ).count(),
            'rejected_today': User.objects.filter(
                approval_status='rejected',
                approved_at__date=timezone.now().date()
            ).count(),
        }
        
        context.update({
            'pending_users': page_obj,
            'stats': stats,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
        })
        
        return context


class CustomLogoutView(View):
    """
    Vista personalizada de logout
    """
    
    def get(self, request):
        return self.post(request)
    
    def post(self, request):
        if request.user.is_authenticated:
            # Marcar la sesión como cerrada
            try:
                session = UserSession.objects.get(
                    user=request.user,
                    session_key=request.session.session_key,
                    logout_at__isnull=True
                )
                session.logout_at = timezone.now()
                session.save()
            except UserSession.DoesNotExist:
                pass
            
            user_name = request.user.get_full_name()
            logout(request)
            messages.success(request, _('Sesión cerrada correctamente. ¡Hasta luego!'))
        
        return redirect('users:login')


# ==========================================
# VISTAS AJAX PARA APROBACIÓN/RECHAZO
# ==========================================

@login_required
@staff_member_required
@require_POST
@csrf_protect
def approve_user_ajax(request, user_id):
    """
    Vista AJAX para aprobar un usuario
    """
    try:
        user_to_approve = get_object_or_404(User, pk=user_id)
        
        # Verificar que el usuario puede ser aprobado
        if not user_to_approve.is_pending_approval():
            return JsonResponse({
                'success': False,
                'message': 'El usuario no está pendiente de aprobación'
            }, status=400)
        
        # Aprobar usuario
        user_to_approve.approve_user(approved_by_user=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {user_to_approve.get_full_name()} aprobado exitosamente',
            'user_id': str(user_to_approve.pk),
            'new_status': 'approved'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }, status=500)


@login_required
@staff_member_required
@require_POST
@csrf_protect
def reject_user_ajax(request, user_id):
    """
    Vista AJAX para rechazar un usuario
    """
    try:
        user_to_reject = get_object_or_404(User, pk=user_id)
        
        # Verificar que el usuario puede ser rechazado
        if not user_to_reject.is_pending_approval():
            return JsonResponse({
                'success': False,
                'message': 'El usuario no está pendiente de aprobación'
            }, status=400)
        
        # Obtener razón del rechazo
        reason = request.POST.get('reason', '').strip()
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'Debe proporcionar una razón para el rechazo'
            }, status=400)
        
        # Rechazar usuario
        user_to_reject.reject_user(
            rejected_by_user=request.user,
            reason=reason
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {user_to_reject.get_full_name()} rechazado exitosamente',
            'user_id': str(user_to_reject.pk),
            'new_status': 'rejected'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }, status=500)


@login_required
@staff_member_required
def pending_users_count_ajax(request):
    """
    Vista AJAX para obtener el conteo de usuarios pendientes
    """
    try:
        count = User.objects.filter(approval_status='pending').count()
        return JsonResponse({
            'success': True,
            'count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==========================================
# VISTA DEL DASHBOARD (SIMPLE)
# ==========================================

@login_required
def dashboard_view(request):
    """
    Vista simple del dashboard
    """
    # Verificar estado de aprobación
    if request.user.is_pending_approval():
        return redirect('users:waiting_room')
    elif request.user.is_rejected():
        return redirect('users:account_rejected')
    elif not request.user.is_approved():
        messages.error(request, _('Tu cuenta tiene un estado desconocido.'))
        return redirect('users:login')
    
    context = {
        'user': request.user,
        'pending_users_count': User.objects.filter(approval_status='pending').count() if request.user.is_staff else 0,
    }
    
    return render(request, 'dashboard.html', context)


# ==========================================
# DECORADORES AUXILIARES
# ==========================================

def is_system_admin(user):
    """
    Verifica si el usuario es administrador del sistema
    """
    return user.is_authenticated and (user.is_superuser or user.is_system_admin)


def approved_user_required(view_func):
    """
    Decorador que requiere que el usuario esté aprobado
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if request.user.is_pending_approval():
            return redirect('users:waiting_room')
        
        if request.user.is_rejected():
            return redirect('users:account_rejected')
        
        if not request.user.is_approved():
            messages.error(request, _('Acceso denegado'))
            return redirect('users:login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper