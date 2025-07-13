from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse, Http404
import os
from .models import (
    SRIConfiguration, ElectronicDocument, DocumentItem,
    DocumentTax, SRIResponse
)

@admin.register(SRIConfiguration)
class SRIConfigurationAdmin(admin.ModelAdmin):
    # CORREGIDO: 'establishment' -> 'establishment_code'
    list_display = ('company', 'environment', 'establishment_code', 'emission_point', 'accounting_required')
    list_filter = ('environment', 'accounting_required')
    search_fields = ('company__business_name',)
    
    fieldsets = (
        ('🏢 Empresa', {
            'fields': ('company', 'environment')
        }),
        ('🏪 Punto de Emisión', {
            'fields': ('establishment_code', 'emission_point')
        }),
        ('🔢 Secuenciales', {
            'fields': ('invoice_sequence', 'credit_note_sequence', 'debit_note_sequence'),
        }),
        ('📧 Email', {
            'fields': ('email_enabled', 'email_subject_template', 'email_body_template'),
            'classes': ('collapse',)
        }),
        ('⚙️ Configuración Adicional', {
            'fields': ('accounting_required', 'special_taxpayer', 'special_taxpayer_number'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ElectronicDocument)
class ElectronicDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'document_number', 'company_name', 'document_type', 'customer_name',
        'total_amount', 'status_colored', 'file_links', 'issue_date'
    )
    list_filter = ('document_type', 'status', 'issue_date', 'company')
    search_fields = (
        'document_number', 'customer_name', 'customer_identification',
        'access_key', 'company__business_name'
    )
    ordering = ('-created_at',)
    readonly_fields = (
        'access_key', 'xml_file', 'signed_xml_file', 'pdf_file',
        'sri_authorization_code', 'sri_authorization_date',
        'created_at', 'updated_at', 'document_preview'
    )
    
    fieldsets = (
        ('🏢 Empresa', {
            'fields': ('company',)
        }),
        ('📄 Documento', {
            'fields': ('document_type', 'document_number', 'issue_date', 'access_key')
        }),
        ('👤 Cliente', {
            'fields': (
                'customer_name', 'customer_identification', 'customer_identification_type',
                'customer_address', 'customer_phone', 'customer_email'
            )
        }),
        ('💰 Totales', {
            'fields': ('subtotal_without_tax', 'total_tax', 'total_amount')
        }),
        ('📁 Archivos Generados', {
            'fields': ('document_preview', 'xml_file', 'signed_xml_file', 'pdf_file'),
            'classes': ('collapse',)
        }),
        ('🏛️ SRI', {
            'fields': ('status', 'sri_authorization_code', 'sri_authorization_date'),
        }),
        ('📅 Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/download_xml/', self.admin_site.admin_view(self.download_xml), name='download_xml'),
            path('<int:pk>/download_pdf/', self.admin_site.admin_view(self.download_pdf), name='download_pdf'),
            path('<int:pk>/preview/', self.admin_site.admin_view(self.preview_document), name='preview_document'),
        ]
        return custom_urls + urls
    
    def download_xml(self, request, pk):
        """Descargar archivo XML"""
        try:
            document = ElectronicDocument.objects.get(pk=pk)
        except ElectronicDocument.DoesNotExist:
            raise Http404("Documento no encontrado")
            
        xml_file = document.signed_xml_file or document.xml_file
        
        if xml_file and os.path.exists(str(xml_file)):
            with open(str(xml_file), 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/xml')
                response['Content-Disposition'] = f'attachment; filename="{document.document_number}.xml"'
                return response
        raise Http404("Archivo XML no encontrado")
    
    def download_pdf(self, request, pk):
        """Descargar archivo PDF"""
        try:
            document = ElectronicDocument.objects.get(pk=pk)
        except ElectronicDocument.DoesNotExist:
            raise Http404("Documento no encontrado")
        
        if document.pdf_file and os.path.exists(str(document.pdf_file)):
            with open(str(document.pdf_file), 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{document.document_number}.pdf"'
                return response
        raise Http404("Archivo PDF no encontrado")
    
    def preview_document(self, request, pk):
        """Vista previa del documento"""
        try:
            document = ElectronicDocument.objects.get(pk=pk)
        except ElectronicDocument.DoesNotExist:
            raise Http404("Documento no encontrado")
            
        context = {
            'document': document,
            'title': f'Vista Previa - {document.document_number}',
        }
        return render(request, 'admin/sri_integration/document_preview.html', context)
    
    def company_name(self, obj):
        return obj.company.business_name
    company_name.short_description = '🏢 Empresa'
    
    def status_colored(self, obj):
        colors = {
            'DRAFT': 'gray',
            'GENERATED': 'blue',
            'SIGNED': 'orange',
            'SENT': 'green',
            'AUTHORIZED': 'darkgreen',
            'REJECTED': 'red',
            'ERROR': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = '📊 Estado'
    
    def file_links(self, obj):
        """Enlaces a archivos generados"""
        links = []
        
        if obj.xml_file and os.path.exists(str(obj.xml_file)):
            links.append(
                f'<a href="/admin/sri_integration/electronicdocument/{obj.pk}/download_xml/" '
                f'style="color: blue;" title="Descargar XML">📄 XML</a>'
            )
        
        if obj.signed_xml_file and os.path.exists(str(obj.signed_xml_file)):
            links.append(
                f'<a href="/admin/sri_integration/electronicdocument/{obj.pk}/download_xml/" '
                f'style="color: green;" title="Descargar XML Firmado">🔐 XML Firmado</a>'
            )
        
        if obj.pdf_file and os.path.exists(str(obj.pdf_file)):
            links.append(
                f'<a href="/admin/sri_integration/electronicdocument/{obj.pk}/download_pdf/" '
                f'style="color: red;" title="Descargar PDF">📋 PDF</a>'
            )
        
        if links:
            return format_html(' | '.join(links))
        return format_html('<span style="color: gray;">Sin archivos</span>')
    file_links.short_description = '📁 Archivos'
    
    def document_preview(self, obj):
        """Vista previa del documento"""
        return format_html('''
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
                <strong>📋 Resumen del Documento:</strong><br>
                <strong>Tipo:</strong> {}<br>
                <strong>Número:</strong> {}<br>
                <strong>Cliente:</strong> {}<br>
                <strong>Fecha:</strong> {}<br>
                <strong>Total:</strong> ${:.2f}<br>
                <strong>Estado:</strong> {}<br>
                <strong>Clave de Acceso:</strong> {}<br>
                <br>
                <a href="/admin/sri_integration/electronicdocument/{}/preview/" 
                   style="background: #007cba; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;">
                   👁️ Ver Detalles
                </a>
            </div>
        ''',
            obj.get_document_type_display(),
            obj.document_number,
            obj.customer_name,
            obj.issue_date.strftime('%Y-%m-%d'),
            obj.total_amount,
            obj.get_status_display(),
            obj.access_key,
            obj.pk
        )
    document_preview.short_description = '📄 Vista Previa'

@admin.register(DocumentItem)
class DocumentItemAdmin(admin.ModelAdmin):
    list_display = ('document', 'description', 'quantity', 'unit_price', 'subtotal_formatted')
    list_filter = ('document__document_type', 'document__company')
    search_fields = ('description', 'main_code', 'document__document_number')
    
    def subtotal_formatted(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal_formatted.short_description = 'Subtotal'

@admin.register(DocumentTax)
class DocumentTaxAdmin(admin.ModelAdmin):
    list_display = ('document', 'tax_code', 'rate', 'taxable_base', 'tax_amount')
    list_filter = ('tax_code', 'percentage_code')
    search_fields = ('document__document_number',)

@admin.register(SRIResponse)
class SRIResponseAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'operation_type', 'response_code',
        'success_colored', 'created_at'
    )
    list_filter = ('operation_type', 'response_code', 'created_at')
    search_fields = ('document__document_number', 'response_message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'raw_response')
    
    fieldsets = (
        ('📄 Documento', {
            'fields': ('document', 'operation_type')
        }),
        ('📨 Respuesta', {
            'fields': ('response_code', 'response_message')
        }),
        ('🔍 Detalles', {
            'fields': ('raw_response', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_colored(self, obj):
        success_codes = ['RECIBIDA', 'AUTORIZADO', '200', 'OK']
        if obj.response_code in success_codes:
            return format_html('<span style="color: green;">✅ Éxito</span>')
        return format_html('<span style="color: red;">❌ Error</span>')
    success_colored.short_description = '✅ Estado'