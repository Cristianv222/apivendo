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
        """Enviar usando requests directamente"""
        try:
            logger.info("Using requests fallback for SRI communication")
            
            # Preparar SOAP envelope
            soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:ec="http://ec.gob.sri.ws.recepcion">
    <soap:Header/>
    <soap:Body>
        <ec:validarComprobante>
            <xml><![CDATA[{signed_xml_content}]]></xml>
        </ec:validarComprobante>
    </soap:Body>
</soap:Envelope>'''
            
            # Headers SOAP
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'validarComprobante',
                'User-Agent': 'VENDO_SRI_Client/1.0'
            }
            
            # Enviar solicitud
            endpoint_url = self.SRI_URLS[self.environment]['reception_endpoint']
            response = requests.post(
                endpoint_url,
                data=soap_body,
                headers=headers,
                timeout=30
            )
            
            # Procesar respuesta
            if response.status_code == 200:
                # Parsear respuesta XML
                try:
                    root = ET.fromstring(response.content)
                    
                    # Buscar estado en la respuesta
                    # Namespace del SRI
                    ns = {
                        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                        'ns2': 'http://ec.gob.sri.ws.recepcion'
                    }
                    
                    estado_elem = root.find('.//ns2:estado', ns)
                    if estado_elem is not None:
                        estado = estado_elem.text
                        
                        # Log de respuesta
                        response_data = {
                            'estado': estado,
                            'response': response.text,
                            'method': 'requests_fallback'
                        }
                        
                        self._log_sri_response(
                            document,
                            'RECEPTION',
                            estado,
                            f"Reception response (requests): {estado}",
                            response_data
                        )
                        
                        if estado == 'RECIBIDA':
                            document.status = 'SENT'
                            document.save()
                            return True, 'Document received by SRI (requests method)'
                        else:
                            document.status = 'ERROR'
                            document.save()
                            return False, f'Document rejected with state: {estado}'
                    else:
                        # Buscar fault
                        fault_elem = root.find('.//soap:Fault', ns)
                        if fault_elem is not None:
                            fault_string = fault_elem.find('faultstring')
                            error_msg = fault_string.text if fault_string is not None else 'Unknown SOAP fault'
                            return False, error_msg
                        
                        return False, 'Unknown response format'
                        
                except ET.ParseError:
                    return False, f'Invalid XML response: {response.text[:200]}...'
            else:
                return False, f'HTTP Error: {response.status_code} - {response.text[:200]}...'
                
        except Exception as e:
            return False, f'Requests method failed: {str(e)}'
    
    def _get_auth_with_zeep(self, document):
        """Consultar autorización usando Zeep"""
        # Similar implementación a _send_with_zeep pero para autorización
        pass
    
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
        # Implementación similar a la versión anterior pero mejorada
        pass
    
    def _process_authorization_response(self, document, response):
        """Procesar respuesta de autorización (para Zeep)"""
        # Implementación similar a la versión anterior pero mejorada
        pass
    
    def _log_sri_response(self, document, operation_type, response_code, message, raw_response):
        """
        Registra la respuesta del SRI en la base de datos
        """
        try:
            SRIResponse.objects.create(
                document=document,
                operation_type=operation_type,
                response_code=response_code,
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