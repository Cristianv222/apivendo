# -*- coding: utf-8 -*-
"""
Admin configuration for users app
Panel de administración para usuarios de VENDO_SRI
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline para el perfil del usuario"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('Profile Information')
    fields = (
        'bio', 'birth_date', 'timezone', 'language', 
        'notifications_enabled'
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administración personalizada para el modelo User"""
    
    inlines = (UserProfileInline,)
    
    # Campos que se muestran en la lista
    list_display = (
        'email', 'get_full_name_display', 'company', 
        'is_company_admin', 'is_staff', 'is_active', 
        'date_joined', 'profile_picture_display'
    )
    
    # Campos por los que se puede filtrar
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 
        'is_company_admin', 'company', 'date_joined'
    )
    
    # Campos por los que se puede buscar
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    
    # Orden por defecto
    ordering = ('-date_joined',)
    
    # Configuración de campos en el formulario de edición
    fieldsets = (
        (_('Authentication'), {
            'fields': ('email', 'password')
        }),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone', 'profile_picture')
        }),
        (_('Company info'), {
            'fields': ('company', 'is_company_admin'),
            'classes': ('collapse',)
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Configuración para agregar nuevo usuario
    add_fieldsets = (
        (_('Authentication'), {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        (_('Personal info'), {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone'),
        }),
        (_('Company info'), {
            'classes': ('wide', 'collapse'),
            'fields': ('company', 'is_company_admin'),
        }),
        (_('Permissions'), {
            'classes': ('wide', 'collapse'),
            'fields': ('is_staff', 'is_active'),
        }),
    )
    
    # Configuración de filtros horizontales
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_full_name_display(self, obj):
        """Muestra el nombre completo del usuario"""
        return obj.get_display_name()
    get_full_name_display.short_description = _('Full Name')
    get_full_name_display.admin_order_field = 'first_name'
    
    def profile_picture_display(self, obj):
        """Muestra una miniatura de la foto de perfil"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="30" height="30" style="border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return _('No image')
    profile_picture_display.short_description = _('Picture')
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        try:
            qs = qs.select_related('company')
        except:
            pass  # Si company no existe aún, continúa sin error
        return qs


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Administración para el perfil del usuario"""
    
    list_display = (
        'user', 'language', 'timezone', 
        'notifications_enabled', 'updated_at'
    )
    
    list_filter = (
        'language', 'timezone', 'notifications_enabled', 
        'created_at', 'updated_at'
    )
    
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'bio')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Profile Information'), {
            'fields': ('bio', 'birth_date', 'language', 'timezone')
        }),
        (_('Preferences'), {
            'fields': ('notifications_enabled',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        try:
            qs = qs.select_related('user', 'user__company')
        except:
            qs = qs.select_related('user')  # Si company no existe, solo user
        return qs