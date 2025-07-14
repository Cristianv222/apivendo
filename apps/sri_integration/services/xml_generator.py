# -*- coding: utf-8 -*-
"""
Generador de XML para documentos del SRI
"""

import logging
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from django.utils import timezone
from apps.sri_integration.models import ElectronicDocument

logger = logging.getLogger(__name__)


class XMLGenerator:
    """
    Generador de XML para documentos electrónicos del SRI
    """
    
    def __init__(self, document):
        self.document = document
        self.company = document.company
        self.sri_config = self.company.sri_configuration
    
    def generate_invoice_xml(self):
        """
        Genera XML para factura electrónica
        """
        try:
            # Crear elemento raíz
            factura = Element('factura', {
                'id': 'comprobante',
                'version': '1.1.0'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('01')  # 01 = Factura
            factura.append(info_tributaria)
            
            # Información de la factura
            info_factura = self._create_info_factura()
            factura.append(info_factura)
            
            # Detalles
            detalles = SubElement(factura, 'detalles')
            for item in self.document.items.all():
                detalle = self._create_detalle_factura(item)
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
        Genera XML para nota de crédito
        """
        try:
            # Crear elemento raíz
            nota_credito = Element('notaCredito', {
                'id': 'comprobante',
                'version': '1.1.0'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('04')  # 04 = Nota de Crédito
            nota_credito.append(info_tributaria)
            
            # Información de la nota de crédito
            info_nota_credito = self._create_info_nota_credito()
            nota_credito.append(info_nota_credito)
            
            # Detalles
            detalles = SubElement(nota_credito, 'detalles')
            for item in self.document.items.all():
                detalle = self._create_detalle_nota_credito(item)
                detalles.append(detalle)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                nota_credito.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(nota_credito)
            
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating credit note XML: {str(e)}")
            raise ValueError(f"Error generating credit note XML: {str(e)}")
    
    def generate_debit_note_xml(self):
        """
        Genera XML para nota de débito
        """
        try:
            # Crear elemento raíz
            nota_debito = Element('notaDebito', {
                'id': 'comprobante',
                'version': '1.0.0'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('05')  # 05 = Nota de Débito
            nota_debito.append(info_tributaria)
            
            # Información de la nota de débito
            info_nota_debito = self._create_info_nota_debito()
            nota_debito.append(info_nota_debito)
            
            # Motivos
            motivos = SubElement(nota_debito, 'motivos')
            for item in self.document.items.all():
                motivo = self._create_motivo_nota_debito(item)
                motivos.append(motivo)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                nota_debito.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(nota_debito)
            
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating debit note XML: {str(e)}")
            raise ValueError(f"Error generating debit note XML: {str(e)}")
    
    def generate_retention_xml(self):
        """
        Genera XML para comprobante de retención
        """
        try:
            # Crear elemento raíz
            comp_retencion = Element('comprobanteRetencion', {
                'id': 'comprobante',
                'version': '1.0.0'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('07')  # 07 = Retención
            comp_retencion.append(info_tributaria)
            
            # Información de retención
            info_comp_retencion = self._create_info_comp_retencion()
            comp_retencion.append(info_comp_retencion)
            
            # Impuestos (detalles de retención)
            impuestos = SubElement(comp_retencion, 'impuestos')
            
            if hasattr(self.document, 'details'):
                for detail in self.document.details.all():
                    impuesto = self._create_impuesto_retencion(detail)
                    impuestos.append(impuesto)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                comp_retencion.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(comp_retencion)
            
            return xml_str
            
        except Exception as e:
            logger.error(f"Error generating retention XML: {str(e)}")
            raise ValueError(f"Error generating retention XML: {str(e)}")
    
    def generate_purchase_settlement_xml(self):
        """
        Genera XML para liquidación de compra
        """
        try:
            # Crear elemento raíz
            liquidacion_compra = Element('liquidacionCompra', {
                'id': 'comprobante',
                'version': '1.1.0'
            })
            
            # Información tributaria
            info_tributaria = self._create_info_tributaria('03')  # 03 = Liquidación de compra
            liquidacion_compra.append(info_tributaria)
            
            # Información de liquidación
            info_liquidacion_compra = self._create_info_liquidacion_compra()
            liquidacion_compra.append(info_liquidacion_compra)
            
            # Detalles
            detalles = SubElement(liquidacion_compra, 'detalles')
            if hasattr(self.document, 'items'):
                for item in self.document.items.all():
                    detalle = self._create_detalle_liquidacion(item)
                    detalles.append(detalle)
            
            # Información adicional
            info_adicional = self._create_info_adicional()
            if len(info_adicional) > 0:
                liquidacion_compra.append(info_adicional)
            
            # Convertir a string con formato
            xml_str = self._prettify_xml(liquidacion_compra)
            
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
        razon_social.text = self.company.business_name
        
        # Nombre comercial
        if self.company.trade_name:
            nombre_comercial = SubElement(info_tributaria, 'nombreComercial')
            nombre_comercial.text = self.company.trade_name
        
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
        dir_matriz.text = self.company.address
        
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
        dir_establecimiento.text = self.company.address
        
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
        razon_social_comprador.text = self.document.customer_name
        
        # Identificación del comprador
        identificacion_comprador = SubElement(info_factura, 'identificacionComprador')
        identificacion_comprador.text = self.document.customer_identification
        
        # Dirección del comprador
        if self.document.customer_address:
            direccion_comprador = SubElement(info_factura, 'direccionComprador')
            direccion_comprador.text = self.document.customer_address
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_factura, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{self.document.subtotal_without_tax:.2f}"
        
        # Total descuento
        total_descuento = SubElement(info_factura, 'totalDescuento')
        total_descuento.text = f"{self.document.total_discount:.2f}"
        
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
        importe_total.text = f"{self.document.total_amount:.2f}"
        
        # Moneda
        moneda = SubElement(info_factura, 'moneda')
        moneda.text = "DOLAR"
        
        return info_factura
    
    def _create_detalle_factura(self, item):
        """
        Crea un detalle de factura
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code
        
        # Código auxiliar
        if item.auxiliary_code:
            codigo_auxiliar = SubElement(detalle, 'codigoAuxiliar')
            codigo_auxiliar.text = item.auxiliary_code
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{item.quantity:.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{item.unit_price:.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{item.discount:.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{item.subtotal:.2f}"
        
        # Detalles adicionales
        if item.additional_details:
            detalles_adicionales = SubElement(detalle, 'detallesAdicionales')
            for key, value in item.additional_details.items():
                detalle_adicional = SubElement(detalles_adicionales, 'detAdicional', {
                    'nombre': key,
                    'valor': str(value)
                })
        
        # Impuestos del ítem
        impuestos = SubElement(detalle, 'impuestos')
        for tax in item.taxes.all():
            impuesto = SubElement(impuestos, 'impuesto')
            
            codigo = SubElement(impuesto, 'codigo')
            codigo.text = tax.tax_code
            
            codigo_porcentaje = SubElement(impuesto, 'codigoPorcentaje')
            codigo_porcentaje.text = tax.percentage_code
            
            tarifa = SubElement(impuesto, 'tarifa')
            tarifa.text = f"{tax.rate:.2f}"
            
            base_imponible = SubElement(impuesto, 'baseImponible')
            base_imponible.text = f"{tax.taxable_base:.2f}"
            
            valor = SubElement(impuesto, 'valor')
            valor.text = f"{tax.tax_amount:.2f}"
        
        return detalle
    
    # ========== MÉTODOS PARA NOTAS DE CRÉDITO ==========
    
    def _create_info_nota_credito(self):
        """
        Crea la sección infoNotaCredito
        """
        info_nota_credito = Element('infoNotaCredito')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_nota_credito, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_nota_credito, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address
        
        # Tipo de identificación del comprador
        tipo_identificacion_comprador = SubElement(info_nota_credito, 'tipoIdentificacionComprador')
        tipo_identificacion_comprador.text = self.document.customer_identification_type
        
        # Razón social del comprador
        razon_social_comprador = SubElement(info_nota_credito, 'razonSocialComprador')
        razon_social_comprador.text = self.document.customer_name
        
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
        motivo.text = getattr(self.document, 'reason_description', 'Nota de crédito')
        
        # Documento modificado
        if hasattr(self.document, 'original_document'):
            doc_modificado = SubElement(info_nota_credito, 'docModificado')
            doc_modificado.text = '01'  # Factura
            
            num_doc_modificado = SubElement(info_nota_credito, 'numDocModificado')
            num_doc_modificado.text = self.document.original_document.document_number
            
            fecha_emision_doc_sustento = SubElement(info_nota_credito, 'fechaEmisionDocSustento')
            fecha_emision_doc_sustento.text = self.document.original_document.issue_date.strftime('%d/%m/%Y')
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_nota_credito, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{self.document.subtotal_without_tax:.2f}"
        
        # Total con impuestos
        total_con_impuestos = SubElement(info_nota_credito, 'totalConImpuestos')
        
        # Agregar impuestos agrupados
        taxes_summary = self._get_taxes_summary()
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
        valor_modificacion.text = f"{self.document.total_amount:.2f}"
        
        # Moneda
        moneda = SubElement(info_nota_credito, 'moneda')
        moneda.text = "DOLAR"
        
        return info_nota_credito
    
    def _create_detalle_nota_credito(self, item):
        """
        Crea un detalle de nota de crédito
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code
        
        # Código auxiliar
        if hasattr(item, 'auxiliary_code') and item.auxiliary_code:
            codigo_auxiliar = SubElement(detalle, 'codigoAuxiliar')
            codigo_auxiliar.text = item.auxiliary_code
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{item.quantity:.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{item.unit_price:.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{item.discount:.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{item.subtotal:.2f}"
        
        return detalle
    
    # ========== MÉTODOS PARA NOTAS DE DÉBITO ==========
    
    def _create_info_nota_debito(self):
        """
        Crea la sección infoNotaDebito
        """
        info_nota_debito = Element('infoNotaDebito')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_nota_debito, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_nota_debito, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address
        
        # Tipo de identificación del comprador
        tipo_identificacion_comprador = SubElement(info_nota_debito, 'tipoIdentificacionComprador')
        tipo_identificacion_comprador.text = self.document.customer_identification_type
        
        # Razón social del comprador
        razon_social_comprador = SubElement(info_nota_debito, 'razonSocialComprador')
        razon_social_comprador.text = self.document.customer_name
        
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
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_nota_debito, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{self.document.subtotal_without_tax:.2f}"
        
        # Impuestos
        impuestos = SubElement(info_nota_debito, 'impuestos')
        taxes_summary = self._get_taxes_summary()
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
        valor_total.text = f"{self.document.total_amount:.2f}"
        
        return info_nota_debito
    
    def _create_motivo_nota_debito(self, item):
        """
        Crea un motivo de nota de débito
        """
        motivo = Element('motivo')
        
        # Razón
        razon = SubElement(motivo, 'razon')
        razon.text = getattr(self.document, 'reason_description', item.description)
        
        # Valor
        valor = SubElement(motivo, 'valor')
        valor.text = f"{item.subtotal:.2f}"
        
        return motivo
    
    # ========== MÉTODOS PARA RETENCIONES ==========
    
    def _create_info_comp_retencion(self):
        """
        Crea la sección infoCompRetencion
        """
        info_comp_retencion = Element('infoCompRetencion')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_comp_retencion, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_comp_retencion, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_comp_retencion, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_comp_retencion, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Tipo de identificación del sujeto retenido
        tipo_identificacion_sujeto_retenido = SubElement(info_comp_retencion, 'tipoIdentificacionSujetoRetenido')
        tipo_identificacion_sujeto_retenido.text = self.document.supplier_identification_type
        
        # Razón social del sujeto retenido
        razon_social_sujeto_retenido = SubElement(info_comp_retencion, 'razonSocialSujetoRetenido')
        razon_social_sujeto_retenido.text = self.document.supplier_name
        
        # Identificación del sujeto retenido
        identificacion_sujeto_retenido = SubElement(info_comp_retencion, 'identificacionSujetoRetenido')
        identificacion_sujeto_retenido.text = self.document.supplier_identification
        
        # Período fiscal
        periodo_fiscal = SubElement(info_comp_retencion, 'periodoFiscal')
        periodo_fiscal.text = getattr(self.document, 'fiscal_period', self.document.issue_date.strftime('%m/%Y'))
        
        return info_comp_retencion
    
    def _create_impuesto_retencion(self, detail):
        """
        Crea un impuesto de retención
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
        base_imponible.text = f"{detail.taxable_base:.2f}"
        
        # Porcentaje de retención
        porcentaje_retener = SubElement(impuesto, 'porcentajeRetener')
        porcentaje_retener.text = f"{detail.retention_percentage:.2f}"
        
        # Valor retenido
        valor_retenido = SubElement(impuesto, 'valorRetenido')
        valor_retenido.text = f"{detail.retained_amount:.2f}"
        
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
        Crea la sección infoLiquidacionCompra
        """
        info_liquidacion = Element('infoLiquidacionCompra')
        
        # Fecha de emisión
        fecha_emision = SubElement(info_liquidacion, 'fechaEmision')
        fecha_emision.text = self.document.issue_date.strftime('%d/%m/%Y')
        
        # Dirección establecimiento
        dir_establecimiento = SubElement(info_liquidacion, 'dirEstablecimiento')
        dir_establecimiento.text = self.company.address
        
        # Contribuyente especial
        if self.sri_config.special_taxpayer and self.sri_config.special_taxpayer_number:
            contribuyente_especial = SubElement(info_liquidacion, 'contribuyenteEspecial')
            contribuyente_especial.text = self.sri_config.special_taxpayer_number
        
        # Obligado a llevar contabilidad
        obligado_contabilidad = SubElement(info_liquidacion, 'obligadoContabilidad')
        obligado_contabilidad.text = 'SI' if self.sri_config.accounting_required else 'NO'
        
        # Tipo de identificación del proveedor
        tipo_identificacion_proveedor = SubElement(info_liquidacion, 'tipoIdentificacionProveedor')
        tipo_identificacion_proveedor.text = self.document.supplier_identification_type
        
        # Razón social del proveedor
        razon_social_proveedor = SubElement(info_liquidacion, 'razonSocialProveedor')
        razon_social_proveedor.text = self.document.supplier_name
        
        # Identificación del proveedor
        identificacion_proveedor = SubElement(info_liquidacion, 'identificacionProveedor')
        identificacion_proveedor.text = self.document.supplier_identification
        
        # Dirección del proveedor
        if self.document.supplier_address:
            direccion_proveedor = SubElement(info_liquidacion, 'direccionProveedor')
            direccion_proveedor.text = self.document.supplier_address
        
        # Total sin impuestos
        total_sin_impuestos = SubElement(info_liquidacion, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{self.document.subtotal_without_tax:.2f}"
        
        # Total con impuestos
        total_con_impuestos = SubElement(info_liquidacion, 'totalConImpuestos')
        
        # Agregar impuestos (simplificado para el ejemplo)
        total_impuesto = SubElement(total_con_impuestos, 'totalImpuesto')
        codigo = SubElement(total_impuesto, 'codigo')
        codigo.text = '2'  # IVA
        codigo_porcentaje = SubElement(total_impuesto, 'codigoPorcentaje')
        codigo_porcentaje.text = '2'  # 12%
        base_imponible = SubElement(total_impuesto, 'baseImponible')
        base_imponible.text = f"{self.document.subtotal_without_tax:.2f}"
        tarifa = SubElement(total_impuesto, 'tarifa')
        tarifa.text = "15.00"
        valor = SubElement(total_impuesto, 'valor')
        valor.text = f"{self.document.total_tax:.2f}"
        
        # Importe total
        importe_total = SubElement(info_liquidacion, 'importeTotal')
        importe_total.text = f"{self.document.total_amount:.2f}"
        
        # Moneda
        moneda = SubElement(info_liquidacion, 'moneda')
        moneda.text = "DOLAR"
        
        return info_liquidacion
    
    def _create_detalle_liquidacion(self, item):
        """
        Crea un detalle de liquidación de compra
        """
        detalle = Element('detalle')
        
        # Código principal
        codigo_principal = SubElement(detalle, 'codigoPrincipal')
        codigo_principal.text = item.main_code
        
        # Descripción
        descripcion = SubElement(detalle, 'descripcion')
        descripcion.text = item.description
        
        # Cantidad
        cantidad = SubElement(detalle, 'cantidad')
        cantidad.text = f"{item.quantity:.6f}"
        
        # Precio unitario
        precio_unitario = SubElement(detalle, 'precioUnitario')
        precio_unitario.text = f"{item.unit_price:.6f}"
        
        # Descuento
        descuento = SubElement(detalle, 'descuento')
        descuento.text = f"{item.discount:.2f}"
        
        # Precio total sin impuesto
        precio_total_sin_impuesto = SubElement(detalle, 'precioTotalSinImpuesto')
        precio_total_sin_impuesto.text = f"{item.subtotal:.2f}"
        
        return detalle
    
    # ========== MÉTODOS AUXILIARES ==========
    
    def _get_taxes_summary(self):
        """
        Obtiene resumen de impuestos agrupados
        """
        taxes_summary = {}
        
        # Si el documento tiene impuestos directos
        if hasattr(self.document, 'taxes'):
            for tax in self.document.taxes.all():
                key = (tax.tax_code, tax.percentage_code)
                if key not in taxes_summary:
                    taxes_summary[key] = {
                        'base': 0,
                        'valor': 0,
                        'codigo': tax.tax_code,
                        'codigoPorcentaje': tax.percentage_code,
                        'tarifa': tax.rate
                    }
                taxes_summary[key]['base'] += tax.taxable_base
                taxes_summary[key]['valor'] += tax.tax_amount
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
    
    def _create_info_adicional(self):
        """
        Crea la sección de información adicional
        """
        info_adicional = Element('infoAdicional')
        
        # Agregar información adicional del documento
        if self.document.additional_data:
            for key, value in self.document.additional_data.items():
                campo = SubElement(info_adicional, 'campoAdicional', {
                    'nombre': key
                })
                campo.text = str(value)
        
        # Agregar email del cliente si existe
        if self.document.customer_email:
            email = SubElement(info_adicional, 'campoAdicional', {
                'nombre': 'EMAIL'
            })
            email.text = self.document.customer_email
        
        # Agregar teléfono del cliente si existe
        if self.document.customer_phone:
            telefono = SubElement(info_adicional, 'campoAdicional', {
                'nombre': 'TELEFONO'
            })
            telefono.text = self.document.customer_phone
        
        return info_adicional
    
    def _prettify_xml(self, elem):
        """
        Convierte el elemento XML a string con formato bonito
        """
        rough_string = tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        
        # Obtener el XML con declaración y formato
        xml_str = reparsed.toprettyxml(indent="  ", encoding='UTF-8').decode('utf-8')
        
        # Limpiar líneas vacías extra
        lines = [line for line in xml_str.splitlines() if line.strip()]
        
        return '\n'.join(lines)