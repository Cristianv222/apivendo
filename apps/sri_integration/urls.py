# -*- coding: utf-8 -*-
"""
PASO 2: REEMPLAZAR COMPLETAMENTE apps/sri_integration/urls.py
URLs for sri_integration app con descarga de documentos
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SRIConfigurationViewSet, ElectronicDocumentViewSet,
    DocumentItemViewSet, SRIResponseViewSet,
    # Nuevas vistas de descarga
    download_document_pdf, download_document_xml, 
    check_document_files, generate_missing_files
)

app_name = 'sri_integration'

router = DefaultRouter()
router.register(r'configurations', SRIConfigurationViewSet)
router.register(r'documents', ElectronicDocumentViewSet)
router.register(r'items', DocumentItemViewSet)
router.register(r'responses', SRIResponseViewSet)

urlpatterns = [
    # ==========================================
    # API ROUTER - FUNCIONALIDAD EXISTENTE
    # ==========================================
    path('api/', include(router.urls)),
    path('', include(router.urls)),
    
    # ==========================================
    # NUEVAS URLs PARA DESCARGA DE DOCUMENTOS
    # ==========================================
    
    # Descarga directa de archivos
    path('documents/<int:document_id>/download/pdf/', 
         download_document_pdf, 
         name='download_document_pdf'),
    
    path('documents/<int:document_id>/download/xml/', 
         download_document_xml, 
         name='download_document_xml'),
    
    # Verificación de archivos disponibles
    path('documents/<int:document_id>/files/check/', 
         check_document_files, 
         name='check_document_files'),
    
    # Generación de archivos faltantes
    path('documents/<int:document_id>/files/generate/', 
         generate_missing_files, 
         name='generate_missing_files'),
    
    # ==========================================
    # ALIASES PARA COMPATIBILIDAD CON EL TEMPLATE
    # ==========================================
    
    # Rutas alternativas que el template podría usar
    path('download/pdf/<int:document_id>/', 
         download_document_pdf, 
         name='download_pdf'),
    
    path('download/xml/<int:document_id>/', 
         download_document_xml, 
         name='download_xml'),
]