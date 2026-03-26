import requests
import xml.etree.ElementTree as ET

CLAVE = "2503202601049153465100120010010000000124121123517"

soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
   <soapenv:Header/>
   <soapenv:Body>
      <ec:autorizacionComprobante>
         <claveAcceso>{CLAVE}</claveAcceso>
      </ec:autorizacionComprobante>
   </soapenv:Body>
</soapenv:Envelope>"""

print(f"--- CONSULTANDO CLAVE: {CLAVE} ---")

headers = {
    'Content-Type': 'application/xml',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

try:
    r = requests.post(
        'https://cel.sri.gob.ec/comprobanteselectronicos/ws/AutorizacionComprobantes', 
        data=soap.encode('utf-8'), 
        headers=headers,
        timeout=30
    )
    print(f"HTTP Status: {r.status_code}")
    print("\n--- RESPUESTA COMPLETA ---")
    print(r.text)
except Exception as e:
    print(f"Error: {e}")
