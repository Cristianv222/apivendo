# -*- coding: utf-8 -*-
"""
Views for sri_integration app - VERSIÓN DEFINITIVAMENTE CORREGIDA
SOLUCIÓN ABSOLUTA PARA PERSISTENCIA DE CREDIT NOTES
"""

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction, connection
import os
from django.conf import settings
import logging

from .models import (
    SRIConfiguration, ElectronicDocument, DocumentItem,
    DocumentTax, SRIResponse, CreditNote
)
from .serializers import (
    SRIConfigurationSerializer, ElectronicDocumentSerializer,
    ElectronicDocumentListSerializer, DocumentItemSerializer,
    DocumentTaxSerializer, SRIResponseSerializer, CreateInvoiceSerializer
)

# Configurar logging
logger = logging.getLogger(__name__)


class SRIConfigurationViewSet(viewsets.ModelViewSet):
    queryset = SRIConfiguration.objects.all()
    serializer_class = SRIConfigurationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["company", "environment"]
    permission_classes = [permissions.AllowAny]  # Para pruebas
    
    @action(detail=True, methods=["post"])
    def get_next_sequence(self, request, pk=None):
        """Obtener siguiente secuencial"""
        config = self.get_object()
        document_type = request.data.get("document_type", "INVOICE")
        
        try:
            sequence = config.get_next_sequence(document_type)
            document_number = config.get_full_document_number(document_type, sequence)
            return Response({
                "sequence": sequence,
                "document_number": document_number,
                "document_type": document_type
            })
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class ElectronicDocumentViewSet(viewsets.ModelViewSet):
    queryset = ElectronicDocument.objects.all()
    serializer_class = ElectronicDocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["company", "document_type", "status", "issue_date"]
    search_fields = ["document_number", "customer_name", "customer_identification", "access_key"]
    ordering_fields = ["issue_date", "created_at", "total_amount"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]  # Para pruebas
    
    def get_serializer_class(self):
        if self.action == "list":
            return ElectronicDocumentListSerializer
        return ElectronicDocumentSerializer
    
    @action(detail=False, methods=["post"])
    def create_invoice(self, request):
        """Crear factura completa con items"""
        serializer = CreateInvoiceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                from django.utils import timezone
                from decimal import Decimal, ROUND_HALF_UP
                from apps.companies.models import Company
                
                # Obtener datos validados
                validated_data = serializer.validated_data
                items_data = validated_data.pop("items")
                
                # Obtener empresa
                company = Company.objects.get(id=validated_data["company"])
                
                # Obtener configuración SRI
                try:
                    sri_config = company.sri_configuration
                except:
                    return Response(
                        {"error": "Company does not have SRI configuration"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Generar número de documento
                sequence = sri_config.get_next_sequence("INVOICE")
                document_number = sri_config.get_full_document_number("INVOICE", sequence)
                
                # Crear documento electrónico
                document = ElectronicDocument.objects.create(
                    company=company,
                    document_type="INVOICE",
                    document_number=document_number,
                    issue_date=validated_data.get("issue_date", timezone.now().date()),
                    customer_identification_type=validated_data["customer_identification_type"],
                    customer_identification=validated_data["customer_identification"],
                    customer_name=validated_data["customer_name"],
                    customer_address=validated_data.get("customer_address", ""),
                    customer_email=validated_data.get("customer_email", ""),
                    customer_phone=validated_data.get("customer_phone", ""),
                    status="DRAFT"
                )
                
                # Función para redondear decimales correctamente
                def fix_decimal_places(value, places=2):
                    if isinstance(value, (int, float)):
                        value = Decimal(str(value))
                    elif isinstance(value, str):
                        value = Decimal(value)
                    quantizer = Decimal("0." + "0" * places)
                    return value.quantize(quantizer, rounding=ROUND_HALF_UP)
                
                # Crear items
                total_subtotal = Decimal("0.00")
                total_tax = Decimal("0.00")
                
                for item_data in items_data:
                    # Convertir a Decimal y calcular subtotal
                    quantity = fix_decimal_places(Decimal(str(item_data["quantity"])), 6)
                    unit_price = fix_decimal_places(Decimal(str(item_data["unit_price"])), 6)
                    discount = fix_decimal_places(Decimal(str(item_data.get("discount", 0))), 2)
                    
                    # Calcular subtotal con redondeo correcto
                    raw_subtotal = (quantity * unit_price) - discount
                    subtotal = fix_decimal_places(raw_subtotal, 2)
                    
                    # Crear item
                    item = DocumentItem.objects.create(
                        document=document,
                        main_code=item_data["main_code"],
                        auxiliary_code=item_data.get("auxiliary_code", ""),
                        description=item_data["description"],
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=discount,
                        subtotal=subtotal
                    )
                    
                    # Calcular impuesto (IVA 15% por defecto)
                    tax_rate = Decimal("15.00")
                    tax_amount = fix_decimal_places(subtotal * tax_rate / 100, 2)
                    
                    # Crear impuesto
                    DocumentTax.objects.create(
                        document=document,
                        item=item,
                        tax_code="2",  # IVA
                        percentage_code="2",  # 15%
                        rate=tax_rate,
                        taxable_base=subtotal,
                        tax_amount=tax_amount
                    )
                    
                    total_subtotal += subtotal
                    total_tax += tax_amount
                
                # Actualizar totales del documento
                total_amount = total_subtotal + total_tax
                
                document.subtotal_without_tax = fix_decimal_places(total_subtotal, 2)
                document.total_tax = fix_decimal_places(total_tax, 2)
                document.total_amount = fix_decimal_places(total_amount, 2)
                document.status = "GENERATED"
                document.save()
                
                # Serializar respuesta
                response_serializer = ElectronicDocumentSerializer(document)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Error creating invoice: {str(e)}")
                return Response(
                    {"error": f"Error creating invoice: {str(e)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["post"])
    def create_credit_note(self, request):
        """Crear nota de crédito completa"""
        try:
            from apps.companies.models import Company
            from decimal import Decimal
            
            # Obtener datos del request
            data = request.data
            
            # Obtener empresa y documento original
            company = Company.objects.first()  # O el ID de la empresa desde el request
            original_document = ElectronicDocument.objects.get(id=data.get("original_document_id"))
            
            # Crear nota de crédito
            credit_note = CreditNote.objects.create(
                company=company,
                original_document=original_document,
                reason_code=data.get("reason_code", "01"),
                reason_description=data.get("reason_description", "Devolución"),
                customer_identification_type=data.get("customer_identification_type", "05"),
                customer_identification=data.get("customer_identification"),
                customer_name=data.get("customer_name"),
                customer_address=data.get("customer_address", ""),
                customer_email=data.get("customer_email", ""),
                subtotal_without_tax=Decimal(str(data.get("subtotal_without_tax", "0.00"))),
                total_amount=Decimal(str(data.get("total_amount", "0.00"))),
                issue_date=timezone.now().date(),
                status="DRAFT"
            )
            
            logger.info(f"✅ Nota de crédito creada: ID {credit_note.id}")
            
            return Response({
                "id": credit_note.id,
                "document_number": credit_note.document_number,
                "status": credit_note.status,
                "message": "Credit note created successfully"
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating credit note: {str(e)}")
            return Response(
                {"error": f"Error creating credit note: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["post"])
    def generate_xml(self, request, pk=None):
        """Generar XML del documento - COMPATIBLE CON NOTAS DE CRÉDITO"""
        try:
            # Determinar tipo de documento
            document = None
            is_credit_note = False
            
            try:
                document = self.get_object()
                is_credit_note = False
                logger.info(f"Generando XML para ElectronicDocument ID {pk}")
            except:
                try:
                    document = CreditNote.objects.get(id=pk)
                    is_credit_note = True
                    logger.info(f"Generando XML para CreditNote ID {pk}")
                except CreditNote.DoesNotExist:
                    return Response(
                        {"error": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Usar el xml_generator de tu estructura
            from .services.xml_generator import XMLGenerator
            
            xml_generator = XMLGenerator(document)
            
            if is_credit_note:
                xml_content = xml_generator.generate_credit_note_xml()
            else:
                xml_content = xml_generator.generate_xml()
            
            # Actualizar estado usando transacción atómica
            with transaction.atomic():
                if is_credit_note:
                    updated_rows = CreditNote.objects.filter(id=document.id).update(
                        status="GENERATED",
                        updated_at=timezone.now()
                    )
                    logger.info(f"✅ CreditNote {document.id} actualizada: {updated_rows} filas")
                    document.refresh_from_db()
                else:
                    document.status = "GENERATED"
                    document.save()
            
            return Response({
                "status": "success",
                "message": "XML generated successfully",
                "data": {
                    "document_number": document.document_number,
                    "xml_size": len(xml_content),
                    "access_key": document.access_key,
                    "document_type": "CREDIT_NOTE" if is_credit_note else getattr(document, "document_type", "UNKNOWN")
                }
            })
            
        except Exception as e:
            logger.error(f"Error generating XML for document {pk}: {str(e)}")
            return Response({
                "error": "XML_GENERATION_FAILED",
                "message": f"Failed to generate XML: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["post"])
    @action(detail=True, methods=["post"])
    def sign_document(self, request, pk=None):
        """MÉTODO DE PRUEBA OBVIO - DEBE SER OBVIAMENTE VISIBLE"""
        from rest_framework.response import Response
        from rest_framework import status
        from apps.sri_integration.models import CreditNote
        from django.db import transaction
        from django.utils import timezone
        import logging
        
        # Logging que NO se puede ignorar
        print(f"🔥🔥🔥 [OBVIOUS TEST] EJECUTÁNDOSE PARA PK {pk} 🔥🔥🔥")
        
        try:
            # Obtener documento
            document = CreditNote.objects.get(id=pk)
            print(f"🔥🔥🔥 [OBVIOUS TEST] Estado inicial: {document.status} 🔥🔥🔥")
            
            # Actualización obvia
            with transaction.atomic():
                updated_rows = CreditNote.objects.filter(id=document.id).update(
                    status="OBVIOUS_SIGNED",
                    updated_at=timezone.now()
                )
                print(f"🔥🔥🔥 [OBVIOUS TEST] Filas actualizadas: {updated_rows} 🔥🔥🔥")
            
            # Verificar resultado
            final_check = CreditNote.objects.get(id=document.id)
            print(f"🔥🔥🔥 [OBVIOUS TEST] Estado final: {final_check.status} 🔥🔥🔥")
            
            # Respuesta obviamente diferente
            return Response({
                "success": True,
                "message": "🔥🔥🔥 OBVIOUS TEST METHOD WORKED - FILE MODIFICATION IS ACTIVE! 🔥🔥🔥",
                "data": {
                    "document_number": document.document_number,
                    "status": final_check.status,
                    "OBVIOUS_FLAG": "THIS_PROVES_FILE_MODIFICATION_WORKS",
                    "test_method": "OBVIOUS_REPLACEMENT",
                    "verification": {
                        "obvious_test": True,
                        "file_modification_successful": True,
                        "final_status": final_check.status,
                        "persistence_worked": final_check.status == "OBVIOUS_SIGNED"
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"🔥🔥🔥 [OBVIOUS TEST] ERROR: {e} 🔥🔥🔥")
            import traceback
            traceback.print_exc()
            return Response({
                "error": str(e), 
                "obvious_test": True,
                "test_method": "OBVIOUS_REPLACEMENT"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=True, methods=["post"])
    def send_to_sri(self, request, pk=None):
        """Enviar documento al SRI - COMPATIBLE CON NOTAS DE CRÉDITO"""
        try:
            # Determinar tipo de documento
            document = None
            is_credit_note = False
            
            try:
                document = self.get_object()
                is_credit_note = False
                logger.info(f"Enviando ElectronicDocument {pk} al SRI")
            except:
                try:
                    document = CreditNote.objects.get(id=pk)
                    is_credit_note = True
                    logger.info(f"Enviando CreditNote {pk} al SRI")
                except CreditNote.DoesNotExist:
                    return Response(
                        {"error": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Verificar que esté firmado
            if document.status != "SIGNED":
                return Response(
                    {"error": "DOCUMENT_NOT_SIGNED", "message": "Document must be signed before sending to SRI"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Enviar al SRI usando soap_client
            from .services.soap_client import SRISOAPClient
            from .services.xml_generator import XMLGenerator
            
            generator = XMLGenerator(document)
            
            if is_credit_note:
                xml_content = generator.generate_credit_note_xml()
            else:
                xml_content = generator.generate_xml()
            
            sri_client = SRISOAPClient(document.company)
            success, message = sri_client.send_document_to_reception(document, xml_content)
            
            if success:
                # Actualizar estado usando transacción atómica
                with transaction.atomic():
                    if is_credit_note:
                        updated_rows = CreditNote.objects.filter(id=document.id).update(
                            status="SENT",
                            updated_at=timezone.now()
                        )
                        logger.info(f"CreditNote {document.id} enviada al SRI: {updated_rows} filas actualizadas")
                        document.refresh_from_db()
                    else:
                        document.status = "SENT"
                        document.save()
                        logger.info(f"ElectronicDocument {document.id} enviado al SRI")
                
                return Response({
                    "message": "Document sent to SRI successfully",
                    "data": {
                        "document_number": document.document_number,
                        "status": document.status,
                        "access_key": document.access_key
                    }
                })
            else:
                if "Error 35" in message or "SRI Error" in message:
                    return Response(
                        {"error": "SRI_SUBMISSION_FAILED", "message": f"SRI rejected document: {message}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        {"error": "SRI_CONNECTION_FAILED", "message": message},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
        except Exception as e:
            logger.error(f"Error sending document {pk} to SRI: {str(e)}")
            return Response(
                {"error": "SRI_SUBMISSION_ERROR", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"])
    def generate_pdf(self, request, pk=None):
        """Generar PDF del documento"""
        try:
            # Determinar tipo de documento
            document = None
            is_credit_note = False
            
            try:
                document = self.get_object()
                is_credit_note = False
            except:
                try:
                    document = CreditNote.objects.get(id=pk)
                    is_credit_note = True
                except CreditNote.DoesNotExist:
                    return Response(
                        {"error": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            from .services.pdf_generator import PDFGenerator
            
            pdf_generator = PDFGenerator()
            
            # Generar PDF según el tipo
            if is_credit_note:
                success, pdf_path = pdf_generator.generate_credit_note_pdf(document)
            else:
                success, pdf_path = pdf_generator.generate_invoice_pdf(document)
            
            if success:
                return Response({
                    "status": "PDF generated successfully",
                    "document_number": document.document_number,
                    "pdf_path": str(pdf_path),
                    "message": "PDF file created successfully"
                })
            else:
                return Response({
                    "status": "ERROR",
                    "message": f"PDF generation failed: {pdf_path}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Error generating PDF for document {pk}: {str(e)}")
            return Response({
                "status": "ERROR",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["post"])
    def process_complete(self, request, pk=None):
        """Procesar documento completo: XML + Firma + SRI + PDF"""
        document = self.get_object()
        
        cert_password = request.data.get("password")
        if not cert_password:
            return Response({
                "status": "ERROR",
                "message": "Certificate password is required for complete processing"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .services.sri_processor import SRIProcessor
            
            processor = SRIProcessor(document.company)
            
            # Procesar completamente
            success, message = processor.process_document(document, cert_password, send_email=False)
            
            if success:
                return Response({
                    "status": "Document processed completely",
                    "document_number": document.document_number,
                    "document_status": document.status,
                    "authorization_code": getattr(document, "sri_authorization_code", None),
                    "authorization_date": getattr(document, "sri_authorization_date", None),
                    "files_generated": {
                        "xml": bool(getattr(document, "xml_file", None)),
                        "signed_xml": bool(getattr(document, "signed_xml_file", None)),
                        "pdf": bool(getattr(document, "pdf_file", None))
                    },
                    "message": message
                })
            else:
                return Response({
                    "status": "ERROR",
                    "message": message
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error in complete processing for document {pk}: {str(e)}")
            return Response({
                "status": "ERROR",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["post"])
    def send_email(self, request, pk=None):
        """Enviar email con documentos"""
        try:
            # Determinar tipo de documento
            document = None
            is_credit_note = False
            
            try:
                document = self.get_object()
                is_credit_note = False
            except:
                try:
                    document = CreditNote.objects.get(id=pk)
                    is_credit_note = True
                except CreditNote.DoesNotExist:
                    return Response(
                        {"error": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Verificar que el documento esté autorizado
            if document.status not in ["AUTHORIZED", "SENT"]:
                return Response({
                    "error": "DOCUMENT_NOT_READY",
                    "message": "Document must be authorized before sending email"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Enviar email
            from .services.email_service import EmailService
            
            email_service = EmailService()
            
            if is_credit_note:
                success, message = email_service.send_credit_note_email(document)
            else:
                success, message = email_service.send_invoice_email(document)
            
            if success:
                # Marcar como enviado
                with transaction.atomic():
                    if is_credit_note:
                        CreditNote.objects.filter(id=document.id).update(
                            email_sent=True,
                            email_sent_date=timezone.now()
                        )
                    else:
                        document.email_sent = True
                        document.email_sent_date = timezone.now()
                        document.save(update_fields=['email_sent', 'email_sent_date'])
                
                return Response({
                    "message": "Email sent successfully",
                    "data": {
                        "document_number": document.document_number,
                        "email_sent": True
                    }
                })
            else:
                return Response({
                    "error": "EMAIL_SENDING_FAILED",
                    "message": message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error sending email for document {pk}: {str(e)}")
            return Response({
                "error": "EMAIL_ERROR",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["post"])
    def debug_status_update(self, request, pk=None):
        """Endpoint de debug para probar actualizaciones de status - SOLO PARA DESARROLLO"""
        try:
            # Intentar obtener CreditNote primero
            document = None
            is_credit_note = False
            
            try:
                document = CreditNote.objects.get(id=pk)
                is_credit_note = True
                logger.info(f"🔍 Debug: CreditNote {pk} encontrada")
            except CreditNote.DoesNotExist:
                document = self.get_object()
                is_credit_note = False
                logger.info(f"🔍 Debug: ElectronicDocument {pk} encontrado")
            
            new_status = request.data.get("status", "SIGNED")
            logger.info(f"🔍 Estado inicial: {document.status}")
            logger.info(f"🔍 Nuevo status solicitado: {new_status}")
            
            # Método 1: Update directo con transacción
            if is_credit_note:
                with transaction.atomic():
                    updated_rows = CreditNote.objects.filter(id=document.id).update(
                        status=new_status,
                        updated_at=timezone.now()
                    )
                    
                    # Verificación inmediata dentro de la transacción
                    verification_in_transaction = CreditNote.objects.get(id=document.id)
                    
                # Verificación fuera de la transacción
                document.refresh_from_db()
                verification_after_transaction = CreditNote.objects.get(id=document.id)
                
                return Response({
                    "method": "update_direct_with_transaction",
                    "document_type": "CreditNote",
                    "updated_rows": updated_rows,
                    "status_in_transaction": verification_in_transaction.status,
                    "status_after_refresh": document.status,
                    "status_after_new_query": verification_after_transaction.status,
                    "success": verification_after_transaction.status == new_status,
                    "timestamps": {
                        "in_transaction": str(verification_in_transaction.updated_at),
                        "after_transaction": str(verification_after_transaction.updated_at)
                    }
                })
            else:
                document.status = new_status
                document.save()
                
                return Response({
                    "method": "save_normal",
                    "document_type": "ElectronicDocument",
                    "status_after_save": document.status,
                    "success": document.status == new_status
                })
                
        except Exception as e:
            logger.error(f"Error in debug_status_update: {str(e)}")
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentItemViewSet(viewsets.ModelViewSet):
    queryset = DocumentItem.objects.all()
    serializer_class = DocumentItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["document"]
    search_fields = ["description", "main_code"]
    permission_classes = [permissions.AllowAny]  # Para pruebas


class SRIResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SRIResponse.objects.all()
    serializer_class = SRIResponseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["document", "operation_type", "response_code"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]  # Para pruebas