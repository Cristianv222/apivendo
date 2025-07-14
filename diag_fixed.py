import os
import django

# Configurar Django PRIMERO
os.environ.setdefault(DJANGO_SETTINGS_MODULE, vendo_sri.settings)
django.setup()

# AHORA importar los modelos
from sri_integration.models import CreditNote, DebitNote, Retention, PurchaseSettlement

print(
