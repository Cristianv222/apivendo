# -*- coding: utf-8 -*-
"""
Servicio de envío de emails para documentos electrónicos
"""

import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from apps.core.models import AuditLog

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio para envío de documentos electrónicos por email
    """
    
    def __init__(self, company):
        self.company = company
        self.sri_config = company.sri_configuration
    
    def send_document_email(self, document):
        """
        Envía un documento electrónico por email
        """
        try:
            if not document.customer_email:
                return False, "Customer email not provided"
            
            if not self.sri_config.email_enabled:
                return False, "Email sending is disabled for this company"
            
            # Preparar datos para el template
            context = self._prepare_email_context(document)
            
            # Generar contenido del email
            subject = self._generate_subject(document)
            html_content = self._generate_html_content(context)
            text_content = self._generate_text_content(context)
            
            # Crear email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[document.customer_email],
                reply_to=[self.company.email]
            )
            
            # Adjuntar HTML
            email.attach_alternative(html_content, "text/html")
            
            # Adjuntar archivos
            self._attach_files(email, document)
            
            # Enviar
            email.send()
            
            # Log de auditoría
            AuditLog.objects.create(
                action='SEND',
                model_name='EmailDocument',
                object_id=str(document.id),
                object_representation=f"Email to {document.customer_email}",
                additional_data={
                    'document_type': document.document_type,
                    'document_number': document.document_number,
                    'customer_email': document.customer_email,
                    'subject': subject
                }
            )
            
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending email for document {document.id}: {str(e)}")
            return False, str(e)
    
    def send_authorization_notification(self, document):
        """
        Envía notificación de autorización de documento
        """
        try:
            if not document.customer_email:
                return False, "Customer email not provided"
            
            context = self._prepare_email_context(document)
            context['is_authorization_notification'] = True
            
            subject = f"Documento Autorizado - {document.get_document_type_display()} {document.document_number}"
            html_content = self._generate_html_content(context)
            text_content = self._generate_text_content(context)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[document.customer_email],
                reply_to=[self.company.email]
            )
            
            email.attach_alternative(html_content, "text/html")
            self._attach_files(email, document)
            
            email.send()
            
            return True, "Authorization notification sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending authorization notification for document {document.id}: {str(e)}")
            return False, str(e)
    
    def _prepare_email_context(self, document):
        """
        Prepara el contexto para los templates de email
        """
        return {
            'document': document,
            'company': self.company,
            'sri_config': self.sri_config,
            'document_type_display': document.get_document_type_display(),
            'status_display': document.get_status_display(),
            'is_authorized': document.status == 'AUTHORIZED',
        }
    
    def _generate_subject(self, document):
        """
        Genera el asunto del email usando el template configurado
        """
        try:
            template = self.sri_config.email_subject_template
            return template.format(
                document_type=document.get_document_type_display(),
                document_number=document.document_number,
                company_name=self.company.business_name,
                customer_name=document.customer_name
            )
        except Exception:
            # Fallback si hay error en el template
            return f"Documento Electrónico - {document.get_document_type_display()} {document.document_number}"
    
    def _generate_html_content(self, context):
        """
        Genera el contenido HTML del email
        """
        try:
            return render_to_string('email_templates/document_email.html', context)
        except Exception as e:
            logger.warning(f"Error loading HTML template: {str(e)}")
            # Fallback HTML simple
            return self._generate_fallback_html(context)
    
    def _generate_text_content(self, context):
        """
        Genera el contenido de texto plano del email
        """
        try:
            template = self.sri_config.email_body_template
            return template.format(
                document_type=context['document_type_display'],
                document_number=context['document'].document_number,
                company_name=self.company.business_name,
                customer_name=context['document'].customer_name
            )
        except Exception:
            # Fallback si hay error en el template
            return f"""Estimado cliente,

En archivo adjunto encontrará su {context['document_type_display']} electrónico número {context['document'].document_number}.

Saludos cordiales,
{self.company.business_name}"""
    
    def _generate_fallback_html(self, context):
        """
        Genera HTML simple como fallback
        """
        document = context['document']
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Documento Electrónico</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .footer {{ font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{self.company.business_name}</h2>
                <p>RUC: {self.company.ruc}</p>
            </div>
            
            <div class="content">
                <h3>Estimado/a {document.customer_name},</h3>
                
                <p>En archivo adjunto encontrará su <strong>{context['document_type_display']}</strong> 
                electrónico número <strong>{document.document_number}</strong>.</p>
                
                <h4>Detalles del Documento:</h4>
                <ul>
                    <li><strong>Número:</strong> {document.document_number}</li>
                    <li><strong>Fecha:</strong> {document.issue_date.strftime('%d/%m/%Y')}</li>
                    <li><strong>Total:</strong> ${document.total_amount:.2f}</li>
                    <li><strong>Estado:</strong> {context['status_display']}</li>
        """
        
        if document.sri_authorization_code:
            html += f"""
                    <li><strong>Autorización SRI:</strong> {document.sri_authorization_code}</li>
                    <li><strong>Fecha Autorización:</strong> {document.sri_authorization_date.strftime('%d/%m/%Y %H:%M:%S') if document.sri_authorization_date else ''}</li>
            """
        
        html += f"""
                </ul>
                
                <p>Para verificar la autenticidad del documento, puede consultar en el sitio web del SRI: 
                <a href="https://srienlinea.sri.gob.ec/facturacion-electronica/consultas/publico/comprobantes-electronicos">www.sri.gob.ec</a>
                usando la clave de acceso: <strong>{document.access_key}</strong></p>
                
                <p>Saludos cordiales.</p>
            </div>
            
            <div class="footer">
                <p>{self.company.business_name}<br>
                {self.company.address}<br>
                Email: {self.company.email}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _attach_files(self, email, document):
        """
        Adjunta archivos al email
        """
        try:
            # Adjuntar PDF si existe
            if document.pdf_file:
                with open(document.pdf_file.path, 'rb') as f:
                    email.attach(
                        f"{document.document_number}.pdf",
                        f.read(),
                        'application/pdf'
                    )
            
            # Adjuntar XML firmado si existe
            if document.signed_xml_file:
                with open(document.signed_xml_file.path, 'rb') as f:
                    email.attach(
                        f"{document.document_number}.xml",
                        f.read(),
                        'application/xml'
                    )
                    
        except Exception as e:
            logger.warning(f"Error attaching files to email: {str(e)}")
            # No es crítico, continuar sin archivos adjuntos