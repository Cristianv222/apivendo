import os
import sys
from unittest.mock import MagicMock

# Create a mock for django_celery_beat if it's missing or causes issues
sys.modules['celery'] = MagicMock()
sys.modules['django_celery_beat'] = MagicMock()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')

import django
django.setup()

from apps.companies.models import Company
from apps.sri_integration.models import SRIConfiguration
from apps.certificates.models import DigitalCertificate

print("Sincronizando estados SRI para todas las empresas...")

for company in Company.objects.all():
    # El modelo authoritative en este sistema parece ser SRIConfiguration 
    # o DigitalCertificate (donde se cambia el ambiente en admin)
    
    # Vamos a usar DigitalCertificate como fuente de verdad si existe, 
    # si no SRIConfiguration, si no Company.
    
    env = 'TEST'
    if hasattr(company, 'digital_certificate'):
        env = company.digital_certificate.environment
    elif hasattr(company, 'sri_configuration'):
        env = company.sri_configuration.environment
    else:
        env = 'TEST' if company.ambiente_sri == '1' else 'PRODUCTION'
    
    print(f"Empresa {company.ruc}: Sincronizando a {env}")
    
    # Forzar sync guardando (esto disparará mis nuevos save() con sync)
    # Pero para estar seguros y evitar efectos secundarios, lo hacemos manual con update
    
    Company.objects.filter(pk=company.pk).update(ambiente_sri='1' if env == 'TEST' else '2')
    SRIConfiguration.objects.filter(company=company).update(environment=env)
    DigitalCertificate.objects.filter(company=company).update(environment=env)

print("Sincronización completada.")
