# -*- coding: utf-8 -*-
"""
Configuración del admin para el módulo Users de VENDO_SRI
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q

from .models import User, UserProfile, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Administración personalizada para el modelo User
    """
    list_display = [
        'email', 'get_full_name', 'username', 'approval_status_display',
        'is_active', 'is_staff', 'created_at', 'last_login'
    ]
    list_filter = [
        'approval_status', 'is_active', 'is_staff', 'is_superuser',
        'created_at', 'last_login', 'document_type'
    ]
    search_fields = [
        'email', 'username', 'first_name', 'last_name', 
        'document_number', 'phone', 'mobile'
    ]
    ordering = ['-created_at']
    list_per_page = 50
    
    # Configuración de campos en formularios
    fieldsets = (
        (_('Información de autenticación'), {
            'fields': ('username', 'email', 'password')
        }),
        (_('Información personal'), {
            'fields': (
                'first_name', 'last_name', 'document_type', 'document_number',
                'phone', 'mobile', 'birth_date', 'address', 'avatar'
            )
        }),
        (_('Configuración de cuenta'), {
            'fields': (
                'language', 'timezone', 'is_active', 'is_staff', 
                'is_superuser', 'is_system_admin'
            )
        }),
        (_('Estado de aprobación'), {
            'fields': (
                'approval_status', 'approved_by', 'approved_at', 
                'rejection_reason'
            ),
            'classes': ('collapse',)
        }),
        (_('Seguridad'), {
            'fields': (
                'force_password_change', 'password_changed_at', 'last_activity'
            ),
            'classes': ('collapse',)
        }),
        (_('Permisos'), {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Fechas importantes'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (_('Información requerida'), {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name',
                'password1', 'password2'
            ),
        }),
        (_('Información adicional (opcional)'), {
            'classes': ('wide', 'collapse'),
            'fields': (
                'document_type', 'document_number', 'phone', 'mobile'
            ),
        }),
    )
    
    readonly_fields = [
        'created_at', 'updated_at', 'last_login', 'date_joined',
        'password_changed_at', 'last_activity'
    ]
    
    filter_horizontal = ('groups', 'user_permissions')
    
    def approval_status_display(self, obj):
        """Mostrar estado de aprobación con colores"""
        status_colors = {
            'pending': '#ffc107',  # amarillo
            'approved': '#28a745',  # verde
            'rejected': '#dc3545',  # rojo
        }
        
        status_icons = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
        }
        
        color = status_colors.get(obj.approval_status, '#6c757d')
        icon = status_icons.get(obj.approval_status, '❓')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_approval_status_display()
        )
    approval_status_display.short_description = _('Estado de aprobación')
    approval_status_display.admin_order_field = 'approval_status'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('approved_by').prefetch_related('groups')
    
    def save_model(self, request, obj, form, change):
        """Lógica personalizada al guardar"""
        # Si es un usuario nuevo, establecer quien lo creó
        if not change:
            # El usuario se creará con estado 'pending' por defecto
            pass
        
        # Si se está aprobando/rechazando manualmente desde el admin
        if change:
            old_obj = User.objects.get(pk=obj.pk)
            
            # Si cambió el estado de aprobación
            if old_obj.approval_status != obj.approval_status:
                if obj.approval_status == 'approved' and not obj.approved_by:
                    obj.approved_by = request.user
                    obj.approved_at = timezone.now()
                elif obj.approval_status == 'rejected' and not obj.approved_by:
                    obj.approved_by = request.user
                    obj.approved_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    # Acciones personalizadas
    actions = ['approve_users', 'reject_users', 'activate_users', 'deactivate_users']
    
    def approve_users(self, request, queryset):
        """Aprobar usuarios seleccionados"""
        pending_users = queryset.filter(approval_status='pending')
        count = 0
        
        for user in pending_users:
            user.approve_user(approved_by_user=request.user, send_notification=False)
            count += 1
        
        if count > 0:
            self.message_user(
                request,
                f'{count} usuario(s) aprobado(s) exitosamente.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No hay usuarios pendientes en la selección.',
                messages.WARNING
            )
    approve_users.short_description = _('Aprobar usuarios seleccionados')
    
    def reject_users(self, request, queryset):
        """Rechazar usuarios seleccionados"""
        pending_users = queryset.filter(approval_status='pending')
        count = 0
        
        for user in pending_users:
            user.reject_user(
                rejected_by_user=request.user,
                reason='Rechazado masivamente desde el admin',
                send_notification=False
            )
            count += 1
        
        if count > 0:
            self.message_user(
                request,
                f'{count} usuario(s) rechazado(s) exitosamente.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No hay usuarios pendientes en la selección.',
                messages.WARNING
            )
    reject_users.short_description = _('Rechazar usuarios seleccionados')
    
    def activate_users(self, request, queryset):
        """Activar usuarios seleccionados"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            f'{count} usuario(s) activado(s) exitosamente.',
            messages.SUCCESS
        )
    activate_users.short_description = _('Activar usuarios seleccionados')
    
    def deactivate_users(self, request, queryset):
        """Desactivar usuarios seleccionados"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            f'{count} usuario(s) desactivado(s) exitosamente.',
            messages.SUCCESS
        )
    deactivate_users.short_description = _('Desactivar usuarios seleccionados')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Administración para UserProfile
    """
    list_display = [
        'user', 'position', 'department', 'employee_code',
        'theme', 'email_notifications', 'created_at'
    ]
    list_filter = [
        'theme', 'email_notifications', 'sms_notifications',
        'system_notifications', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'position', 'department', 'employee_code'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Usuario'), {
            'fields': ('user',)
        }),
        (_('Información profesional'), {
            'fields': ('position', 'department', 'employee_code')
        }),
        (_('Configuraciones de interfaz'), {
            'fields': ('theme', 'sidebar_collapsed')
        }),
        (_('Configuraciones de notificaciones'), {
            'fields': (
                'email_notifications', 'sms_notifications', 'system_notifications'
            )
        }),
        (_('Información adicional'), {
            'fields': ('bio', 'social_media'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Administración para UserSession
    """
    list_display = [
        'user', 'ip_address', 'login_at', 'last_activity',
        'logout_at', 'is_expired', 'session_duration'
    ]
    list_filter = [
        'is_expired', 'login_at', 'logout_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'ip_address', 'session_key'
    ]
    ordering = ['-login_at']
    
    fieldsets = (
        (_('Usuario y sesión'), {
            'fields': ('user', 'session_key')
        }),
        (_('Información de conexión'), {
            'fields': ('ip_address', 'user_agent')
        }),
        (_('Timestamps'), {
            'fields': ('login_at', 'last_activity', 'logout_at', 'is_expired')
        }),
    )
    
    readonly_fields = [
        'user', 'session_key', 'ip_address', 'user_agent',
        'login_at', 'last_activity', 'logout_at'
    ]
    
    def session_duration(self, obj):
        """Mostrar duración de la sesión"""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "-"
    session_duration.short_description = _('Duración')
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def has_add_permission(self, request):
        """No permitir crear sesiones manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Solo permitir marcar como expirada"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar sesiones antiguas"""
        return True


# Configuración del admin site
admin.site.site_header = 'VENDO SRI - Administración'
admin.site.site_title = 'VENDO SRI Admin'
admin.site.index_title = 'Panel de Administración'

# Registrar modelos de allauth si es necesario
try:
    from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
    
    # Personalizar la administración de SocialApp
    class SocialAppAdmin(admin.ModelAdmin):
        list_display = ['name', 'provider', 'client_id_display']
        list_filter = ['provider']
        search_fields = ['name', 'provider', 'client_id']
        
        def client_id_display(self, obj):
            """Mostrar solo parte del client_id por seguridad"""
            if obj.client_id:
                return f"{obj.client_id[:20]}..."
            return "-"
        client_id_display.short_description = 'Client ID'
    
    # Re-registrar con configuración personalizada
    admin.site.unregister(SocialApp)
    admin.site.register(SocialApp, SocialAppAdmin)
    
except ImportError:
    pass