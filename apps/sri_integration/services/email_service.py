# -*- coding: utf-8 -*-
"""
Servicio de envío de emails para documentos electrónicos
USANDO SENDGRID EXCLUSIVAMENTE
"""

import logging
from django.utils import timezone
from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio para envío de documentos electrónicos por email
    USA SOLO SENDGRID - NO USA DJANGO MAIL
    """
    
    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
    
    def send_document_email(self, document):
        """
        Envía un documento electrónico por email usando SOLO SendGrid
        """
        try:
            # Validaciones básicas
            if not document.customer_email:
                return False, "Customer email not provided"
            
            if not self.sri_config.email_enabled:
                return False, "Email sending is disabled for this company"
            
            # IMPORTAR Y USAR SENDGRID
            from apps.sri_integration.services.sendgrid_service import SendGridService
            sendgrid = SendGridService()
            
            # Verificar configuración
            if not sendgrid.api_key:
                logger.error("❌ SendGrid API key not configured")
                return False, "SendGrid API key not configured"
            
            # Obtener rutas de archivos
            xml_path = None
            pdf_path = None
            
            # XML firmado (preferido)
            if document.signed_xml_file:
                try:
                    xml_path = document.signed_xml_file.path
                    logger.info(f"✅ Using signed XML: {xml_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Cannot access signed XML: {e}")
            
            # XML regular si no hay firmado
            if not xml_path and document.xml_file:
                try:
                    xml_path = document.xml_file.path
                    logger.info(f"✅ Using regular XML: {xml_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Cannot access XML: {e}")
            
            # PDF
            if document.pdf_file:
                try:
                    pdf_path = document.pdf_file.path
                    logger.info(f"✅ Using PDF: {pdf_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Cannot access PDF: {e}")
            
            # Debe tener al menos un archivo
            if not xml_path and not pdf_path:
                logger.error("❌ No files to send")
                return False, "No files available to send"
            
            # Enviar con SendGrid
            logger.info(f"📤 Sending invoice via SendGrid to {document.customer_email}")
            
            success = sendgrid.send_invoice(
                to_email=document.customer_email,
                invoice_number=document.document_number,
                xml_path=xml_path if xml_path else "",
                pdf_path=pdf_path if pdf_path else "",
                cliente_nombre=document.customer_name
            )
            
            if success:
                # Actualizar documento
                document.email_sent = True
                document.email_sent_date = timezone.now()
                document.save()
                
                # Auditoría
                try:
                    AuditLog.objects.create(
                        action='SEND_EMAIL_SENDGRID',
                        model_name='ElectronicDocument',
                        object_id=str(document.id),
                        object_representation=f"SendGrid: {document.customer_email}",
                        additional_data={
                            'document_number': document.document_number,
                            'customer': document.customer_name,
                            'email': document.customer_email,
                            'service': 'SendGrid'
                        }
                    )
                except:
                    pass  # No crítico si falla auditoría
                
                logger.info(f"✅ SendGrid email sent successfully to {document.customer_email}")
                return True, f"Email sent successfully via SendGrid"
            else:
                logger.error(f"❌ SendGrid failed to send")
                return False, "SendGrid failed to send email"
                
        except Exception as e:
            logger.error(f"❌ SendGrid error: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def send_authorization_notification(self, document):
        """
        Notificación de autorización usando SendGrid
        """
        return self.send_document_email(document)