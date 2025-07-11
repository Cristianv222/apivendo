# -*- coding: utf-8 -*-
"""
Views for users app
Vistas para la gestión de usuarios en VENDO_SRI
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


@login_required
def dashboard_view(request):
    """
    Vista principal del dashboard para usuarios autenticados
    """
    context = {
        'user': request.user,
        'company': request.user.company if hasattr(request.user, 'company') else None,
        'title': _('Dashboard'),
    }
    return render(request, 'users/dashboard.html', context)


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vista basada en clase para el dashboard
    """
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            'company': getattr(self.request.user, 'company', None),
            'title': _('Dashboard'),
        })
        return context


@login_required
def profile_view(request):
    """
    Vista del perfil del usuario
    """
    context = {
        'user': request.user,
        'profile': getattr(request.user, 'profile', None),
        'title': _('User Profile'),
    }
    return render(request, 'users/profile.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_update_view(request):
    """
    Vista para actualizar el perfil del usuario
    """
    if request.method == 'POST':
        try:
            # Aquí puedes agregar la lógica para actualizar el perfil
            # Por ahora, solo mostramos un mensaje de éxito
            messages.success(request, _('Profile updated successfully.'))
            return JsonResponse({'success': True, 'message': str(_('Profile updated successfully.'))})
        except Exception as e:
            messages.error(request, _('Error updating profile.'))
            return JsonResponse({'success': False, 'message': str(e)})
    
    return profile_view(request)


def login_view(request):
    """
    Vista personalizada de login (opcional, django-allauth maneja esto)
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    context = {
        'title': _('Login'),
    }
    return render(request, 'account/login.html', context)


def logout_view(request):
    """
    Vista personalizada de logout
    """
    logout(request)
    messages.success(request, _('You have been logged out successfully.'))
    return redirect('account_login')


@login_required
def settings_view(request):
    """
    Vista de configuraciones del usuario
    """
    context = {
        'user': request.user,
        'title': _('Settings'),
    }
    return render(request, 'users/settings.html', context)


# Vista de API para obtener información del usuario (para AJAX)
@login_required
@require_http_methods(["GET"])
def user_info_api(request):
    """
    API endpoint para obtener información del usuario actual
    """
    user_data = {
        'id': request.user.id,
        'email': request.user.email,
        'full_name': request.user.get_full_name(),
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'is_staff': request.user.is_staff,
        'is_company_admin': getattr(request.user, 'is_company_admin', False),
        'company': {
            'id': request.user.company.id,
            'name': request.user.company.business_name,
            'ruc': request.user.company.ruc,
        } if hasattr(request.user, 'company') and request.user.company else None,
    }
    
    return JsonResponse(user_data)


# Vista de inicio (redirect)
def home_view(request):
    """
    Vista de inicio que redirige según el estado de autenticación
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('account_login')