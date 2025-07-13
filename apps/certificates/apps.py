# -*- coding: utf-8 -*-
"""
Configuración de la aplicación de certificados digitales
"""

from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    """
    Configuración de la app de certificados digitales
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.certificates'
    verbose_name = 'Certificados Digitales'
    verbose_name_plural = 'Certificados Digitales'
    
    def ready(self):
        """
        Código que se ejecuta cuando la app está lista
        """
        # Aquí puedes importar signals si los necesitas
        # import apps.certificates.signals
        pass