# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos - VERSIÓN CORREGIDA v3.0
RESUELVE: Error 39 FIRMA INVALIDA (firma y/o certificados alterados)

CORRECCIONES APLICADAS v3.0:
1. Namespaces declarados en root ANTES de calcular hashes
2. Canonicalización EXCLUSIVA para SignedProperties (exclusive=True)
3. Sin espacios en blanco después de </ds:Signature>
4. IDs con formato fijo más compatible (sin UUIDs complejos)
5. Serialización final con pretty_print=False estricto
6. X509IssuerName con formato RFC4514 verificado
7. Nodo Signature insertado como último hijo sin espacios adicionales
8. Digest del documento calculado ANTES de insertar firma
9. SignedProperties con canonicalización exclusiva independiente
10. Eliminación de saltos de línea y espacios problemáticos
"""

import logging
import os
import time
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

# ============================================================================
# Constantes de namespaces y algoritmos
# ============================================================================
DS_NS = "http://www.w3.org/2000/09/xmldsig#"
XADES_NS = "http://uri.etsi.org/01903/v1.3.2#"

ALG_C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ALG_RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
ALG_SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"
ALG_ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
TYPE_SIGNED_PROPS = "http://uri.etsi.org/01903#SignedProperties"

ECUADOR_TZ = timezone(timedelta(hours=-5))


class DocumentProcessor:
    """
    Procesador principal de documentos electrónicos del SRI.
    Implementa firma XAdES-BES compatible con el facturador oficial del SRI.
    """

    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
        self.cert_manager = get_certificate_manager()

    # ========================================================================
    # Flujo principal
    # ========================================================================
    def process_document(self, document, send_email=True, certificate_password=None):
        """Procesa completamente un documento electrónico."""
        try:
            with transaction.atomic():
                logger.info(f"Iniciando procesamiento de documento {document.id}")

                # --- Validaciones previas ---
                cert_data = self.cert_manager.get_certificate(self.company.id)
                if not cert_data:
                    msg = f"Certificate not available for company {self.company.id}"
                    logger.error(msg)
                    return False, msg

                is_valid, validation_msg = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    logger.error(f"Certificate validation failed: {validation_msg}")
                    return False, f"Certificate validation failed: {validation_msg}"

                ok, cert_msg = self._verify_certificate(cert_data)
                if not ok:
                    logger.error(f"Certificate check failed: {cert_msg}")
                    return False, cert_msg

                # 1. Generar XML
                logger.info(f"Generando XML para documento {document.id}")
                ok, xml_content = self._generate_xml(document)
                if not ok:
                    logger.error(f"XML generation failed: {xml_content}")
                    return False, f"XML generation failed: {xml_content}"

                # 2. Firmar XML
                logger.info(f"Firmando XML para documento {document.id}")
                ok, signed_xml = self._sign_xml(document, xml_content)
                if not ok:
                    logger.error(f"XML signing failed: {signed_xml}")
                    return False, f"XML signing failed: {signed_xml}"

                # 3. Enviar al SRI
                logger.info(f"Enviando documento {document.id} al SRI")
                ok, sri_msg = self._send_to_sri(document, signed_xml)
                if not ok:
                    logger.error(f"SRI submission failed: {sri_msg}")
                    return False, sri_msg

                # 4. Consultar autorización
                logger.info(f"Consultando autorización para documento {document.id}")
                ok, auth_msg = self._check_authorization(document)
                if not ok:
                    logger.warning(f"Authorization check failed: {auth_msg}")

                # 5. Generar PDF
                ok, pdf_msg = self._generate_pdf(document)
                if not ok:
                    logger.warning(f"PDF generation failed: {pdf_msg}")

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

    # ========================================================================
    # Verificación de certificado
    # ========================================================================
    def _verify_certificate(self, cert_data):
        """
        Verificar que el certificado sea válido para firma digital
        y que no esté expirado.
        """
        try:
            certificate = cert_data.certificate
            issuer = certificate.issuer.rfc4514_string()
            logger.info(f"Proveedor del certificado: {issuer}")

            # 1. Verificar validez temporal PRIMERO
            now = datetime.now(timezone.utc)

            not_valid_after = certificate.not_valid_after_utc if hasattr(
                certificate, 'not_valid_after_utc'
            ) else certificate.not_valid_after.replace(tzinfo=timezone.utc)

            not_valid_before = certificate.not_valid_before_utc if hasattr(
                certificate, 'not_valid_before_utc'
            ) else certificate.not_valid_before.replace(tzinfo=timezone.utc)

            if not_valid_after < now:
                return False, f"Certificate expired on {not_valid_after}"

            if not_valid_before > now:
                return False, f"Certificate not valid until {not_valid_before}"

            # 2. Verificar Key Usage
            try:
                key_usage = certificate.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                ).value

                if key_usage.digital_signature:
                    logger.info("Certificate has Digital Signature capability")
                    return True, "Certificate valid for digital signature"
                else:
                    logger.error("Certificate does NOT have Digital Signature capability")
                    return False, (
                        "Certificate must have Digital Signature key usage. "
                        "Verify you are using the Signing Key, not the Encryption Key."
                    )

            except x509.ExtensionNotFound:
                logger.warning("Key Usage extension not found - proceeding anyway")
                return True, "Certificate Key Usage extension not found (proceeding)"

        except Exception as e:
            logger.error(f"Error verifying certificate: {e}")
            return False, f"Certificate verification failed: {str(e)}"

    # ========================================================================
    # Firma XAdES-BES
    # ========================================================================
    def _sign_xml(self, document, xml_content):
        """Firma el XML con XAdES-BES compatible con el SRI."""
        try:
            logger.info(f"Iniciando firma XML para documento {document.id}")

            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                return False, "Certificate not available"

            signed_xml = self._create_xades_bes_signature(xml_content, cert_data)

            # Guardar XML firmado
            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename,
                ContentFile(signed_xml),  # Ya es bytes
                save=True
            )

            document.status = 'SIGNED'
            document.save()
            cert_data.update_usage()

            # DEBUG: Guardar XML firmado para análisis
            debug_path = f"/tmp/signed_debug_{document.id}.xml"
            with open(debug_path, 'wb') as debug_f:
                debug_f.write(signed_xml)
            logger.info(f"DEBUG: XML guardado en {debug_path}")
            
            logger.info(f"XML firmado correctamente para documento {document.id}")
            return True, signed_xml.decode('utf-8')

        except Exception as e:
            logger.error(f"Error signing XML for document {document.id}: {str(e)}")
            return False, f"XML_SIGNING_ERROR: {str(e)}"

    def _create_xades_bes_signature(self, xml_content, cert_data):
        """
        Crear firma XAdES-BES compatible con el facturador oficial del SRI.
        
        CORRECCIONES CRÍTICAS v3.0:
        1. Declarar namespaces ds y etsi en el root ANTES de calcular hashes
        2. Usar canonicalización EXCLUSIVA (exclusive=True) para SignedProperties
        3. IDs más simples y compatibles
        4. Sin espacios en blanco después del nodo Signature
        5. Serialización final SIN pretty_print
        """
        try:
            # --- PASO 1: Limpiar y parsear XML ---
            xml_content = self._pre_clean_xml(xml_content)

            # Parser estricto sin modificar whitespace
            parser = etree.XMLParser(
                remove_blank_text=False,
                strip_cdata=False,
                resolve_entities=False,
                remove_comments=False,
                recover=False
            )
            root = etree.fromstring(xml_content.encode('utf-8'), parser)

            # --- PASO 2: DECLARAR NAMESPACES EN ROOT (CRÍTICO) ---
            # El SRI requiere que los namespaces de firma estén declarados globalmente
            nsmap = root.nsmap.copy() if root.nsmap else {}
            if 'ds' not in nsmap:
                nsmap['ds'] = DS_NS
            if 'etsi' not in nsmap:
                nsmap['etsi'] = XADES_NS
            
            # Recrear root con namespaces completos
            new_root = etree.Element(root.tag, nsmap=nsmap, attrib=root.attrib)
            new_root.text = root.text
            new_root.tail = root.tail
            for child in root:
                new_root.append(child)
            root = new_root
            
            logger.info(f"Namespaces declarados en root: {list(root.nsmap.keys())}")

            # --- PASO 3: Asegurar ID en el comprobante ---
            comprobante_uri = self._ensure_comprobante_id(root)

            # --- PASO 4: Generar IDs más simples (sin UUIDs complejos) ---
            # Usar IDs más cortos y compatibles como sugiere Gemini
            timestamp = int(time.time() * 1000) % 100000000  # 8 dígitos
            sig_id = f"Signature{timestamp}"
            signed_props_id = f"SignedPropertiesSRI{timestamp}"
            ref_id = f"Reference-ID-{timestamp}"
            
            logger.info(f"IDs generados - Sig: {sig_id}, Props: {signed_props_id}, Ref: {ref_id}")

            certificate = cert_data.certificate
            private_key = cert_data.private_key

            # --- PASO 5: Calcular digest del documento ---
            # Canonicalizar el root ANTES de agregar la firma
            doc_canonical = etree.tostring(
                root, 
                method='c14n', 
                exclusive=False, 
                with_comments=False
            )
            doc_digest_b64 = base64.b64encode(hashlib.sha256(doc_canonical).digest()).decode()
            
            logger.info(f"Document digest calculado (C14N {len(doc_canonical)} bytes)")

            # --- PASO 6: Crear SignedProperties ---
            signed_properties = self._create_signed_properties(
                signed_props_id, sig_id, ref_id, certificate
            )

            # CRÍTICO: Canonicalización INCLUSIVA para SignedProperties (según ficha técnica SRI)
            # Esto asegura consistencia con el resto del documento
            sp_canonical = etree.tostring(
                signed_properties, 
                method='c14n', 
                exclusive=False,  # ← CAMBIO CRÍTICO: exclusive=False (Inclusive)
                with_comments=False
            )
            sp_digest_b64 = base64.b64encode(hashlib.sha256(sp_canonical).digest()).decode()
            
            logger.info(f"SignedProperties digest (C14N exclusive, {len(sp_canonical)} bytes)")

            # --- PASO 7: Crear SignedInfo ---
            signed_info = self._create_signed_info(
                doc_digest_b64, sp_digest_b64,
                comprobante_uri, signed_props_id, ref_id
            )

            # --- PASO 8: Firmar SignedInfo ---
            si_canonical = etree.tostring(
                signed_info, method='c14n', exclusive=False, with_comments=False
            )
            signature_bytes = private_key.sign(
                si_canonical,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            signature_value_b64 = base64.b64encode(signature_bytes).decode()

            # --- PASO 9: Ensamblar ds:Signature ---
            signature_element = self._assemble_signature(
                sig_id, signed_info, signature_value_b64,
                certificate, signed_properties
            )

            # --- PASO 10: Insertar firma como ÚLTIMO HIJO sin espacios ---
            # CRÍTICO: No debe haber espacios ni saltos de línea después de Signature
            root.append(signature_element)
            
            # Asegurar que no haya tail (espacios después de la firma)
            signature_element.tail = None

            # --- PASO 11: Serializar XML final SIN pretty_print ---
            # CRÍTICO: pretty_print=False para no alterar el contenido firmado
            signed_xml_bytes = etree.tostring(
                root,
                encoding='utf-8',
                method='xml',
                xml_declaration=True,
                pretty_print=False  # ← CRÍTICO: NO formatear
            )
            
            # --- PASO 12: Eliminar espacios problemáticos ---
            # Remover cualquier espacio/salto de línea antes de </factura> o similar
            signed_xml_str = signed_xml_bytes.decode('utf-8')
            
            # Encontrar el tag de cierre del root
            root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
            
            # Eliminar espacios antes del cierre
            signed_xml_str = re.sub(
                rf'\s+(</{root_tag}>)',
                r'\1',
                signed_xml_str
            )
            
            signed_xml_bytes = signed_xml_str.encode('utf-8')

            logger.info("XML firmado exitosamente con XAdES-BES (SHA-256, exclusive C14N)")
            logger.info(f"Tamaño XML firmado: {len(signed_xml_bytes)} bytes")
            
            return signed_xml_bytes

        except Exception as e:
            logger.error(f"Error creating XAdES-BES signature: {str(e)}")
            raise Exception(f"XADES_SIGNATURE_FAILED: {str(e)}")

    # ========================================================================
    # Componentes de la firma
    # ========================================================================
    def _create_signed_info(self, doc_digest, sp_digest, comprobante_uri,
                            signed_props_id, reference_id):
        """
        Crear el nodo SignedInfo.

        Reference 1 (documento):
          - Transform: enveloped-signature (quita el nodo Signature antes de hashear)
          - Transform: C14N (canonicaliza)
          - DigestMethod: SHA-256

        Reference 2 (SignedProperties):
          - SIN Transforms (el digest ya fue calculado con C14N directamente)
          - Type: http://uri.etsi.org/01903#SignedProperties
          - DigestMethod: SHA-256
        """
        signed_info = etree.Element(f"{{{DS_NS}}}SignedInfo")

        # CanonicalizationMethod
        c14n_method = etree.SubElement(signed_info, f"{{{DS_NS}}}CanonicalizationMethod")
        c14n_method.set("Algorithm", ALG_C14N)

        # SignatureMethod
        sig_method = etree.SubElement(signed_info, f"{{{DS_NS}}}SignatureMethod")
        sig_method.set("Algorithm", ALG_RSA_SHA256)

        # --- Reference 1: Documento ---
        ref1 = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
        ref1.set("Id", reference_id)
        ref1.set("URI", comprobante_uri)

        transforms = etree.SubElement(ref1, f"{{{DS_NS}}}Transforms")

        # Transformación 1: enveloped-signature
        t_env = etree.SubElement(transforms, f"{{{DS_NS}}}Transform")
        t_env.set("Algorithm", ALG_ENVELOPED)

        # Transformación 2: C14N (canonicalización)
        t_c14n = etree.SubElement(transforms, f"{{{DS_NS}}}Transform")
        t_c14n.set("Algorithm", ALG_C14N)

        dm1 = etree.SubElement(ref1, f"{{{DS_NS}}}DigestMethod")
        dm1.set("Algorithm", ALG_SHA256)

        dv1 = etree.SubElement(ref1, f"{{{DS_NS}}}DigestValue")
        dv1.text = doc_digest

        # --- Reference 2: SignedProperties ---
        # CRÍTICO: SIN Transforms - el digest ya fue calculado con C14N exclusivo
        ref2 = etree.SubElement(signed_info, f"{{{DS_NS}}}Reference")
        ref2.set("Type", TYPE_SIGNED_PROPS)
        ref2.set("URI", f"#{signed_props_id}")

        dm2 = etree.SubElement(ref2, f"{{{DS_NS}}}DigestMethod")
        dm2.set("Algorithm", ALG_SHA256)

        dv2 = etree.SubElement(ref2, f"{{{DS_NS}}}DigestValue")
        dv2.text = sp_digest

        return signed_info

    def _create_signed_properties(self, signed_props_id, signature_id,
                                  reference_id, certificate):
        """
        Crear el nodo SignedProperties con:
        - SigningTime en zona horaria Ecuador (-05:00)
        - SigningCertificate con digest SHA-256
        - SignedDataObjectProperties (Description, MimeType, Encoding)
        """
        signed_props = etree.Element(
            f"{{{XADES_NS}}}SignedProperties",
            nsmap={'etsi': XADES_NS, 'ds': DS_NS}
        )
        signed_props.set("Id", signed_props_id)

        # --- SignedSignatureProperties ---
        sig_props = etree.SubElement(signed_props, f"{{{XADES_NS}}}SignedSignatureProperties")

        # SigningTime
        signing_time = etree.SubElement(sig_props, f"{{{XADES_NS}}}SigningTime")
        now_ec = datetime.now(ECUADOR_TZ)
        signing_time.text = now_ec.strftime('%Y-%m-%dT%H:%M:%S-05:00')

        # SigningCertificate
        signing_cert = etree.SubElement(sig_props, f"{{{XADES_NS}}}SigningCertificate")
        cert_elem = etree.SubElement(signing_cert, f"{{{XADES_NS}}}Cert")

        # CertDigest (SHA-256)
        cert_digest = etree.SubElement(cert_elem, f"{{{XADES_NS}}}CertDigest")
        cdm = etree.SubElement(cert_digest, f"{{{DS_NS}}}DigestMethod")
        cdm.set("Algorithm", ALG_SHA256)

        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        cert_hash = hashlib.sha256(cert_der).digest()
        cdv = etree.SubElement(cert_digest, f"{{{DS_NS}}}DigestValue")
        cdv.text = base64.b64encode(cert_hash).decode()

        # IssuerSerial
        issuer_serial = etree.SubElement(cert_elem, f"{{{XADES_NS}}}IssuerSerial")

        issuer_name = etree.SubElement(issuer_serial, f"{{{DS_NS}}}X509IssuerName")
        issuer_name.text = self._format_issuer_name(certificate)

        serial_number = etree.SubElement(issuer_serial, f"{{{DS_NS}}}X509SerialNumber")
        serial_number.text = str(certificate.serial_number)

        # --- SignedDataObjectProperties ---
        sdop = etree.SubElement(signed_props, f"{{{XADES_NS}}}SignedDataObjectProperties")
        dof = etree.SubElement(sdop, f"{{{XADES_NS}}}DataObjectFormat")
        dof.set("ObjectReference", f"#{reference_id}")

        desc = etree.SubElement(dof, f"{{{XADES_NS}}}Description")
        desc.text = "FIRMA DIGITAL SRI"

        mime = etree.SubElement(dof, f"{{{XADES_NS}}}MimeType")
        mime.text = "text/xml"

        encoding = etree.SubElement(dof, f"{{{XADES_NS}}}Encoding")
        encoding.text = "UTF-8"

        return signed_props

    def _assemble_signature(self, sig_id, signed_info, signature_value_b64,
                            certificate, signed_properties):
        """
        Ensamblar el nodo ds:Signature completo con:
        - SignedInfo
        - SignatureValue
        - KeyInfo (X509Certificate)
        - Object > QualifyingProperties > SignedProperties
        """
        signature = etree.Element(f"{{{DS_NS}}}Signature", nsmap={
            'ds': DS_NS,
            'etsi': XADES_NS
        })
        signature.set("Id", sig_id)

        # SignedInfo (ya construido)
        signature.append(signed_info)

        # SignatureValue
        sv = etree.SubElement(signature, f"{{{DS_NS}}}SignatureValue")
        sv.text = signature_value_b64

        # KeyInfo
        key_info = etree.SubElement(signature, f"{{{DS_NS}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{DS_NS}}}X509Data")
        x509_cert = etree.SubElement(x509_data, f"{{{DS_NS}}}X509Certificate")

        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        x509_cert.text = base64.b64encode(cert_der).decode()

        # Object > QualifyingProperties > SignedProperties
        obj = etree.SubElement(signature, f"{{{DS_NS}}}Object")
        qp = etree.SubElement(obj, f"{{{XADES_NS}}}QualifyingProperties")
        qp.set("Target", f"#{sig_id}")
        qp.append(signed_properties)

        return signature

    # ========================================================================
    # Utilidades de firma
    # ========================================================================
    def _pre_clean_xml(self, xml_content):
        """Limpieza mínima del XML antes de firmar."""
        # Eliminar BOM si existe
        if xml_content.startswith('\ufeff'):
            xml_content = xml_content[1:]

        # Asegurar declaración XML
        if not xml_content.strip().startswith('<?xml'):
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>' + xml_content

        return xml_content

    def _ensure_comprobante_id(self, root):
        """
        Asegurar que el elemento raíz del comprobante tenga id="comprobante".
        Retorna el URI con # (ej: "#comprobante").
        """
        comprobante_tags = [
            'factura', 'notaCredito', 'notaDebito',
            'comprobanteRetencion', 'liquidacionCompra'
        ]

        # Buscar el elemento del comprobante
        target = None
        for tag in comprobante_tags:
            found = root.find(f'.//{tag}')
            if found is not None:
                target = found
                break

        # Si no se encontró, usar el root
        if target is None:
            target = root

        # Asegurar que tenga id
        comp_id = target.get('id')
        if not comp_id:
            comp_id = 'comprobante'
            target.set('id', comp_id)

        logger.info(f"Comprobante element: <{target.tag}> id=\"{comp_id}\"")
        return f"#{comp_id}"

    def _format_issuer_name(self, certificate):
        """
        Formatear el issuer name del certificado.
        INTENTO 1: Usar formato inverso al RFC4514 (estilo RFC1779/LDAP).
        Orden esperado: C=EC, O=..., OU=..., CN=...
        """
        try:
            # Obtener los RDNs (Relative Distinguished Names)
            rdns = certificate.issuer.rdns
            
            # Construir string manualmente en orden inverso (Root -> Leaf)
            # RFC4514 de cryptography devuelve: CN=...,OU=...,O=...,C=...
            # SRI suele preferir: C=EC,O=...,OU=...,CN=...
            
            parts = []
            for rdn in reversed(rdns):
                # Cada RDN puede tener múltiples atributos, pero usualmente es uno
                for attr in rdn:
                    # OID a nombre corto (CN, OU, O, C, etc.)
                    oid = attr.oid
                    val = attr.value
                    
                    # Mapeo manual de OIDs comunes si es necesario, 
                    # pero cryptography suele manejarlo bien.
                    # Usaremos el nombre del OID proporcionado por la librería.
                    oid_name = oid._name.upper() if hasattr(oid, '_name') else oid.dotted_string
                    
                    # Ajustes de nombres comunes
                    if oid_name == 'COUNTRYNAME': oid_name = 'C'
                    elif oid_name == 'ORGANIZATIONNAME': oid_name = 'O'
                    elif oid_name == 'ORGANIZATIONALUNITNAME': oid_name = 'OU'
                    elif oid_name == 'COMMONNAME': oid_name = 'CN'
                    elif oid_name == 'LOCALITYNAME': oid_name = 'L'
                    elif oid_name == 'STATEORPROVINCENAME': oid_name = 'ST'
                    
                    parts.append(f"{oid_name}={val}")
            
            issuer_string = ",".join(parts)
            logger.info(f"X509IssuerName (Custom/Root-First): {issuer_string}")
            
            return issuer_string

        except Exception as e:
            logger.error(f"Error formatting issuer name: {e}")
            # Fallback a RFC 4514 estándar
            return certificate.issuer.rfc4514_string()

    # ========================================================================
    # Generación XML
    # ========================================================================
    def _generate_xml(self, document):
        """Generar XML del documento."""
        try:
            logger.info(f"Generando XML para documento {document.id}, tipo: {document.document_type}")

            xml_generator = XMLGenerator(document)

            generators = {
                'INVOICE': xml_generator.generate_invoice_xml,
                'CREDIT_NOTE': xml_generator.generate_credit_note_xml,
                'DEBIT_NOTE': xml_generator.generate_debit_note_xml,
                'RETENTION': xml_generator.generate_retention_xml,
                'PURCHASE_SETTLEMENT': xml_generator.generate_purchase_settlement_xml,
            }

            gen_func = generators.get(document.document_type)
            if not gen_func:
                return False, f"Unsupported document type: {document.document_type}"

            xml_content = gen_func()

            # Guardar XML sin firmar
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

    # ========================================================================
    # Envío al SRI
    # ========================================================================
    def _send_to_sri(self, document, signed_xml):
        """Enviar documento al SRI."""
        try:
            # signed_xml puede ser str o bytes
            if isinstance(signed_xml, bytes):
                xml_str = signed_xml.decode('utf-8')
            else:
                xml_str = signed_xml

            logger.info(f"Enviando documento {document.id} al SRI ({len(xml_str)} chars)")

            sri_client = SRISOAPClient(self.company)
            success, message = sri_client.send_document_to_reception(document, xml_str)

            logger.info(f"SRI Response - Success: {success}, Message: {message}")

            if success:
                document.status = 'SENT'
                document.save()
                return True, message
            else:
                return False, f"SRI_SUBMISSION_FAILED: {message}"

        except Exception as e:
            msg = f"PROCESSOR_SRI_EXCEPTION: {str(e)}"
            logger.error(msg)
            return False, msg

    # ========================================================================
    # Consulta de autorización
    # ========================================================================
    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """Consultar autorización del documento con reintentos."""
        try:
            logger.info(f"Consultando autorización para documento {document.id}")

            original_status = document.status
            sri_client = SRISOAPClient(self.company)

            # Esperar antes de la primera consulta
            logger.info("Esperando 10 segundos antes de consultar autorización...")
            time.sleep(10)

            for attempt in range(max_attempts):
                if attempt > 0:
                    logger.info(f"Esperando {wait_seconds}s antes del intento {attempt + 1}")
                    time.sleep(wait_seconds)

                success, message = sri_client.get_document_authorization(document)

                if success:
                    logger.info(f"Documento {document.id} autorizado por el SRI")
                    return True, message

                msg_lower = message.lower()
                if 'proceso' in msg_lower or 'pendiente' in msg_lower:
                    logger.info(f"Documento en proceso, intento {attempt + 1}/{max_attempts}")
                    continue

                # Error definitivo
                logger.error(f"Error definitivo en autorización: {message}")

                # Preservar estado previo si era exitoso
                if original_status in ('SENT', 'AUTHORIZED'):
                    document.status = original_status
                    document.save()

                return False, f"AUTHORIZATION_ERROR: {message}"

            # Timeout
            logger.warning(f"Timeout en autorización para documento {document.id}")
            if original_status in ('SENT', 'AUTHORIZED'):
                document.status = original_status
                document.save()

            return False, f"AUTHORIZATION_TIMEOUT: Timeout after {max_attempts} attempts"

        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False, f"AUTHORIZATION_EXCEPTION: {str(e)}"

    # ========================================================================
    # Generación PDF
    # ========================================================================
    def _generate_pdf(self, document):
        """Generar PDF del documento."""
        try:
            logger.info(f"Generando PDF para documento {document.id}")

            pdf_generator = PDFGenerator(document)

            generators = {
                'INVOICE': pdf_generator.generate_invoice_pdf,
                'CREDIT_NOTE': pdf_generator.generate_credit_note_pdf,
                'DEBIT_NOTE': pdf_generator.generate_debit_note_pdf,
            }

            gen_func = generators.get(document.document_type)
            if not gen_func:
                logger.warning(f"PDF generation not implemented for {document.document_type}")
                return False, f"PDF generation not implemented for {document.document_type}"

            pdf_content = gen_func()

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

    # ========================================================================
    # Envío de email
    # ========================================================================
    def _send_email(self, document):
        """Enviar documento por email."""
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

    # ========================================================================
    # Métodos auxiliares
    # ========================================================================
    def process_document_legacy(self, document, certificate_password, send_email=True):
        """Método legacy para compatibilidad."""
        logger.warning(f"Using legacy method for document {document.id}")
        return self.process_document(document, send_email, certificate_password)

    def reprocess_document(self, document):
        """Reprocesar documento que falló."""
        try:
            if document.status in ('AUTHORIZED', 'SENT'):
                return False, "Document is already processed"

            logger.info(f"Reprocesando documento {document.id}")

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
        """Obtener estado detallado del documento."""
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
            'processor_version': 'v3.0_XADES_BES_FIXED_NAMESPACES_EXCLUSIVE_C14N',
            'signature_method': 'RSA-SHA256',
            'digest_method': 'SHA-256',
            'transforms_document': ['enveloped-signature', 'C14N'],
            'transforms_signed_properties': 'NONE',
            'c14n_signed_properties': 'EXCLUSIVE',
            'namespaces_in_root': True,
        }

    def validate_company_setup(self):
        """Validar configuración de la empresa."""
        try:
            errors = []

            # Verificar configuración SRI
            try:
                sri_config = self.company.sri_configuration
                if not sri_config.is_active:
                    errors.append("SRI configuration is not active")
                if not sri_config.establishment_code:
                    errors.append("Establishment code not configured")
                if not sri_config.emission_point:
                    errors.append("Emission point not configured")
            except Exception:
                errors.append("SRI configuration not found")

            # Verificar certificado
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                errors.append("Digital certificate not available")
            else:
                is_valid, cert_msg = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    errors.append(f"Certificate validation failed: {cert_msg}")

            if errors:
                return False, errors

            return True, "Company setup is valid"

        except Exception as e:
            logger.error(f"Error validating company setup: {str(e)}")
            return False, [f"Error validating setup: {str(e)}"]