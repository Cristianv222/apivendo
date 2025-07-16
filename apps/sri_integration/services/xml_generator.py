# -*- coding: utf-8 -*-
"""
Generador de XML para documentos del SRI - VERSIÓN FINAL CORREGIDA
"""

import logging
import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from apps.sri_integration.models import ElectronicDocument

logger = logging.getLogger(__name__)


class XMLGenerator:
    """
    Generador de XML para documentos electrónicos del SRI - VERSIÓN FINAL CON SCHEMA LOCATIONS CORREGIDOS
    """
    
    def __init__(self, document):
        self.document = document
        self.company = document.company
        self.sri_config = self.company.sri_configuration
        
        # Crear directorio base para XMLs si no existe
        self.xml_base_dir = os.path.join(settings.BASE_DIR, 'storage', 'invoices', 'xml')
        os.makedirs(self.xml_base_dir, exist_ok=True)
    
    # ========== MÉTODOS PRINCIPALES ==========
    
    def generate_xml(self):
        """
        Método principal que determina qué tipo de XML generar según el tipo de documento
        """
        from apps.sri_integration.models import CreditNote, DebitNote, Retention, PurchaseSettlement
        
        # Determinar el tipo de documento y llamar al método correspondiente
        if isinstance(self.document, CreditNote):
            return self.generate_credit_note_xml()
        elif isinstance(self.document, DebitNote):
            return self.generate_debit_note_xml()
        elif isinstance(self.document, Retention):
            return self.generate_retention_xml()
        elif isinstance(self.document, PurchaseSettlement):
            return self.generate_purchase_settlement_xml()
        else:
            # Por defecto, generar factura
            return self.generate_invoice_xml()
    
    # ========== MÉTODOS DE RUTAS DE ARCHIVOS ==========
    
    def get_xml_path(self):
        """
        Obtiene la ruta del archivo XML para ElectronicDocument
        """
        filename = f"{self.document.access_key}.xml"
        return os.path.join(self.xml_base_dir, filename)
    
    def get_credit_note_xml_path(self):
        """
        Obtiene la ruta del archivo XML para CreditNote
        """
        filename = f"{self.document.access_key}.xml"
        return os.path.join(self.xml_base_dir, filename)
    
    def get_debit_note_xml_path(self):
        """
        Obtiene la ruta del archivo XML para DebitNote
        """
        filename = f"{self.document.access_key}.xml"
        return os.path.join(self.xml_base_dir, filename)
    
    def get_retention_xml_path(self):
        """
        Obtiene la ruta del archivo XML para Retention
        """
        filename = f"{self.document.access_key}.xml"
        return os.path.join(self.xml_base_dir, filename)
    
    def get_purchase_settlement_xml_path(self):
        """
        Obtiene la ruta del archivo XML para PurchaseSettlement
        """
        filename = f"{self.document.access_key}.xml"
        return os.path.join(self.xml_base_dir, filename)
    
    def save_xml_to_file(self, xml_content):
        """
        Guarda el contenido XML en el archivo correspondiente
        """
        try:
            from apps.sri_integration.models import CreditNote, DebitNote, Retention, PurchaseSettlement
            
            # Determinar la ruta según el tipo de documento
            if isinstance(self.document, CreditNote):
                xml_path = self.get_credit_note_xml_path()
            elif isinstance(self.document, DebitNote):
                xml_path = self.get_debit_note_xml_path()
            elif isinstance(self.document, Retention):
                xml_path = self.get_retention_xml_path()
            elif isinstance(self.document, PurchaseSettlement):
                xml_path = self.get_purchase_settlement_xml_path()
            else:
                xml_path = self.get_xml_path()
            
            # Escribir archivo
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            logger.info(f"XML guardado en: {xml_path}")
            return xml_path
            
        except Exception as e:
            logger.error(f"Error guardando XML: {str(e)}")
            raise
    
    # ========== GENERACIÓN DE XML POR TIPO - CORREGIDOS CON SCHEMA LOCATIONS CORRECTOS ==========
    
    def generate_invoice_xml(self):
        """
        Genera XML para factura electrónica - CORREGIDO CON SCHEMA LOCATION COMPLETO
        """
        try:
            # Crear elemento raíz CON SCHEMA LOCATION CORREGIDO
            factura = Element('factura', {
                'id': 'comprobante',
                'version': '1.1.0',
                'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.ec.gob.sri.ws.componentes http://www.ec.gob.sri.ws.componentes/facturaOffline.xsd'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('01')  # 01 = Factura
            factura.append(info_tributaria)
            
            # Información de la factura
            info_factura = self._create_info_factura()
            factura.append(info_factura)
            
            # Detalles
            detalles = SubElement(factura, 'detalles')
            if hasattr(self.document, 'items') and self.document.items.exists():
                for item in self.document.items.all():
                    detalle = self._create_detalle_factura(item)
                    detalles.append(detalle)
            else:
                # Crear detalle genérico para facturas sin items
                detalle = self._create_detalle_generico()
                detalles.append(detalle)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                factura.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(factura)
            
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating invoice XML: {str(e)}")
            raise ValueError(f"Error generating invoice XML: {str(e)}")
    
    def generate_credit_note_xml(self):
        """
        Genera XML para nota de crédito - CORREGIDO CON SCHEMA LOCATION COMPLETO
        """
        try:
            logger.info(f"Generando XML para CreditNote ID {self.document.id}")
            
            # Crear elemento raíz CON SCHEMA LOCATION CORREGIDO
            nota_credito = Element('notaCredito', {
                'id': 'comprobante',
                'version': '1.1.0',
                'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.ec.gob.sri.ws.componentes http://www.ec.gob.sri.ws.componentes/notaCreditoOffline.xsd'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('04')  # 04 = Nota de Crédito
            nota_credito.append(info_tributaria)
            
            # Información de la nota de crédito
            info_nota_credito = self._create_info_nota_credito()
            nota_credito.append(info_nota_credito)
            
            # Detalles - manejo especial para CreditNote
            detalles = SubElement(nota_credito, 'detalles')
            
            if hasattr(self.document, 'items') and self.document.items.exists():
                for item in self.document.items.all():
                    detalle = self._create_detalle_nota_credito(item)
                    detalles.append(detalle)
            else:
                # Crear detalle genérico para nota de crédito
                detalle = Element('detalle')
                
                # Código principal
                codigo_principal = SubElement(detalle, 'codigoPrincipal')
                codigo_principal.text = 'NOTAC001'
                
                # Descripción basada en el motivo
                descripcion = SubElement(detalle, 'descripcion')
                descripcion.text = getattr(self.document, 'reason_description', 'Nota de crédito')
                
                # Cantidad
                cantidad = SubElement(detalle, 'cantidad')
                cantidad.text = '1.000000'
                
                # Precio unitario
                precio_unitario = SubElement(detalle, 'precioUnitario')
                precio_unitario.text = f"{float(self.document.subtotal_without_tax):.6f}"
                
                # Descuento
                descuento = SubElement(detalle, 'descuento')
                descuento.text = '0.00'
                
                # Precio total sin impuesto
                precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
                precio_total_sin_impuesto.text = f"{float(self.document.subtotal_without_tax):.2f}"
                
                # Impuestos del detalle
                impuestos = SubElement(detalle, 'impuestos')
                impuesto = SubElement(impuestos, 'impuesto')
                
                SubElement(impuesto, 'codigo').text = '2'  # IVA
                SubElement(impuesto, 'codigoPorcentaje').text = '2'  # 15%
                SubElement(impuesto, 'tarifa').text = '15.00'
                SubElement(impuesto, 'baseImponible').text = f"{float(self.document.subtotal_without_tax):.2f}"
                SubElement(impuesto, 'valor').text = f"{float(self.document.total_tax):.2f}"
                
                detalles.append(detalle)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                nota_credito.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(nota_credito)
            
            logger.info(f"XML de CreditNote generado exitosamente: {len(xml_str)} caracteres")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating credit note XML: {str(e)}")
            raise ValueError(f"Error generating credit note XML: {str(e)}")
    
    def generate_debit_note_xml(self):
        """
        Genera XML para nota de débito - CORREGIDO CON SCHEMA LOCATION COMPLETO
        """
        try:
            logger.info(f"Generando XML para DebitNote ID {self.document.id}")
            
            # Crear elemento raíz CON SCHEMA LOCATION CORREGIDO
            nota_debito = Element('notaDebito', {
                'id': 'comprobante',
                'version': '1.0.0',
                'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.ec.gob.sri.ws.componentes http://www.ec.gob.sri.ws.componentes/notaDebitoOffline.xsd'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('05')  # 05 = Nota de Débito
            nota_debito.append(info_tributaria)
            
            # Información de la nota de débito
            info_nota_debito = self._create_info_nota_debito()
            nota_debito.append(info_nota_debito)
            
            # Motivos
            motivos = SubElement(nota_debito, 'motivos')
            
            if hasattr(self.document, 'motives') and self.document.motives.exists():
                for motive in self.document.motives.all():
                    motivo = self._create_motivo_nota_debito_from_motive(motive)
                    motivos.append(motivo)
            elif hasattr(self.document, 'items') and self.document.items.exists():
                for item in self.document.items.all():
                    motivo = self._create_motivo_nota_debito(item)
                    motivos.append(motivo)
            else:
                # Crear motivo genérico
                motivo = Element('motivo')
                razon = SubElement(motivo, 'razon')
                razon.text = getattr(self.document, 'reason_description', 'Nota de débito')
                valor = SubElement(motivo, 'valor')
                valor.text = f"{float(self.document.subtotal_without_tax):.2f}"
                motivos.append(motivo)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                nota_debito.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(nota_debito)
            
            logger.info(f"XML de DebitNote generado exitosamente: {len(xml_str)} caracteres")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating debit note XML: {str(e)}")
            raise ValueError(f"Error generating debit note XML: {str(e)}")
    
    def generate_retention_xml(self):
        """
        Genera XML para comprobante de retención - CORREGIDO CON SCHEMA LOCATION COMPLETO
        """
        try:
            logger.info(f"Generando XML para Retention ID {self.document.id}")
            
            # Crear elemento raíz CON SCHEMA LOCATION CORREGIDO
            comp_retencion = Element('comprobanteRetencion', {
                'id': 'comprobante',
                'version': '1.0.0',
                'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.ec.gob.sri.ws.componentes http://www.ec.gob.sri.ws.componentes/comprobanteRetencionOffline.xsd'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('07')  # 07 = Retención
            comp_retencion.append(info_tributaria)
            
            # Información de retención
            info_comp_retencion = self._create_info_comp_retencion()
            comp_retencion.append(info_comp_retencion)
            
            # Impuestos (detalles de retención)
            impuestos = SubElement(comp_retencion, 'impuestos')
            
            if hasattr(self.document, 'details') and self.document.details.exists():
                for detail in self.document.details.all():
                    impuesto = self._create_impuesto_retencion(detail)
                    impuestos.append(impuesto)
            else:
                # Crear impuesto genérico de retención
                impuesto = Element('impuesto')
                SubElement(impuesto, 'codigo').text = '2'  # IVA
                SubElement(impuesto, 'codigoRetencion').text = '303'  # Código genérico
                SubElement(impuesto, 'baseImponible').text = f"{float(getattr(self.document, 'subtotal_without_tax', 100)):.2f}"
                SubElement(impuesto, 'porcentajeRetener').text = '30.00'
                SubElement(impuesto, 'valorRetenido').text = f"{float(getattr(self.document, 'total_retained', 30)):.2f}"
                SubElement(impuesto, 'codDocSustento').text = '01'
                SubElement(impuesto, 'numDocSustento').text = '001-001-000000001'
                SubElement(impuesto, 'fechaEmisionDocSustento').text = self.document.issue_date.strftime('%d/%m/%Y')
                impuestos.append(impuesto)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                comp_retencion.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(comp_retencion)
            
            logger.info(f"XML de Retention generado exitosamente: {len(xml_str)} caracteres")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating retention XML: {str(e)}")
            raise ValueError(f"Error generating retention XML: {str(e)}")
    
    def generate_purchase_settlement_xml(self):
        """
        Genera XML para liquidación de compra - CORREGIDO CON SCHEMA LOCATION COMPLETO
        """
        try:
            logger.info(f"Generando XML para PurchaseSettlement ID {self.document.id}")
            
            # Crear elemento raíz CON SCHEMA LOCATION CORREGIDO
            liquidacion_compra = Element('liquidacionCompra', {
                'id': 'comprobante',
                'version': '1.1.0',
                'xmlns:ds': 'http://www.w3.org/2000/09/xmldsig#',
                'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsi:schemaLocation': 'http://www.ec.gob.sri.ws.componentes http://www.ec.gob.sri.ws.componentes/liquidacionCompraOffline.xsd'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('03')  # 03 = Liquidación de compra
            liquidacion_compra.append(info_tributaria)
            
            # Información de liquidación
            info_liquidacion_compra = self._create_info_liquidacion_compra()
            liquidacion_compra.append(info_liquidacion_compra)
            
            # Detalles
            detalles = SubElement(liquidacion_compra, 'detalles')
            if hasattr(self.document, 'items') and self.document.items.exists():
                for item in self.document.items.all():
                    detalle = self._create_detalle_liquidacion(item)
                    detalles.append(detalle)
            else:
                # Crear detalle genérico
                detalle = self._create_detalle_generico()
                detalles.append(detalle)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                liquidacion_compra.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(liquidacion_compra)
            
            logger.info(f"XML de PurchaseSettlement generado exitosamente: {len(xml_str)} caracteres")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating purchase settlement XML: {str(e)}")
            raise ValueError(f"Error generating purchase settlement XML: {str(e)}")
    
    # ========== MÉTODOS PARA INFORMACIÓN TRIBUTARIA ==========
    
    def _create_info_tributaria(self, cod_doc):
        """
        Crea la sección infoTributaria común a todos los documentos
        """
        info_tributaria = Element('infoTributaria')
        
        # Ambiente
        ambiente = SubElement(info_tributaria, 'ambiente')
        ambiente.text = '2' if self.sri_config.environment == 'PRODUCTION' else '1'
        
        # Tipo de emisión
        tipo_emision = SubElement(info_tributaria, 'tipoEmision')
        tipo_emision.text = '1'  # Emisión normal
        
        # Razón social
        razon_social = SubElement(info_tributaria, 'razonSocial')
        razon_social.text = self.company.business_name[:300]  # Límite SRI
        
        # Nombre comercial
        if self.company.trade_name:
            nombre_comercial = SubElement(info_tributaria, 'nombreComercial')
            nombre_comercial.text = self.company.trade_name[:300]  # Límite SRI
        
        # RUC
        ruc = SubElement(info_tributaria, 'ruc')
        ruc.text = self.company.ruc
        
        # Clave de acceso
        clave_acceso = SubElement(info_tributaria, 'claveAcceso')
        clave_acceso.text = self.document.access_key
        
        # Código de documento
        cod_documento = SubElement(info_tributaria, 'codDoc')
        cod_documento.text = cod_doc
        
        # Establecimiento
        establecimiento = SubElement(info_tributaria, 'estab')
        establecimiento.text = self.sri_config.establishment_code
        
        # Punto de emisión
        punto_emision = SubElement(info_tributaria, 'ptoEmi')
        punto_emision.text = self.sri_config.emission_point
        
        # Secuencial
        secuencial = SubElement(info_tributaria, 'secuencial')
        secuencial.text = self.document.document_number.split('-')[-1]
        
        # Dirección matriz
        dir_matriz = SubElement(info_tributaria, 'dirMatriz')
        dir_matriz.text = self.company.address[:300]  # Límite SRI
        
        return info_tributaria
    
    # ========== MÉTODOS PARA FACTURAS ==========
    
    def _create_info_factura(self):
        """
        Crea la sección infoFactura
        """
        info_factura = Element('infoFactura')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_factura, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_factura, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address[:300]
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_factura, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_factura, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Tipo de identificación del comprador
        tipo_identificacion_comprador = SubElement(info_factura, 'tipoIdentificacionComprador')
        tipo_identificacion_comprador.text = self.document.customer_identification_type
        
        # Razón social del comprador
        razon_social_comprador = SubElement(info_factura, 'razonSocialComprador')
        razon_social_comprador.text = self.document.customer_name[:300]
        
        # Identificación del comprador
        identificacion_comprador = SubElement(info_factura, 'identificacionComprador')
        identificacion_comprador.text = self.document.customer_identification
        
        # Dirección del comprador
        if hasattr(self.document, 'customer_address') and self.document.customer_address:
            direccion_comprador = SubElement(info_factura, 'direccionComprador')
            direccion_comprador.text = self.document.customer_address[:300]
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_factura, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{float(self.document.subtotal_without_tax):.2f}"
        
        # Total descuento
        total_descuento = SubElement(info_factura, 'totalDescuento')
        total_descuento.text = f"{float(getattr(self.document, 'total_discount', 0)):.2f}"
        
        # Total con impuestos
        total_con_impuestos = SubElement(info_factura, 'totalConImpuestos')
        
        # Agrupar impuestos por código y tarifa
        taxes_summary = self._get_taxes_summary()
        for tax_data in taxes_summary.values():
            total_impuesto = SubElement(total_con_impuestos, 'totalImpuesto')
            
            codigo = SubElement(total_impuesto, 'codigo')
            codigo.text = tax_data['codigo']
            
            codigo_porcentaje = SubElement(total_impuesto, 'codigoPorcentaje')
            codigo_porcentaje.text = tax_data['codigoPorcentaje']
            
            base_imponible = SubElement(total_impuesto, 'baseImponible')
            base_imponible.text = f"{tax_data['base']:.2f}"
            
            tarifa = SubElement(total_impuesto, 'tarifa')
            tarifa.text = f"{tax_data['tarifa']:.2f}"
            
            valor = SubElement(total_impuesto, 'valor')
            valor.text = f"{tax_data['valor']:.2f}"
        
        # Propina
        propina = SubElement(info_factura, 'propina')
        propina.text = "0.00"
        
        # Importe total
        importe_total = SubElement(info_factura, 'importeTotal')
        importe_total.text = f"{float(self.document.total_amount):.2f}"
        
        # Moneda
        moneda = SubElement(info_factura, 'moneda')
        moneda.text = "DOLAR"
        
        return info_factura
    
    def _create_detalle_factura(self, item):
        """
        Crea un detalle de factura - ✅ CORREGIDO
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code[:25]  # Límite SRI
        
        # Código auxiliar
        if hasattr(item, 'auxiliary_code') and item.auxiliary_code:
            codigo_auxiliar = SubElement(detalle, 'codigoAuxiliar')
            codigo_auxiliar.text = item.auxiliary_code[:25]
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description[:300]  # Límite SRI
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{float(item.quantity):.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{float(item.unit_price):.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{float(getattr(item, 'discount', 0)):.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{float(item.subtotal):.2f}"
        
        # Impuestos del ítem
        impuestos = SubElement(detalle, 'impuestos')
        if hasattr(item, 'taxes') and item.taxes.exists():
            for tax in item.taxes.all():
                impuesto = SubElement(impuestos, 'impuesto')
                
                codigo = SubElement(impuesto, 'codigo')
                codigo.text = tax.tax_code
                
                codigo_porcentaje = SubElement(impuesto, 'codigoPorcentaje')
                codigo_porcentaje.text = tax.percentage_code
                
                tarifa = SubElement(impuesto, 'tarifa')
                tarifa.text = f"{float(tax.rate):.2f}"
                
                base_imponible = SubElement(impuesto, 'baseImponible')
                base_imponible.text = f"{float(tax.taxable_base):.2f}"
                
                valor = SubElement(impuesto, 'valor')
                valor.text = f"{float(tax.tax_amount):.2f}"
        else:
            # Impuesto por defecto - ✅ CORREGIDO
            impuesto = SubElement(impuestos, 'impuesto')
            SubElement(impuesto, 'codigo').text = '2'
            SubElement(impuesto, 'codigoPorcentaje').text = '2'
            SubElement(impuesto, 'tarifa').text = '15.00'
            SubElement(impuesto, 'baseImponible').text = f"{float(item.subtotal):.2f}"
            SubElement(impuesto, 'valor').text = f"{float(item.subtotal) * 0.15:.2f}"  # ✅ CORREGIDO
        
        return detalle
    
    # ========== MÉTODOS PARA NOTAS DE CRÉDITO ==========
    
    def _create_info_nota_credito(self):
        """
        Crea la sección infoNotaCredito - VERSIÓN MEJORADA
        """
        info_nota_credito = Element('infoNotaCredito')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_nota_credito, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_nota_credito, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address[:300]
        
        # Tipo de identificación del comprador
        tipo_identificacion_comprador = SubElement(info_nota_credito, 'tipoIdentificacionComprador')
        tipo_identificacion_comprador.text = self.document.customer_identification_type
        
        # Razón social del comprador
        razon_social_comprador = SubElement(info_nota_credito, 'razonSocialComprador')
        razon_social_comprador.text = self.document.customer_name[:300]
        
        # Identificación del comprador
        identificacion_comprador = SubElement(info_nota_credito, 'identificacionComprador')
        identificacion_comprador.text = self.document.customer_identification
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_nota_credito, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_nota_credito, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Motivo
        motivo = SubElement(info_nota_credito, 'motivo')
        motivo.text = getattr(self.document, 'reason_description', 'Nota de crédito')[:300]
        
        # Documento modificado
        if hasattr(self.document, 'original_document') and self.document.original_document:
            cod_doc_modificado = SubElement(info_nota_credito, 'codDocModificado')
            cod_doc_modificado.text = '01'  # Factura
            
            num_doc_modificado = SubElement(info_nota_credito, 'numDocModificado')
            num_doc_modificado.text = self.document.original_document.document_number
            
            fecha_emision_doc_sustento = SubElement(info_nota_credito, 'fechaEmisionDocSustento')
            fecha_emision_doc_sustento.text = self.document.original_document.issue_date.strftime('%d/%m/%Y')
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_nota_credito, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{float(self.document.subtotal_without_tax):.2f}"
        
        # Total con impuestos
        total_con_impuestos = SubElement(info_nota_credito, 'totalConImpuestos')
        
        # Agregar impuestos agrupados - MEJORADO PARA CREDIT NOTE
        taxes_summary = self._get_taxes_summary_for_credit_note()
        for tax_data in taxes_summary.values():
            total_impuesto = SubElement(total_con_impuestos, 'totalImpuesto')
            
            codigo = SubElement(total_impuesto, 'codigo')
            codigo.text = tax_data['codigo']
            
            codigo_porcentaje = SubElement(total_impuesto, 'codigoPorcentaje')
            codigo_porcentaje.text = tax_data['codigoPorcentaje']
            
            base_imponible = SubElement(total_impuesto, 'baseImponible')
            base_imponible.text = f"{tax_data['base']:.2f}"
            
            valor = SubElement(total_impuesto, 'valor')
            valor.text = f"{tax_data['valor']:.2f}"
        
        # Valor modificación
        valor_modificacion = SubElement(info_nota_credito, 'valorModificacion')
        valor_modificacion.text = f"{float(self.document.total_amount):.2f}"
        
        # Moneda
        moneda = SubElement(info_nota_credito, 'moneda')
        moneda.text = "DOLAR"
        
        return info_nota_credito
    
    def _create_detalle_nota_credito(self, item):
        """
        Crea un detalle de nota de crédito - ✅ CORREGIDO
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code[:25]
        
        # Código auxiliar
        if hasattr(item, 'auxiliary_code') and item.auxiliary_code:
            codigo_auxiliar = SubElement(detalle, 'codigoAuxiliar')
            codigo_auxiliar.text = item.auxiliary_code[:25]
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description[:300]
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{float(item.quantity):.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{float(item.unit_price):.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{float(getattr(item, 'discount', 0)):.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{float(item.subtotal):.2f}"
        
        return detalle
    
    # ========== MÉTODOS PARA NOTAS DE DÉBITO - MEJORADOS ==========
    
    def _create_info_nota_debito(self):
        """
        Crea la sección infoNotaDebito - VERSIÓN MEJORADA Y CORREGIDA
        """
        info_nota_debito = Element('infoNotaDebito')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_nota_debito, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_nota_debito, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address[:300]
        
        # Tipo de identificación del comprador
        tipo_identificacion_comprador = SubElement(info_nota_debito, 'tipoIdentificacionComprador')
        tipo_identificacion_comprador.text = self.document.customer_identification_type
        
        # Razón social del comprador
        razon_social_comprador = SubElement(info_nota_debito, 'razonSocialComprador')
        razon_social_comprador.text = self.document.customer_name[:300]
        
        # Identificación del comprador
        identificacion_comprador = SubElement(info_nota_debito, 'identificacionComprador')
        identificacion_comprador.text = self.document.customer_identification
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_nota_debito, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_nota_debito, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Documento modificado - AGREGADO PARA NOTAS DE DÉBITO
        if hasattr(self.document, 'original_document') and self.document.original_document:
            cod_doc_modificado = SubElement(info_nota_debito, 'codDocModificado')
            cod_doc_modificado.text = '01'  # Factura
            
            num_doc_modificado = SubElement(info_nota_debito, 'numDocModificado')
            num_doc_modificado.text = self.document.original_document.document_number
            
            fecha_emision_doc_sustento = SubElement(info_nota_debito, 'fechaEmisionDocSustento')
            fecha_emision_doc_sustento.text = self.document.original_document.issue_date.strftime('%d/%m/%Y')
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_nota_debito, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{float(self.document.subtotal_without_tax):.2f}"
        
        # Impuestos
        impuestos = SubElement(info_nota_debito, 'impuestos')
        taxes_summary = self._get_taxes_summary_for_debit_note()
        for tax_data in taxes_summary.values():
            impuesto = SubElement(impuestos, 'impuesto')
            
            codigo = SubElement(impuesto, 'codigo')
            codigo.text = tax_data['codigo']
            
            codigo_porcentaje = SubElement(impuesto, 'codigoPorcentaje')
            codigo_porcentaje.text = tax_data['codigoPorcentaje']
            
            tarifa = SubElement(impuesto, 'tarifa')
            tarifa.text = f"{tax_data['tarifa']:.2f}"
            
            base_imponible = SubElement(impuesto, 'baseImponible')
            base_imponible.text = f"{tax_data['base']:.2f}"
            
            valor = SubElement(impuesto, 'valor')
            valor.text = f"{tax_data['valor']:.2f}"
        
        # Valor total
        valor_total = SubElement(info_nota_debito, 'valorTotal')
        valor_total.text = f"{float(self.document.total_amount):.2f}"
        
        return info_nota_debito
    
    def _create_motivo_nota_debito(self, item):
        """
        Crea un motivo de nota de débito desde un item - ✅ CORREGIDO
        """
        motivo = Element('motivo')
        
        # Razón
        razon = SubElement(motivo, 'razon')
        razon.text = getattr(self.document, 'reason_description', item.description)[:300]
        
        # Valor
        valor = SubElement(motivo, 'valor')
        valor.text = f"{float(item.subtotal):.2f}"
        
        return motivo
    
    def _create_motivo_nota_debito_from_motive(self, motive):
        """
        Crea un motivo de nota de débito desde un objeto motive específico - ✅ CORREGIDO
        """
        motivo = Element('motivo')
        
        # Razón
        razon = SubElement(motivo, 'razon')
        razon.text = getattr(motive, 'reason', 'Motivo de nota de débito')[:300]
        
        # Valor
        valor = SubElement(motivo, 'valor')
        valor.text = f"{float(getattr(motive, 'amount', 0)):.2f}"
        
        return motivo
    
    # ========== MÉTODOS PARA RETENCIONES ==========
    
    def _create_info_comp_retencion(self):
        """
        Crea la sección infoCompRetencion - VERSIÓN MEJORADA
        """
        info_comp_retencion = Element('infoCompRetencion')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_comp_retencion, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_comp_retencion, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address[:300]
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_comp_retencion, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_comp_retencion, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Tipo de identificación del sujeto retenido
        tipo_identificacion_sujeto_retenido = SubElement(info_comp_retencion, 'tipoIdentificacionSujetoRetenido')
        tipo_identificacion_sujeto_retenido.text = getattr(self.document, 'supplier_identification_type', '04')
        
        # Razón social del sujeto retenido
        razon_social_sujeto_retenido = SubElement(info_comp_retencion, 'razonSocialSujetoRetenido')
        razon_social_sujeto_retenido.text = getattr(self.document, 'supplier_name', 'Proveedor')[:300]
        
        # Identificación del sujeto retenido
        identificacion_sujeto_retenido = SubElement(info_comp_retencion, 'identificacionSujetoRetenido')
        identificacion_sujeto_retenido.text = getattr(self.document, 'supplier_identification', '9999999999999')
        
        # Período fiscal
        periodo_fiscal = SubElement(info_comp_retencion, 'periodoFiscal')
        periodo_fiscal.text = getattr(self.document, 'fiscal_period', self.document.issue_date.strftime('%m/%Y'))
        
        return info_comp_retencion
    
    def _create_impuesto_retencion(self, detail):
        """
        Crea un impuesto de retención - VERSIÓN MEJORADA Y CORREGIDA
        """
        impuesto = Element('impuesto')
        
        # Código
        codigo = SubElement(impuesto, 'codigo')
        codigo.text = detail.tax_code
        
        # Código de retención
        codigo_retencion = SubElement(impuesto, 'codigoRetencion')
        codigo_retencion.text = detail.retention_code
        
        # Base imponible
        base_imponible = SubElement(impuesto, 'baseImponible')
        base_imponible.text = f"{float(detail.taxable_base):.2f}"
        
        # Porcentaje de retención
        porcentaje_retener = SubElement(impuesto, 'porcentajeRetener')
        porcentaje_retener.text = f"{float(detail.retention_percentage):.2f}"
        
        # Valor retenido
        valor_retenido = SubElement(impuesto, 'valorRetenido')
        valor_retenido.text = f"{float(detail.retained_amount):.2f}"
        
        # Código del documento sustento
        cod_doc_sustento = SubElement(impuesto, 'codDocSustento')
        cod_doc_sustento.text = detail.support_document_type
        
        # Número del documento sustento
        num_doc_sustento = SubElement(impuesto, 'numDocSustento')
        num_doc_sustento.text = detail.support_document_number
        
        # Fecha emisión del documento sustento
        fecha_emision_doc_sustento = SubElement(impuesto, 'fechaEmisionDocSustento')
        fecha_emision_doc_sustento.text = detail.support_document_date.strftime('%d/%m/%Y')
        
        return impuesto
    
    # ========== MÉTODOS PARA LIQUIDACIONES DE COMPRA ==========
    
    def _create_info_liquidacion_compra(self):
        """
        Crea la sección infoLiquidacionCompra - VERSIÓN MEJORADA Y CORREGIDA
        """
        info_liquidacion = Element('infoLiquidacionCompra')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_liquidacion, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_liquidacion, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address[:300]
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_liquidacion, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_liquidacion, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Tipo de identificación del proveedor
        tipo_identificacion_proveedor = SubElement(info_liquidacion, 'tipoIdentificacionProveedor')
        tipo_identificacion_proveedor.text = getattr(self.document, 'supplier_identification_type', '04')
        
        # Razón social del proveedor
        razon_social_proveedor = SubElement(info_liquidacion, 'razonSocialProveedor')
        razon_social_proveedor.text = getattr(self.document, 'supplier_name', 'Proveedor')[:300]
        
        # Identificación del proveedor
        identificacion_proveedor = SubElement(info_liquidacion, 'identificacionProveedor')
        identificacion_proveedor.text = getattr(self.document, 'supplier_identification', '9999999999999')
        
        # Dirección del proveedor
        if hasattr(self.document, 'supplier_address') and self.document.supplier_address:
            direccion_proveedor = SubElement(info_liquidacion, 'direccionProveedor')
            direccion_proveedor.text = self.document.supplier_address[:300]
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_liquidacion, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{float(self.document.subtotal_without_tax):.2f}"
        
        # Total con impuestos
        total_con_impuestos = SubElement(info_liquidacion, 'totalConImpuestos')
        
        # Agregar impuestos (mejorado)
        taxes_summary = self._get_taxes_summary()
        for tax_data in taxes_summary.values():
            total_impuesto = SubElement(total_con_impuestos, 'totalImpuesto')
            codigo = SubElement(total_impuesto, 'codigo')
            codigo.text = tax_data['codigo']
            codigo_porcentaje = SubElement(total_impuesto, 'codigoPorcentaje')
            codigo_porcentaje.text = tax_data['codigoPorcentaje']
            base_imponible = SubElement(total_impuesto, 'baseImponible')
            base_imponible.text = f"{tax_data['base']:.2f}"
            tarifa = SubElement(total_impuesto, 'tarifa')
            tarifa.text = f"{tax_data['tarifa']:.2f}"
            valor = SubElement(total_impuesto, 'valor')
            valor.text = f"{tax_data['valor']:.2f}"
        
        # Importe total
        importe_total = SubElement(info_liquidacion, 'importeTotal')
        importe_total.text = f"{float(self.document.total_amount):.2f}"
        
        # Moneda
        moneda = SubElement(info_liquidacion, 'moneda')
        moneda.text = "DOLAR"
        
        return info_liquidacion
    
    def _create_detalle_liquidacion(self, item):
        """
        Crea un detalle de liquidación de compra - VERSIÓN MEJORADA Y CORREGIDA
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code[:25]
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description[:300]
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{float(item.quantity):.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{float(item.unit_price):.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{float(getattr(item, 'discount', 0)):.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{float(item.subtotal):.2f}"
        
        return detalle
    
    # ========== MÉTODOS AUXILIARES MEJORADOS ==========
    
    def _create_detalle_generico(self):
        """
        Crea un detalle genérico para documentos sin items específicos - VERSIÓN MEJORADA Y CORREGIDA
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = 'SERV001'
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = 'Servicio genérico'
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = '1.000000'
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{float(self.document.subtotal_without_tax):.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = '0.00'
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{float(self.document.subtotal_without_tax):.2f}"
        
        # Impuestos
        impuestos = SubElement(detalle, 'impuestos')
        impuesto = SubElement(impuestos, 'impuesto')
        SubElement(impuesto, 'codigo').text = '2'
        SubElement(impuesto, 'codigoPorcentaje').text = '2'
        SubElement(impuesto, 'tarifa').text = '15.00'
        SubElement(impuesto, 'baseImponible').text = f"{float(self.document.subtotal_without_tax):.2f}"
        SubElement(impuesto, 'valor').text = f"{float(self.document.total_tax):.2f}"
        
        return detalle
    
    def _get_taxes_summary(self):
        """
        Obtiene resumen de impuestos agrupados - VERSIÓN MEJORADA
        """
        taxes_summary = {}
        
        # Si el documento tiene impuestos directos
        if hasattr(self.document, 'taxes') and self.document.taxes.exists():
            for tax in self.document.taxes.all():
                key = (tax.tax_code, tax.percentage_code)
                if key not in taxes_summary:
                    taxes_summary[key] = {
                        'base': 0,
                        'valor': 0,
                        'codigo': tax.tax_code,
                        'codigoPorcentaje': tax.percentage_code,
                        'tarifa': float(tax.rate)
                    }
                taxes_summary[key]['base'] += float(tax.taxable_base)
                taxes_summary[key]['valor'] += float(tax.tax_amount)
        else:
            # Crear un impuesto por defecto (IVA 15%)
            taxes_summary[('2', '2')] = {
                'base': float(self.document.subtotal_without_tax),
                'valor': float(self.document.total_tax),
                'codigo': '2',
                'codigoPorcentaje': '2',
                'tarifa': 15.00
            }
        
        return taxes_summary
    
    def _get_taxes_summary_for_credit_note(self):
        """
        Obtiene resumen de impuestos específico para notas de crédito
        """
        taxes_summary = {}
        
        # Para notas de crédito, usar los campos específicos
        taxes_summary[('2', '2')] = {
            'base': float(self.document.subtotal_without_tax),
            'valor': float(self.document.total_tax),
            'codigo': '2',
            'codigoPorcentaje': '2',
            'tarifa': 15.00
        }
        
        return taxes_summary
    
    def _get_taxes_summary_for_debit_note(self):
        """
        Obtiene resumen de impuestos específico para notas de débito
        """
        taxes_summary = {}
        
        # Para notas de débito, usar los campos específicos
        taxes_summary[('2', '2')] = {
            'base': float(self.document.subtotal_without_tax),
            'valor': float(self.document.total_tax),
            'codigo': '2',
            'codigoPorcentaje': '2',
            'tarifa': 15.00
        }
        
        return taxes_summary
    
    def _create_info_adicional(self):
        """
        Crea la sección de información adicional - VERSIÓN MEJORADA
        """
        info_adicional = Element('infoAdicional')
        
        # Agregar información adicional del documento
        if hasattr(self.document, 'additional_data') and self.document.additional_data:
            for key, value in self.document.additional_data.items():
                if value:  # Solo agregar si tiene valor
                    campo = SubElement(info_adicional, 'campoAdicional', {
                        'nombre': str(key)[:50]  # Límite SRI
                    })
                    campo.text = str(value)[:300]  # Límite SRI
        
        # Agregar email del cliente si existe
        if hasattr(self.document, 'customer_email') and self.document.customer_email:
            email = SubElement(info_adicional, 'campoAdicional', {
                'nombre': 'EMAIL'
            })
            email.text = self.document.customer_email[:300]
        
        # Agregar teléfono del cliente si existe
        if hasattr(self.document, 'customer_phone') and self.document.customer_phone:
            telefono = SubElement(info_adicional, 'campoAdicional', {
                'nombre': 'TELEFONO'
            })
            telefono.text = self.document.customer_phone[:50]
        
        return info_adicional
    
    def _prettify_xml(self, elem):
        """
        Convierte el elemento XML a string con formato bonito - VERSIÓN MEJORADA
        """
        try:
            rough_string = tostring(elem, encoding='utf-8')
            reparsed = minidom.parseString(rough_string)
            
            # Obtener el XML con declaración y formato
            xml_str = reparsed.toprettyxml(indent="  ", encoding='UTF-8').decode('utf-8')
            
            # Limpiar líneas vacías extra
            lines = [line for line in xml_str.splitlines() if line.strip()]
            
            return '\n'.join(lines)
            
        except Exception as e:
            logger.error(f"Error formateando XML: {str(e)}")
            # Si falla el formateo, devolver XML sin formato
            return tostring(elem, encoding='utf-8').decode('utf-8')