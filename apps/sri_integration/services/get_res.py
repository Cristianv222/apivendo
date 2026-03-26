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

headers = {
    'Content-Type': 'application/xml',
    'User-Agent': 'SRI-Ecuador-Agent/2.0',
    'Accept': '*/*',
    'Host': 'cel.sri.gob.ec'
}

try:
    r = requests.post(
        'https://cel.sri.gob.ec/comprobanteselectronicos/ws/AutorizacionComprobantes', 
        data=soap.encode('utf-8'), 
        headers=headers,
        timeout=30,
        verify=True
    )
    with open('/app/sri_response.txt', 'w', encoding='utf-8') as f:
        f.write(r.text)
    print("SUCCESS: Result saved to /app/sri_response.txt")
except Exception as e:
    with open('/app/sri_response_error.txt', 'w', encoding='utf-8') as f:
        f.write(str(e))
    print(f"ERROR: {e}")
