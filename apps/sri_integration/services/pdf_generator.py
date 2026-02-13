# -*- coding: utf-8 -*-
"""
Generador de PDF (RIDE) para documentos del SRI
"""

import logging
import io
import qrcode
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.platypus.flowables import HRFlowable
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generador de PDF (RIDE) para documentos electrónicos del SRI
    """
    
    def __init__(self, document):
        self.document = document
        self.company = document.company
        self.sri_config = self.company.sri_configuration
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """
        Configura estilos personalizados para el PDF
        """
        # Estilo para título principal
        self.styles.add(ParagraphStyle(
            name='CompanyTitle',
            parent=self.styles['Title'],
            fontSize=16,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=6
        ))
        
        # Estilo para subtítulos
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            alignment=0,  # Izquierda
            spaceBefore=12,
            spaceAfter=6
        ))
        
        # Estilo para datos de empresa
        self.styles.add(ParagraphStyle(
            name='CompanyData',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=1,  # Centro
            spaceAfter=3
        ))
        
        # Estilo para encabezados de tabla
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            alignment=1,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para celdas de tabla
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            alignment=0
        ))
        
        # Estilo para totales
        self.styles.add(ParagraphStyle(
            name='TotalStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=2,  # Derecha
            fontName='Helvetica-Bold'
        ))
    
    def generate_invoice_pdf(self):
        """
        Genera PDF para factura electrónica
        """
        try:
            # Crear buffer para el PDF
            buffer = io.BytesIO()
            
            # Crear documento
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Construir contenido
            story = []
            
            # Encabezado
            story.extend(self._build_header())
            
            # Información de la factura
            story.extend(self._build_invoice_info())
            
            # Información del cliente
            story.extend(self._build_customer_info())
            
            # Detalles de productos/servicios
            story.extend(self._build_invoice_details())
            
            # Totales
            story.extend(self._build_invoice_totals())
            
            # Información adicional
            story.extend(self._build_additional_info())
            
            # Información de autorización
            story.extend(self._build_authorization_info())
            
            # Pie de página con QR
            story.extend(self._build_footer())
            
            # Construir PDF
            doc.build(story)
            
            # Obtener contenido del buffer
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except Exception as e:
            logger.error(f"Error generating invoice PDF: {str(e)}")
            raise ValueError(f"Error generating invoice PDF: {str(e)}")

    def generate_credit_note_pdf(self):
        """
        Genera PDF para nota de crédito
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=20*mm, leftMargin=20*mm,
                topMargin=20*mm, bottomMargin=20*mm
            )
            story = []
            
            story.extend(self._build_header())
            story.extend(self._build_invoice_info()) # Info tributaria común
            story.extend(self._build_modified_doc_info()) # Info documento modificado
            story.extend(self._build_customer_info())
            story.extend(self._build_invoice_details()) # Reusa detalles (items)
            story.extend(self._build_invoice_totals())
            story.extend(self._build_additional_info())
            story.extend(self._build_authorization_info())
            story.extend(self._build_footer())
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            return pdf_content
        except Exception as e:
            logger.error(f"Error generating credit note PDF: {str(e)}")
            raise ValueError(f"Error generating credit note PDF: {str(e)}")

    def generate_debit_note_pdf(self):
        """
        Genera PDF para nota de débito
        """
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=20*mm, leftMargin=20*mm,
                topMargin=20*mm, bottomMargin=20*mm
            )
            story = []
            
            story.extend(self._build_header())
            story.extend(self._build_invoice_info())
            story.extend(self._build_modified_doc_info())
            story.extend(self._build_customer_info())
            story.extend(self._build_debit_note_reasons()) # Motivos en lugar de items
            story.extend(self._build_invoice_totals()) # Totales funcionan igual
            story.extend(self._build_additional_info())
            story.extend(self._build_authorization_info())
            story.extend(self._build_footer())
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            return pdf_content
        except Exception as e:
            logger.error(f"Error generating debit note PDF: {str(e)}")
            raise ValueError(f"Error generating debit note PDF: {str(e)}")

    def _build_modified_doc_info(self):
        """
        Construye información del documento modificado (para NC/ND)
        """
        elements = []
        if hasattr(self.document, 'modified_document_number') and self.document.modified_document_number:
            elements.append(Paragraph("DOCUMENTO MODIFICADO", self.styles['SectionTitle']))
            
            data = [
                [f"Comprobante Modificado ({self.document.get_modified_document_type_display()}):", self.document.modified_document_number],
                ["Fecha Emisión (Sustento):", self.document.modified_document_date.strftime('%d/%m/%Y') if self.document.modified_document_date else ""],
                ["Razón de Modificación:", getattr(self.document, 'modification_reason', '')]
            ]
            
            table = Table(data, colWidths=[2.5*inch, 3*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 5*mm))
        return elements

    def _build_debit_note_reasons(self):
        """
        Construye tabla de motivos para Nota de Débito
        """
        elements = []
        elements.append(Paragraph("RAZONES DE LA MODIFICACIÓN", self.styles['SectionTitle']))
        
        headers = ["Razón", "Valor"]
        table_data = [headers]
        
        # Asumiendo que usamos 'items' o 'motives'
        items = getattr(self.document, 'items', None) or getattr(self.document, 'motives', None)
        if items and items.exists():
            for item in items.all():
                desc = getattr(item, 'description', getattr(item, 'reason', ''))
                val = getattr(item, 'value', getattr(item, 'subtotal', 0))
                row = [desc, f"${val:.2f}"]
                table_data.append(row)
        
        table = Table(table_data, colWidths=[4*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))
        return elements
    
    def _build_header(self):
        """
        Construye el encabezado del documento
        """
        elements = []
        
        # Tabla principal del encabezado
        header_data = [
            [
                # Columna izquierda - Datos de la empresa
                [
                    Paragraph(self.company.business_name, self.styles['CompanyTitle']),
                    Paragraph(f"<b>RUC:</b> {self.company.ruc}", self.styles['CompanyData']),
                    Paragraph(f"<b>Dirección:</b> {self.company.address}", self.styles['CompanyData']),
                    Paragraph(f"<b>Teléfono:</b> {self.company.phone}", self.styles['CompanyData']) if self.company.phone else "",
                    Paragraph(f"<b>Email:</b> {self.company.email}", self.styles['CompanyData']),
                ],
                # Columna derecha - Tipo de documento y numeración
                [
                    Paragraph(f"<b>{self.document.get_document_type_display().upper()}</b>", self.styles['CompanyTitle']),
                    Paragraph(f"<b>No:</b> {self.document.document_number}", self.styles['CompanyData']),
                    Paragraph(f"<b>Fecha:</b> {self.document.issue_date.strftime('%d/%m/%Y')}", self.styles['CompanyData']),
                    Paragraph(f"<b>Ambiente:</b> {self.sri_config.get_environment_display()}", self.styles['CompanyData']),
                ]
            ]
        ]
        
        header_table = Table(header_data, colWidths=[3.5*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        return elements
    
    def _build_invoice_info(self):
        """
        Construye la información de la factura
        """
        elements = []
        
        # Información de contribuyente especial y contabilidad
        info_data = []
        
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            info_data.append(f"CONTRIBUYENTE ESPECIAL No: {self.sri_config.special_taxpayer_number}")
        
        info_data.append(f"OBLIGADO A LLEVAR CONTABILIDAD: {'SÍ' if self.sri_config.accounting_required else 'NO'}")
        
        for info in info_data:
            elements.append(Paragraph(info, self.styles['CompanyData']))
        
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_customer_info(self):
        """
        Construye la información del cliente
        """
        elements = []
        
        elements.append(Paragraph("DATOS DEL CLIENTE", self.styles['SectionTitle']))
        
        customer_data = [
            ["Razón Social:", self.document.customer_name],
            ["Identificación:", f"{self.document.customer_identification} ({self.document.get_customer_identification_type_display()})"],
        ]
        
        if self.document.customer_address:
            customer_data.append(["Dirección:", self.document.customer_address])
        
        if self.document.customer_phone:
            customer_data.append(["Teléfono:", self.document.customer_phone])
        
        if self.document.customer_email:
            customer_data.append(["Email:", self.document.customer_email])
        
        customer_table = Table(customer_data, colWidths=[1.5*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(customer_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_invoice_details(self):
        """
        Construye la tabla de detalles de la factura
        """
        elements = []
        
        elements.append(Paragraph("DETALLE", self.styles['SectionTitle']))
        
        # Encabezados de la tabla
        headers = [
            "Código",
            "Descripción", 
            "Cant.",
            "P. Unit.",
            "Desc.",
            "Subtotal"
        ]
        
        # Datos de la tabla
        table_data = [headers]
        
        for item in self.document.items.all():
            row = [
                item.main_code,
                item.description,
                f"{item.quantity:.2f}",
                f"${item.unit_price:.2f}",
                f"${item.discount:.2f}",
                f"${item.subtotal:.2f}"
            ]
            table_data.append(row)
        
        # Crear tabla
        details_table = Table(table_data, colWidths=[
            1*inch,    # Código
            2.5*inch,  # Descripción
            0.7*inch,  # Cantidad
            0.8*inch,  # Precio
            0.7*inch,  # Descuento
            0.8*inch   # Subtotal
        ])
        
        # Estilo de la tabla
        table_style = [
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Contenido
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Código
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Descripción
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),   # Números
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        details_table.setStyle(TableStyle(table_style))
        
        elements.append(details_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_invoice_totals(self):
        """
        Construye la sección de totales
        """
        elements = []
        
        # Tabla de totales
        totals_data = [
            ["SUBTOTAL SIN IMPUESTOS:", f"${self.document.subtotal_without_tax:.2f}"],
            ["DESCUENTO:", f"${self.document.total_discount:.2f}"],
        ]
        
        # Agregar impuestos
        taxes_summary = {}
        for tax in self.document.taxes.all():
            tax_name = f"{tax.get_tax_code_display()} {tax.rate}%"
            if tax_name not in taxes_summary:
                taxes_summary[tax_name] = 0
            taxes_summary[tax_name] += tax.tax_amount
        
        for tax_name, tax_amount in taxes_summary.items():
            totals_data.append([f"{tax_name}:", f"${tax_amount:.2f}"])
        
        totals_data.append(["TOTAL:", f"${self.document.total_amount:.2f}"])
        
        # Crear tabla alineada a la derecha
        totals_table = Table(totals_data, colWidths=[2*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Última fila en negrita
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, -1), (-1, -1), 1, colors.black),  # Borde solo en total
        ]))
        
        # Alinear tabla a la derecha
        totals_flow = Table([[totals_table]], colWidths=[6.5*inch])
        totals_flow.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ]))
        
        elements.append(totals_flow)
        elements.append(Spacer(1, 10*mm))
        
        return elements
    
    def _build_additional_info(self):
        """
        Construye información adicional si existe
        """
        elements = []
        
        if self.document.additional_data:
            elements.append(Paragraph("INFORMACIÓN ADICIONAL", self.styles['SectionTitle']))
            
            for key, value in self.document.additional_data.items():
                elements.append(Paragraph(f"<b>{key}:</b> {value}", self.styles['Normal']))
            
            elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_authorization_info(self):
        """
        Construye información de autorización del SRI
        """
        elements = []
        
        elements.append(Paragraph("INFORMACIÓN DE AUTORIZACIÓN", self.styles['SectionTitle']))
        
        auth_data = [
            ["CLAVE DE ACCESO:", self.document.access_key],
        ]
        
        if self.document.sri_authorization_code:
            auth_data.extend([
                ["No. AUTORIZACIÓN:", self.document.sri_authorization_code],
                ["FECHA AUTORIZACIÓN:", self.document.sri_authorization_date.strftime('%d/%m/%Y %H:%M:%S') if self.document.sri_authorization_date else ""],
                ["ESTADO:", "AUTORIZADO"],
            ])
        else:
            auth_data.append(["ESTADO:", "PENDIENTE DE AUTORIZACIÓN"])
        
        auth_table = Table(auth_data, colWidths=[2*inch, 4*inch])
        auth_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(auth_table)
        elements.append(Spacer(1, 5*mm))
        
        return elements
    
    def _build_footer(self):
        """
        Construye el pie de página con código QR
        """
        elements = []
        
        # Generar código QR
        qr_img = self._generate_qr_code()
        
        if qr_img:
            # Tabla con QR e información
            footer_data = [
                [
                    qr_img,
                    [
                        Paragraph("Código QR para verificación", self.styles['Normal']),
                        Paragraph(f"Clave de Acceso: {self.document.access_key}", self.styles['TableCell']),
                        Paragraph("Consulte su documento en: www.sri.gob.ec", self.styles['TableCell']),
                    ]
                ]
            ]
            
            footer_table = Table(footer_data, colWidths=[1.5*inch, 4.5*inch])
            footer_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ]))
            
            elements.append(footer_table)
        
        return elements
    
    def _generate_qr_code(self):
        """
        Genera código QR con la clave de acceso
        """
        try:
            # Crear QR con la clave de acceso
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(self.document.access_key)
            qr.make(fit=True)
            
            # Crear imagen
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convertir a formato que ReportLab pueda usar
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Crear objeto Image de ReportLab
            reportlab_img = Image(img_buffer, width=1*inch, height=1*inch)
            
            return reportlab_img
            
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return None