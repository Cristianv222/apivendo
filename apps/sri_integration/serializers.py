# -*- coding: utf-8 -*-
"""
Serializers for sri_integration app
"""

from rest_framework import serializers
from .models import (
    SRIConfiguration, ElectronicDocument, DocumentItem, 
    DocumentTax, SRIResponse
)

class SRIConfigurationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    
    class Meta:
        model = SRIConfiguration
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class DocumentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentItem
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'subtotal')

class DocumentTaxSerializer(serializers.ModelSerializer):
    tax_code_display = serializers.CharField(source='get_tax_code_display', read_only=True)
    percentage_code_display = serializers.CharField(source='get_percentage_code_display', read_only=True)
    
    class Meta:
        model = DocumentTax
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class ElectronicDocumentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = DocumentItemSerializer(many=True, read_only=True)
    taxes = DocumentTaxSerializer(many=True, read_only=True)
    
    class Meta:
        model = ElectronicDocument
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'access_key')

class ElectronicDocumentListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas"""
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ElectronicDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'document_number', 
            'issue_date', 'status', 'status_display', 'customer_name', 
            'total_amount', 'company_name', 'sri_authorization_code'
        ]

class SRIResponseSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source='document.document_number', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    
    class Meta:
        model = SRIResponse
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class CreateInvoiceSerializer(serializers.Serializer):
    """Serializer para crear facturas completas"""
    # Datos del cliente
    customer_identification_type = serializers.ChoiceField(choices=ElectronicDocument.DOCUMENT_TYPES)
    customer_identification = serializers.CharField(max_length=20)
    customer_name = serializers.CharField(max_length=300)
    customer_address = serializers.CharField(required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Items
    items = DocumentItemSerializer(many=True)
    
    # Configuración adicional
    issue_date = serializers.DateField(required=False)
    additional_data = serializers.DictField(required=False)