import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vendo_sri.settings")
django.setup()

# Leer archivo actual
with open("/app/apps/sri_integration/services/soap_client.py", "r") as f:
    content = f.read()

# Encontrar y reemplazar el método _send_with_requests
old_method_start = "    def _send_with_requests(self, document, signed_xml_content, service_type):"
new_method = """    def _send_with_requests(self, document, signed_xml_content, service_type):
        \"\"\"Enviar usando requests directamente - VERSIÓN CORREGIDA\"\"\"
        try:
            logger.info("Using corrected requests method for SRI communication")
            
            # SOAP envelope corregido basado en pruebas exitosas
            soap_body = f\'\'\'<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:rec="http://ec.gob.sri.ws.recepcion">
    <soap:Header/>
    <soap:Body>
        <rec:validarComprobante>
            <xml><![CDATA[{signed_xml_content}]]></xml>
        </rec:validarComprobante>
    </soap:Body>
</soap:Envelope>\'\'\'
            
            # Headers corregidos
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "",
                "User-Agent": "VENDO_SRI_Client/1.0"
            }
            
            # Enviar solicitud
            endpoint_url = self.SRI_URLS[self.environment]["reception_endpoint"]
            response = requests.post(
                endpoint_url,
                data=soap_body.encode("utf-8"),
                headers=headers,
                timeout=30
            )
            
            # Procesar respuesta
            if response.status_code == 200:
                response_text = response.text
                print("🔍 DEBUG - Respuesta SRI:", response_text[:500])
                
                if "RECIBIDA" in response_text:
                    self._log_sri_response(
                        document,
                        "RECEPTION",
                        "RECIBIDA",
                        "Document received by SRI (corrected requests)",
                        {"response": response_text, "method": "requests_corrected"}
                    )
                    document.status = "SENT"
                    document.save()
                    return True, "Document received by SRI (corrected method)"
                elif "Error 35" in response_text:
                    error_msg = "SRI Error 35: XML structure problem - this is a known issue with XML parsing"
                    self._log_sri_response(
                        document,
                        "RECEPTION",
                        "ERROR_35",
                        error_msg,
                        {"response": response_text, "method": "requests_corrected"}
                    )
                    document.status = "ERROR"
                    document.save()
                    return False, error_msg
                else:
                    # Buscar otros tipos de error
                    if "identificador" in response_text:
                        # Extraer mensaje de error específico
                        import re
                        error_match = re.search(r"<mensaje>(.*?)</mensaje>", response_text)
                        if error_match:
                            error_msg = f"SRI Error: {error_match.group(1)}"
                        else:
                            error_msg = "SRI returned unknown error format"
                    else:
                        error_msg = "Unknown SRI response format"
                    
                    self._log_sri_response(
                        document,
                        "RECEPTION",
                        "ERROR",
                        error_msg,
                        {"response": response_text, "method": "requests_corrected"}
                    )
                    document.status = "ERROR"
                    document.save()
                    return False, error_msg
            else:
                error_msg = f"HTTP Error: {response.status_code} - {response.text[:200]}"
                return False, error_msg
                
        except Exception as e:
            return False, f"Corrected requests method failed: {str(e)}\""""

# Encontrar inicio del método
start_index = content.find(old_method_start)
if start_index == -1:
    print("❌ No se encontró el método _send_with_requests")
    exit(1)

# Encontrar final del método (buscar el siguiente método)
temp_content = content[start_index:]
next_method_index = temp_content.find("    def _get_auth_with_zeep(self, document):")
if next_method_index == -1:
    print("❌ No se encontró el final del método")
    exit(1)

# Calcular índices absolutos
end_index = start_index + next_method_index

# Reemplazar método
new_content = content[:start_index] + new_method + "\n\n" + content[end_index:]

# Escribir archivo corregido
with open("/app/apps/sri_integration/services/soap_client.py", "w") as f:
    f.write(new_content)

print("✅ Método _send_with_requests actualizado con formato SOAP correcto")