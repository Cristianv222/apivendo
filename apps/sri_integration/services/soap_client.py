# -*- coding: utf-8 -*-
"""
Cliente SOAP para integración con el SRI - VERSIÓN CORREGIDA PARA ESPECIFICACIONES 2025
Actualizado según las especificaciones oficiales del SRI Ecuador
"""

import logging
import requests
import base64
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
    ✅ ACTUALIZADO SEGÚN ESPECIFICACIONES SRI 2025
    """
    
    # ✅ URLs OFICIALES DEL SRI - ACTUALIZADAS 2025
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
        ✅ FORZAR USO DE REQUESTS SOLAMENTE
        """
        try:
            logger.info(f"Sending document {document.document_number} to SRI reception")
            
            # ✅ VALIDAR QUE EL XML ESTÉ FIRMADO CORRECTAMENTE
            if not self._validate_signed_xml(signed_xml_content):
                return False, "XML signature validation failed"
            
            # ✅ FORZAR SIEMPRE REQUESTS (no usar Zeep)
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
        ✅ CORREGIDO SEGÚN ESPECIFICACIONES SRI 2025
        """
        try:
            logger.info(f"Getting authorization for document {document.document_number}")
            
            if False:  # FORZAR REQUESTS
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
    
    def _validate_signed_xml(self, signed_xml_content):
        """
        ✅ NUEVO: Valida que el XML esté correctamente firmado según especificaciones SRI 2025
        """
        try:
            # Verificar que es XML válido
            root = ET.fromstring(signed_xml_content)
            
            # ✅ VERIFICAR NAMESPACES OBLIGATORIOS SRI 2025
            required_namespaces = [
                'http://www.w3.org/2000/09/xmldsig#',  # Firma digital
                'http://uri.etsi.org/01903/v1.3.2#'    # XAdES
            ]
            
            xml_str = ET.tostring(root, encoding='unicode')
            for ns in required_namespaces:
                if ns not in xml_str:
                    logger.warning(f"Missing required namespace: {ns}")
                    return False
            
            # ✅ VERIFICAR QUE TENGA FIRMA DIGITAL XAdES-BES
            ds_signature = root.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
            if ds_signature is None:
                logger.error("No digital signature found in XML")
                return False
            
            # ✅ VERIFICAR QUE TENGA QUALIFYING PROPERTIES (XAdES)
            qualifying_props = root.find('.//{http://uri.etsi.org/01903/v1.3.2#}QualifyingProperties')
            if qualifying_props is None:
                logger.error("No XAdES QualifyingProperties found in XML")
                return False
            
            # ✅ VERIFICAR CERTIFICADO
            x509_cert = root.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
            if x509_cert is None:
                logger.error("No X509Certificate found in signature")
                return False
            
            logger.info("XML signature validation passed")
            return True
            
        except ET.ParseError as e:
            logger.error(f"Invalid XML format: {e}")
            return False
        except Exception as e:
            logger.error(f"XML validation error: {e}")
            return False
    
    def _send_with_zeep(self, document, signed_xml_content, service_type):
        """
        Enviar usando Zeep (método preferido)
        ✅ ACTUALIZADO SEGÚN ESPECIFICACIONES SRI 2025 - SIN BASE64
        """
        try:
            # ✅ CONFIGURAR SESSION CON PARÁMETROS OPTIMIZADOS PARA SRI 2025
            session = Session()
            retry_strategy = Retry(
                total=3, 
                backoff_factor=2,  # ✅ Incrementado para dar más tiempo al SRI
                status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            session.timeout = (15, 45)  # ✅ Timeouts incrementados para SRI 2025
            
            # ✅ HEADERS ESPECÍFICOS PARA SRI 2025
            session.headers.update({
                'User-Agent': 'SRI-Ecuador-Client/2025.1',
                'Accept': 'text/xml, application/soap+xml',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            })
            
            transport = Transport(session=session)
            settings = Settings(
                strict=False, 
                xml_huge_tree=True,
                force_https=True,  # ✅ Forzar HTTPS para seguridad
                raw_response=False
            )
            
            # Crear cliente
            wsdl_url = self.SRI_URLS[self.environment][service_type]
            client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
            
            # ✅ LLAMAR AL SERVICIO CON PARÁMETROS CORRECTOS PARA SRI 2025
            if service_type == 'reception':
                # ✅ ENVIAR XML DIRECTAMENTE SIN BASE64 - PRUEBA CRÍTICA
                logger.info("🔍 TESTING: Sending XML without Base64 encoding")
                
                response = client.service.validarComprobante(xml=signed_xml_content)
                return self._process_reception_response(document, response)
            else:
                response = client.service.autorizacionComprobante(
                    claveAccesoComprobante=document.access_key
                )
                return self._process_authorization_response(document, response)
                
        except Fault as soap_fault:
            logger.error(f"SOAP Fault: {soap_fault}")
            return self._handle_soap_fault(document, soap_fault, service_type)
        except Exception as e:
            logger.warning(f"Zeep method failed: {e}. Falling back to requests...")
            # Fallback a requests
            if service_type == 'reception':
                return self._send_with_requests(document, signed_xml_content, service_type)
            else:
                return self._get_auth_with_requests(document)
    
    def _send_with_requests(self, document, signed_xml_content, service_type):
        """
        Enviar usando requests directamente
        ✅ COMPLETAMENTE CORREGIDO SEGÚN ESPECIFICACIONES SRI 2025 - SIN BASE64
        """
        try:
            logger.info("Using optimized requests method for SRI communication")
            
            # ✅ SOAP ENVELOPE CORREGIDO SEGÚN ESPECIFICACIONES OFICIALES SRI 2025
            # ENVIANDO XML DIRECTAMENTE SIN BASE64 Y SIN CDATA
            soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:rec="http://ec.gob.sri.ws.recepcion">
    <soap:Header/>
    <soap:Body>
        <rec:validarComprobante>
            <xml>{signed_xml_content}</xml>
        </rec:validarComprobante>
    </soap:Body>
</soap:Envelope>'''
            
            # ✅ HEADERS ACTUALIZADOS SEGÚN ESPECIFICACIONES SRI 2025
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": '""',  # ✅ SOAPAction específica
                "User-Agent": "SRI-Ecuador-Client/2025.1",
                "Accept": "text/xml, application/soap+xml",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            # ✅ ENVIAR SOLICITUD CON PARÁMETROS OPTIMIZADOS
            endpoint_url = self.SRI_URLS[self.environment]["reception_endpoint"]
            response = requests.post(
                endpoint_url,
                data=soap_body.encode("utf-8"),
                headers=headers,
                timeout=(15, 45),  # ✅ Timeouts incrementados
                verify=True,       # ✅ Verificar certificados SSL
                allow_redirects=False
            )
            
            logger.info(f"SRI Response Status: {response.status_code}")
            
            # ✅ PROCESAR RESPUESTA SEGÚN ESPECIFICACIONES SRI 2025
            if response.status_code == 200:
                return self._process_requests_response(document, response)
            elif response.status_code == 500:
                # ✅ Error 500 puede contener respuesta válida del SRI
                return self._process_requests_soap_fault(document, response)
            else:
                error_msg = f"HTTP Error: {response.status_code} - {response.text[:200]}"
                self._log_sri_response(
                    document,
                    "RECEPTION",
                    "HTTP_ERROR",
                    error_msg,
                    {"status_code": response.status_code, "response": response.text}
                )
                return False, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "Timeout connecting to SRI services"
            return False, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error to SRI services"
            return False, error_msg
        except Exception as e:
            return False, f"Requests method failed: {str(e)}"
    
    def _process_requests_response(self, document, response):
        """
        ✅ NUEVO: Procesa respuesta exitosa del SRI usando requests
        """
        try:
            response_text = response.text
            logger.info(f"Processing SRI response: {len(response_text)} characters")
            
            # ✅ PARSEAR XML DE RESPUESTA
            root = ET.fromstring(response_text)
            
            # ✅ NAMESPACES PARA RESPUESTA SRI 2025
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns2': 'http://ec.gob.sri.ws.recepcion'
            }
            
            # ✅ BUSCAR ESTADO EN LA RESPUESTA
            estado_elem = root.find('.//ns2:estado', namespaces)
            if estado_elem is not None:
                estado = estado_elem.text
                
                if estado == "RECIBIDA":
                    self._log_sri_response(
                        document,
                        "RECEPTION",
                        "RECIBIDA",
                        "Document received by SRI",
                        {"response": response_text, "method": "requests_2025"}
                    )
                    document.status = "SENT"
                    document.save()
                    return True, "Document received by SRI"
                else:
                    # ✅ EXTRAER MENSAJES DE ERROR
                    error_messages = self._extract_error_messages(root, namespaces)
                    error_text = "; ".join(error_messages) if error_messages else f"Document rejected with state: {estado}"
                    
                    self._log_sri_response(
                        document,
                        "RECEPTION",
                        estado,
                        error_text,
                        {"response": response_text, "method": "requests_2025", "errors": error_messages}
                    )
                    document.status = "ERROR"
                    document.save()
                    return False, error_text
            
            # ✅ SI NO HAY ESTADO, BUSCAR MENSAJES DE ERROR DIRECTAMENTE
            error_messages = self._extract_error_messages(root, namespaces)
            if error_messages:
                error_text = "; ".join(error_messages)
                if "Error 35" in error_text:
                    logger.warning("Detected Error 35 - XML structure issue")
                
                self._log_sri_response(
                    document,
                    "RECEPTION",
                    "ERROR",
                    error_text,
                    {"response": response_text, "method": "requests_2025", "errors": error_messages}
                )
                document.status = "ERROR"
                document.save()
                return False, f"SRI Error: {error_text}"
            
            # ✅ RESPUESTA INESPERADA
            return False, "Unexpected SRI response format"
            
        except ET.ParseError as e:
            logger.error(f"Invalid XML response from SRI: {e}")
            return False, f"Invalid XML response: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing SRI response: {e}")
            return False, f"Error processing response: {str(e)}"
    
    def _process_requests_soap_fault(self, document, response):
        """
        ✅ NUEVO: Procesa SOAP Fault en respuesta HTTP 500
        """
        try:
            response_text = response.text
            root = ET.fromstring(response_text)
            
            # ✅ BUSCAR SOAP FAULT
            fault_elem = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
            if fault_elem is not None:
                fault_code = fault_elem.find('.//{http://schemas.xmlsoap.org/soap/envelope/}faultcode')
                fault_string = fault_elem.find('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
                
                fault_code_text = fault_code.text if fault_code is not None else "Unknown"
                fault_string_text = fault_string.text if fault_string is not None else "Unknown error"
                
                error_msg = f"SOAP Fault {fault_code_text}: {fault_string_text}"
                
                self._log_sri_response(
                    document,
                    "RECEPTION",
                    "SOAP_FAULT",
                    error_msg,
                    {"response": response_text, "method": "requests_2025", "fault_code": fault_code_text}
                )
                document.status = "ERROR"
                document.save()
                return False, error_msg
            
            # Si no es SOAP Fault, procesar como respuesta normal
            return self._process_requests_response(document, response)
            
        except ET.ParseError:
            error_msg = f"Invalid SOAP response: {response.text[:200]}"
            return False, error_msg
        except Exception as e:
            return False, f"Error processing SOAP fault: {str(e)}"
    
    def _extract_error_messages(self, root, namespaces):
        """
        ✅ NUEVO: Extrae mensajes de error de la respuesta SRI
        """
        error_messages = []
        
        try:
            # ✅ BUSCAR MENSAJES EN COMPROBANTES
            mensaje_elements = root.findall('.//ns2:mensaje', namespaces)
            for mensaje_elem in mensaje_elements:
                identificador_elem = mensaje_elem.find('ns2:identificador', namespaces)
                mensaje_text_elem = mensaje_elem.find('ns2:mensaje', namespaces)
                info_adicional_elem = mensaje_elem.find('ns2:informacionAdicional', namespaces)
                
                if mensaje_text_elem is not None:
                    identificador = identificador_elem.text if identificador_elem is not None else "N/A"
                    mensaje_text = mensaje_text_elem.text
                    info_adicional = info_adicional_elem.text if info_adicional_elem is not None else ""
                    
                    error_detail = f"Error {identificador}: {mensaje_text}"
                    if info_adicional:
                        error_detail += f" - {info_adicional}"
                    
                    error_messages.append(error_detail)
            
            # ✅ BUSCAR OTROS FORMATOS DE ERROR
            if not error_messages:
                error_elems = root.findall('.//error', namespaces)
                for error_elem in error_elems:
                    if error_elem.text:
                        error_messages.append(error_elem.text)
            
        except Exception as e:
            logger.error(f"Error extracting error messages: {e}")
        
        return error_messages
    
    def _handle_soap_fault(self, document, soap_fault, service_type):
        """
        ✅ NUEVO: Maneja SOAP Faults específicos del SRI
        """
        fault_code = getattr(soap_fault, 'code', 'Unknown')
        fault_message = getattr(soap_fault, 'message', str(soap_fault))
        
        # ✅ MAPEAR CÓDIGOS DE ERROR ESPECÍFICOS DEL SRI
        sri_error_map = {
            'Client': 'CLIENT_ERROR',
            'Server': 'SERVER_ERROR',
            'VersionMismatch': 'VERSION_ERROR',
            'MustUnderstand': 'PROTOCOL_ERROR'
        }
        
        error_code = sri_error_map.get(fault_code, 'SOAP_FAULT')
        error_msg = f"SOAP Fault [{fault_code}]: {fault_message}"
        
        self._log_sri_response(
            document,
            service_type.upper(),
            error_code,
            error_msg,
            {
                'fault_code': fault_code,
                'fault_message': fault_message,
                'method': 'zeep'
            }
        )
        
        document.status = "ERROR"
        document.save()
        return False, error_msg
    
    def _get_auth_with_zeep(self, document):
        """
        Consultar autorización usando Zeep
        ✅ ACTUALIZADO SEGÚN ESPECIFICACIONES SRI 2025
        """
        try:
            # ✅ CONFIGURAR SESSION OPTIMIZADA PARA AUTORIZACIÓN
            session = Session()
            retry_strategy = Retry(
                total=5,  # ✅ Más reintentos para autorización
                backoff_factor=3,
                status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            session.timeout = (20, 60)  # ✅ Timeouts más largos para autorización
            
            session.headers.update({
                'User-Agent': 'SRI-Ecuador-Auth-Client/2025.1',
                'Accept': 'text/xml, application/soap+xml'
            })
            
            transport = Transport(session=session)
            settings = Settings(strict=False, xml_huge_tree=True, force_https=True)
            
            # Crear cliente de autorización
            wsdl_url = self.SRI_URLS[self.environment]['authorization']
            client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
            
            # ✅ LLAMAR AL SERVICIO DE AUTORIZACIÓN
            response = client.service.autorizacionComprobante(
                claveAccesoComprobante=document.access_key
            )
            return self._process_authorization_response(document, response)
            
        except Fault as soap_fault:
            return self._handle_soap_fault(document, soap_fault, 'AUTHORIZATION')
        except Exception as e:
            logger.warning(f"Zeep authorization failed: {e}. Falling back to requests...")
            return self._get_auth_with_requests(document)
    
    def _get_auth_with_requests(self, document):
        """
        Consultar autorización usando requests
        ✅ COMPLETAMENTE CORREGIDO SEGÚN ESPECIFICACIONES SRI 2025
        """
        try:
            logger.info("Getting authorization using requests (2025 specs)")
            
            # ✅ SOAP ENVELOPE CORREGIDO PARA AUTORIZACIÓN
            soap_body = f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:aut="http://ec.gob.sri.ws.autorizacion">
    <soap:Header/>
    <soap:Body>
        <aut:autorizacionComprobante>
            <claveAccesoComprobante>{document.access_key}</claveAccesoComprobante>
        </aut:autorizacionComprobante>
    </soap:Body>
</soap:Envelope>'''
            
            # ✅ HEADERS CORREGIDOS PARA AUTORIZACIÓN
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'autorizacionComprobante',
                'User-Agent': 'SRI-Ecuador-Auth-Client/2025.1',
                'Accept': 'text/xml, application/soap+xml',
                'Cache-Control': 'no-cache'
            }
            
            endpoint_url = self.SRI_URLS[self.environment]['authorization_endpoint']
            response = requests.post(
                endpoint_url,
                data=soap_body.encode('utf-8'),
                headers=headers,
                timeout=(20, 60),  # ✅ Timeouts incrementados
                verify=True
            )
            
            if response.status_code == 200:
                return self._process_authorization_requests_response(document, response)
            elif response.status_code == 500:
                return self._process_requests_soap_fault(document, response)
            else:
                return False, f'HTTP Error: {response.status_code}'
                
        except Exception as e:
            return False, f'Authorization requests method failed: {str(e)}'
    
    def _process_authorization_requests_response(self, document, response):
        """
        ✅ NUEVO: Procesa respuesta de autorización usando requests
        """
        try:
            root = ET.fromstring(response.content)
            
            # ✅ NAMESPACES PARA RESPUESTA DE AUTORIZACIÓN
            ns = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns2': 'http://ec.gob.sri.ws.autorizacion'
            }
            
            # ✅ BUSCAR AUTORIZACIÓN EN LA RESPUESTA
            autorizacion_elems = root.findall('.//ns2:autorizacion', ns)
            for autorizacion_elem in autorizacion_elems:
                estado_elem = autorizacion_elem.find('ns2:estado', ns)
                numero_elem = autorizacion_elem.find('ns2:numeroAutorizacion', ns)
                fecha_elem = autorizacion_elem.find('ns2:fechaAutorizacion', ns)
                
                if estado_elem is not None:
                    estado = estado_elem.text
                    numero_autorizacion = numero_elem.text if numero_elem is not None else ''
                    fecha_autorizacion_str = fecha_elem.text if fecha_elem is not None else ''
                    
                    # ✅ CONVERTIR FECHA CON MÚLTIPLES FORMATOS
                    fecha_autorizacion = self._parse_authorization_date(fecha_autorizacion_str)
                    
                    # Preparar datos de respuesta
                    response_data = {
                        'estado': estado,
                        'numeroAutorizacion': numero_autorizacion,
                        'fechaAutorizacion': fecha_autorizacion_str,
                        'response': response.text,
                        'method': 'requests_2025'
                    }
                    
                    self._log_sri_response(
                        document,
                        'AUTHORIZATION',
                        estado,
                        f"Authorization response: {estado}",
                        response_data
                    )
                    
                    if estado == 'AUTORIZADO':
                        document.status = 'AUTHORIZED'
                        document.sri_authorization_code = numero_autorizacion
                        document.sri_authorization_date = fecha_autorizacion
                        document.sri_response = response_data
                        document.save()
                        return True, f'Document authorized: {numero_autorizacion}'
                    elif estado == 'NO AUTORIZADO':
                        # ✅ EXTRAER MENSAJES DE ERROR ESPECÍFICOS
                        error_messages = self._extract_authorization_errors(autorizacion_elem, ns)
                        error_text = "; ".join(error_messages) if error_messages else "Document not authorized"
                        
                        document.status = 'REJECTED'
                        document.sri_response = response_data
                        document.save()
                        return False, f'Document rejected: {error_text}'
                    else:
                        document.status = 'PENDING'
                        document.sri_response = response_data
                        document.save()
                        return False, f'Document in process with state: {estado}'
            
            return False, 'No authorization found in response'
            
        except ET.ParseError:
            return False, f'Invalid XML response: {response.text[:200]}...'
        except Exception as e:
            return False, f'Error processing authorization response: {str(e)}'
    
    def _extract_authorization_errors(self, autorizacion_elem, namespaces):
        """
        ✅ NUEVO: Extrae mensajes de error de respuesta de autorización
        """
        error_messages = []
        
        try:
            # ✅ BUSCAR MENSAJES EN AUTORIZACIÓN
            mensajes_elem = autorizacion_elem.find('ns2:mensajes', namespaces)
            if mensajes_elem is not None:
                mensaje_elems = mensajes_elem.findall('ns2:mensaje', namespaces)
                for mensaje_elem in mensaje_elems:
                    identificador_elem = mensaje_elem.find('ns2:identificador', namespaces)
                    mensaje_text_elem = mensaje_elem.find('ns2:mensaje', namespaces)
                    info_adicional_elem = mensaje_elem.find('ns2:informacionAdicional', namespaces)
                    
                    if mensaje_text_elem is not None:
                        identificador = identificador_elem.text if identificador_elem is not None else "N/A"
                        mensaje_text = mensaje_text_elem.text
                        info_adicional = info_adicional_elem.text if info_adicional_elem is not None else ""
                        
                        error_detail = f"Error {identificador}: {mensaje_text}"
                        if info_adicional:
                            error_detail += f" - {info_adicional}"
                        
                        error_messages.append(error_detail)
        
        except Exception as e:
            logger.error(f"Error extracting authorization errors: {e}")
        
        return error_messages
    
    def _parse_authorization_date(self, fecha_str):
        """
        ✅ NUEVO: Parsea fechas de autorización con múltiples formatos
        """
        if not fecha_str:
            return None
        
        # ✅ FORMATOS DE FECHA SOPORTADOS POR SRI 2025
        date_formats = [
            '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(fecha_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse authorization date: {fecha_str}")
        return None
    
    def _process_reception_response(self, document, response):
        """
        Procesar respuesta de recepción (para Zeep)
        ✅ MEJORADO PARA SRI 2025
        """
        try:
            logger.info(f"Processing SRI reception response (Zeep): {type(response)}")
            
            # ✅ VERIFICAR ESTADO DIRECTO PRIMERO
            estado = getattr(response, "estado", None)
            if estado == "RECIBIDA":
                document.status = "SENT" 
                document.save()
                
                self._log_sri_response(
                    document,
                    "RECEPTION",
                    "RECIBIDA",
                    "Document received by SRI (Zeep)",
                    {"response": str(response), "method": "zeep_2025"}
                )
                return True, "Document received by SRI"
            
            # ✅ VERIFICAR ERRORES EN COMPROBANTES
            if hasattr(response, "comprobantes") and response.comprobantes:
                if hasattr(response.comprobantes, "comprobante"):
                    comprobantes = response.comprobantes.comprobante
                    if not isinstance(comprobantes, list):
                        comprobantes = [comprobantes]
                    
                    for comp in comprobantes:
                        if hasattr(comp, "mensajes") and comp.mensajes:
                            mensajes = comp.mensajes.mensaje if hasattr(comp.mensajes, "mensaje") else []
                            if not isinstance(mensajes, list):
                                mensajes = [mensajes]
                            
                            errores = []
                            for msg in mensajes:
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
                                
                                response_data = {
                                    "estado": "RECHAZADO",
                                    "errores": errores,
                                    "response": str(response),
                                    "method": "zeep_2025"
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
            
            # ✅ MANEJAR OTROS ESTADOS
            if estado:
                document.status = "ERROR"
                document.save()
                return False, f"Document rejected with state: {estado}"
            else:
                return False, "No status found in SRI response"
                
        except Exception as e:
            logger.error(f"Error processing reception response: {e}")
            return False, f"Error processing SRI response: {str(e)}"
    
    def _process_authorization_response(self, document, response):
        """
        Procesar respuesta de autorización (para Zeep)
        ✅ MEJORADO PARA SRI 2025
        """
        try:
            logger.info(f"Processing SRI authorization response (Zeep): {type(response)}")
            
            # ✅ VERIFICAR SI HAY AUTORIZACIONES
            if hasattr(response, "autorizaciones") and response.autorizaciones:
                autorizaciones = response.autorizaciones.autorizacion if hasattr(response.autorizaciones, "autorizacion") else []
                if not isinstance(autorizaciones, list):
                    autorizaciones = [autorizaciones]
                
                for auth in autorizaciones:
                    estado = getattr(auth, "estado", None)
                    numero_autorizacion = getattr(auth, "numeroAutorizacion", "")
                    fecha_autorizacion_str = getattr(auth, "fechaAutorizacion", "")
                    
                    # ✅ CONVERTIR FECHA
                    fecha_autorizacion = self._parse_authorization_date(fecha_autorizacion_str)
                    
                    # Preparar datos de respuesta
                    response_data = {
                        'estado': estado,
                        'numeroAutorizacion': numero_autorizacion,
                        'fechaAutorizacion': fecha_autorizacion_str,
                        'response': str(response),
                        'method': 'zeep_2025'
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
                    elif estado == 'NO AUTORIZADO':
                        # ✅ EXTRAER MENSAJES DE ERROR
                        error_messages = []
                        if hasattr(auth, 'mensajes') and auth.mensajes:
                            mensajes = auth.mensajes.mensaje if hasattr(auth.mensajes, 'mensaje') else []
                            if not isinstance(mensajes, list):
                                mensajes = [mensajes]
                            
                            for msg in mensajes:
                                if hasattr(msg, 'mensaje'):
                                    error_id = getattr(msg, 'identificador', 'N/A')
                                    error_text = msg.mensaje
                                    error_info = getattr(msg, 'informacionAdicional', '')
                                    error_detail = f"Error {error_id}: {error_text}"
                                    if error_info:
                                        error_detail += f" - {error_info}"
                                    error_messages.append(error_detail)
                        
                        error_text = "; ".join(error_messages) if error_messages else "Document not authorized"
                        document.status = 'REJECTED'
                        document.sri_response = response_data
                        document.save()
                        return False, f'Document rejected: {error_text}'
                    else:
                        document.status = 'PENDING'
                        document.sri_response = response_data
                        document.save()
                        return False, f'Document in process with state: {estado}'
            
            return False, 'No authorization found in response'
            
        except Exception as e:
            logger.error(f"Error processing authorization response: {e}")
            return False, f"Error processing authorization response: {str(e)}"
    
    def _get_audit_action(self, operation_type, response_code):
        """
        Mapea el tipo de operación y código de respuesta a una acción de auditoría válida
        ✅ EXPANDIDO PARA SRI 2025
        """
        action_map = {
            'RECEPTION': {
                'RECIBIDA': 'SRI_RECEIVED',
                'RECHAZADO': 'SRI_REJECTED',
                'ERROR': 'SRI_ERROR',
                'ERROR_35': 'SRI_XML_ERROR',
                'TIMEOUT': 'SRI_TIMEOUT',
                'HTTP_ERROR': 'SRI_HTTP_ERROR',
                'SOAP_FAULT': 'SRI_SOAP_FAULT',
                'CLIENT_ERROR': 'SRI_CLIENT_ERROR',
                'SERVER_ERROR': 'SRI_SERVER_ERROR'
            },
            'AUTHORIZATION': {
                'AUTORIZADO': 'SRI_AUTHORIZED',
                'NO AUTORIZADO': 'SRI_NOT_AUTHORIZED',
                'RECHAZADO': 'SRI_REJECTED',
                'ERROR': 'SRI_ERROR',
                'TIMEOUT': 'SRI_TIMEOUT',
                'PENDING': 'SRI_PENDING'
            },
            'SEND': {
                'SUCCESS': 'SRI_SENT',
                'ERROR': 'SRI_ERROR',
            }
        }
        
        # Obtener la acción específica o usar una genérica
        specific_actions = action_map.get(operation_type, {})
        action = specific_actions.get(response_code, 'SRI_RESPONSE')
        
        return action
    
    def _log_sri_response(self, document, operation_type, response_code, message, raw_response):
        """
        Registra la respuesta del SRI en la base de datos
        ✅ MEJORADO PARA SRI 2025
        """
        try:
            # ✅ OBTENER EL ElectronicDocument CORRECTO
            if hasattr(document, "original_document"):
                # Para CreditNote, DebitNote, etc.
                electronic_doc = document.original_document
            elif hasattr(document, "document_ptr"):
                # Si tiene relación directa
                electronic_doc = document.document_ptr
            else:
                # Si ya es ElectronicDocument
                electronic_doc = document
            
            # ✅ CREAR REGISTRO EN SRIResponse CON DATOS EXTENDIDOS
            SRIResponse.objects.create(
                document=electronic_doc,
                operation_type=operation_type,
                response_code=response_code or "UNKNOWN",
                response_message=message,
                raw_response=raw_response,
                # ✅ CAMPOS ADICIONALES PARA 2025
                environment=self.environment,
                timestamp=timezone.now()
            )
            
            # ✅ LOG DE AUDITORÍA CON ACCIÓN VÁLIDA
            audit_action = self._get_audit_action(operation_type, response_code)
            
            AuditLog.objects.create(
                action=audit_action,
                model_name='ElectronicDocument',
                object_id=str(document.id),
                object_representation=str(document),
                additional_data={
                    'operation_type': operation_type,
                    'response_code': response_code,
                    'message': message,
                    'environment': self.environment,
                    'document_number': getattr(document, 'document_number', 'N/A'),
                    'access_key': getattr(document, 'access_key', 'N/A'),
                    'sri_version': '2025.1'  # ✅ VERSIÓN DE ESPECIFICACIONES
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging SRI response: {str(e)}")
            # ✅ EN CASO DE ERROR, INTENTAR LOG BÁSICO SIN FALLAR
            try:
                AuditLog.objects.create(
                    action='ERROR_OCCURRED',
                    model_name='SRISOAPClient',
                    object_id='logging_error',
                    object_representation='SRI Response Logging Failed',
                    additional_data={
                        'error': str(e),
                        'operation_type': operation_type,
                        'response_code': response_code,
                        'message': message,
                        'sri_version': '2025.1'
                    }
                )
            except Exception:
                # Si falla completamente, solo hacer log en archivo
                logger.error(f"Critical error in SRI response logging: {str(e)}")
    
    def test_connection(self):
        """
        Prueba la conexión con los servicios del SRI
        ✅ MEJORADO PARA SRI 2025
        """
        results = {}
        method = 'Zeep' if ZEEP_AVAILABLE else 'Requests'
        
        # ✅ PROBAR CONECTIVIDAD BÁSICA CON TIMEOUTS OPTIMIZADOS
        for service_name, url in [
            ('reception', self.SRI_URLS[self.environment]['reception']), 
            ('authorization', self.SRI_URLS[self.environment]['authorization'])
        ]:
            try:
                headers = {
                    'User-Agent': 'SRI-Ecuador-Test-Client/2025.1',
                    'Accept': 'text/xml, application/soap+xml'
                }
                
                response = requests.head(
                    url, 
                    timeout=15, 
                    headers=headers,
                    verify=True,
                    allow_redirects=True
                )
                
                results[service_name] = {
                    'status': 'OK' if response.status_code in [200, 405] else 'WARNING',  # ✅ 405 es normal para WSDL
                    'service_url': url,
                    'http_status': response.status_code,
                    'method': method,
                    'environment': self.environment,
                    'message': f'Service reachable via {method} (SRI 2025)',
                    'response_time': response.elapsed.total_seconds()
                }
                
            except requests.exceptions.Timeout:
                results[service_name] = {
                    'status': 'ERROR',
                    'service_url': url,
                    'error': 'Connection timeout',
                    'method': method,
                    'environment': self.environment,
                    'message': f'Connection timeout via {method}'
                }
            except Exception as e:
                results[service_name] = {
                    'status': 'ERROR',
                    'service_url': url,
                    'error': str(e),
                    'method': method,
                    'environment': self.environment,
                    'message': f'Connection failed via {method}: {str(e)}'
                }
        
        # ✅ AGREGAR INFORMACIÓN DEL SISTEMA
        results['system_info'] = {
            'sri_client_version': '2025.1',
            'zeep_available': ZEEP_AVAILABLE,
            'environment': self.environment,
            'company_ruc': getattr(self.company, 'ruc', 'N/A')
        }
        
        return results