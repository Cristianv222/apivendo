# -*- coding: utf-8 -*-
"""
Admin configuration for core app
Panel de administración para modelos core de VENDO_SRI
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
import json
from .models import AuditLog, SystemConfiguration, FileUpload


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Administración para los logs de auditoría"""
    
    list_display = (
        'created_at', 'user_display', 'action', 'model_name', 
        'object_representation', 'ip_address'
    )
    
    list_filter = (
        'action', 'model_name', 'created_at', 'user'
    )
    
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'model_name', 'object_representation', 'ip_address'
    )
    
    readonly_fields = (
        'created_at', 'user', 'action', 'model_name', 'object_id',
        'object_representation', 'changes_display', 'ip_address',
        'user_agent', 'additional_data_display'
    )
    
    date_hierarchy = 'created_at'
    
    ordering = ['-created_at']
    
    # Hacer todos los campos de solo lectura
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def user_display(self, obj):
        """Muestra el usuario con enlace"""
        if obj.user:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:users_user_change', args=[obj.user.pk]),
                obj.user.get_display_name()
            )
        return _('System')
    user_display.short_description = _('User')
    user_display.admin_order_field = 'user__email'
    
    def changes_display(self, obj):
        """Muestra los cambios en formato JSON legible"""
        if obj.changes:
            formatted_json = json.dumps(obj.changes, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_json)
        return _('No changes')
    changes_display.short_description = _('Changes')
    
    def additional_data_display(self, obj):
        """Muestra datos adicionales en formato JSON legible"""
        if obj.additional_data:
            formatted_json = json.dumps(obj.additional_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_json)
        return _('No additional data')
    additional_data_display.short_description = _('Additional Data')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('created_at', 'user', 'action')
        }),
        (_('Object Information'), {
            'fields': ('model_name', 'object_id', 'object_representation')
        }),
        (_('Changes'), {
            'fields': ('changes_display',),
            'classes': ('collapse',)
        }),
        (_('Request Information'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        (_('Additional Data'), {
            'fields': ('additional_data_display',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """Administración para configuraciones del sistema"""
    
    list_display = (
        'key', 'config_type', 'value_preview', 'is_sensitive', 
        'is_active', 'updated_at'
    )
    
    list_filter = (
        'config_type', 'is_sensitive', 'is_active', 'created_at', 'updated_at'
    )
    
    search_fields = ('key', 'description', 'value')
    
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    ordering = ['config_type', 'key']
    
    fieldsets = (
        (_('Configuration'), {
            'fields': ('key', 'config_type', 'value', 'description')
        }),
        (_('Security'), {
            'fields': ('is_sensitive', 'is_active')
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        """Muestra una vista previa del valor de configuración"""
        if obj.is_sensitive:
            return _('*** Hidden ***')
        
        value = obj.value
        if len(value) > 50:
            return f"{value[:50]}..."
        return value
    value_preview.short_description = _('Value Preview')
    
    def get_form(self, request, obj=None, **kwargs):
        """Personaliza el formulario para campos sensibles"""
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.is_sensitive:
            form.base_fields['value'].widget.attrs['type'] = 'password'
        return form
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo con información de auditoría"""
        if hasattr(obj, 'created_by') and not change:
            obj.created_by = request.user
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    """Administración para archivos subidos"""
    
    list_display = (
        'original_name', 'file_type', 'file_size_display', 
        'is_public', 'is_active', 'created_at', 'created_by'
    )
    
    list_filter = (
        'file_type', 'is_public', 'is_active', 'mime_type', 
        'created_at', 'created_by'
    )
    
    search_fields = (
        'original_name', 'description', 'mime_type'
    )
    
    readonly_fields = (
        'file_size', 'mime_type', 'checksum', 'created_at', 
        'updated_at', 'created_by', 'updated_by', 'file_preview'
    )
    
    date_hierarchy = 'created_at'
    
    ordering = ['-created_at']
    
    fieldsets = (
        (_('File Information'), {
            'fields': ('file', 'original_name', 'file_type', 'description')
        }),
        (_('File Details'), {
            'fields': ('file_size', 'mime_type', 'checksum', 'file_preview'),
            'classes': ('collapse',)
        }),
        (_('Access Control'), {
            'fields': ('is_public', 'is_active')
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Muestra el tamaño del archivo en formato legible"""
        return obj.file_size_human
    file_size_display.short_description = _('File Size')
    file_size_display.admin_order_field = 'file_size'
    
    def file_preview(self, obj):
        """Muestra una vista previa del archivo si es una imagen"""
        if obj.file and obj.mime_type and obj.mime_type.startswith('image/'):
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.file.url
            )
        elif obj.file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.file.url,
                _('Download file')
            )
        return _('No file')
    file_preview.short_description = _('File Preview')
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo con información de auditoría"""
        if hasattr(obj, 'created_by') and not change:
            obj.created_by = request.user
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        qs = super().get_queryset(request)
        if hasattr(self.model, 'created_by'):
            qs = qs.select_related('created_by', 'updated_by')
        return qs


# Personalización del sitio de administración
admin.site.site_header = _('VENDO SRI Administration')
admin.site.site_title = _('VENDO SRI Admin')
admin.site.index_title = _('Welcome to VENDO SRI Administration')