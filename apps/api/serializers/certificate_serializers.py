# -*- coding: utf-8 -*-
"""
Serializers for digital certificates
"""

from rest_framework import serializers
from apps.certificates.models import DigitalCertificate, CertificateUsageLog


class DigitalCertificateSerializer(serializers.ModelSerializer):
    """
    Serializer para certificados digitales
    """
    company_name = serializers.CharField(source='company.business_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = DigitalCertificate
        fields = [
            'id',
            'company',
            'company_name',
            'subject_name',
            'issuer_name',
            'serial_number',
            'valid_from',
            'valid_to',
            'status',
            'status_display',
            'fingerprint',
            'environment',
            'environment_display',
            'is_expired',
            'days_until_expiration',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'subject_name',
            'issuer_name',
            'serial_number',
            'valid_from',
            'valid_to',
            'fingerprint'
        ]


class CertificateUploadSerializer(serializers.Serializer):
    """
    Serializer para subir certificados P12
    """
    certificate_file = serializers.FileField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    environment = serializers.ChoiceField(
        choices=[('TEST', 'Test'), ('PRODUCTION', 'Production')],
        default='TEST'
    )
    
    def validate_certificate_file(self, value):
        """
        Valida el archivo de certificado
        """
        if not value.name.lower().endswith('.p12'):
            raise serializers.ValidationError("File must be a P12 certificate")
        
        if value.size > 5 * 1024 * 1024:  # 5MB
            raise serializers.ValidationError("File size cannot exceed 5MB")
        
        return value
    
    def validate_password(self, value):
        """
        Valida la contraseña
        """
        if not value:
            raise serializers.ValidationError("Password is required")
        
        if len(value) < 4:
            raise serializers.ValidationError("Password must be at least 4 characters")
        
        return value


class CertificateUsageLogSerializer(serializers.ModelSerializer):
    """
    Serializer para logs de uso de certificados
    """
    certificate_subject = serializers.CharField(source='certificate.subject_name', read_only=True)
    
    class Meta:
        model = CertificateUsageLog
        fields = [
            'id',
            'certificate',
            'certificate_subject',
            'operation',
            'document_type',
            'document_number',
            'success',
            'error_message',
            'ip_address',
            'created_at'
        ]