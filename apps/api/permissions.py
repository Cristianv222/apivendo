# -*- coding: utf-8 -*-
"""
Custom permissions for API
"""

from rest_framework import permissions


class IsCompanyOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso que permite acceso solo a propietarios de empresa o administradores
    """
    
    def has_permission(self, request, view):
        """
        Verifica permisos a nivel de vista
        """
        # Los usuarios deben estar autenticados
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Los superusuarios tienen acceso total
        if request.user.is_superuser:
            return True
        
        # Los usuarios regulares deben tener al menos una empresa
        return request.user.companies.filter(is_active=True).exists()
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto
        """
        # Los superusuarios tienen acceso total
        if request.user.is_superuser:
            return True
        
        # Determinar la empresa relacionada con el objeto
        company = self._get_related_company(obj)
        
        if not company:
            return False
        
        # Verificar si el usuario tiene acceso a la empresa
        return company in request.user.companies.filter(is_active=True)
    
    def _get_related_company(self, obj):
        """
        Obtiene la empresa relacionada con el objeto
        """
        # Si el objeto tiene directamente una empresa
        if hasattr(obj, 'company'):
            return obj.company
        
        # Si el objeto es una empresa
        if hasattr(obj, 'ruc'):  # Asumiendo que es Company
            return obj
        
        # Si el objeto tiene un documento relacionado
        if hasattr(obj, 'document') and hasattr(obj.document, 'company'):
            return obj.document.company
        
        # Si el objeto tiene un certificado relacionado
        if hasattr(obj, 'certificate') and hasattr(obj.certificate, 'company'):
            return obj.certificate.company
        
        return None


class IsAdminUser(permissions.BasePermission):
    """
    Permiso solo para administradores
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite edición solo al propietario, lectura para otros
    """
    
    def has_object_permission(self, request, view, obj):
        # Permisos de lectura para cualquier request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Permisos de escritura solo para el propietario
        return obj.created_by == request.user


class IsCompanyMember(permissions.BasePermission):
    """
    Permiso para miembros de la empresa
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Obtener company_id de los parámetros
        company_id = request.data.get('company') or request.query_params.get('company')
        
        if not company_id:
            return True  # Será validado a nivel de objeto
        
        try:
            from apps.companies.models import Company
            company = Company.objects.get(id=company_id, is_active=True)
            return company in request.user.companies.all()
        except Company.DoesNotExist:
            return False