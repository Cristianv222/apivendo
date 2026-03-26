import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')
django.setup()

from apps.companies.models import Company
from apps.sri_integration.models import SRIConfiguration
from apps.certificates.models import DigitalCertificate

print(f"{'Company (RUC)':<20} | {'Ambiente SRI':<15} | {'SRI Config Env':<15} | {'Cert Env':<15}")
print("-" * 75)

for company in Company.objects.all():
    sri_env = "N/A"
    if hasattr(company, 'sri_configuration'):
        sri_env = company.sri_configuration.environment
    
    cert_env = "N/A"
    if hasattr(company, 'digital_certificate'):
        cert_env = company.digital_certificate.environment
    
    # Mapping Company.ambiente_sri to readable text
    company_env = "Pruebas (1)" if company.ambiente_sri == '1' else "Producción (2)" if company.ambiente_sri == '2' else f"Unknown ({company.ambiente_sri})"
    
    print(f"{company.ruc:<20} | {company_env:<15} | {sri_env:<15} | {cert_env:<15}")
