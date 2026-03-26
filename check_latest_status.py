import os
import sys
from unittest.mock import MagicMock

# Mocks
sys.modules['decouple'] = MagicMock()
sys.modules['decouple'].config = MagicMock(side_effect=lambda x, default='', cast=lambda y: y: os.environ.get(x, default if not callable(cast) else cast(os.environ.get(x, default))))
sys.modules['celery'] = MagicMock()
sys.modules['django_celery_beat'] = MagicMock()
sys.modules['apps.notifications.tasks'] = MagicMock()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendo_sri.settings')

import django
django.setup()

from apps.sri_integration.models import ElectronicDocument

print(f"{'ID':<5} | {'Status':<15} | {'Auth Code':<50}")
print("-" * 75)

for doc in ElectronicDocument.objects.all().order_by('-created_at')[:5]:
    status = doc.status
    auth = doc.sri_authorization_code or "NONE"
    
    print(f"{doc.id:<5} | {status:<15} | {auth}")
