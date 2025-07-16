import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendo_sri.settings")
django.setup()

print("=== APLICANDO FIX PARA NOTAS DE CREDITO ===")

# Leer archivo de views
with open("/app/apps/sri_integration/views.py", "r") as f:
    content = f.read()

# Encontrar el método sign_document
sign_method_start = content.find("def sign_document(self, request, pk=None):")
if sign_method_start == -1:
    print("❌ Método sign_document no encontrado")
    exit(1)

print("✅ Método sign_document encontrado")

# Buscar el final del método (siguiente método o final de clase)
temp_content = content[sign_method_start:]
next_method_pos = temp_content.find("\n    def ")
if next_method_pos == -1:
    # Buscar final de clase
    class_end = temp_content.find("\n\nclass ")
    if class_end == -1:
        method_end = len(content)
    else:
        method_end = sign_method_start + class_end
else:
    method_end = sign_method_start + next_method_pos

print(f"📍 Método encontrado en posición {sign_method_start} a {method_end}")

# Nuevo método corregido
fixed_method = '''    def sign_document(self, request, pk=None):
        """Firmar documento electrónico - VERSIÓN CORREGIDA"""
        try:
            from apps.sri_integration.models import CreditNote
            import os
            
            # Determinar si es ElectronicDocument o CreditNote
            document = None
            is_credit_note = False
            
            try:
                # Primero intentar como ElectronicDocument
                document = self.get_object()
                is_credit_note = False
                print(f"📄 Procesando ElectronicDocument ID {pk}")
            except:
                # Si falla, intentar como CreditNote
                try:
                    document = CreditNote.objects.get(id=pk)
                    is_credit_note = True
                    print(f"💳 Procesando CreditNote ID {pk}")
                except CreditNote.DoesNotExist:
                    return Response(
                        {"error": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Validar contraseña
            password = request.data.get('password')
            if not password:
                return Response(
                    {"error": "PASSWORD_REQUIRED", "message": "Certificate password is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar que el XML existe
            from apps.sri_integration.services.xml_generator import XMLGenerator
            generator = XMLGenerator(document)
            
            if is_credit_note:
                xml_path = generator.get_credit_note_xml_path()
            else:
                xml_path = generator.get_xml_path()
                
            if not os.path.exists(xml_path):
                return Response(
                    {"error": "XML_NOT_FOUND", "message": "XML file must be generated first before signing"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Firmar documento
            from apps.sri_integration.services.digital_signature import DigitalSignatureService
            signature_service = DigitalSignatureService(document.company)
            
            signed_result = signature_service.sign_xml_file(xml_path, password)
            
            if signed_result['success']:
                # ✅ FIX PRINCIPAL: Actualizar estado en el modelo correcto
                document.status = 'SIGNED'
                document.save()
                
                print(f"✅ Estado actualizado a SIGNED para {'CreditNote' if is_credit_note else 'ElectronicDocument'} ID {pk}")
                
                return Response({
                    "message": "Document signed successfully",
                    "data": {
                        "document_number": document.document_number,
                        "certificate_serial": signed_result.get('certificate_serial', 'N/A'),
                        "certificate_subject": signed_result.get('certificate_subject', 'N/A'),
                        "signature_algorithm": signed_result.get('signature_algorithm', 'XAdES-BES'),
                        "status": document.status
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "SIGNING_FAILED", "message": signed_result.get('error', 'Unknown signing error')},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            import traceback
            print(f"❌ Error en sign_document: {str(e)}")
            traceback.print_exc()
            return Response(
                {"error": "SIGNING_ERROR", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
'''

# Reemplazar método
new_content = content[:sign_method_start] + fixed_method + content[method_end:]

# Crear backup
with open("/app/apps/sri_integration/views.py.backup", "w") as f:
    f.write(content)

# Escribir archivo corregido
with open("/app/apps/sri_integration/views.py", "w") as f:
    f.write(new_content)

print("✅ Fix aplicado exitosamente")
print("🔧 Backup creado en views.py.backup")
print("📝 Método sign_document ahora maneja CreditNote correctamente")