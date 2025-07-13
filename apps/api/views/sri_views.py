# -*- coding: utf-8 -*-
"""
Views for SRI integration API
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from apps.sri_integration.models import ElectronicDocument, SRIConfiguration, SRIResponse
from apps.sri_integration.services.document_processor import DocumentProcessor
from apps.api.serializers.sri_serializers import (
    ElectronicDocumentSerializer,
    ElectronicDocumentCreateSerializer,
    SRIConfigurationSerializer,
    SRIResponseSerializer,
    DocumentProcessRequestSerializer,
    DocumentStatusSerializer
)
from apps.api.permissions import IsCompanyOwnerOrAdmin

logger = logging.getLogger(__name__)


class ElectronicDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para documentos electrónicos
    """
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'document_type',
        'status',
        'issue_date',
        'customer_identification_type'
    ]
    search_fields = [
        'document_number',
        'customer_name',
        'customer_identification',
        'access_key'
    ]
    ordering_fields = [
        'created_at',
        'issue_date',
        'document_number',
        'total_amount'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra documentos por empresa del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return ElectronicDocument.objects.all()
        
        # Filtrar por empresas a las que tiene acceso el usuario
        companies = user.companies.filter(is_active=True)
        return ElectronicDocument.objects.filter(company__in=companies)
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción
        """
        if self.action == 'create':
            return ElectronicDocumentCreateSerializer
        return ElectronicDocumentSerializer
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Procesa un documento (genera XML, firma, envía al SRI)
        """
        document = self.get_object()
        
        # Validar estado
        if document.status not in ['DRAFT', 'GENERATED', 'ERROR']:
            return Response(
                {'error': 'Document cannot be processed in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar datos de entrada
        serializer = DocumentProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Procesar documento
            processor = DocumentProcessor(document.company)
            success, message = processor.process_document(
                document,
                serializer.validated_data['certificate_password'],
                serializer.validated_data.get('send_email', True)
            )
            
            if success:
                # Recargar documento con cambios
                document.refresh_from_db()
                response_serializer = ElectronicDocumentSerializer(
                    document, 
                    context={'request': request}
                )
                
                return Response({
                    'success': True,
                    'message': message,
                    'document': response_serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error processing document {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """
        Reprocesa un documento que falló
        """
        document = self.get_object()
        
        serializer = DocumentProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            processor = DocumentProcessor(document.company)
            success, message = processor.reprocess_document(
                document,
                serializer.validated_data['certificate_password']
            )
            
            if success:
                document.refresh_from_db()
                response_serializer = ElectronicDocumentSerializer(
                    document,
                    context={'request': request}
                )
                
                return Response({
                    'success': True,
                    'message': message,
                    'document': response_serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error reprocessing document {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Obtiene estado detallado de un documento
        """
        document = self.get_object()
        
        try:
            processor = DocumentProcessor(document.company)
            status_info = processor.get_document_status(document)
            
            serializer = DocumentStatusSerializer(status_info)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting document status {pk}: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """
        Reenvía el documento por email
        """
        document = self.get_object()
        
        if not document.customer_email:
            return Response({
                'success': False,
                'message': 'Customer email not provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.sri_integration.services.email_service import EmailService
            
            email_service = EmailService(document.company)
            success, message = email_service.send_document_email(document)
            
            if success:
                document.email_sent = True
                document.save()
            
            return Response({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"Error sending email for document {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Dashboard con estadísticas de documentos
        """
        try:
            queryset = self.get_queryset()
            
            # Estadísticas por estado
            status_stats = {}
            for choice in ElectronicDocument.STATUS_CHOICES:
                status_key = choice[0]
                count = queryset.filter(status=status_key).count()
                status_stats[status_key] = {
                    'count': count,
                    'label': choice[1]
                }
            
            # Estadísticas por tipo
            type_stats = {}
            for choice in ElectronicDocument.DOCUMENT_TYPES:
                type_key = choice[0]
                count = queryset.filter(document_type=type_key).count()
                type_stats[type_key] = {
                    'count': count,
                    'label': choice[1]
                }
            
            # Documentos recientes
            recent_documents = queryset.order_by('-created_at')[:10]
            recent_serializer = ElectronicDocumentSerializer(
                recent_documents,
                many=True,
                context={'request': request}
            )
            
            return Response({
                'status_stats': status_stats,
                'type_stats': type_stats,
                'recent_documents': recent_serializer.data,
                'total_documents': queryset.count()
            })
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SRIConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuración SRI
    """
    serializer_class = SRIConfigurationSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filtra configuraciones por empresa del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return SRIConfiguration.objects.all()
        
        companies = user.companies.filter(is_active=True)
        return SRIConfiguration.objects.filter(company__in=companies)
    
    @action(detail=True, methods=['post'])
    def reset_sequences(self, request, pk=None):
        """
        Reinicia secuenciales de documentos
        """
        config = self.get_object()
        
        # Validar permiso de administrador
        if not request.user.is_superuser:
            return Response({
                'error': 'Only administrators can reset sequences'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            config.invoice_sequence = 1
            config.credit_note_sequence = 1
            config.debit_note_sequence = 1
            config.retention_sequence = 1
            config.remission_guide_sequence = 1
            config.save()
            
            return Response({
                'success': True,
                'message': 'Sequences reset successfully'
            })
            
        except Exception as e:
            logger.error(f"Error resetting sequences: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para respuestas del SRI (solo lectura)
    """
    serializer_class = SRIResponseSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation_type', 'response_code']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtra respuestas por empresa del usuario
        """
        user = self.request.user
        
        if user.is_superuser:
            return SRIResponse.objects.all()
        
        companies = user.companies.filter(is_active=True)
        return SRIResponse.objects.filter(document__company__in=companies)