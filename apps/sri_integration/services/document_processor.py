# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos - VERSIÓN ACTUALIZADA
Integrado con GlobalCertificateManager para máximo rendimiento multi-empresa
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
    VERSIÓN ACTUALIZADA con GlobalCertificateManager
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
                logger.info(f"🚀 Iniciando procesamiento completo de documento {document.id}")
                
                # Verificar que el certificado esté disponible en el gestor global
                cert_data = self.cert_manager.get_certificate(self.company.id)
                if not cert_data:
                    error_msg = f"Certificate not available for company {self.company.id}. Ensure certificate is properly configured."
                    logger.error(error_msg)
                    return False, error_msg
                
                # Validar certificado
                is_valid, validation_message = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    logger.error(f"Certificate validation failed: {validation_message}")
                    return False, f"Certificate validation failed: {validation_message}"
                
                if "expires in" in validation_message:
                    logger.warning(f"Certificate warning: {validation_message}")
                
                # 1. Generar XML
                logger.info(f"📄 Generando XML para documento {document.id}")
                success, xml_content = self._generate_xml(document)
                if not success:
                    return False, xml_content
                
                # 2. Firmar XML (usando certificado del gestor global)
                logger.info(f"✍️  Firmando XML para documento {document.id}")
                success, signed_xml = self._sign_xml_with_global_manager(document, xml_content)
                if not success:
                    return False, signed_xml
                
                # 3. Enviar al SRI
                logger.info(f"📤 Enviando documento {document.id} al SRI")
                success, sri_message = self._send_to_sri(document, signed_xml)
                if not success:
                    return False, sri_message
                
                # 4. Consultar autorización
                logger.info(f"🔍 Consultando autorización para documento {document.id}")
                success, auth_message = self._check_authorization(document)
                if not success:
                    return False, auth_message
                
                # 5. Generar PDF
                logger.info(f"📋 Generando PDF para documento {document.id}")
                success, pdf_message = self._generate_pdf(document)
                if not success:
                    logger.warning(f"PDF generation failed: {pdf_message}")
                    # No es crítico, continuamos
                
                # 6. Enviar email si está autorizado
                if document.status == 'AUTHORIZED' and send_email:
                    logger.info(f"📧 Enviando email para documento {document.id}")
                    success, email_message = self._send_email(document)
                    if not success:
                        logger.warning(f"Email sending failed: {email_message}")
                        # No es crítico, continuamos
                
                # Log de auditoría
                AuditLog.objects.create(
                    action='PROCESS_COMPLETE',
                    model_name='ElectronicDocument',
                    object_id=str(document.id),
                    object_representation=str(document),
                    additional_data={
                        'status': document.status,
                        'sri_response': document.sri_response,
                        'certificate_manager': 'GlobalCertificateManager',
                        'company_id': self.company.id
                    }
                )
                
                logger.info(f"✅ Documento {document.id} procesado exitosamente con estado: {document.status}")
                return True, f"Document processed successfully with status: {document.status}"
                
        except Exception as e:
            logger.error(f"❌ Error processing document {document.id}: {str(e)}")
            document.status = 'ERROR'
            document.save()
            return False, str(e)
    
    def process_document_legacy(self, document, certificate_password, send_email=True):
        """
        Método legacy para compatibilidad con código existente
        Redirige al nuevo método sin password
        """
        logger.warning(f"Using legacy process_document method for document {document.id}")
        return self.process_document(document, send_email, certificate_password)
    
    def reprocess_document(self, document):
        """
        Reprocesa un documento que falló anteriormente
        VERSIÓN ACTUALIZADA sin requerir password
        """
        try:
            if document.status in ['AUTHORIZED', 'SENT']:
                return False, "Document is already processed"
            
            logger.info(f"🔄 Reprocesando documento {document.id}")
            
            # Resetear estado
            document.status = 'GENERATED'
            document.sri_authorization_code = ''
            document.sri_authorization_date = None
            document.sri_response = {}
            document.save()
            
            # Procesar nuevamente
            return self.process_document(document)
            
        except Exception as e:
            logger.error(f"Error reprocessing document {document.id}: {str(e)}")
            return False, str(e)
    
    def _generate_xml(self, document):
        """
        Genera el XML del documento
        """
        try:
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
                return False, f"Unsupported document type: {document.document_type}"
            
            # Guardar XML
            filename = f"{document.access_key}.xml"
            document.xml_file.save(
                filename,
                ContentFile(xml_content.encode('utf-8')),
                save=True
            )
            
            logger.info(f"✅ XML generado para documento {document.id}")
            return True, xml_content
            
        except Exception as e:
            logger.error(f"Error generating XML for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _sign_xml_with_global_manager(self, document, xml_content):
        """
        Firma el XML usando el GlobalCertificateManager
        NUEVO MÉTODO que no requiere password
        """
        try:
            # Obtener certificado del gestor global
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                return False, f"Certificate not available for company {self.company.id}"
            
            logger.info(f"🔐 Usando certificado cacheado para empresa {self.company.id}")
            
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
            
            logger.info(f"✅ XML firmado para documento {document.id} usando GlobalCertificateManager")
            return True, signed_xml
            
        except Exception as e:
            logger.error(f"Error signing XML for document {document.id}: {str(e)}")
            return False, str(e)
    
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
            
            logger.debug("Iniciando firma XML con implementación personalizada")
            
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
            
            logger.debug("✅ Firma XML completada exitosamente")
            return signed_xml
            
        except Exception as e:
            raise Exception(f"Custom XML signing failed: {str(e)}")
    
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
    
    def _sign_xml_legacy(self, document, xml_content, certificate_password):
        """
        Método legacy de firma XML (para compatibilidad)
        """
        try:
            # Usar el CertificateManager original si es necesario
            from apps.sri_integration.services.certificate_manager import CertificateManager
            
            cert_manager = CertificateManager(self.company)
            cert_manager.load_certificate(certificate_password)
            
            # Validar certificado
            valid, message = cert_manager.validate_certificate()
            if not valid:
                return False, f"Certificate validation failed: {message}"
            
            # Firmar XML
            signed_xml = cert_manager.sign_xml(xml_content, document)
            
            # Guardar XML firmado
            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename,
                ContentFile(signed_xml.encode('utf-8')),
                save=True
            )
            
            document.status = 'SIGNED'
            document.save()
            
            return True, signed_xml
            
        except Exception as e:
            logger.error(f"Error signing XML (legacy) for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _send_to_sri(self, document, signed_xml):
        """
        Envía el documento firmado al SRI
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
            logger.error(f"Error sending document {document.id} to SRI: {str(e)}")
            return False, str(e)
    
    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """
        Consulta la autorización del documento en el SRI
        """
        import time
        
        try:
            sri_client = SRISOAPClient(self.company)
            
            for attempt in range(max_attempts):
                if attempt > 0:
                    logger.info(f"⏳ Esperando {wait_seconds}s antes del intento {attempt + 1}")
                    time.sleep(wait_seconds)
                
                success, message = sri_client.get_document_authorization(document)
                
                if success:
                    logger.info(f"✅ Documento {document.id} autorizado por el SRI")
                    return True, message
                
                # Si el documento aún está en proceso, continuar intentando
                if 'proceso' in message.lower() or 'pendiente' in message.lower():
                    logger.info(f"🔄 Documento {document.id} aún en proceso, intento {attempt + 1}/{max_attempts}")
                    continue
                
                # Si hay error definitivo, parar
                logger.error(f"❌ Error definitivo en autorización: {message}")
                return False, message
            
            logger.warning(f"⏰ Timeout en autorización para documento {document.id}")
            return False, f"Authorization timeout after {max_attempts} attempts"
            
        except Exception as e:
            logger.error(f"Error checking authorization for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _generate_pdf(self, document):
        """
        Genera el PDF del documento
        """
        try:
            pdf_generator = PDFGenerator(document)
            
            if document.document_type == 'INVOICE':
                pdf_content = pdf_generator.generate_invoice_pdf()
            elif document.document_type == 'CREDIT_NOTE':
                pdf_content = pdf_generator.generate_credit_note_pdf()
            elif document.document_type == 'DEBIT_NOTE':
                pdf_content = pdf_generator.generate_debit_note_pdf()
            else:
                # Por ahora solo facturas y notas, expandir según necesidad
                logger.warning(f"PDF generation not implemented for {document.document_type}")
                return False, f"PDF generation not implemented for {document.document_type}"
            
            # Guardar PDF
            filename = f"{document.access_key}.pdf"
            document.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
            
            logger.info(f"✅ PDF generado para documento {document.id}")
            return True, "PDF generated successfully"
            
        except Exception as e:
            logger.error(f"Error generating PDF for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _send_email(self, document):
        """
        Envía el documento por email al cliente
        """
        try:
            if not document.customer_email:
                return False, "Customer email not provided"
            
            if not self.sri_config.email_enabled:
                return False, "Email sending is disabled"
            
            email_service = EmailService(self.company)
            success, message = email_service.send_document_email(document)
            
            if success:
                document.email_sent = True
                document.email_sent_date = timezone.now()
                document.save()
                logger.info(f"✅ Email enviado para documento {document.id}")
            else:
                logger.warning(f"⚠️  Error enviando email para documento {document.id}: {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error sending email for document {document.id}: {str(e)}")
            return False, str(e)
    
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
            if not sri_config.reception_url or not sri_config.authorization_url:
                validation_errors.append("SRI URLs not configured")
            
            if validation_errors:
                return False, validation_errors
            
            return True, "Company setup is valid"
            
        except Exception as e:
            logger.error(f"Error validating company setup: {str(e)}")
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
                    'error_documents': company_docs.filter(status='ERROR').count(),
                    'processing_method': 'GlobalCertificateManager'
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {'error': str(e)}
    
    def reload_certificate(self):
        """
        Recarga el certificado de la empresa en el gestor global
        """
        try:
            success = self.cert_manager.reload_certificate(self.company.id)
            if success:
                logger.info(f"✅ Certificado recargado para empresa {self.company.id}")
                return True, "Certificate reloaded successfully"
            else:
                logger.error(f"❌ Error recargando certificado para empresa {self.company.id}")
                return False, "Failed to reload certificate"
        except Exception as e:
            logger.error(f"Error reloading certificate: {str(e)}")
            return False, str(e)