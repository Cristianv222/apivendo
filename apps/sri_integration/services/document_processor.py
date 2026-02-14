# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos - VERSIÓN JAR
RESUELVE: Error 39 FIRMA INVALIDA usando JAR de Java oficial

FIX DEFINITIVO JAR: 
- Usa JAR compilado de firma XAdES-BES (compatible con TODOS los proveedores)
- Soporta multi-tenant (múltiples empresas con diferentes certificados)
"""

import logging
import os
import time
import subprocess
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

# Imports básicos para verificación de certificado
from cryptography import x509

logger = logging.getLogger(__name__)

# ============================================================================
# Constantes
# ============================================================================
ECUADOR_TZ = timezone(timedelta(hours=-5))


class DocumentProcessor:
    """
    Procesador principal de documentos electrónicos del SRI.
    Implementa firma XAdES-BES usando JAR de Java oficial.
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

                # 2. Firmar XML (usando JAR)
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
        """Verificar que el certificado sea válido para firma digital."""
        try:
            certificate = cert_data.certificate
            issuer = certificate.issuer.rfc4514_string()
            logger.info(f"Proveedor del certificado: {issuer}")

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
    # Firma XAdES-BES usando JAR de Java
    # ========================================================================
    def _sign_xml(self, document, xml_content):
        """
        Firma el XML usando JAR de Java (compatible con TODOS los proveedores).
        Resuelve Error 39 - Funciona con Security Data, BCE, Uanataca, etc.
        """
        try:
            logger.info(f"🔐 Iniciando firma XML para documento {document.id} usando JAR")

            # Obtener certificado de la empresa
            cert_data = self.cert_manager.get_certificate(self.company.id)
            if not cert_data:
                return False, "Certificate not available"

            # Rutas temporales
            xml_unsigned_path = f"/tmp/factura_{document.id}_unsigned.xml"
            xml_signed_path = f"/tmp/factura_{document.id}_signed.xml"
            
            # Guardar XML sin firmar
            with open(xml_unsigned_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # Obtener certificado P12 y password de LA EMPRESA actual
            p12_path = cert_data.certificate_obj.certificate_file.path
            password = cert_data.password
            
            logger.info(f"📋 Firmando con JAR")
            logger.info(f"   Certificado: {p12_path}")
            logger.info(f"   XML input: {xml_unsigned_path}")
            logger.info(f"   XML output: {xml_signed_path}")
            
            # Ejecutar JAR de firma
            result = subprocess.run([
                'java', '-jar', '/app/sri.jar',
                p12_path,
                password,
                xml_unsigned_path,
                xml_signed_path
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"✅ JAR ejecutado exitosamente")
            if result.stdout:
                logger.info(f"   JAR stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.warning(f"   JAR stderr: {result.stderr.strip()}")
            
            # Leer XML firmado
            with open(xml_signed_path, 'rb') as f:
                signed_xml = f.read()
            
            logger.info(f"📊 XML firmado: {len(signed_xml)} bytes")
            
            # Guardar en el documento
            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename,
                ContentFile(signed_xml),
                save=True
            )

            document.status = 'SIGNED'
            document.save()
            cert_data.update_usage()

            # Debug
            debug_path = f"/tmp/signed_debug_{document.id}.xml"
            with open(debug_path, 'wb') as debug_f:
                debug_f.write(signed_xml)
            logger.info(f"DEBUG: XML firmado guardado en {debug_path}")
            
            # Limpiar archivos temporales
            try:
                os.unlink(xml_unsigned_path)
                os.unlink(xml_signed_path)
            except:
                pass
            
            logger.info(f"✅ XML firmado correctamente con JAR para documento {document.id}")
            return True, signed_xml.decode('utf-8')

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error ejecutando JAR: {e.stderr}")
            return False, f"JAR_SIGNING_ERROR: {e.stderr}"
        except Exception as e:
            logger.error(f"❌ Error signing XML for document {document.id}: {str(e)}")
            return False, f"XML_SIGNING_ERROR: {str(e)}"

    # ========================================================================
    # Resto de métodos
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

    def _send_to_sri(self, document, signed_xml):
        """Enviar documento al SRI."""
        try:
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

    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """Consultar autorización del documento."""
        try:
            logger.info(f"Consultando autorización para documento {document.id}")

            original_status = document.status
            sri_client = SRISOAPClient(self.company)

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

                logger.error(f"Error definitivo en autorización: {message}")

                if original_status in ('SENT', 'AUTHORIZED'):
                    document.status = original_status
                    document.save()

                return False, f"AUTHORIZATION_ERROR: {message}"

            logger.warning(f"Timeout en autorización para documento {document.id}")
            if original_status in ('SENT', 'AUTHORIZED'):
                document.status = original_status
                document.save()

            return False, f"AUTHORIZATION_TIMEOUT: Timeout after {max_attempts} attempts"

        except Exception as e:
            logger.error(f"Error checking authorization: {str(e)}")
            return False, f"AUTHORIZATION_EXCEPTION: {str(e)}"

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
            'processor_version': 'JAR_JAVA_OFICIAL',
        }

    def validate_company_setup(self):
        """Validar configuración de la empresa."""
        try:
            errors = []

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