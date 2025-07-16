import os

# Crear script de reemplazo
script = '''
import re

# Leer archivo actual
with open('/app/apps/sri_integration/views.py', 'r') as f:
    content = f.read()

# Método de reemplazo simple
new_method = \"\"\"    @action(detail=True, methods=[\"post\"])
    def sign_document(self, request, pk=None):
        from rest_framework.response import Response
        from apps.sri_integration.models import CreditNote
        from django.db import transaction
        from django.utils import timezone
        
        print(f\"OBVIOUS METHOD EXECUTING FOR {pk}\")
        
        try:
            document = CreditNote.objects.get(id=pk)
            print(f\"OBVIOUS: Status {document.status}\")
            
            with transaction.atomic():
                CreditNote.objects.filter(id=document.id).update(
                    status=\"OBVIOUS_SIGNED\",
                    updated_at=timezone.now()
                )
            
            final_check = CreditNote.objects.get(id=document.id)
            print(f\"OBVIOUS: Final {final_check.status}\")
            
            return Response({
                \"success\": True,
                \"message\": \"OBVIOUS METHOD WORKED\",
                \"data\": {
                    \"OBVIOUS_FLAG\": \"FILE_IS_ACTIVE\",
                    \"status\": final_check.status,
                    \"verification\": {
                        \"obvious_test\": True
                    }
                }
            })
            
        except Exception as e:
            print(f\"OBVIOUS ERROR: {e}\")
            return Response({\"error\": str(e)}, status=500)\"\"\"

# Buscar el método actual y reemplazarlo
lines = content.split('\n')
new_lines = []
in_sign_document = False
indent_level = 0

for line in lines:
    if \"def sign_document(self, request, pk=None):\" in line:
        in_sign_document = True
        indent_level = len(line) - len(line.lstrip())
        new_lines.extend(new_method.split('\n'))
        continue
    elif in_sign_document:
        current_indent = len(line) - len(line.lstrip()) if line.strip() else float('inf')
        if line.strip() and current_indent <= indent_level and (\"def \" in line or \"@action\" in line):
            in_sign_document = False
            new_lines.append(line)
        continue
    else:
        new_lines.append(line)

# Escribir archivo modificado
with open('/app/apps/sri_integration/views.py', 'w') as f:
    f.write('\n'.join(new_lines))

print(\"File modified with obvious method\")
'''

# Escribir script
with open('/app/replace_method.py', 'w') as f:
    f.write(script)

print('Script creado')