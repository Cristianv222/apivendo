# -*- coding: utf-8 -*-
"""
Admin configuration for companies app
Panel de administración para empresas de VENDO_SRI
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Administración para empresas"""
    
    list_display = (
        'business_name', 'ruc', 'trade_name', 'email', 
        'phone', 'is_active', 'users_count', 'created_at'
    )
    
    list_filter = (
        'is_active', 'created_at', 'updated_at'
    )
    
    search_fields = (
        'ruc', 'business_name', 'trade_name', 'email'
    )
    
    readonly_fields = (
        'created_at', 'updated_at'
    )
    
    ordering = ['business_name']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('ruc', 'business_name', 'trade_name')
        }),
        (_('Contact Information'), {
            'fields': ('email', 'phone', 'address')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def users_count(self, obj):
        """Muestra el número de usuarios asociados"""
        count = obj.users.count()
        if count > 0:
            return format_html(
                '<a href="/admin/users/user/?company__id__exact={}">{} usuarios</a>',
                obj.id,
                count
            )
        return '0 usuarios'
    users_count.short_description = _('Users')
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo (sin campos de auditoría por ahora)"""
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimiza las consultas"""
        return super().get_queryset(request).prefetch_related('users')