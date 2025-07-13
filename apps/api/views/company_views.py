# -*- coding: utf-8 -*-
"""
Views for companies API
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.companies.models import Company
from apps.api.serializers.company_serializers import CompanySerializer
from apps.api.permissions import IsCompanyOwnerOrAdmin

logger = logging.getLogger(__name__)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet para empresas
    """
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    search_fields = ['business_name', 'trade_name', 'ruc', 'email']
    ordering_fields = ['business_name', 'created_at']
    ordering = ['business_name']
    
    def get_queryset(self):
        """
        Filtra empresas según permisos del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return Company.objects.all()
        
        # Los usuarios solo ven empresas a las que están asociados
        return user.companies.all()
    
    @action(detail=True, methods=['get'])
    def sri_status(self, request, pk=None):
        """
        Obtiene el estado de la configuración SRI de la empresa
        """
        company = self.get_object()
        
        try:
            sri_config = company.sri_configuration
            
            # Verificar certificado digital
            certificate_status = {'exists': False, 'valid': False, 'expires_soon': False}
            try:
                cert = company.digital_certificate
                certificate_status['exists'] = True
                certificate_status['valid'] = not cert.is_expired
                certificate_status['expires_soon'] = cert.days_until_expiration <= 30
                certificate_status['days_until_expiration'] = cert.days_until_expiration
                certificate_status['subject_name'] = cert.subject_name
                certificate_status['valid_to'] = cert.valid_to
            except Exception:
                pass
            
            return Response({
                'company_id': company.id,
                'company_name': company.business_name,
                'sri_configuration': {
                    'exists': True,
                    'environment': sri_config.environment,
                    'establishment_code': sri_config.establishment_code,
                    'emission_point': sri_config.emission_point,
                    'email_enabled': sri_config.email_enabled,
                    'is_active': sri_config.is_active
                },
                'certificate': certificate_status,
                'ready_for_processing': (
                    sri_config.is_active and 
                    certificate_status['exists'] and 
                    certificate_status['valid']
                )
            })
            
        except Exception:
            return Response({
                'company_id': company.id,
                'company_name': company.business_name,
                'sri_configuration': {'exists': False},
                'certificate': {'exists': False, 'valid': False},
                'ready_for_processing': False
            })
    
    @action(detail=True, methods=['get'])
    def documents_summary(self, request, pk=None):
        """
        Resumen de documentos de la empresa
        """
        company = self.get_object()
        
        try:
            from apps.sri_integration.models import ElectronicDocument
            from django.db.models import Count, Sum, Q
            from datetime import datetime, timedelta
            
            documents = company.electronic_documents.all()
            
            # Estadísticas generales
            total_documents = documents.count()
            total_amount = documents.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            
            # Por estado
            status_summary = documents.values('status').annotate(
                count=Count('id')
            ).order_by('status')
            
            # Por tipo
            type_summary = documents.values('document_type').annotate(
                count=Count('id')
            ).order_by('document_type')
            
            # Últimos 30 días
            last_30_days = datetime.now().date() - timedelta(days=30)
            recent_documents = documents.filter(
                issue_date__gte=last_30_days
            ).count()
            
            # Documentos pendientes
            pending_documents = documents.filter(
                status__in=['DRAFT', 'GENERATED', 'SIGNED', 'SENT']
            ).count()
            
            return Response({
                'company_id': company.id,
                'company_name': company.business_name,
                'summary': {
                    'total_documents': total_documents,
                    'total_amount': total_amount,
                    'recent_documents': recent_documents,
                    'pending_documents': pending_documents
                },
                'status_breakdown': status_summary,
                'type_breakdown': type_summary
            })
            
        except Exception as e:
            logger.error(f"Error getting documents summary for company {pk}: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def my_companies(self, request):
        """
        Empresas del usuario autenticado
        """
        user = request.user
        companies = user.companies.filter(is_active=True)
        
        serializer = self.get_serializer(companies, many=True)
        return Response(serializer.data)