# -*- coding: utf-8 -*-
"""
Views for digital certificates API
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from apps.certificates.models import DigitalCertificate, CertificateUsageLog
from apps.sri_integration.services.certificate_manager import CertificateManager
from apps.api.serializers.certificate_serializers import (
    DigitalCertificateSerializer,
    CertificateUploadSerializer,
    CertificateUsageLogSerializer
)
from apps.api.permissions import IsCompanyOwnerOrAdmin

logger = logging.getLogger(__name__)


class DigitalCertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para certificados digitales
    """
    serializer_class = DigitalCertificateSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'environment']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra certificados por empresa del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return DigitalCertificate.objects.all()
        
        companies = user.companies.filter(is_active=True)
        return DigitalCertificate.objects.filter(company__in=companies)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Sube un nuevo certificado P12
        """
        serializer = CertificateUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Obtener empresa del usuario
            company_id = request.data.get('company')
            if not company_id:
                return Response({
                    'error': 'Company ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from apps.companies.models import Company
            try:
                company = Company.objects.get(id=company_id)
                
                # Verificar permisos
                if not request.user.is_superuser and company not in request.user.companies.all():
                    return Response({
                        'error': 'Permission denied'
                    }, status=status.HTTP_403_FORBIDDEN)
                    
            except Company.DoesNotExist:
                return Response({
                    'error': 'Company not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verificar si ya existe un certificado activo
            existing_cert = DigitalCertificate.objects.filter(
                company=company,
                status='ACTIVE'
            ).first()
            
            if existing_cert:
                # Desactivar certificado anterior
                existing_cert.status = 'INACTIVE'
                existing_cert.save()
            
            # Crear gestor de certificados
            cert_manager = CertificateManager(company)
            
            # Crear registro de certificado
            certificate = cert_manager.create_certificate_record(
                serializer.validated_data['certificate_file'],
                serializer.validated_data['password'],
                serializer.validated_data['environment']
            )
            
            # Serializar respuesta
            response_serializer = DigitalCertificateSerializer(certificate)
            
            return Response({
                'success': True,
                'message': 'Certificate uploaded successfully',
                'certificate': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error uploading certificate: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """
        Valida un certificado con su contraseña
        """
        certificate = self.get_object()
        
        password = request.data.get('password')
        if not password:
            return Response({
                'error': 'Password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Cargar certificado
            cert_manager = CertificateManager(certificate.company)
            cert_manager.load_certificate(password)
            
            # Validar
            valid, message = cert_manager.validate_certificate()
            
            return Response({
                'valid': valid,
                'message': message,
                'certificate_info': {
                    'subject_name': certificate.subject_name,
                    'issuer_name': certificate.issuer_name,
                    'valid_from': certificate.valid_from,
                    'valid_to': certificate.valid_to,
                    'is_expired': certificate.is_expired,
                    'days_until_expiration': certificate.days_until_expiration
                }
            })
            
        except Exception as e:
            logger.error(f"Error validating certificate {pk}: {str(e)}")
            return Response({
                'valid': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activa un certificado (desactiva otros de la misma empresa)
        """
        certificate = self.get_object()
        
        try:
            # Desactivar otros certificados de la empresa
            DigitalCertificate.objects.filter(
                company=certificate.company,
                status='ACTIVE'
            ).exclude(id=certificate.id).update(status='INACTIVE')
            
            # Activar este certificado
            certificate.status = 'ACTIVE'
            certificate.save()
            
            return Response({
                'success': True,
                'message': 'Certificate activated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error activating certificate {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Desactiva un certificado
        """
        certificate = self.get_object()
        
        try:
            certificate.status = 'INACTIVE'
            certificate.save()
            
            return Response({
                'success': True,
                'message': 'Certificate deactivated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deactivating certificate {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def usage_logs(self, request, pk=None):
        """
        Obtiene logs de uso del certificado
        """
        certificate = self.get_object()
        
        logs = CertificateUsageLog.objects.filter(
            certificate=certificate
        ).order_by('-created_at')
        
        # Paginación
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = CertificateUsageLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CertificateUsageLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Certificados que expiran pronto (próximos 30 días)
        """
        from datetime import datetime, timedelta
        
        expiration_date = datetime.now().date() + timedelta(days=30)
        
        expiring_certificates = self.get_queryset().filter(
            valid_to__date__lte=expiration_date,
            status='ACTIVE'
        )
        
        serializer = self.get_serializer(expiring_certificates, many=True)
        return Response({
            'count': expiring_certificates.count(),
            'certificates': serializer.data
        })


class CertificateUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de uso de certificados (solo lectura)
    """
    serializer_class = CertificateUsageLogSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation', 'document_type', 'success']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra logs por empresa del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return CertificateUsageLog.objects.all()
        
        companies = user.companies.filter(is_active=True)
        return CertificateUsageLog.objects.filter(
            certificate__company__in=companies
        )