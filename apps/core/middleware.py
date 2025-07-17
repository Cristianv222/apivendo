# -*- coding: utf-8 -*-
"""
Session Timeout Middleware
Gestiona el cierre automático de sesión por inactividad
"""

from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from datetime import timedelta
import json


class SessionTimeoutMiddleware:
    """
    Middleware para cerrar sesión automáticamente después de un período de inactividad
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Tiempo de timeout en segundos (default 1 hora)
        self.timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)
        # Rutas exentas del timeout
        self.exempt_urls = [
            '/accounts/login/',
            '/accounts/logout/',
            '/api/session/heartbeat/',
            '/static/',
            '/media/',
            '/__debug__/',
            '/admin/jsi18n/',  # Para evitar problemas con el admin
        ]
    
    def __call__(self, request):
        # No aplicar a rutas exentas
        if any(request.path.startswith(url) for url in self.exempt_urls):
            return self.get_response(request)
        
        # Solo para usuarios autenticados
        if request.user.is_authenticated:
            # Obtener última actividad
            last_activity_str = request.session.get('last_activity')
            
            if last_activity_str:
                # Convertir string a datetime
                last_activity = timezone.datetime.fromisoformat(last_activity_str)
                elapsed_time = timezone.now() - last_activity
                
                # Si ha pasado más del tiempo límite
                if elapsed_time > timedelta(seconds=self.timeout):
                    # Cerrar sesión
                    logout(request)
                    messages.warning(
                        request, 
                        'Tu sesión ha expirado por inactividad. Por favor, inicia sesión nuevamente.'
                    )
                    
                    # Guardar la URL a la que intentaba acceder
                    if request.method == 'GET':
                        request.session['next_url'] = request.get_full_path()
                    
                    # Redirigir al login
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        # Para peticiones AJAX
                        from django.http import JsonResponse
                        return JsonResponse({
                            'session_expired': True,
                            'redirect_url': reverse('users:login')
                        }, status=401)
                    else:
                        # Para peticiones normales
                        return redirect('users:login')
            
            # Actualizar última actividad
            request.session['last_activity'] = timezone.now().isoformat()
            
            # Calcular tiempo restante para el cliente
            if last_activity_str:
                last_activity = timezone.datetime.fromisoformat(last_activity_str)
                elapsed = (timezone.now() - last_activity).total_seconds()
                time_remaining = max(0, self.timeout - elapsed)
                request.session['time_remaining'] = int(time_remaining)
        
        response = self.get_response(request)
        
        # Agregar headers para el JavaScript del cliente
        if request.user.is_authenticated and hasattr(request, 'session'):
            time_remaining = request.session.get('time_remaining', self.timeout)
            response['X-Session-Timeout'] = str(self.timeout)
            response['X-Session-Time-Remaining'] = str(time_remaining)
        
        return response


class SessionActivityMiddleware:
    """
    Middleware para trackear la actividad del usuario
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs que no cuentan como actividad
        self.non_activity_urls = [
            '/api/session/heartbeat/',
            '/api/session/check/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # Solo para usuarios autenticados
        if request.user.is_authenticated:
            # No contar ciertas URLs como actividad
            is_activity = not any(
                request.path.startswith(url) for url in self.non_activity_urls
            )
            
            if is_activity:
                # Registrar actividad
                request.session['last_real_activity'] = timezone.now().isoformat()
                
                # Registrar tipo de actividad
                activity_log = request.session.get('activity_log', [])
                activity_log.append({
                    'path': request.path,
                    'method': request.method,
                    'timestamp': timezone.now().isoformat()
                })
                
                # Mantener solo las últimas 10 actividades
                request.session['activity_log'] = activity_log[-10:]
        
        response = self.get_response(request)
        return response