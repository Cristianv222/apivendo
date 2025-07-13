# -*- coding: utf-8 -*-
"""
Procesador principal de documentos electrónicos
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
from apps.sri_integration.services.certificate_manager import CertificateManager
from apps.sri_integration.services.soap_client import SRISOAPClient
from apps.sri_integration.services.email_service import EmailService
from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Procesador principal de documentos electrónicos del SRI
    """
    
    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
        
    def process_document(self, document, certificate_password, send_email=True):
        """
        Procesa completamente un documento electrónico
        """
        try:
            with transaction.atomic():
                # 1. Generar XML
                success, xml_content = self._generate_xml(document)
                if not success:
                    return False, xml_content
                
                # 2. Firmar XML
                success, signed_xml = self._sign_xml(document, xml_content, certificate_password)
                if not success:
                    return False, signed_xml
                
                # 3. Enviar al SRI
                success, sri_message = self._send_to_sri(document, signed_xml)
                if not success:
                    return False, sri_message
                
                # 4. Consultar autorización
                success, auth_message = self._check_authorization(document)
                if not success:
                    return False, auth_message
                
                # 5. Generar PDF
                success, pdf_message = self._generate_pdf(document)
                if not success:
                    logger.warning(f"PDF generation failed: {pdf_message}")
                    # No es crítico, continuamos
                
                # 6. Enviar email si está autorizado
                if document.status == 'AUTHORIZED' and send_email:
                    success, email_message = self._send_email(document)
                    if not success:
                        logger.warning(f"Email sending failed: {email_message}")
                        # No es crítico, continuamos
                
                # Log de auditoría
                AuditLog.objects.create(
                    action='SEND',
                    model_name='ElectronicDocument',
                    object_id=str(document.id),
                    object_representation=str(document),
                    additional_data={
                        'status': document.status,
                        'sri_response': document.sri_response
                    }
                )
                
                return True, "Document processed successfully"
                
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {str(e)}")
            document.status = 'ERROR'
            document.save()
            return False, str(e)
    
    def reprocess_document(self, document, certificate_password):
        """
        Reprocesa un documento que falló anteriormente
        """
        try:
            if document.status in ['AUTHORIZED', 'SENT']:
                return False, "Document is already processed"
            
            # Resetear estado
            document.status = 'GENERATED'
            document.sri_authorization_code = ''
            document.sri_authorization_date = None
            document.sri_response = {}
            document.save()
            
            # Procesar nuevamente
            return self.process_document(document, certificate_password)
            
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
            else:
                return False, f"Unsupported document type: {document.document_type}"
            
            # Guardar XML
            filename = f"{document.access_key}.xml"
            document.xml_file.save(
                filename,
                ContentFile(xml_content.encode('utf-8')),
                save=True
            )
            
            return True, xml_content
            
        except Exception as e:
            logger.error(f"Error generating XML for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _sign_xml(self, document, xml_content, certificate_password):
        """
        Firma el XML con el certificado digital
        """
        try:
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
            logger.error(f"Error signing XML for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _send_to_sri(self, document, signed_xml):
        """
        Envía el documento firmado al SRI
        """
        try:
            sri_client = SRISOAPClient(self.company)
            success, message = sri_client.send_document_to_reception(document, signed_xml)
            
            if success:
                return True, message
            else:
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
                    time.sleep(wait_seconds)
                
                success, message = sri_client.get_document_authorization(document)
                
                if success:
                    return True, message
                
                # Si el documento aún está en proceso, continuar intentando
                if 'proceso' in message.lower() or 'pendiente' in message.lower():
                    logger.info(f"Document {document.id} still processing, attempt {attempt + 1}")
                    continue
                
                # Si hay error definitivo, parar
                return False, message
            
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
            else:
                # Por ahora solo facturas, expandir según necesidad
                return False, f"PDF generation not implemented for {document.document_type}"
            
            # Guardar PDF
            filename = f"{document.access_key}.pdf"
            document.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
            
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