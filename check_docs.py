import os
import sys
from unittest.mock import MagicMock

# Mocks
sys.modules['decouple'] = MagicMock()
sys.modules['decouple'].config = MagicMock(side_effect=lambda x, default='', cast=lambda y: y: os.environ.get(x, default if not callable(cast) else cast(os.environ.get(x, default))))
sys.modules['celery'] = MagicMock()
sys.modules['django_celery_beat'] = MagicMock()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')

# Trick decouple to use os.environ
import django
django.setup()

from apps.sri_integration.models import ElectronicDocument

print(f"{'ID':<5} | {'Doc Number':<20} | {'Status':<15} | {'Access Key Flag':<15}")
print("-" * 65)

for doc in ElectronicDocument.objects.all().order_by('-created_at')[:10]:
    # Environment flag is the 24th digit (index 23)
    env_flag = doc.access_key[23] if doc.access_key and len(doc.access_key) >= 24 else "N/A"
    env_name = "TEST (1)" if env_flag == '1' else "PROD (2)" if env_flag == '2' else f"Unknown ({env_flag})"
    
    print(f"{doc.id:<5} | {doc.document_number:<20} | {doc.status:<15} | {env_name}")
