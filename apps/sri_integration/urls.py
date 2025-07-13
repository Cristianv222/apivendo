# -*- coding: utf-8 -*-
"""
URLs for sri_integration app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SRIConfigurationViewSet, ElectronicDocumentViewSet,
    DocumentItemViewSet, SRIResponseViewSet
)

app_name = 'sri_integration'

router = DefaultRouter()
router.register(r'configurations', SRIConfigurationViewSet)
router.register(r'documents', ElectronicDocumentViewSet)
router.register(r'items', DocumentItemViewSet)
router.register(r'responses', SRIResponseViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', include(router.urls)),
]