#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación manual para comprobar si un documento existe en el SRI (Windows compatible)
Uso: python verify_sri_document.py <clave_de_acceso>
"""

import requests
import xml.etree.ElementTree as ET
import sys
import json
import os
from datetime import datetime

def verify_document_in_sri(access_key, environment='TEST'):
    """Verifica manualmente si un documento existe en el SRI"""
    
    print(f"🔍 Verificando documento: {access_key}")
    print(f"🌍 Ambiente: {environment}")
    print(f"🕐 Hora: {datetime.now()}")
    print("-" * 50)
    
    sri_urls = {
        'TEST': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline',
        'PRODUCTION': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
    }
    
    soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <autorizacionComprobante xmlns="http://ec.gob.sri.ws.autorizacion">
            <claveAccesoComprobante xmlns="">{access_key}</claveAccesoComprobante>
        </autorizacionComprobante>
    </soap:Body>
</soap:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '',
        'User-Agent': 'Manual-SRI-Verification/1.0'
    }
    
    try:
        print("📤 Enviando consulta al SRI...")
        print(f"📡 URL: {sri_urls[environment]}")
        
        response = requests.post(
            sri_urls[environment],
            data=soap_envelope.encode('utf-8'),
            headers=headers,
            timeout=30,
            verify=True
        )
        
        print(f"📨 Status Code: {response.status_code}")
        print(f"📏 Response Size: {len(response.text)} characters")
        
        # Guardar respuesta completa para análisis (Windows compatible)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.getcwd()
        response_file = os.path.join(current_dir, f"sri_response_{access_key[:10]}_{timestamp}.xml")
        
        try:
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"💾 Respuesta guardada en: {response_file}")
        except Exception as e:
            print(f"⚠️ No se pudo guardar respuesta: {e}")
        
        # Analizar respuesta
        analysis_result = analyze_sri_response(response, access_key)
        
        return analysis_result
        
    except requests.exceptions.Timeout:
        print("⏰ Timeout - El SRI no responde en 30 segundos")
        return {'status': 'timeout', 'exists': False, 'access_key': access_key}
    except requests.exceptions.ConnectionError:
        print("🌐 Error de conexión al SRI")
        return {'status': 'connection_error', 'exists': False, 'access_key': access_key}
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return {'status': 'error', 'exists': False, 'error': str(e), 'access_key': access_key}

def analyze_sri_response(response, access_key):
    """Analiza la respuesta del SRI en detalle"""
    
    result = {
        'access_key': access_key,
        'http_status': response.status_code,
        'exists': False,
        'authorized': False,
        'authorization_number': None,
        'authorization_date': None,
        'status': 'unknown',
        'messages': [],
        'response_size': len(response.text)
    }
    
    if response.status_code == 200:
        print("✅ Respuesta HTTP 200 - Analizando contenido XML...")
        
        try:
            # Buscar palabras clave en el texto
            response_text = response.text.upper()
            
            # Mostrar los primeros caracteres para debug
            print("🔍 Primeros 500 caracteres de la respuesta:")
            print(response.text[:500])
            print("..." if len(response.text) > 500 else "")
            print()
            
            if 'AUTORIZADO' in response_text:
                print("🎉 ENCONTRADO: Estado AUTORIZADO")
                result['exists'] = True
                result['authorized'] = True
                result['status'] = 'authorized'
                
                # Intentar parsear XML para extraer detalles
                try:
                    root = ET.fromstring(response.text)
                    
                    # Buscar número de autorización
                    for elem in root.iter():
                        if 'numeroAutorizacion' in elem.tag:
                            result['authorization_number'] = elem.text
                            print(f"📋 Número de autorización: {elem.text}")
                        
                        if 'fechaAutorizacion' in elem.tag:
                            result['authorization_date'] = elem.text
                            print(f"📅 Fecha de autorización: {elem.text}")
                        
                        if 'mensaje' in elem.tag.lower() and elem.text:
                            result['messages'].append(elem.text)
                            print(f"💬 Mensaje: {elem.text}")
                
                except ET.ParseError as e:
                    print(f"⚠️ Error parseando XML: {e}")
                
            elif 'NO AUTORIZADO' in response_text:
                print("❌ ENCONTRADO: Estado NO AUTORIZADO")
                result['exists'] = True
                result['authorized'] = False
                result['status'] = 'not_authorized'
                
            elif any(phrase in response_text for phrase in [
                'NO EXISTE', 'NO SE ENCONTRÓ', 'NO ENCONTRADO', 'NOT FOUND'
            ]):
                print("❌ DOCUMENTO NO ENCONTRADO EN EL SRI")
                result['exists'] = False
                result['status'] = 'not_found'
                
            elif 'DEVUELTA' in response_text:
                print("🔙 DOCUMENTO DEVUELTO (rechazado)")
                result['exists'] = True
                result['authorized'] = False
                result['status'] = 'returned'
                
            elif 'SOAP' in response_text and 'FAULT' in response_text:
                print("⚠️ SOAP Fault detectado")
                result['status'] = 'soap_fault'
                
                # Extraer mensaje de error
                try:
                    root = ET.fromstring(response.text)
                    for elem in root.iter():
                        if 'faultstring' in elem.tag:
                            result['messages'].append(elem.text)
                            print(f"❌ Error SOAP: {elem.text}")
                except:
                    pass
                    
            else:
                print("⚠️ Respuesta ambigua del SRI - analizando XML...")
                result['status'] = 'ambiguous'
                
                # Intentar parsear para buscar más información
                try:
                    root = ET.fromstring(response.text)
                    print("📄 Elementos XML encontrados:")
                    for i, elem in enumerate(root.iter()):
                        if i < 10:  # Mostrar solo los primeros 10 elementos
                            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                            print(f"   • {tag_name}: {elem.text[:50] if elem.text else '(vacío)'}")
                    
                    if i >= 10:
                        print(f"   ... y {i-9} elementos más")
                        
                except ET.ParseError:
                    print("❌ No se pudo parsear como XML válido")
                
        except Exception as e:
            print(f"❌ Error analizando respuesta: {e}")
            result['status'] = 'analysis_error'
            
    elif response.status_code == 500:
        print("❌ Error del servidor SRI (HTTP 500)")
        result['status'] = 'server_error'
        
        # Analizar si el 500 contiene información útil
        if 'AUTORIZADO' in response.text:
            print("🔍 Detectado contenido de autorización en error 500")
            result['exists'] = True
            
    else:
        print(f"❌ Error HTTP {response.status_code}")
        result['status'] = f'http_error_{response.status_code}'
    
    return result

def print_summary(result):
    """Imprime un resumen final del resultado"""
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 50)
    
    print(f"🔑 Clave de acceso: {result.get('access_key', 'N/A')}")
    print(f"🌐 Estado HTTP: {result.get('http_status', 'N/A')}")
    print(f"📍 Estado: {result.get('status', 'unknown')}")
    print(f"📏 Tamaño respuesta: {result.get('response_size', 0)} caracteres")
    
    if result.get('exists'):
        print("✅ CONCLUSIÓN: El documento SÍ existe en el SRI")
        
        if result.get('authorized'):
            print("🎉 ESTADO: AUTORIZADO")
            if result.get('authorization_number'):
                print(f"📋 Número: {result['authorization_number']}")
            if result.get('authorization_date'):
                print(f"📅 Fecha: {result['authorization_date']}")
        else:
            print("❌ ESTADO: NO AUTORIZADO o DEVUELTO")
            
    elif result.get('status') == 'not_found':
        print("❌ CONCLUSIÓN: El documento NO existe en el SRI")
    elif result.get('status') == 'ambiguous':
        print("❓ CONCLUSIÓN: Estado ambiguo - requiere análisis manual")
    else:
        print("❓ CONCLUSIÓN: No se pudo determinar el estado")
    
    if result.get('messages'):
        print("\n💬 MENSAJES:")
        for msg in result['messages']:
            print(f"   • {msg}")
    
    print("\n🔍 INTERPRETACIÓN:")
    status = result.get('status', 'unknown')
    
    if status == 'authorized':
        print("   ✅ El documento fue enviado y autorizado correctamente")
    elif status == 'not_authorized':
        print("   ⚠️ El documento fue enviado pero NO autorizado")
    elif status == 'not_found':
        print("   ❌ El documento NUNCA fue enviado al SRI")
    elif status == 'returned':
        print("   🔙 El documento fue rechazado por errores")
    elif status == 'ambiguous':
        print("   ❓ Respuesta del SRI ambigua - revisar XML manualmente")
    elif status == 'soap_fault':
        print("   ⚠️ Error en la comunicación SOAP con el SRI")
    else:
        print("   ❓ Estado incierto - revisar respuesta manualmente")

def main():
    if len(sys.argv) != 2:
        print("Uso: python verify_sri_document.py <clave_de_acceso>")
        print("Ejemplo: python verify_sri_document.py 1234567890123456789012345678901234567890123456789")
        sys.exit(1)
    
    access_key = sys.argv[1]
    
    # Validaciones básicas
    if not access_key.isdigit():
        print("❌ La clave de acceso debe contener solo dígitos")
        sys.exit(1)
        
    if len(access_key) != 49:
        print(f"❌ La clave de acceso debe tener 49 dígitos (actual: {len(access_key)})")
        sys.exit(1)
    
    # Verificar documento
    result = verify_document_in_sri(access_key)
    
    # Mostrar resumen
    if isinstance(result, dict):
        print_summary(result)
        
        # Guardar resultado en JSON (Windows compatible)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.getcwd()
        result_file = os.path.join(current_dir, f"verification_result_{access_key[:10]}_{timestamp}.json")
        
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                # Remover raw_response para que el JSON sea más limpio
                clean_result = {k: v for k, v in result.items() if k not in ['raw_response']}
                json.dump(clean_result, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Resultado guardado en: {result_file}")
        except Exception as e:
            print(f"⚠️ No se pudo guardar resultado: {e}")
    
    print("\n🔧 PRÓXIMOS PASOS:")
    if result.get('exists') and result.get('authorized'):
        print("   • Tu sistema está funcionando correctamente para este documento")
    elif result.get('exists') and not result.get('authorized'):
        print("   • El documento existe pero no está autorizado - revisar errores")
    elif result.get('status') == 'not_found':
        print("   • ⚠️ CONFIRMADO: Este documento NO fue enviado al SRI")
        print("   • Tu sistema tiene 'éxito falso' - aplicar parches")
    elif result.get('status') == 'ambiguous':
        print("   • Revisar archivo XML generado para análisis manual")
        print("   • Posible problema de comunicación o formato")
    else:
        print("   • Revisar logs del sistema y conectividad con SRI")

if __name__ == "__main__":
    main()