# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos - VERSIÓN CORREGIDA FINAL
CORRIGE: No modificar XML después de firmar - Resuelve Error 39 FIRMA INVALIDA
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone as django_timezone
from apps.sri_integration.models import ElectronicDocument
from apps.sri_integration.services.xml_generator import XMLGenerator
from apps.sri_integration.services.pdf_generator import PDFGenerator
from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
from apps.sri_integration.services.soap_client import SRISOAPClient
from apps.sri_integration.services.email_service import EmailService
from apps.core.models import AuditLog

# Imports para firma XAdES-BES
from lxml import etree
import base64
import hashlib
import uuid
import re
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Procesador principal de documentos electrónicos del SRI
    VERSIÓN CORREGIDA: NO modifica el XML después de firmarlo
    """
    
    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
        self.cert_manager = get_certificate_manager()
        
    def process_document(self, document, send_email=True, certificate_password=None):
        """Procesa completamente un documento electrónico"""
        try:
            with transaction.atomic():
                logger.info(f"Iniciando procesamiento de documento {document.id}")
                
                # Verificar certificado disponible
                cert_data = self.cert_manager.get_certificate(self.company.id)
                if not cert_data:
                    error_msg = f"Certificate not available for company {self.company.id}"
                    logger.error(error_msg)
                    return False, error_msg
                
                # Validar certificado
                is_valid, validation_message = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    logger.error(f"Certificate validation failed: {validation_message}")
                    return False, f"Certificate validation failed: {validation_message}"
                
                # Verificar tipo de certificado
                cert_check_success, cert_check_message = self._verify_certificate_type_universal(cert_data)
                if not cert_check_success:
                    logger.error(f"Certificate type check failed: {cert_check_message}")
                    return False, cert_check_message
                
                # 1. Generar XML
                logger.info(f"Generando XML para documento {document.id}")
                success, xml_content = self._generate_xml(document)
                if not success:
                    logger.error(f"XML generation failed: {xml_content}")
                    return False, f"XML generation failed: {xml_content}"
                
                # 2. Firmar XML con estructura corregida
                logger.info(f"Firmando XML para documento {document.id}")
                success, signed_xml = self._sign_xml_corrected(document, xml_content)
                if not success:
                    logger.error(f"XML signing failed: {signed_xml}")
                    return False, f"XML signing failed: {signed_xml}"
                
                # 3. Enviar al SRI
                logger.info(f"Enviando documento {document.id} al SRI")
                success, sri_message = self._send_to_sri_enhanced(document, signed_xml)
                if not success:
                    logger.error(f"SRI submission failed: {sri_message}")
                    return False, sri_message
                
                # 4. Consultar autorización
                logger.info(f"Consultando autorización para documento {document.id}")
                success, auth_message = self._check_authorization(document)
                if not success:
                    logger.warning(f"Authorization check failed: {auth_message}")
                    if document.status == 'SENT':
                        logger.info(f"Manteniendo status SENT aunque autorización falle")
                
                # 5. Generar PDF
                success, pdf_message = self._generate_pdf(document)
                if not success:
                    logger.warning(f"PDF generation failed: {pdf_message}")
                
                # Recargar documento
                document.refresh_from_db()
                
                # 6. Enviar email si está autorizado
                if document.status == 'AUTHORIZED' and send_email:
                    logger.info(f"Enviando email para documento {document.id}")
                    self._send_email(document)
                
                logger.info(f"Documento {document.id} procesado con estado: {document.status}")
                return True, f"Document processed successfully with status: {document.status}"
                
        except Exception as e:
            logger.error(f"Critical error processing document {document.id}: {str(e)}")
            document.status = 'ERROR'
            document.save()
            return False, f"PROCESSOR_CRITICAL_ERROR: {str(e)}"
    
    def _verify_certificate_type_universal(self, cert_data):
        """Verificar certificado de manera tolerante"""
        try:
            certificate = cert_data.certificate
            issuer = certificate.issuer.rfc4514_string()
            logger.info(f"Proveedor del certificado: {issuer}")
            
            # Verificar Key Usage
            try:
                key_usage = certificate.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                ).value
                
                if key_usage.digital_signature:
                    logger.info("Certificate has Digital Signature capability")
                    return True, "Certificate valid for digital signature"
                else:
                    logger.error("Certificate does NOT have Digital Signature capability")
                    return False, "Certificate must have Digital Signature key usage for XML signing"
                    
            except x509.ExtensionNotFound:
                logger.warning("Key Usage extension not found - proceeding anyway")
                return True, "Certificate Key Usage extension not found (proceeding anyway)"
            
            # Verificar validez temporal
            now = datetime.now(timezone.utc)
            if certificate.not_valid_after < now:
                return False, f"Certificate expired on {certificate.not_valid_after}"
            
            if certificate.not_valid_before > now:
                return False, f"Certificate not valid until {certificate.not_valid_before}"
            
            return True, "Certificate validation passed"
                
        except Exception as e:
            logger.error(f"Error verifying certificate type: {e}")
            return False, f"Certificate verification failed: {str(e)}"
    
    def _sign_xml_corrected(self, document, xml_content):
        """Firma el XML SIN modificaciones posteriores"""
        try:
            logger.info(f"Iniciando firma XML corregida para documento {document.id}")
            
            # Obtener certificado
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                return False, "Certificate not available"
            
            # Firmar con implementación corregida
            signed_xml = self._create_xades_bes_signature_fixed(xml_content, cert_data)
            
            # Guardar XML firmado
            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename,
                ContentFile(signed_xml.encode('utf-8')),
                save=True
            )
            
            document.status = 'SIGNED'
            document.save()
            
            cert_data.update_usage()
            
            logger.info(f"XML firmado correctamente para documento {document.id}")
            return True, signed_xml
            
        except Exception as e:
            logger.error(f"Error signing XML for document {document.id}: {str(e)}")
            return False, f"XML_SIGNING_ERROR: {str(e)}"
    
    def _create_xades_bes_signature_fixed(self, xml_content, cert_data):
        """
        Crear firma XAdES-BES SIN modificaciones posteriores - CORREGIDO
        ✅ NO modifica el XML después de firmarlo
        """
        try:
            # ✅ PASO 1: Limpiar XML ANTES de parsear (si es necesario)
            xml_content = self._pre_clean_xml_if_needed(xml_content)
            
            # PASO 2: Parsear XML original
            parser = etree.XMLParser(
                remove_blank_text=False,
                strip_cdata=False,
                resolve_entities=False,
                remove_comments=False,
                recover=False
            )
            
            root = etree.fromstring(xml_content.encode('utf-8'), parser)
            
            # PASO 3: Configurar elemento comprobante
            comprobante_id = self._ensure_comprobante_id(root)
            
            # PASO 4: Generar IDs únicos
            signature_id = f"Signature{uuid.uuid4().hex[:8]}"
            signed_properties_id = f"{signature_id}-SignedProperties{uuid.uuid4().hex[:6]}"
            reference_id = f"Reference-ID-{uuid.uuid4().hex[:6]}"
            
            # PASO 5: Extraer certificado
            certificate = cert_data.certificate
            
            # PASO 6: Crear estructura de firma completa
            signature_element = self._build_signature_structure_fixed(
                signature_id,
                signed_properties_id, 
                reference_id,
                comprobante_id,
                certificate,
                cert_data.private_key,
                root
            )
            
            # PASO 7: Insertar firma en documento
            root.append(signature_element)
            
            # ✅ PASO 8: Generar XML final SIN pretty_print y SIN modificaciones
            canonical_body = etree.tostring(
                root,
                method='c14n',
                exclusive=False,
                with_comments=False
            ).decode('utf-8')

             # Agregar declaración XML
            signed_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + canonical_body
                
            # ✅ CRÍTICO: NO MODIFICAR EL XML DESPUÉS DE FIRMAR
            # ❌ NO llamar a _clean_xml_for_sri() aquí
            # ❌ NO hacer replace, strip, o cualquier modificación
            
            logger.info("✅ XML firmado SIN atributo Id en X509Certificate")
            logger.info("✅ XML NO modificado después de firmar")
            return signed_xml
            
        except Exception as e:
            logger.error(f"Error creating XAdES-BES signature: {str(e)}")
            raise Exception(f"XADES_SIGNATURE_FAILED: {str(e)}")
    
    def _pre_clean_xml_if_needed(self, xml_content):
        """
        Limpieza PRE-firma si es absolutamente necesaria
        Solo se ejecuta ANTES de firmar
        """
        try:
            # Solo asegurar que tenga declaración XML correcta
            if not xml_content.strip().startswith('<?xml'):
                xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
            
            # Eliminar BOM si existe
            if xml_content.startswith('\ufeff'):
                xml_content = xml_content[1:]
            
            return xml_content
            
        except Exception as e:
            logger.warning(f"Error in pre-cleaning: {e}")
            return xml_content
    
    def _ensure_comprobante_id(self, root):
        """Asegurar que el comprobante tenga ID válido"""
        # Buscar elementos de comprobante
        comprobante_elements = [
            'factura', 'notaCredito', 'notaDebito', 
            'comprobanteRetencion', 'liquidacionCompra'
        ]
        
        for element_name in comprobante_elements:
            element = root.find(f'.//{element_name}')
            if element is not None:
                comp_id = element.get('id')
                if not comp_id:
                    comp_id = 'comprobante'
                    element.set('id', comp_id)
                
                logger.info(f"Found comprobante element: {element_name} with ID: {comp_id}")
                return f"#{comp_id}"
        
        # Fallback al elemento raíz
        root_id = root.get('id')
        if not root_id:
            root_id = 'comprobante'
            root.set('id', root_id)
        
        return f"#{root_id}"
    
    def _build_signature_structure_fixed(self, signature_id, signed_properties_id, reference_id, 
                                       comprobante_id, certificate, private_key, document_root):
        """Construir estructura completa de firma XAdES-BES SIN Id en X509Certificate"""
        
        # Namespaces
        ds_ns = "http://www.w3.org/2000/09/xmldsig#"
        xades_ns = "http://uri.etsi.org/01903/v1.3.2#"
        
        # 1. Calcular digest del documento
        document_canonical = self._canonicalize_element(document_root, comprobante_id)
        document_digest = hashlib.sha1(document_canonical).digest()
        document_digest_b64 = base64.b64encode(document_digest).decode()
        
        # 2. Crear SignedProperties
        signed_properties = self._create_signed_properties(
            signed_properties_id, signature_id, reference_id, certificate, ds_ns, xades_ns
        )
        
        # 3. Calcular digest de SignedProperties
        signed_props_canonical = etree.tostring(
            signed_properties,
            method='c14n',
            exclusive=False,
            with_comments=False
        )
        signed_props_digest = hashlib.sha1(signed_props_canonical).digest()
        signed_props_digest_b64 = base64.b64encode(signed_props_digest).decode()
        
        # 4. Crear SignedInfo
        signed_info = self._create_signed_info(
            document_digest_b64, signed_props_digest_b64, 
            comprobante_id, signed_properties_id, reference_id, ds_ns
        )
        
        # 5. Firmar SignedInfo
        signed_info_canonical = etree.tostring(
            signed_info,
            method='c14n',
            exclusive=False, 
            with_comments=False
        )
        
        signature_bytes = private_key.sign(
            signed_info_canonical,
            padding.PKCS1v15(),
            hashes.SHA1()  # SHA-1 según facturador oficial
        )
        signature_value = base64.b64encode(signature_bytes).decode()
        
        # 6. Crear elemento Signature completo
        signature = etree.Element(f"{{{ds_ns}}}Signature", nsmap={
            'ds': ds_ns,
            'etsi': xades_ns
        })
        signature.set("Id", signature_id)
        
        # SignedInfo
        signature.append(signed_info)
        
        # SignatureValue
        sig_value_elem = etree.SubElement(signature, f"{{{ds_ns}}}SignatureValue")
        sig_value_elem.text = signature_value
        
        # KeyInfo
        key_info = etree.SubElement(signature, f"{{{ds_ns}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{ds_ns}}}X509Data")
        x509_cert = etree.SubElement(x509_data, f"{{{ds_ns}}}X509Certificate")
        
        # ✅ CRÍTICO: NO agregar atributo Id al X509Certificate
        
        # Certificado en base64
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode().replace('\n', '').replace('\r', '')
        x509_cert.text = cert_b64
        
        # Object con QualifyingProperties
        obj = etree.SubElement(signature, f"{{{ds_ns}}}Object")
        qualifying_props = etree.SubElement(obj, f"{{{xades_ns}}}QualifyingProperties")
        qualifying_props.set("Target", f"#{signature_id}")
        qualifying_props.append(signed_properties)
        
        logger.info("✅ Signature structure built WITHOUT Id attribute in X509Certificate")
        return signature
    
    def _create_signed_info(self, doc_digest, props_digest, comprobante_id, 
                          signed_props_id, reference_id, ds_ns):
        """Crear SignedInfo con algoritmos SHA-1"""
        signed_info = etree.Element(f"{{{ds_ns}}}SignedInfo")
        
        # CanonicalizationMethod
        canon_method = etree.SubElement(signed_info, f"{{{ds_ns}}}CanonicalizationMethod")
        canon_method.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        
        # SignatureMethod - SHA-1 según facturador oficial
        sig_method = etree.SubElement(signed_info, f"{{{ds_ns}}}SignatureMethod")
        sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")
        
        # Reference 1: Documento
        ref1 = etree.SubElement(signed_info, f"{{{ds_ns}}}Reference")
        ref1.set("URI", comprobante_id)
        ref1.set("Id", reference_id)
        
        transforms1 = etree.SubElement(ref1, f"{{{ds_ns}}}Transforms")
        transform1 = etree.SubElement(transforms1, f"{{{ds_ns}}}Transform")
        transform1.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        
        digest_method1 = etree.SubElement(ref1, f"{{{ds_ns}}}DigestMethod")
        digest_method1.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")  # SHA-1
        
        digest_value1 = etree.SubElement(ref1, f"{{{ds_ns}}}DigestValue")
        digest_value1.text = doc_digest
        
        # Reference 2: SignedProperties
        ref2 = etree.SubElement(signed_info, f"{{{ds_ns}}}Reference")
        ref2.set("URI", f"#{signed_props_id}")
        ref2.set("Type", "http://www.w3.org/2000/09/xmldsig#SignatureProperties")
        
        transforms2 = etree.SubElement(ref2, f"{{{ds_ns}}}Transforms")
        transform2 = etree.SubElement(transforms2, f"{{{ds_ns}}}Transform")
        transform2.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        
        digest_method2 = etree.SubElement(ref2, f"{{{ds_ns}}}DigestMethod")
        digest_method2.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")  # SHA-1
        
        digest_value2 = etree.SubElement(ref2, f"{{{ds_ns}}}DigestValue")
        digest_value2.text = props_digest
        
        return signed_info
    
    def _create_signed_properties(self, signed_props_id, signature_id, reference_id, 
                                certificate, ds_ns, xades_ns):
        """Crear SignedProperties con zona horaria local y SignedDataObjectProperties"""
        
        signed_props = etree.Element(f"{{{xades_ns}}}SignedProperties")
        signed_props.set("Id", signed_props_id)
        
        # SignedSignatureProperties
        signed_sig_props = etree.SubElement(signed_props, f"{{{xades_ns}}}SignedSignatureProperties")
        
        # SigningTime con zona horaria local Ecuador (-05:00)
        signing_time = etree.SubElement(signed_sig_props, f"{{{xades_ns}}}SigningTime")
        ecuador_tz = timezone(timedelta(hours=-5))
        now_ecuador = datetime.now(ecuador_tz)
        signing_time.text = now_ecuador.strftime('%Y-%m-%dT%H:%M:%S-05:00')
        
        # SigningCertificate
        signing_cert = etree.SubElement(signed_sig_props, f"{{{xades_ns}}}SigningCertificate")
        cert_elem = etree.SubElement(signing_cert, f"{{{xades_ns}}}Cert")
        
        # CertDigest con SHA-1
        cert_digest = etree.SubElement(cert_elem, f"{{{xades_ns}}}CertDigest")
        cert_digest_method = etree.SubElement(cert_digest, f"{{{ds_ns}}}DigestMethod")
        cert_digest_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
        
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_hash = hashlib.sha1(cert_der).digest()
        cert_digest_value = etree.SubElement(cert_digest, f"{{{ds_ns}}}DigestValue")
        cert_digest_value.text = base64.b64encode(cert_hash).decode()
        
        # IssuerSerial
        issuer_serial = etree.SubElement(cert_elem, f"{{{xades_ns}}}IssuerSerial")
        
        x509_issuer_name = etree.SubElement(issuer_serial, f"{{{ds_ns}}}X509IssuerName")
        x509_issuer_name.text = self._clean_issuer_name_for_sri(certificate)
        
        x509_serial_number = etree.SubElement(issuer_serial, f"{{{ds_ns}}}X509SerialNumber")
        x509_serial_number.text = str(certificate.serial_number)
        
        # SignedDataObjectProperties
        signed_data_props = etree.SubElement(signed_props, f"{{{xades_ns}}}SignedDataObjectProperties")
        data_obj_format = etree.SubElement(signed_data_props, f"{{{xades_ns}}}DataObjectFormat")
        data_obj_format.set("ObjectReference", f"#{reference_id}")
        
        description = etree.SubElement(data_obj_format, f"{{{xades_ns}}}Description")
        description.text = "contenido comprobante"
        
        mime_type = etree.SubElement(data_obj_format, f"{{{xades_ns}}}MimeType")
        mime_type.text = "text/xml"
        
        return signed_props
    
    def _clean_issuer_name_for_sri(self, certificate):
        """Limpiar issuer name según proveedor de certificado"""
        try:
            issuer_string = certificate.issuer.rfc4514_string()
            
            # Para UANATACA: mantener formato exacto
            if "UANATACA" in issuer_string and "Barcelona" in issuer_string:
                logger.info("Certificado UANATACA detectado - manteniendo formato exacto")
                return issuer_string
            else:
                # Para otros proveedores: limpiar caracteres problemáticos
                issuer_string = re.sub(r"[<>\"']", "", issuer_string)
                issuer_string = re.sub(r"\s+", " ", issuer_string)
                return issuer_string.strip()
            
        except Exception as e:
            logger.error(f"Error procesando issuer: {e}")
            return certificate.issuer.rfc4514_string()
    
    def _canonicalize_element(self, root, comprobante_id):
        """Canonicalizar elemento específico"""
        try:
            if comprobante_id.startswith('#'):
                element_id = comprobante_id[1:]
                
                # Buscar elemento por ID
                if root.get('id') == element_id:
                    target_element = root
                else:
                    target_element = root.find(f".//*[@id='{element_id}']")
                
                if target_element is not None:
                    canonical = etree.tostring(
                        target_element,
                        method='c14n',
                        exclusive=False,
                        with_comments=False
                    )
                    return canonical
            
            # Fallback: canonicalizar documento completo
            return etree.tostring(
                root,
                method='c14n', 
                exclusive=False,
                with_comments=False
            )
            
        except Exception as e:
            logger.error(f"Error canonicalizing: {e}")
            raise Exception(f"CANONICALIZATION_FAILED: {str(e)}")
    
    def _send_to_sri_enhanced(self, document, signed_xml):
        """Enviar documento al SRI con manejo mejorado"""
        try:
            logger.info(f"Enviando documento {document.id} al SRI")
            logger.info(f"XML firmado tamaño: {len(signed_xml)} caracteres")
            
            sri_client = SRISOAPClient(self.company)
            success, message = sri_client.send_document_to_reception(document, signed_xml)
            
            logger.info(f"SRI Response - Success: {success}, Message: {message}")
            
            document.refresh_from_db()
            
            if success:
                logger.info("SRI reportó ÉXITO - actualizando status a SENT")
                document.status = 'SENT'
                document.save()
                document.refresh_from_db()
                logger.info(f"Status final verificado: {document.status}")
                return True, message
            else:
                detailed_error = f"SRI_SUBMISSION_FAILED: {message}"
                logger.error(detailed_error)
                return False, detailed_error
                
        except Exception as e:
            error_msg = f"PROCESSOR_SRI_EXCEPTION: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _generate_xml(self, document):
        """Generar XML del documento"""
        try:
            logger.info(f"Generando XML para documento {document.id}, tipo: {document.document_type}")
            
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
            
            logger.info(f"XML generado, tamaño: {len(xml_content)} caracteres")
            return True, xml_content
            
        except Exception as e:
            logger.error(f"Error generating XML: {str(e)}")
            return False, f"XML_GENERATION_ERROR: {str(e)}"
    
    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """Consultar autorización del documento"""
        import time
        
        try:
            logger.info(f"Consultando autorización para documento {document.id}")
            
            original_status = document.status
            sri_client = SRISOAPClient(self.company)
            
            for attempt in range(max_attempts):
                if attempt > 0:
                    logger.info(f"Esperando {wait_seconds}s antes del intento {attempt + 1}")
                    time.sleep(wait_seconds)
                
                success, message = sri_client.get_document_authorization(document)
                
                if success:
                    logger.info(f"Documento {document.id} autorizado por el SRI")
                    return True, message
                
                if 'proceso' in message.lower() or 'pendiente' in message.lower():
                    logger.info(f"Documento aún en proceso, intento {attempt + 1}/{max_attempts}")
                    continue
                
                logger.error(f"Error definitivo en autorización: {message}")
                
                if original_status in ['SENT', 'AUTHORIZED']:
                    document.status = original_status
                    document.save()
                
                return False, f"AUTHORIZATION_ERROR: {message}"
            
            logger.warning(f"Timeout en autorización para documento {document.id}")
            
            if original_status in ['SENT', 'AUTHORIZED']:
                document.status = original_status
                document.save()
            
            return False, f"AUTHORIZATION_TIMEOUT: Timeout after {max_attempts} attempts"
            
        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False, f"AUTHORIZATION_EXCEPTION: {str(e)}"
    
    def _generate_pdf(self, document):
        """Generar PDF del documento"""
        try:
            logger.info(f"Generando PDF para documento {document.id}")
            
            pdf_generator = PDFGenerator(document)
            
            if document.document_type == 'INVOICE':
                pdf_content = pdf_generator.generate_invoice_pdf()
            elif document.document_type == 'CREDIT_NOTE':
                pdf_content = pdf_generator.generate_credit_note_pdf()
            elif document.document_type == 'DEBIT_NOTE':
                pdf_content = pdf_generator.generate_debit_note_pdf()
            else:
                logger.warning(f"PDF generation not implemented for {document.document_type}")
                return False, f"PDF generation not implemented for {document.document_type}"
            
            # Guardar PDF
            filename = f"{document.access_key}.pdf"
            document.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
            
            logger.info(f"PDF generado para documento {document.id}")
            return True, "PDF generated successfully"
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return False, f"PDF_GENERATION_ERROR: {str(e)}"

    def _send_email(self, document):
        """Enviar documento por email"""
        try:
            logger.info(f"Enviando email para documento {document.id}")
            
            if not document.customer_email:
                return False, "Customer email not provided"
            
            if not self.sri_config.email_enabled:
                return False, "Email sending is disabled"
            
            email_service = EmailService(self.company)
            success, message = email_service.send_document_email(document)
            
            if success:
                document.email_sent = True
                document.email_sent_date = django_timezone.now()
                document.save()
                logger.info(f"Email enviado para documento {document.id}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False, f"EMAIL_EXCEPTION: {str(e)}"
    
    # Métodos de compatibilidad
    def process_document_legacy(self, document, certificate_password, send_email=True):
        """Método legacy para compatibilidad"""
        logger.warning(f"Using legacy process_document method for document {document.id}")
        return self.process_document(document, send_email, certificate_password)
    
    def reprocess_document(self, document):
        """Reprocesar documento que falló"""
        try:
            if document.status in ['AUTHORIZED', 'SENT']:
                return False, "Document is already processed"
            
            logger.info(f"Reprocesando documento {document.id}")
            
            # Resetear estado
            document.status = 'GENERATED'
            document.sri_authorization_code = ''
            document.sri_authorization_date = None
            document.sri_response = {}
            document.save()
            
            return self.process_document(document)
            
        except Exception as e:
            logger.error(f"Error reprocessing document: {str(e)}")
            return False, f"REPROCESS_ERROR: {str(e)}"
    
    def get_document_status(self, document):
        """Obtener estado detallado del documento"""
        return {
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
            'processing_method': 'SRI_Compatible_NO_POST_SIGN_MODIFICATIONS',
            'processor_version': 'FIXED_FIRMA_INVALIDA_ERROR_39',
            'fixes_applied': [
                'NO_MODIFICATIONS_AFTER_SIGNING',
                'NO_PRETTY_PRINT_AFTER_SIGNING',
                'NO_CLEAN_XML_FOR_SRI_AFTER_SIGNING',
                'REMOVED_ID_ATTRIBUTE_FROM_X509CERTIFICATE',
                'SHA1_ALGORITHMS_EXACT_MATCH',
                'CORRECT_CANONICALIZATION'
            ]
        }
    
    def validate_company_setup(self):
        """Validar configuración de la empresa"""
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
            
            # Verificar certificado
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                validation_errors.append("Digital certificate not available")
            else:
                is_valid, cert_message = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    validation_errors.append(f"Certificate validation failed: {cert_message}")
            
            if validation_errors:
                return False, validation_errors
            
            return True, "Company setup is valid"
            
        except Exception as e:
            logger.error(f"Error validating company setup: {str(e)}")
            return False, [f"Error validating setup: {str(e)}"]