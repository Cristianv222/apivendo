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
        taxes_summary = {}
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