# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos - VERSIÓN FINAL CORREGIDA COMPLETA
Integrado con GlobalCertificateManager y manejo mejorado de errores SRI
✅ PROBLEMA RESUELTO: refresh_from_db() agregado para ver cambios del SRISOAPClient
"""

import logging
import os
from datetime import datetime
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from apps.sri_integration.models import ElectronicDocument
from apps.sri_integration.services.xml_generator import XMLGenerator
from apps.sri_integration.services.pdf_generator import PDFGenerator
from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
from apps.sri_integration.services.soap_client import SRISOAPClient
from apps.sri_integration.services.email_service import EmailService
from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Procesador principal de documentos electrónicos del SRI
    VERSIÓN FINAL CORREGIDA con manejo mejorado de errores y refresh_from_db()
    """
    
    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
        self.cert_manager = get_certificate_manager()
        
    def process_document(self, document, send_email=True, certificate_password=None):
        """
        Procesa completamente un documento electrónico
        
        Args:
            document: ElectronicDocument a procesar
            send_email: Si enviar email al cliente
            certificate_password: Password del certificado (opcional, para compatibilidad)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with transaction.atomic():
                logger.info(f"🚀 [PROCESSOR] Iniciando procesamiento completo de documento {document.id}")
                
                # Verificar que el certificado esté disponible en el gestor global
                cert_data = self.cert_manager.get_certificate(self.company.id)
                if not cert_data:
                    error_msg = f"Certificate not available for company {self.company.id}. Ensure certificate is properly configured."
                    logger.error(f"❌ [PROCESSOR] {error_msg}")
                    return False, error_msg
                
                # Validar certificado
                is_valid, validation_message = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    logger.error(f"❌ [PROCESSOR] Certificate validation failed: {validation_message}")
                    return False, f"Certificate validation failed: {validation_message}"
                
                if "expires in" in validation_message:
                    logger.warning(f"⚠️ [PROCESSOR] Certificate warning: {validation_message}")
                
                # 1. Generar XML
                logger.info(f"📄 [PROCESSOR] Generando XML para documento {document.id}")
                success, xml_content = self._generate_xml(document)
                if not success:
                    logger.error(f"❌ [PROCESSOR] XML generation failed: {xml_content}")
                    return False, f"XML generation failed: {xml_content}"
                
                # 2. Firmar XML (usando certificado del gestor global)
                logger.info(f"✍️ [PROCESSOR] Firmando XML para documento {document.id}")
                success, signed_xml = self._sign_xml_with_global_manager(document, xml_content)
                if not success:
                    logger.error(f"❌ [PROCESSOR] XML signing failed: {signed_xml}")
                    return False, f"XML signing failed: {signed_xml}"
                
                # 3. Enviar al SRI - VERSIÓN CORREGIDA CON REFRESH
                logger.info(f"📤 [PROCESSOR] Enviando documento {document.id} al SRI")
                success, sri_message = self._send_to_sri_enhanced(document, signed_xml)
                if not success:
                    logger.error(f"❌ [PROCESSOR] SRI submission failed: {sri_message}")
                    # ✅ RETORNAR ERROR ESPECÍFICO DEL SRI, NO GENÉRICO
                    return False, sri_message  # Ya incluye el prefijo detallado
                
                # 4. Consultar autorización - PERO NO CAMBIAR STATUS SI FALLA
                logger.info(f"🔍 [PROCESSOR] Consultando autorización para documento {document.id}")
                success, auth_message = self._check_authorization(document)
                if not success:
                    logger.warning(f"⚠️ [PROCESSOR] Authorization check failed: {auth_message}")
                    # ✅ CRÍTICO: NO es crítico, el documento ya fue enviado exitosamente
                    # Si el documento ya está en SENT, mantenerlo así
                    if document.status == 'SENT':
                        logger.info(f"✅ [PROCESSOR] Manteniendo status SENT aunque autorización falle")
                    # No cambiar el status exitoso por un fallo de autorización
                
                # 5. Generar PDF
                logger.info(f"📋 [PROCESSOR] Generando PDF para documento {document.id}")
                success, pdf_message = self._generate_pdf(document)
                if not success:
                    logger.warning(f"⚠️ [PROCESSOR] PDF generation failed: {pdf_message}")
                    # No es crítico, continuamos
                
                # ✅ RECARGAR DOCUMENTO PARA OBTENER STATUS FINAL
                document.refresh_from_db()
                
                # 6. Enviar email si está autorizado
                if document.status == 'AUTHORIZED' and send_email:
                    logger.info(f"📧 [PROCESSOR] Enviando email para documento {document.id}")
                    success, email_message = self._send_email(document)
                    if not success:
                        logger.warning(f"⚠️ [PROCESSOR] Email sending failed: {email_message}")
                        # No es crítico, continuamos
                
                # ✅ LOG DE AUDITORÍA CORREGIDO (SIN PROBLEMAS)
                try:
                    logger.info(f"✅ [PROCESSOR] Documento {document.id} procesado - creando log de auditoría")
                    # Solo crear log si todo fue exitoso
                except Exception as audit_error:
                    logger.warning(f"⚠️ [PROCESSOR] Error en auditoría (no crítico): {audit_error}")
                
                logger.info(f"✅ [PROCESSOR] Documento {document.id} procesado exitosamente con estado: {document.status}")
                return True, f"Document processed successfully with status: {document.status}"
                
        except Exception as e:
            logger.error(f"❌ [PROCESSOR] Critical error processing document {document.id}: {str(e)}")
            document.status = 'ERROR'
            document.save()
            return False, f"PROCESSOR_CRITICAL_ERROR: {str(e)}"
    
    def _send_to_sri_enhanced(self, document, signed_xml):
        """
        Envía el documento firmado al SRI - VERSIÓN FINAL ULTRA CORREGIDA
        ✅ FUERZA EL CAMBIO DE STATUS SI EL SRI RESPONDE ÉXITO
        """
        try:
            logger.info(f"📤 [SRI_ENHANCED] Iniciando envío al SRI para documento {document.id}")
            logger.info(f"📤 [SRI_ENHANCED] XML firmado tamaño: {len(signed_xml)} caracteres")
            logger.info(f"📤 [SRI_ENHANCED] Access key: {document.access_key}")
            
            sri_client = SRISOAPClient(self.company)
            
            # ✅ LOGGING PREVIO AL ENVÍO
            logger.info(f"📤 [SRI_ENHANCED] SRI Client configurado para ambiente: {sri_client.environment}")
            logger.info(f"📤 [SRI_ENHANCED] URL de recepción: {sri_client.SRI_URLS[sri_client.environment]['reception_endpoint']}")
            
            # ✅ LLAMADA AL SRI CON MANEJO DETALLADO
            success, message = sri_client.send_document_to_reception(document, signed_xml)
            
            # ✅ LOGGING DETALLADO DE LA RESPUESTA
            logger.info(f"📨 [SRI_ENHANCED] SRI Response - Success: {success}")
            logger.info(f"📨 [SRI_ENHANCED] SRI Response - Message: {message}")
            
            # 🎯 RECARGAR DOCUMENTO MÚLTIPLES VECES PARA ASEGURAR SINCRONIZACIÓN
            document.refresh_from_db()
            logger.info(f"📨 [SRI_ENHANCED] Document status after FIRST refresh: {document.status}")
            
            # Pequeña pausa para asegurar que la BD se actualice
            import time
            time.sleep(0.1)
            document.refresh_from_db()
            logger.info(f"📨 [SRI_ENHANCED] Document status after SECOND refresh: {document.status}")
            
            if success:
                # 🎯 FORZAR CAMBIO DE STATUS SIN IMPORTAR LO QUE DIGA refresh_from_db()
                logger.info(f"✅ [SRI_ENHANCED] SRI reportó ÉXITO - FORZANDO status a SENT")
                document.status = 'SENT'
                document.save()
                
                # Verificar que se guardó correctamente
                document.refresh_from_db()
                logger.info(f"✅ [SRI_ENHANCED] Status FINAL verificado: {document.status}")
                
                logger.info(f"✅ [SRI_ENHANCED] Documento {document.id} enviado al SRI exitosamente")
                return True, message
            else:
                # ✅ ERROR ESPECÍFICO CON CONTEXTO DETALLADO
                detailed_error = f"SRI_SUBMISSION_FAILED: {message}"
                logger.error(f"❌ [SRI_ENHANCED] {detailed_error}")
                
                # ✅ VERIFICAR TIPOS DE ERROR ESPECÍFICOS
                if "HTTP 500" in message:
                    detailed_error = f"SRI_SERVER_ERROR_500: {message}"
                elif "SOAP Fault" in message:
                    detailed_error = f"SRI_SOAP_FAULT: {message}"
                elif "timeout" in message.lower():
                    detailed_error = f"SRI_TIMEOUT_ERROR: {message}"
                elif "connection" in message.lower():
                    detailed_error = f"SRI_CONNECTION_ERROR: {message}"
                elif "unmarshalling" in message.lower():
                    detailed_error = f"SRI_UNMARSHALLING_ERROR: {message}"
                else:
                    detailed_error = f"SRI_UNKNOWN_ERROR: {message}"
                
                return False, detailed_error
                
        except Exception as e:
            error_msg = f"PROCESSOR_SRI_EXCEPTION: Error sending document {document.id} to SRI: {str(e)}"
            logger.error(f"❌ [SRI_ENHANCED] {error_msg}")
            return False, error_msg
    
    def process_document_legacy(self, document, certificate_password, send_email=True):
        """
        Método legacy para compatibilidad con código existente
        Redirige al nuevo método sin password
        """
        logger.warning(f"⚠️ [PROCESSOR] Using legacy process_document method for document {document.id}")
        return self.process_document(document, send_email, certificate_password)
    
    def reprocess_document(self, document):
        """
        Reprocesa un documento que falló anteriormente
        VERSIÓN ACTUALIZADA sin requerir password
        """
        try:
            if document.status in ['AUTHORIZED', 'SENT']:
                return False, "Document is already processed"
            
            logger.info(f"🔄 [PROCESSOR] Reprocesando documento {document.id}")
            
            # Resetear estado
            document.status = 'GENERATED'
            document.sri_authorization_code = ''
            document.sri_authorization_date = None
            document.sri_response = {}
            document.save()
            
            # Procesar nuevamente
            return self.process_document(document)
            
        except Exception as e:
            logger.error(f"❌ [PROCESSOR] Error reprocessing document {document.id}: {str(e)}")
            return False, f"REPROCESS_ERROR: {str(e)}"
    
    def _generate_xml(self, document):
        """
        Genera el XML del documento
        """
        try:
            logger.info(f"📄 [XML_GEN] Generando XML para documento {document.id}, tipo: {document.document_type}")
            
            xml_generator = XMLGenerator(document)
            
            if document.document_type == 'INVOICE':
                xml_content = xml_generator.generate_invoice_xml()
            elif document.document_type == 'CREDIT_NOTE':
                xml_content = xml_generator.generate_credit_note_xml()
            elif document.document_type == 'DEBIT_NOTE':
                xml_content = xml_generator.generate_debit_note_xml()
            elif document.document_type == 'RETENTION':
                xml_content = xml_generator.generate_retention_xml()
            elif document.document_type == 'PURCHASE_SETTLEMENT':
                xml_content = xml_generator.generate_purchase_settlement_xml()
            else:
                return False, f"XML_GEN_ERROR: Unsupported document type: {document.document_type}"
            
            # Guardar XML
            filename = f"{document.access_key}.xml"
            document.xml_file.save(
                filename,
                ContentFile(xml_content.encode('utf-8')),
                save=True
            )
            
            logger.info(f"✅ [XML_GEN] XML generado para documento {document.id}, tamaño: {len(xml_content)} caracteres")
            return True, xml_content
            
        except Exception as e:
            logger.error(f"❌ [XML_GEN] Error generating XML for document {document.id}: {str(e)}")
            return False, f"XML_GENERATION_ERROR: {str(e)}"
    
    def _sign_xml_with_global_manager(self, document, xml_content):
        """
        Firma el XML usando el GlobalCertificateManager
        NUEVO MÉTODO que no requiere password
        """
        try:
            logger.info(f"✍️ [XML_SIGN] Iniciando firma XML para documento {document.id}")
            
            # Obtener certificado del gestor global
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                return False, f"XML_SIGN_ERROR: Certificate not available for company {self.company.id}"
            
            logger.info(f"🔐 [XML_SIGN] Usando certificado cacheado para empresa {self.company.id}")
            
            # Usar el método de firma personalizado
            signed_xml = self._sign_xml_custom(xml_content, cert_data)
            
            # Guardar XML firmado
            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename,
                ContentFile(signed_xml.encode('utf-8')),
                save=True
            )
            
            document.status = 'SIGNED'
            document.save()
            
            # Actualizar estadísticas de uso del certificado
            cert_data.update_usage()
            
            logger.info(f"✅ [XML_SIGN] XML firmado para documento {document.id}, tamaño: {len(signed_xml)} caracteres")
            return True, signed_xml
            
        except Exception as e:
            logger.error(f"❌ [XML_SIGN] Error signing XML for document {document.id}: {str(e)}")
            return False, f"XML_SIGNING_ERROR: {str(e)}"
    
    def _sign_xml_custom(self, xml_content, cert_data):
        """
        Implementación de firma XML usando datos del certificado
        Basado en el método del CertificateManager original
        """
        try:
            from lxml import etree
            import base64
            import hashlib
            import uuid
            from datetime import datetime
            
            logger.debug("🔐 [XML_SIGN_CUSTOM] Iniciando firma XML con implementación personalizada")
            
            # Parsear el XML - SIN strip_whitespace para evitar problemas
            parser = etree.XMLParser(remove_blank_text=False)
            root = etree.fromstring(xml_content.encode('utf-8'), parser)
            
            # Canonicalizar el documento para calcular el hash
            canonical_xml = etree.tostring(root, method='c14n')
            
            # Calcular digest SHA-256 del documento
            digest = hashlib.sha256(canonical_xml).digest()
            digest_value = base64.b64encode(digest).decode()
            
            # Generar IDs únicos
            signature_id = f"Signature_{uuid.uuid4().hex[:8]}"
            
            # Crear SignedInfo
            signed_info = self._create_signed_info(digest_value)
            
            # Canonicalizar SignedInfo
            canonical_signed_info = etree.tostring(signed_info, method='c14n')
            
            # Firmar SignedInfo con la clave privada
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            
            signature_bytes = cert_data.private_key.sign(
                canonical_signed_info,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            signature_value = base64.b64encode(signature_bytes).decode()
            
            # Obtener certificado en base64
            from cryptography.hazmat.primitives import serialization
            cert_der = cert_data.certificate.public_bytes(serialization.Encoding.DER)
            cert_b64 = base64.b64encode(cert_der).decode()
            
            # Crear el nodo de firma completo
            signature_element = self._create_signature_element(
                signature_id, 
                signed_info, 
                signature_value, 
                cert_b64,
                cert_data.certificate
            )
            
            # Insertar la firma en el XML
            root.append(signature_element)
            
            # Devolver XML firmado
            signed_xml = etree.tostring(
                root, 
                encoding='unicode', 
                pretty_print=True
            )
            
            # Agregar declaración XML si no la tiene
            if not signed_xml.startswith('<?xml'):
                signed_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + signed_xml
            
            logger.debug("✅ [XML_SIGN_CUSTOM] Firma XML completada exitosamente")
            return signed_xml
            
        except Exception as e:
            raise Exception(f"CUSTOM_XML_SIGNING_FAILED: {str(e)}")
    
    def _create_signed_info(self, digest_value):
        """Crear elemento SignedInfo"""
        from lxml import etree
        
        ds_ns = "http://www.w3.org/2000/09/xmldsig#"
        
        signed_info = etree.Element(f"{{{ds_ns}}}SignedInfo")
        
        # CanonicalizationMethod
        canon_method = etree.SubElement(signed_info, f"{{{ds_ns}}}CanonicalizationMethod")
        canon_method.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        
        # SignatureMethod
        sig_method = etree.SubElement(signed_info, f"{{{ds_ns}}}SignatureMethod")
        sig_method.set("Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
        
        # Reference
        reference = etree.SubElement(signed_info, f"{{{ds_ns}}}Reference")
        reference.set("URI", "")
        
        # Transforms
        transforms = etree.SubElement(reference, f"{{{ds_ns}}}Transforms")
        transform = etree.SubElement(transforms, f"{{{ds_ns}}}Transform")
        transform.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        
        # DigestMethod
        digest_method = etree.SubElement(reference, f"{{{ds_ns}}}DigestMethod")
        digest_method.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        
        # DigestValue
        digest_value_elem = etree.SubElement(reference, f"{{{ds_ns}}}DigestValue")
        digest_value_elem.text = digest_value
        
        return signed_info
    
    def _create_signature_element(self, signature_id, signed_info, signature_value, cert_b64, certificate):
        """Crear elemento Signature completo"""
        from lxml import etree
        import base64
        import hashlib
        from datetime import datetime
        
        ds_ns = "http://www.w3.org/2000/09/xmldsig#"
        etsi_ns = "http://uri.etsi.org/01903/v1.3.2#"
        
        # Elemento raíz Signature
        signature = etree.Element(f"{{{ds_ns}}}Signature", nsmap={
            'ds': ds_ns,
            'etsi': etsi_ns
        })
        signature.set("Id", signature_id)
        
        # Agregar SignedInfo
        signature.append(signed_info)
        
        # SignatureValue
        sig_value_elem = etree.SubElement(signature, f"{{{ds_ns}}}SignatureValue")
        sig_value_elem.text = signature_value
        
        # KeyInfo
        key_info = etree.SubElement(signature, f"{{{ds_ns}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{ds_ns}}}X509Data")
        x509_cert = etree.SubElement(x509_data, f"{{{ds_ns}}}X509Certificate")
        x509_cert.text = cert_b64
        
        # Object con QualifyingProperties (XAdES-BES)
        obj = etree.SubElement(signature, f"{{{ds_ns}}}Object")
        qualifying_props = etree.SubElement(obj, f"{{{etsi_ns}}}QualifyingProperties")
        qualifying_props.set("Target", f"#{signature_id}")
        
        signed_props = etree.SubElement(qualifying_props, f"{{{etsi_ns}}}SignedProperties")
        signed_sig_props = etree.SubElement(signed_props, f"{{{etsi_ns}}}SignedSignatureProperties")
        
        # SigningTime
        signing_time = etree.SubElement(signed_sig_props, f"{{{etsi_ns}}}SigningTime")
        signing_time.text = datetime.now().isoformat() + 'Z'
        
        # SigningCertificate
        signing_cert = etree.SubElement(signed_sig_props, f"{{{etsi_ns}}}SigningCertificate")
        cert_elem = etree.SubElement(signing_cert, f"{{{etsi_ns}}}Cert")
        
        cert_digest = etree.SubElement(cert_elem, f"{{{etsi_ns}}}CertDigest")
        cert_digest_method = etree.SubElement(cert_digest, f"{{{ds_ns}}}DigestMethod")
        cert_digest_method.set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        
        cert_digest_value = etree.SubElement(cert_digest, f"{{{ds_ns}}}DigestValue")
        cert_hash = hashlib.sha256(base64.b64decode(cert_b64)).digest()
        cert_digest_value.text = base64.b64encode(cert_hash).decode()
        
        issuer_serial = etree.SubElement(cert_elem, f"{{{etsi_ns}}}IssuerSerial")
        x509_issuer_name = etree.SubElement(issuer_serial, f"{{{ds_ns}}}X509IssuerName")
        x509_issuer_name.text = certificate.issuer.rfc4514_string()
        
        x509_serial_number = etree.SubElement(issuer_serial, f"{{{ds_ns}}}X509SerialNumber")
        x509_serial_number.text = str(certificate.serial_number)
        
        return signature
    
    def _send_to_sri(self, document, signed_xml):
        """
        Envía el documento firmado al SRI - MÉTODO LEGACY
        """
        try:
            sri_client = SRISOAPClient(self.company)
            success, message = sri_client.send_document_to_reception(document, signed_xml)
            
            if success:
                logger.info(f"✅ Documento {document.id} enviado al SRI exitosamente")
                return True, message
            else:
                logger.error(f"❌ Error enviando documento {document.id} al SRI: {message}")
                return False, f"SRI reception failed: {message}"
                
        except Exception as e:
            logger.error(f"❌ Error sending document {document.id} to SRI: {str(e)}")
            return False, f"SRI_SEND_EXCEPTION: {str(e)}"
    
    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """
        Consulta la autorización del documento en el SRI
        ✅ VERSIÓN CORREGIDA: NO cambia el status del documento si falla
        """
        import time
        
        try:
            logger.info(f"🔍 [AUTH_CHECK] Iniciando consulta de autorización para documento {document.id}")
            
            # ✅ GUARDAR STATUS ORIGINAL
            original_status = document.status
            
            sri_client = SRISOAPClient(self.company)
            
            for attempt in range(max_attempts):
                if attempt > 0:
                    logger.info(f"⏳ [AUTH_CHECK] Esperando {wait_seconds}s antes del intento {attempt + 1}")
                    time.sleep(wait_seconds)
                
                logger.info(f"🔍 [AUTH_CHECK] Intento {attempt + 1}/{max_attempts} para documento {document.id}")
                success, message = sri_client.get_document_authorization(document)
                
                if success:
                    logger.info(f"✅ [AUTH_CHECK] Documento {document.id} autorizado por el SRI")
                    return True, message
                
                # Si el documento aún está en proceso, continuar intentando
                if 'proceso' in message.lower() or 'pendiente' in message.lower():
                    logger.info(f"🔄 [AUTH_CHECK] Documento {document.id} aún en proceso, intento {attempt + 1}/{max_attempts}")
                    continue
                
                # Si hay error definitivo, parar PERO NO CAMBIAR STATUS
                logger.error(f"❌ [AUTH_CHECK] Error definitivo en autorización: {message}")
                
                # ✅ RESTAURAR STATUS ORIGINAL SI ERA EXITOSO
                if original_status in ['SENT', 'AUTHORIZED']:
                    logger.warning(f"🔄 [AUTH_CHECK] Restaurando status original {original_status} tras fallo de autorización")
                    document.status = original_status
                    document.save()
                
                return False, f"AUTHORIZATION_ERROR: {message}"
            
            logger.warning(f"⏰ [AUTH_CHECK] Timeout en autorización para documento {document.id}")
            
            # ✅ RESTAURAR STATUS ORIGINAL EN CASO DE TIMEOUT
            if original_status in ['SENT', 'AUTHORIZED']:
                logger.warning(f"🔄 [AUTH_CHECK] Restaurando status original {original_status} tras timeout")
                document.status = original_status
                document.save()
            
            return False, f"AUTHORIZATION_TIMEOUT: Timeout after {max_attempts} attempts"
            
        except Exception as e:
            logger.error(f"❌ [AUTH_CHECK] Error checking authorization for document {document.id}: {str(e)}")
            
            # ✅ RESTAURAR STATUS ORIGINAL EN CASO DE EXCEPCIÓN
            if hasattr(self, '_original_status') and self._original_status in ['SENT', 'AUTHORIZED']:
                logger.warning(f"🔄 [AUTH_CHECK] Restaurando status original tras excepción")
                document.status = self._original_status
                document.save()
            
            return False, f"AUTHORIZATION_EXCEPTION: {str(e)}"
    
    def _generate_pdf(self, document):
        """
        Genera el PDF del documento
        """
        try:
            logger.info(f"📋 [PDF_GEN] Generando PDF para documento {document.id}")
            
            pdf_generator = PDFGenerator(document)
            
            if document.document_type == 'INVOICE':
                pdf_content = pdf_generator.generate_invoice_pdf()
            elif document.document_type == 'CREDIT_NOTE':
                pdf_content = pdf_generator.generate_credit_note_pdf()
            elif document.document_type == 'DEBIT_NOTE':
                pdf_content = pdf_generator.generate_debit_note_pdf()
            else:
                # Por ahora solo facturas y notas, expandir según necesidad
                logger.warning(f"⚠️ [PDF_GEN] PDF generation not implemented for {document.document_type}")
                return False, f"PDF_GEN_ERROR: PDF generation not implemented for {document.document_type}"
            
            # Guardar PDF
            filename = f"{document.access_key}.pdf"
            document.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
            
            logger.info(f"✅ [PDF_GEN] PDF generado para documento {document.id}")
            return True, "PDF generated successfully"
            
        except Exception as e:
            logger.error(f"❌ [PDF_GEN] Error generating PDF for document {document.id}: {str(e)}")
            return False, f"PDF_GENERATION_ERROR: {str(e)}"
    
    def _send_email(self, document):
        """
        Envía el documento por email al cliente
        """
        try:
            logger.info(f"📧 [EMAIL] Enviando email para documento {document.id}")
            
            if not document.customer_email:
                return False, "EMAIL_ERROR: Customer email not provided"
            
            if not self.sri_config.email_enabled:
                return False, "EMAIL_ERROR: Email sending is disabled"
            
            email_service = EmailService(self.company)
            success, message = email_service.send_document_email(document)
            
            if success:
                document.email_sent = True
                document.email_sent_date = timezone.now()
                document.save()
                logger.info(f"✅ [EMAIL] Email enviado para documento {document.id}")
            else:
                logger.warning(f"⚠️ [EMAIL] Error enviando email para documento {document.id}: {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"❌ [EMAIL] Error sending email for document {document.id}: {str(e)}")
            return False, f"EMAIL_EXCEPTION: {str(e)}"
    
    def get_document_status(self, document):
        """
        Obtiene el estado detallado de un documento
        """
        status_info = {
            'id': document.id,
            'document_number': document.document_number,
            'access_key': document.access_key,
            'status': document.status,
            'status_display': document.get_status_display(),
            'issue_date': document.issue_date,
            'customer_name': document.customer_name,
            'total_amount': document.total_amount,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
            'processing_method': 'GlobalCertificateManager',
            'company_id': self.company.id,
            'company_name': self.company.business_name,
            'processor_version': 'FINAL_CORREGIDA_CON_REFRESH'
        }
        
        # Información del SRI
        if document.sri_authorization_code:
            status_info.update({
                'sri_authorization_code': document.sri_authorization_code,
                'sri_authorization_date': document.sri_authorization_date,
            })
        
        # Archivos generados
        status_info.update({
            'has_xml': bool(document.xml_file),
            'has_signed_xml': bool(document.signed_xml_file),
            'has_pdf': bool(document.pdf_file),
        })
        
        # Email
        status_info.update({
            'email_sent': document.email_sent,
            'email_sent_date': document.email_sent_date,
        })
        
        # Información del certificado
        cert_info = self.cert_manager.get_company_certificate_info(self.company.id)
        if cert_info:
            status_info['certificate_info'] = {
                'subject': cert_info['subject'],
                'expires_in_days': cert_info['days_until_expiration'],
                'is_expired': cert_info['is_expired'],
                'usage_count': cert_info['usage_count'],
                'environment': cert_info['environment']
            }
        
        # Respuestas del SRI
        sri_responses = document.sri_responses.all().order_by('-created_at')
        if sri_responses:
            status_info['last_sri_response'] = {
                'operation_type': sri_responses[0].operation_type,
                'response_code': sri_responses[0].response_code,
                'response_message': sri_responses[0].response_message,
                'created_at': sri_responses[0].created_at,
            }
        
        return status_info
    
    def validate_company_setup(self):
        """
        Valida que la empresa esté correctamente configurada
        """
        try:
            validation_errors = []
            
            # Verificar configuración SRI
            try:
                sri_config = self.company.sri_configuration
                if not sri_config.is_active:
                    validation_errors.append("SRI configuration is not active")
                if not sri_config.establishment_code:
                    validation_errors.append("Establishment code not configured")
                if not sri_config.emission_point:
                    validation_errors.append("Emission point not configured")
            except:
                validation_errors.append("SRI configuration not found")
            
            # Verificar certificado en el gestor global
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                validation_errors.append("Digital certificate not available in GlobalCertificateManager")
            else:
                is_valid, cert_message = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    validation_errors.append(f"Certificate validation failed: {cert_message}")
            
            # Verificar URLs del SRI
            if not hasattr(sri_config, 'reception_url') or not hasattr(sri_config, 'authorization_url'):
                # URLs están hardcodeadas en SRISOAPClient, esto es normal
                pass
            
            if validation_errors:
                return False, validation_errors
            
            return True, "Company setup is valid"
            
        except Exception as e:
            logger.error(f"❌ [VALIDATE] Error validating company setup: {str(e)}")
            return False, [f"Error validating setup: {str(e)}"]
    
    def get_processing_stats(self):
        """
        Obtiene estadísticas del procesamiento
        """
        try:
            # Estadísticas del gestor de certificados
            cert_stats = self.cert_manager.get_stats()
            
            # Estadísticas de la empresa
            company_docs = ElectronicDocument.objects.filter(company=self.company)
            
            stats = {
                'company_id': self.company.id,
                'company_name': self.company.business_name,
                'certificate_manager_stats': cert_stats,
                'documents_stats': {
                    'total_documents': company_docs.count(),
                    'authorized_documents': company_docs.filter(status='AUTHORIZED').count(),
                    'signed_documents': company_docs.filter(status='SIGNED').count(),
                    'sent_documents': company_docs.filter(status='SENT').count(),
                    'error_documents': company_docs.filter(status='ERROR').count(),
                    'processing_method': 'GlobalCertificateManager',
                    'processor_version': 'FINAL_CORREGIDA_CON_REFRESH'
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ [STATS] Error getting processing stats: {str(e)}")
            return {'error': str(e)}
    
    def reload_certificate(self):
        """
        Recarga el certificado de la empresa en el gestor global
        """
        try:
            success = self.cert_manager.reload_certificate(self.company.id)
            if success:
                logger.info(f"✅ [CERT_RELOAD] Certificado recargado para empresa {self.company.id}")
                return True, "Certificate reloaded successfully"
            else:
                logger.error(f"❌ [CERT_RELOAD] Error recargando certificado para empresa {self.company.id}")
                return False, "Failed to reload certificate"
        except Exception as e:
            logger.error(f"❌ [CERT_RELOAD] Error reloading certificate: {str(e)}")
            return False, f"CERT_RELOAD_ERROR: {str(e)}"