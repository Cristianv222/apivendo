# -*- coding: utf-8 -*-
"""
Cliente SOAP para integración con el SRI - VERSIÓN SEGURA
SIN imports problemáticos de Zeep
"""

import logging
import requests
from datetime import datetime
from xml.etree import ElementTree as ET
from django.conf import settings
from django.utils import timezone
from apps.sri_integration.models import SRIConfiguration, SRIResponse
from apps.core.models import AuditLog

logger = logging.getLogger(__name__)

# Constante para identificar si zeep está disponible
ZEEP_AVAILABLE = False
try:
    from zeep import Client, Transport, Settings
    from zeep.exceptions import Fault
    from requests import Session
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    ZEEP_AVAILABLE = True
    logger.info("Zeep library loaded successfully")
except ImportError as e:
    logger.warning(f"Zeep not available, using requests fallback: {e}")
    # Clases dummy para evitar errores
    class Client:
        pass
    class Transport:
        pass
    class Settings:
        pass
    class Fault(Exception):
        pass


class SRISOAPClient:
    """
    Cliente SOAP para comunicación con los servicios del SRI
    VERSIÓN SEGURA con fallback a requests si Zeep no está disponible
    """
    
    # URLs oficiales del SRI
    SRI_URLS = {
        'TEST': {
            'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
            'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
            'reception_endpoint': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
            'authorization_endpoint': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
        },
        'PRODUCTION': {
            'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
            'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
            'reception_endpoint': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
            'authorization_endpoint': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
        }
    }
    
    def __init__(self, company):
        self.company = company
        try:
            self.sri_config = company.sri_configuration
            self.environment = self.sri_config.environment
        except Exception:
            # Configuración por defecto si no existe
            self.environment = 'TEST'
            self.sri_config = None
        
        # Inicializar clientes
        self._reception_client = None
        self._authorization_client = None
        
        logger.info(f"SRI SOAP Client initialized for {self.environment} environment")
        logger.info(f"Using {'Zeep' if ZEEP_AVAILABLE else 'Requests fallback'} for SOAP communication")
    
    def send_document_to_reception(self, document, signed_xml_content):
        """
        Envía documento firmado al servicio de recepción del SRI
        """
        try:
            logger.info(f"Sending document {document.document_number} to SRI reception")
            
            if ZEEP_AVAILABLE:
                return self._send_with_zeep(document, signed_xml_content, 'reception')
            else:
                return self._send_with_requests(document, signed_xml_content, 'reception')
                
        except Exception as e:
            error_msg = f"Error sending document to SRI reception: {str(e)}"
            logger.error(error_msg)
            self._log_sri_response(
                document,
                'RECEPTION',
                'ERROR',
                error_msg,
                {'error': str(e)}
            )
            return False, error_msg
    
    def get_document_authorization(self, document):
        """
        Consulta la autorización de un documento en el SRI
        """
        try:
            logger.info(f"Getting authorization for document {document.document_number}")
            
            if ZEEP_AVAILABLE:
                return self._get_auth_with_zeep(document)
            else:
                return self._get_auth_with_requests(document)
                
        except Exception as e:
            error_msg = f"Error getting authorization from SRI: {str(e)}"
            logger.error(error_msg)
            self._log_sri_response(
                document,
                'AUTHORIZATION',
                'ERROR',
                error_msg,
                {'error': str(e)}
            )
            return False, error_msg
    
    def _send_with_zeep(self, document, signed_xml_content, service_type):
        """Enviar usando Zeep (método preferido)"""
        try:
            # Configurar session
            session = Session()
            retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            session.timeout = (10, 30)
            
            transport = Transport(session=session)
            settings = Settings(strict=False, xml_huge_tree=True)
            
            # Crear cliente
            wsdl_url = self.SRI_URLS[self.environment][service_type]
            client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
            
            # Llamar al servicio
            if service_type == 'reception':
                response = client.service.validarComprobante(xml=signed_xml_content)
                return self._process_reception_response(document, response)
            else:
                response = client.service.autorizacionComprobante(claveAccesoComprobante=document.access_key)
                return self._process_authorization_response(document, response)
                
        except Exception as e:
            logger.warning(f"Zeep method failed: {e}. Falling back to requests...")
            # Fallback a requests
            if service_type == 'reception':
                return self._send_with_requests(document, signed_xml_content, service_type)
            else:
                return self._get_auth_with_requests(document)
    
    def _send_with_requests(self, document, signed_xml_content, service_type):
        """Enviar usando requests directamente - VERSIÓN CORREGIDA"""
        try:
            logger.info("Using corrected requests method for SRI communication")
            
            # SOAP envelope corregido basado en pruebas exitosas
            soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:rec="http://ec.gob.sri.ws.recepcion">
    <soap:Header/>
    <soap:Body>
        <rec:validarComprobante>
            <xml><![CDATA[{signed_xml_content}]]></xml>
        </rec:validarComprobante>
    </soap:Body>
</soap:Envelope>'''
            
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
            return False, f"Corrected requests method failed: {str(e)}"

    def _get_auth_with_zeep(self, document):
        """Consultar autorización usando Zeep"""
        try:
            # Configurar session
            session = Session()
            retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            session.timeout = (10, 30)
            
            transport = Transport(session=session)
            settings = Settings(strict=False, xml_huge_tree=True)
            
            # Crear cliente de autorización
            wsdl_url = self.SRI_URLS[self.environment]['authorization']
            client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
            
            # Llamar al servicio de autorización
            response = client.service.autorizacionComprobante(claveAccesoComprobante=document.access_key)
            return self._process_authorization_response(document, response)
            
        except Exception as e:
            logger.warning(f"Zeep authorization failed: {e}. Falling back to requests...")
            return self._get_auth_with_requests(document)
    
    def _get_auth_with_requests(self, document):
        """Consultar autorización usando requests"""
        try:
            logger.info("Getting authorization using requests fallback")
            
            # Preparar SOAP envelope para autorización
            soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ec="http://ec.gob.sri.ws.autorizacion">
    <soap:Header/>
    <soap:Body>
        <ec:autorizacionComprobante>
            <claveAccesoComprobante>{document.access_key}</claveAccesoComprobante>
        </ec:autorizacionComprobante>
    </soap:Body>
</soap:Envelope>'''
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'autorizacionComprobante',
                'User-Agent': 'VENDO_SRI_Client/1.0'
            }
            
            endpoint_url = self.SRI_URLS[self.environment]['authorization_endpoint']
            response = requests.post(
                endpoint_url,
                data=soap_body,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                    
                    ns = {
                        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                        'ns2': 'http://ec.gob.sri.ws.autorizacion'
                    }
                    
                    # Buscar autorización
                    autorizacion_elem = root.find('.//ns2:autorizacion', ns)
                    if autorizacion_elem is not None:
                        estado_elem = autorizacion_elem.find('ns2:estado', ns)
                        numero_elem = autorizacion_elem.find('ns2:numeroAutorizacion', ns)
                        fecha_elem = autorizacion_elem.find('ns2:fechaAutorizacion', ns)
                        
                        if estado_elem is not None:
                            estado = estado_elem.text
                            numero_autorizacion = numero_elem.text if numero_elem is not None else ''
                            fecha_autorizacion_str = fecha_elem.text if fecha_elem is not None else ''
                            
                            # Convertir fecha
                            fecha_autorizacion = None
                            if fecha_autorizacion_str:
                                try:
                                    fecha_autorizacion = datetime.strptime(fecha_autorizacion_str, '%d/%m/%Y %H:%M:%S')
                                except ValueError:
                                    try:
                                        fecha_autorizacion = datetime.strptime(fecha_autorizacion_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        pass
                            
                            # Preparar datos de respuesta
                            response_data = {
                                'estado': estado,
                                'numeroAutorizacion': numero_autorizacion,
                                'fechaAutorizacion': fecha_autorizacion_str,
                                'response': response.text,
                                'method': 'requests_fallback'
                            }
                            
                            self._log_sri_response(
                                document,
                                'AUTHORIZATION',
                                estado,
                                f"Authorization response (requests): {estado}",
                                response_data
                            )
                            
                            if estado == 'AUTORIZADO':
                                document.status = 'AUTHORIZED'
                                document.sri_authorization_code = numero_autorizacion
                                document.sri_authorization_date = fecha_autorizacion
                                document.sri_response = response_data
                                document.save()
                                return True, f'Document authorized: {numero_autorizacion}'
                            else:
                                document.status = 'REJECTED'
                                document.sri_response = response_data
                                document.save()
                                return False, f'Document rejected with state: {estado}'
                    
                    return False, 'No authorization found in response'
                    
                except ET.ParseError:
                    return False, f'Invalid XML response: {response.text[:200]}...'
            else:
                return False, f'HTTP Error: {response.status_code}'
                
        except Exception as e:
            return False, f'Authorization requests method failed: {str(e)}'
    
    def _process_reception_response(self, document, response):
        """Procesar respuesta de recepción (para Zeep)"""
        try:
            print("🔍 DEBUG - Respuesta SRI completa:", response)
            print("🔍 DEBUG - Tipo de respuesta:", type(response))
            
            # Verificar errores en comprobantes
            if hasattr(response, "comprobantes") and response.comprobantes:
                if hasattr(response.comprobantes, "comprobante"):
                    for comp in response.comprobantes.comprobante:
                        if hasattr(comp, "mensajes") and comp.mensajes:
                            if hasattr(comp.mensajes, "mensaje"):
                                errores = []
                                for msg in comp.mensajes.mensaje:
                                    if hasattr(msg, "mensaje"):
                                        error_id = getattr(msg, "identificador", "N/A")
                                        error_msg = msg.mensaje
                                        error_info = getattr(msg, "informacionAdicional", "")
                                        error_detail = f"Error {error_id}: {error_msg}"
                                        if error_info:
                                            error_detail += f" - {error_info}"
                                        errores.append(error_detail)
                                
                                if errores:
                                    error_text = "; ".join(errores)
                                    print("🔍 DEBUG - Errores SRI:", error_text)
                                    
                                    response_data = {
                                        "estado": "RECHAZADO",
                                        "errores": errores,
                                        "response": str(response),
                                        "method": "zeep"
                                    }
                                    
                                    self._log_sri_response(
                                        document,
                                        "RECEPTION",
                                        "RECHAZADO",
                                        f"Document rejected by SRI: {error_text}",
                                        response_data
                                    )
                                    
                                    document.status = "ERROR"
                                    document.save()
                                    return False, f"SRI Error: {error_text}"
            
            # Verificar estado directo
            estado = getattr(response, "estado", None)
            if estado == "RECIBIDA":
                document.status = "SENT" 
                document.save()
                return True, "Document received by SRI"
            elif estado:
                document.status = "ERROR"
                document.save()
                return False, f"Document rejected with state: {estado}"
            else:
                return False, "No status found in SRI response"
                
        except Exception as e:
            print(f"🔍 DEBUG - Error procesando respuesta: {e}")
            return False, f"Error processing SRI response: {str(e)}"
    
    def _process_authorization_response(self, document, response):
        """Procesar respuesta de autorización (para Zeep)"""
        try:
            print("🔍 DEBUG - Respuesta autorización SRI:", response)
            
            # Verificar si hay autorizaciones
            if hasattr(response, "autorizaciones") and response.autorizaciones:
                if hasattr(response.autorizaciones, "autorizacion"):
                    for auth in response.autorizaciones.autorizacion:
                        estado = getattr(auth, "estado", None)
                        numero_autorizacion = getattr(auth, "numeroAutorizacion", "")
                        fecha_autorizacion_str = getattr(auth, "fechaAutorizacion", "")
                        
                        # Convertir fecha
                        fecha_autorizacion = None
                        if fecha_autorizacion_str:
                            try:
                                fecha_autorizacion = datetime.strptime(fecha_autorizacion_str, '%d/%m/%Y %H:%M:%S')
                            except ValueError:
                                try:
                                    fecha_autorizacion = datetime.strptime(fecha_autorizacion_str, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    pass
                        
                        # Preparar datos de respuesta
                        response_data = {
                            'estado': estado,
                            'numeroAutorizacion': numero_autorizacion,
                            'fechaAutorizacion': fecha_autorizacion_str,
                            'response': str(response),
                            'method': 'zeep'
                        }
                        
                        self._log_sri_response(
                            document,
                            'AUTHORIZATION',
                            estado,
                            f"Authorization response (zeep): {estado}",
                            response_data
                        )
                        
                        if estado == 'AUTORIZADO':
                            document.status = 'AUTHORIZED'
                            document.sri_authorization_code = numero_autorizacion
                            document.sri_authorization_date = fecha_autorizacion
                            document.sri_response = response_data
                            document.save()
                            return True, f'Document authorized: {numero_autorizacion}'
                        else:
                            document.status = 'REJECTED'
                            document.sri_response = response_data
                            document.save()
                            return False, f'Document rejected with state: {estado}'
            
            return False, 'No authorization found in response'
            
        except Exception as e:
            print(f"🔍 DEBUG - Error procesando autorización: {e}")
            return False, f"Error processing authorization response: {str(e)}"
    
    def _log_sri_response(self, document, operation_type, response_code, message, raw_response):
        """
        Registra la respuesta del SRI en la base de datos
        """
        try:
            # Obtener el ElectronicDocument correcto
            if hasattr(document, "original_document"):
                # Para CreditNote, DebitNote, etc.
                electronic_doc = document.original_document
            elif hasattr(document, "document_ptr"):
                # Si tiene relación directa
                electronic_doc = document.document_ptr
            else:
                # Si ya es ElectronicDocument
                electronic_doc = document
            
            SRIResponse.objects.create(
                document=electronic_doc,
                operation_type=operation_type,
                response_code=response_code or "UNKNOWN",
                response_message=message,
                raw_response=raw_response
            )
            
            # También log de auditoría
            AuditLog.objects.create(
                action='SRI_RESPONSE',
                model_name='ElectronicDocument',
                object_id=str(document.id),
                object_representation=str(document),
                additional_data={
                    'operation_type': operation_type,
                    'response_code': response_code,
                    'message': message,
                    'environment': self.environment
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging SRI response: {str(e)}")
    
    def test_connection(self):
        """
        Prueba la conexión con los servicios del SRI
        """
        results = {}
        method = 'Zeep' if ZEEP_AVAILABLE else 'Requests'
        
        # Probar conectividad básica
        for service_name, url in [('reception', self.SRI_URLS[self.environment]['reception']), 
                                  ('authorization', self.SRI_URLS[self.environment]['authorization'])]:
            try:
                response = requests.head(url, timeout=10)
                results[service_name] = {
                    'status': 'OK' if response.status_code == 200 else 'WARNING',
                    'service_url': url,
                    'http_status': response.status_code,
                    'method': method,
                    'message': f'Service reachable via {method}'
                }
            except Exception as e:
                results[service_name] = {
                    'status': 'ERROR',
                    'service_url': url,
                    'error': str(e),
                    'method': method,
                    'message': f'Connection failed via {method}'
                }
        
        return results