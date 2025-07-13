# -*- coding: utf-8 -*-
"""
Serializers for SRI integration
"""

from rest_framework import serializers
from django.db import transaction
from apps.sri_integration.models import (
    ElectronicDocument, 
    DocumentItem, 
    DocumentTax,
    SRIConfiguration,
    SRIResponse
)
from apps.companies.models import Company


class DocumentTaxSerializer(serializers.ModelSerializer):
    """
    Serializer para impuestos de documentos
    """
    tax_code_display = serializers.CharField(source='get_tax_code_display', read_only=True)
    percentage_code_display = serializers.CharField(source='get_percentage_code_display', read_only=True)
    
    class Meta:
        model = DocumentTax
        fields = [
            'id',
            'tax_code',
            'tax_code_display',
            'percentage_code', 
            'percentage_code_display',
            'rate',
            'taxable_base',
            'tax_amount'
        ]


class DocumentItemSerializer(serializers.ModelSerializer):
    """
    Serializer para items de documentos
    """
    taxes = DocumentTaxSerializer(many=True, required=False)
    
    class Meta:
        model = DocumentItem
        fields = [
            'id',
            'main_code',
            'auxiliary_code',
            'description',
            'quantity',
            'unit_price',
            'discount',
            'subtotal',
            'additional_details',
            'taxes'
        ]
        read_only_fields = ['subtotal']
    
    def create(self, validated_data):
        taxes_data = validated_data.pop('taxes', [])
        item = DocumentItem.objects.create(**validated_data)
        
        for tax_data in taxes_data:
            DocumentTax.objects.create(item=item, **tax_data)
        
        return item


class ElectronicDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer para documentos electrónicos (lectura)
    """
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    company_ruc = serializers.CharField(source='company.ruc', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_identification_type_display = serializers.CharField(
        source='get_customer_identification_type_display', read_only=True
    )
    
    items = DocumentItemSerializer(many=True, read_only=True)
    taxes = DocumentTaxSerializer(many=True, read_only=True)
    
    # URLs de archivos
    xml_file_url = serializers.SerializerMethodField()
    signed_xml_file_url = serializers.SerializerMethodField()
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ElectronicDocument
        fields = [
            'id',
            'company',
            'company_name',
            'company_ruc',
            'document_type',
            'document_type_display',
            'document_number',
            'access_key',
            'issue_date',
            'status',
            'status_display',
            
            # Cliente
            'customer_identification_type',
            'customer_identification_type_display',
            'customer_identification',
            'customer_name',
            'customer_address',
            'customer_email',
            'customer_phone',
            
            # Totales
            'subtotal_without_tax',
            'subtotal_with_tax',
            'total_discount',
            'total_tax',
            'total_amount',
            
            # SRI
            'sri_authorization_code',
            'sri_authorization_date',
            'sri_response',
            
            # Email
            'email_sent',
            'email_sent_date',
            
            # Archivos
            'xml_file_url',
            'signed_xml_file_url',
            'pdf_file_url',
            
            # Relaciones
            'items',
            'taxes',
            
            # Metadata
            'additional_data',
            'created_at',
            'updated_at'
        ]
    
    def get_xml_file_url(self, obj):
        if obj.xml_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.xml_file.url)
        return None
    
    def get_signed_xml_file_url(self, obj):
        if obj.signed_xml_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.signed_xml_file.url)
        return None
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
        return None


class ElectronicDocumentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear documentos electrónicos
    """
    items = DocumentItemSerializer(many=True)
    
    class Meta:
        model = ElectronicDocument
        fields = [
            'company',
            'document_type',
            'issue_date',
            
            # Cliente
            'customer_identification_type',
            'customer_identification',
            'customer_name',
            'customer_address',
            'customer_email',
            'customer_phone',
            
            # Items
            'items',
            
            # Datos adicionales
            'additional_data'
        ]
    
    def validate_company(self, value):
        """
        Valida que la empresa tenga configuración SRI activa
        """
        try:
            sri_config = value.sri_configuration
            if not sri_config.is_active:
                raise serializers.ValidationError("Company SRI configuration is not active")
        except Exception:
            raise serializers.ValidationError("Company does not have SRI configuration")
        
        return value
    
    def validate_items(self, value):
        """
        Valida que haya al menos un item
        """
        if not value:
            raise serializers.ValidationError("At least one item is required")
        
        for item_data in value:
            if item_data.get('quantity', 0) <= 0:
                raise serializers.ValidationError("Item quantity must be greater than 0")
            if item_data.get('unit_price', 0) <= 0:
                raise serializers.ValidationError("Item unit price must be greater than 0")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Obtener secuencial y generar número de documento
        company = validated_data['company']
        sri_config = company.sri_configuration
        document_number = sri_config.get_full_document_number(validated_data['document_type'])
        
        # Crear documento
        document = ElectronicDocument.objects.create(
            document_number=document_number,
            **validated_data
        )
        
        # Crear items y calcular totales
        subtotal_without_tax = 0
        total_discount = 0
        
        for item_data in items_data:
            taxes_data = item_data.pop('taxes', [])
            
            # Crear item
            item = DocumentItem.objects.create(document=document, **item_data)
            
            # Acumular totales
            subtotal_without_tax += item.subtotal
            total_discount += item.discount
            
            # Crear impuestos del item
            for tax_data in taxes_data:
                tax_data['taxable_base'] = item.subtotal
                tax_data['tax_amount'] = item.subtotal * (tax_data['rate'] / 100)
                DocumentTax.objects.create(document=document, item=item, **tax_data)
        
        # Calcular totales del documento
        total_tax = sum(tax.tax_amount for tax in document.taxes.all())
        
        document.subtotal_without_tax = subtotal_without_tax
        document.total_discount = total_discount
        document.total_tax = total_tax
        document.total_amount = subtotal_without_tax + total_tax
        document.save()
        
        return document


class SRIConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer para configuración SRI
    """
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)
    
    class Meta:
        model = SRIConfiguration
        fields = [
            'id',
            'company',
            'company_name',
            'environment',
            'environment_display',
            'reception_url',
            'authorization_url',
            'establishment_code',
            'emission_point',
            'invoice_sequence',
            'credit_note_sequence',
            'debit_note_sequence',
            'retention_sequence',
            'remission_guide_sequence',
            'email_enabled',
            'email_subject_template',
            'email_body_template',
            'special_taxpayer',
            'special_taxpayer_number',
            'accounting_required',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'invoice_sequence',
            'credit_note_sequence', 
            'debit_note_sequence',
            'retention_sequence',
            'remission_guide_sequence'
        ]


class SRIResponseSerializer(serializers.ModelSerializer):
    """
    Serializer para respuestas del SRI
    """
    document_number = serializers.CharField(source='document.document_number', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    
    class Meta:
        model = SRIResponse
        fields = [
            'id',
            'document',
            'document_number',
            'operation_type',
            'operation_type_display',
            'response_code',
            'response_message',
            'raw_response',
            'created_at'
        ]


class DocumentProcessRequestSerializer(serializers.Serializer):
    """
    Serializer para procesar documentos
    """
    certificate_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    send_email = serializers.BooleanField(default=True)
    
    def validate_certificate_password(self, value):
        if not value:
            raise serializers.ValidationError("Certificate password is required")
        return value


class DocumentStatusSerializer(serializers.Serializer):
    """
    Serializer para estado de documentos
    """
    id = serializers.IntegerField()
    document_number = serializers.CharField()
    access_key = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    issue_date = serializers.DateField()
    customer_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    # SRI info
    sri_authorization_code = serializers.CharField(allow_blank=True)
    sri_authorization_date = serializers.DateTimeField(allow_null=True)
    
    # Files
    has_xml = serializers.BooleanField()
    has_signed_xml = serializers.BooleanField()
    has_pdf = serializers.BooleanField()
    
    # Email
    email_sent = serializers.BooleanField()
    email_sent_date = serializers.DateTimeField(allow_null=True)
    
    # Last SRI response
    last_sri_response = serializers.DictField(allow_null=True)