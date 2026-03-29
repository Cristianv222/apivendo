# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos — VERSIÓN PYTHON PURO

✅ Sin Java. Sin subprocess. Sin binarios externos.
   Firma XAdES-BES implementada 100% en Python con lxml + cryptography.
"""

import logging
import time
from datetime import datetime, timezone, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone as django_timezone
from django.conf import settings

from cryptography import x509

from apps.sri_integration.models import ElectronicDocument
from apps.sri_integration.services.xades_signer import XAdesBESSigner
from apps.sri_integration.services.xml_generator import XMLGenerator
from apps.sri_integration.services.pdf_generator import PDFGenerator
from apps.sri_integration.services.global_certificate_manager import get_certificate_manager
from apps.sri_integration.services.soap_client import SRISOAPClient
from apps.sri_integration.services.email_service import EmailService

logger = logging.getLogger(__name__)

ECUADOR_TZ = timezone(timedelta(hours=-5))


class DocumentProcessor:
    """
    Procesa documentos electrónicos del SRI:
      1. Genera XML
      2. Firma XML con XAdES-BES (Python puro)
      3. Envía al SRI por SOAP
      4. Consulta autorización
      5. Genera PDF RIDE
      6. Envía email
      7. Registra consumo de factura en billing
    """

    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
        self.cert_manager = get_certificate_manager()

    # ------------------------------------------------------------------
    # Flujo principal
    # ------------------------------------------------------------------

    def process_document(self, document, send_email=True, certificate_password=None):
        """Procesa completamente un documento electrónico."""
        try:
            with transaction.atomic():
                logger.info("Iniciando procesamiento de documento %s", document.id)

                # Validar certificado
                cert_data = self.cert_manager.get_certificate(self.company.id)
                if not cert_data:
                    return False, f"Certificate not available for company {self.company.id}"

                is_valid, val_msg = self.cert_manager.validate_certificate(self.company.id)
                if not is_valid:
                    return False, f"Certificate validation failed: {val_msg}"

                ok, cert_msg = self._verify_certificate(cert_data)
                if not ok:
                    return False, cert_msg

                # 1. Generar XML
                ok, xml_content = self._generate_xml(document)
                if not ok:
                    return False, f"XML generation failed: {xml_content}"

                # 2. Firmar XML (Python puro — sin Java)
                ok, signed_xml = self._sign_xml(document, xml_content, cert_data)
                if not ok:
                    return False, f"XML signing failed: {signed_xml}"

                # 3. Enviar al SRI
                ok, sri_msg = self._send_to_sri(document, signed_xml)
                if not ok:
                    return False, sri_msg

                # 4. Consultar autorización
                ok, auth_msg = self._check_authorization(document)
                if not ok:
                    logger.warning("Authorization check failed: %s", auth_msg)

                # 5. Generar PDF
                ok, pdf_msg = self._generate_pdf(document)
                if not ok:
                    logger.warning("PDF generation failed: %s", pdf_msg)

                document.refresh_from_db()

                # 6. Email y billing solo si fue autorizado
                if document.status == "AUTHORIZED":
                    if send_email:
                        self._send_email(document)
                    self._consume_invoice_from_plan(document)

                logger.info(
                    "Documento %s procesado con estado: %s",
                    document.id, document.status,
                )
                return True, f"Document processed successfully with status: {document.status}"

        except Exception as e:
            logger.exception("Critical error processing document %s", document.id)
            document.status = "ERROR"
            document.save()
            return False, f"PROCESSOR_CRITICAL_ERROR: {e}"

    # ------------------------------------------------------------------
    # Pasos individuales
    # ------------------------------------------------------------------

    def _verify_certificate(self, cert_data):
        """Verifica que el certificado tenga capacidad de firma digital."""
        try:
            certificate = cert_data.certificate
            logger.info("Proveedor: %s", certificate.issuer.rfc4514_string())

            now = datetime.now(timezone.utc)

            not_after = (
                certificate.not_valid_after_utc
                if hasattr(certificate, "not_valid_after_utc")
                else certificate.not_valid_after.replace(tzinfo=timezone.utc)
            )
            not_before = (
                certificate.not_valid_before_utc
                if hasattr(certificate, "not_valid_before_utc")
                else certificate.not_valid_before.replace(tzinfo=timezone.utc)
            )

            if not_after < now:
                return False, f"Certificate expired on {not_after}"
            if not_before > now:
                return False, f"Certificate not valid until {not_before}"

            try:
                key_usage = certificate.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                ).value
                if not key_usage.digital_signature:
                    return False, "Certificate does not have Digital Signature key usage"
            except x509.ExtensionNotFound:
                logger.warning("Key Usage extension not found — proceeding anyway")

            return True, "Certificate valid"

        except Exception as e:
            logger.error("Error verifying certificate: %s", e)
            return False, f"Certificate verification failed: {e}"

    def _generate_xml(self, document):
        """Genera el XML del documento."""
        try:
            generators = {
                "INVOICE": "generate_invoice_xml",
                "CREDIT_NOTE": "generate_credit_note_xml",
                "DEBIT_NOTE": "generate_debit_note_xml",
                "RETENTION": "generate_retention_xml",
                "PURCHASE_SETTLEMENT": "generate_purchase_settlement_xml",
            }
            method_name = generators.get(document.document_type)
            if not method_name:
                return False, f"Unsupported document type: {document.document_type}"

            xml_gen = XMLGenerator(document)
            xml_content = getattr(xml_gen, method_name)()

            filename = f"{document.access_key}.xml"
            document.xml_file.save(
                filename, ContentFile(xml_content.encode("utf-8")), save=True
            )
            logger.info("XML generado: %d chars", len(xml_content))
            return True, xml_content

        except Exception as e:
            logger.error("Error generating XML: %s", e)
            return False, f"XML_GENERATION_ERROR: {e}"

    def _sign_xml(self, document, xml_content, cert_data):
        """
        Firma el XML usando XAdesBESSigner (100% Python, sin Java).

        cert_data: objeto CertificateData del GlobalCertificateManager.
        """
        try:
            logger.info(
                "🔐 Firmando XML para documento %s (Python puro)", document.id
            )

            signer = XAdesBESSigner(cert_data.private_key, cert_data.certificate)
            signed_xml = signer.sign(xml_content)

            filename = f"{document.access_key}_signed.xml"
            document.signed_xml_file.save(
                filename, ContentFile(signed_xml.encode("utf-8")), save=True
            )
            document.status = "SIGNED"
            document.save()
            cert_data.update_usage()

            logger.info("✅ XML firmado correctamente para documento %s", document.id)
            return True, signed_xml

        except Exception as e:
            logger.error("Error signing XML for document %s: %s", document.id, e)
            return False, f"XML_SIGNING_ERROR: {e}"

    def _send_to_sri(self, document, signed_xml):
        """Envía el XML firmado al SRI por SOAP."""
        try:
            if isinstance(signed_xml, bytes):
                signed_xml = signed_xml.decode("utf-8")

            logger.info("Enviando documento %s al SRI (%d chars)", document.id, len(signed_xml))

            sri_client = SRISOAPClient(self.company)
            success, message = sri_client.send_document_to_reception(document, signed_xml)

            if success:
                document.status = "SENT"
                document.save()
                return True, message
            return False, f"SRI_SUBMISSION_FAILED: {message}"

        except Exception as e:
            logger.error("SRI submission exception: %s", e)
            return False, f"PROCESSOR_SRI_EXCEPTION: {e}"

    def _check_authorization(self, document, max_attempts=10, wait_seconds=30):
        """Consulta la autorización del SRI con reintentos."""
        try:
            logger.info("Consultando autorización para documento %s", document.id)
            original_status = document.status
            sri_client = SRISOAPClient(self.company)

            logger.info("Esperando 10s antes de consultar autorización...")
            time.sleep(10)

            for attempt in range(max_attempts):
                if attempt > 0:
                    logger.info(
                        "Esperando %ds (intento %d/%d)...",
                        wait_seconds, attempt + 1, max_attempts,
                    )
                    time.sleep(wait_seconds)

                success, message = sri_client.get_document_authorization(document)
                if success:
                    logger.info("Documento %s autorizado por el SRI", document.id)
                    return True, message

                # Si el documento aún no aparece o sigue en proceso (o hay error temporal del SRI), reintentar
                temporary_keywords = ["proceso", "pendiente", "not yet processed", "no authorizations", "internal service error", "temporary", "no existen datos", "clv no registrada"]
                if any(kw in message.lower() for kw in temporary_keywords):
                    logger.info("Estado temporal o clave aún no disponible ('%s') — reintentando...", message)
                    continue

                # Error definitivo
                logger.error("Error definitivo en autorización: %s", message)
                if original_status in ("SENT", "AUTHORIZED"):
                    document.status = original_status
                    document.save()
                return False, f"AUTHORIZATION_ERROR: {message}"

            logger.warning("Timeout en autorización para documento %s", document.id)
            if original_status in ("SENT", "AUTHORIZED"):
                document.status = original_status
                document.save()
            return False, f"AUTHORIZATION_TIMEOUT after {max_attempts} attempts"

        except Exception as e:
            logger.error("Error checking authorization: %s", e)
            return False, f"AUTHORIZATION_EXCEPTION: {e}"

    def _generate_pdf(self, document):
        """Genera el PDF RIDE del documento."""
        try:
            generators = {
                "INVOICE": "generate_invoice_pdf",
                "CREDIT_NOTE": "generate_credit_note_pdf",
                "DEBIT_NOTE": "generate_debit_note_pdf",
            }
            method_name = generators.get(document.document_type)
            if not method_name:
                return False, f"PDF not implemented for {document.document_type}"

            pdf_gen = PDFGenerator(document)
            pdf_content = getattr(pdf_gen, method_name)()

            filename = f"{document.access_key}.pdf"
            document.pdf_file.save(filename, ContentFile(pdf_content), save=True)
            logger.info("PDF generado para documento %s", document.id)
            return True, "PDF generated"

        except Exception as e:
            logger.error("Error generating PDF: %s", e)
            return False, f"PDF_GENERATION_ERROR: {e}"

    def _send_email(self, document):
        """Envía el documento autorizado por email al cliente (en segundo plano)."""
        try:
            if not document.customer_email:
                return False, "Customer email not provided"
            
            # Verificar si el envío de email está habilitado (GLOBAL)
            if not getattr(settings, 'SRI_AUTO_EMAIL', True):
                logger.info("📧 [PROCESSOR] Global email sending is DISABLED. Skipping.")
                return False, "Global email sending is disabled"

            # Verificar si el envío de email está habilitado para la empresa
            if not self.sri_config.email_enabled:
                logger.info("📧 [PROCESSOR] Email sending is disabled for company %s", self.company.id)
                return False, "Email sending is disabled for company"

            # 🚀 ENVIAR A SEGUNDO PLANO (CELERY)
            # Usamos import local para evitar importación circular con tasks.py
            from apps.sri_integration.tasks import send_authorization_notification_email
            
            logger.info("📧 [PROCESSOR] Scheduling background email for document %s", document.id)
            send_authorization_notification_email.delay(document.id)
            
            return True, "Email scheduled in background"

        except Exception as e:
            logger.error("Error scheduling background email: %s", e)
            return False, f"EMAIL_SCHEDULING_EXCEPTION: {e}"

    def _consume_invoice_from_plan(self, document):
        """Descuenta una factura del plan de billing."""
        try:
            from apps.billing.models import CompanyBillingProfile, InvoiceConsumption

            profile = CompanyBillingProfile.objects.get(company=self.company)
            balance_before = profile.available_invoices

            if profile.consume_invoice():
                InvoiceConsumption.objects.create(
                    company=self.company,
                    invoice_id=str(document.access_key),
                    invoice_type=document.document_type,
                    balance_before=balance_before,
                    balance_after=profile.available_invoices,
                    api_endpoint="document_processor",
                )
                logger.info(
                    "✅ BILLING: factura consumida — empresa=%s doc=%s saldo=%s→%s",
                    self.company.id, document.access_key,
                    balance_before, profile.available_invoices,
                )
            else:
                logger.warning(
                    "⚠️ BILLING: sin facturas disponibles — empresa=%s saldo=%s",
                    self.company.id, balance_before,
                )

        except CompanyBillingProfile.DoesNotExist:
            logger.error(
                "❌ BILLING: no existe perfil para empresa %s", self.company.id
            )
        except Exception as e:
            logger.error("❌ BILLING: error inesperado — %s", e)

    # ------------------------------------------------------------------
    # Métodos de utilidad pública
    # ------------------------------------------------------------------

    def reprocess_document(self, document):
        """Reprocesa un documento que falló."""
        if document.status in ("AUTHORIZED", "SENT"):
            return False, "Document is already processed"

        logger.info("Reprocesando documento %s", document.id)
        document.status = "GENERATED"
        document.sri_authorization_code = ""
        document.sri_authorization_date = None
        document.sri_response = {}
        
        # En entorno de pruebas, forzar regeneración de número y clave
        try:
            if self.sri_config.environment == 'TEST':
                document.document_number = None
                document.access_key = None
        except:
            pass
            
        document.save()
        return self.process_document(document)

    def process_document_legacy(self, document, certificate_password, send_email=True):
        """Compatibilidad con llamadas antiguas."""
        logger.warning("Using legacy method for document %s", document.id)
        return self.process_document(document, send_email, certificate_password)

    def get_document_status(self, document):
        """Devuelve estado detallado del documento."""
        return {
            "id": document.id,
            "document_number": document.document_number,
            "access_key": document.access_key,
            "status": document.status,
            "status_display": document.get_status_display(),
            "issue_date": document.issue_date,
            "customer_name": document.customer_name,
            "total_amount": document.total_amount,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "processor_version": "PYTHON_PURE_XADES_BES",
        }

    def validate_company_setup(self):
        """Valida que la empresa esté correctamente configurada."""
        errors = []
        try:
            cfg = self.company.sri_configuration
            if not cfg.is_active:
                errors.append("SRI configuration is not active")
            if not cfg.establishment_code:
                errors.append("Establishment code not configured")
            if not cfg.emission_point:
                errors.append("Emission point not configured")
        except Exception:
            errors.append("SRI configuration not found")

        cert_data = self.cert_manager.get_certificate(self.company.id)
        if not cert_data:
            errors.append("Digital certificate not available")
        else:
            is_valid, msg = self.cert_manager.validate_certificate(self.company.id)
            if not is_valid:
                errors.append(f"Certificate validation failed: {msg}")

        if errors:
            return False, errors
        return True, "Company setup is valid"