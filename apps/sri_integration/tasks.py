# -*- coding: utf-8 -*-
"""
Tareas Celery para SRI Integration
apps/sri_integration/tasks.py

Tareas en background para autorización automática de documentos SRI
✅ AUTORIZACIÓN AUTOMÁTICA DE DOCUMENTOS
✅ PROCESAMIENTO EN BACKGROUND
✅ REINTENTOS INTELIGENTES
✅ LIMPIEZA DE DATOS ANTIGUOS
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import ElectronicDocument, SRIResponse
from .services.soap_client import SRISOAPClient
from .services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=10, default_retry_delay=120)
def check_document_authorization_async(self, document_id):
    """
    ✅ TAREA PRINCIPAL: Verificar autorización de documento automáticamente
    
    Args:
        document_id (int): ID del documento a verificar
        
    Returns:
        bool: True si está autorizado o no necesita más verificación
    """
    try:
        logger.info(f"🔄 [CELERY] Checking authorization for document {document_id}")
        
        # Obtener documento con lock para evitar condiciones de carrera
        try:
            with transaction.atomic():
                document = ElectronicDocument.objects.select_for_update().get(id=document_id)
        except ElectronicDocument.DoesNotExist:
            logger.error(f"❌ [CELERY] Document {document_id} not found")
            return False
        
        # Solo procesar si está en SENT
        if document.status != 'SENT':
            logger.info(f"ℹ️ [CELERY] Document {document_id} status is {document.status}, skipping")
            if document.status == 'AUTHORIZED':
                return True  # Ya está autorizado
            return False  # Otro estado, no procesar más
        
        # Verificar que no haya pasado demasiado tiempo
        time_elapsed = timezone.now() - document.created_at
        if time_elapsed.total_seconds() > 86400:  # 24 horas
            logger.warning(f"⏰ [CELERY] Document {document_id} timeout after 24 hours")
            return False
        
        # Verificar autorización en el SRI
        sri_client = SRISOAPClient(document.company)
        success, message = sri_client.get_document_authorization(document)
        
        if success:
            logger.info(f"🎉 [CELERY] Document {document_id} AUTHORIZED: {document.sri_authorization_code}")
            
            # Enviar email si está configurado y es exitoso
            try:
                if document.company.sri_configuration.email_enabled:
                    send_authorization_notification_email.delay(document_id)
            except Exception as email_error:
                logger.warning(f"⚠️ [CELERY] Email notification failed for document {document_id}: {email_error}")
            
            return True
        else:
            # Si aún no está autorizado, programar reintento
            logger.info(f"⏳ [CELERY] Document {document_id} still pending: {message}")
            
            # Calcular tiempo de reintento con backoff exponencial
            retry_count = self.request.retries
            if retry_count < 3:
                countdown = 120  # 2 minutos para los primeros intentos
            elif retry_count < 6:
                countdown = 300  # 5 minutos para intentos medios
            else:
                countdown = 600  # 10 minutos para intentos finales
            
            logger.info(f"🔄 [CELERY] Scheduling retry {retry_count + 1} in {countdown // 60} minutes")
            raise self.retry(countdown=countdown)
    
    except Exception as e:
        logger.error(f"❌ [CELERY] Error checking authorization for {document_id}: {e}")
        
        # Reintentar en caso de error con backoff exponencial
        if self.request.retries < self.max_retries:
            countdown = min(300, (2 ** self.request.retries) * 60)  # Max 5 minutos
            logger.info(f"🔄 [CELERY] Retrying due to error in {countdown} seconds...")
            raise self.retry(countdown=countdown)
        else:
            logger.error(f"❌ [CELERY] Max retries exceeded for document {document_id}")
            return False

@shared_task
def process_document_async(document_id):
    """
    ✅ TAREA: Procesar documento completo en background
    
    Args:
        document_id (int): ID del documento a procesar
        
    Returns:
        dict: Resultado del procesamiento
    """
    try:
        logger.info(f"🚀 [CELERY] Processing document {document_id} in background")
        
        document = ElectronicDocument.objects.get(id=document_id)
        processor = DocumentProcessor(document.company)
        
        success, message = processor.process_document(document)
        
        if success and document.status == 'SENT':
            # Programar verificación de autorización automática
            logger.info(f"📅 [CELERY] Scheduling authorization check for document {document_id}")
            check_document_authorization_async.apply_async(
                args=[document_id], 
                countdown=120  # 2 minutos
            )
        
        logger.info(f"✅ [CELERY] Document {document_id} processing completed: {success}")
        return {
            'success': success, 
            'message': message,
            'document_id': document_id,
            'status': document.status
        }
        
    except ElectronicDocument.DoesNotExist:
        error_msg = f"Document {document_id} not found"
        logger.error(f"❌ [CELERY] {error_msg}")
        return {'success': False, 'message': error_msg}
    except Exception as e:
        error_msg = f"Error processing document {document_id}: {e}"
        logger.error(f"❌ [CELERY] {error_msg}")
        return {'success': False, 'message': error_msg}

@shared_task
def check_all_pending_authorizations():
    """
    ✅ TAREA PERIÓDICA: Verificar todos los documentos pendientes de autorización
    
    Ejecutada automáticamente cada 5 minutos por Celery Beat
    """
    try:
        logger.info("🔍 [CELERY_BEAT] Checking all pending authorizations")
        
        # Obtener documentos en SENT de las últimas 24 horas
        time_limit = timezone.now() - timedelta(hours=24)
        pending_docs = ElectronicDocument.objects.filter(
            status='SENT',
            created_at__gte=time_limit
        ).select_related('company')
        
        total_docs = pending_docs.count()
        if total_docs == 0:
            logger.info("ℹ️ [CELERY_BEAT] No pending documents found")
            return {'checked': 0, 'scheduled': 0}
        
        logger.info(f"📊 [CELERY_BEAT] Found {total_docs} pending documents")
        
        scheduled_count = 0
        for doc in pending_docs:
            try:
                # Verificar si ya hay una tarea programada para este documento
                # (esto es una simplificación - en producción podrías usar Redis para tracking)
                
                # Programar verificación inmediata
                check_document_authorization_async.delay(doc.id)
                scheduled_count += 1
                
            except Exception as e:
                logger.error(f"❌ [CELERY_BEAT] Error scheduling check for document {doc.id}: {e}")
        
        logger.info(f"✅ [CELERY_BEAT] Scheduled authorization checks for {scheduled_count}/{total_docs} documents")
        
        return {
            'checked': total_docs,
            'scheduled': scheduled_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [CELERY_BEAT] Error in check_all_pending_authorizations: {e}")
        return {'error': str(e)}

@shared_task
def cleanup_old_sri_responses():
    """
    ✅ TAREA PERIÓDICA: Limpiar respuestas SRI antiguas
    
    Ejecutada automáticamente cada 24 horas por Celery Beat
    """
    try:
        logger.info("🧹 [CELERY_CLEANUP] Starting SRI responses cleanup")
        
        # Eliminar respuestas de más de 30 días
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_responses = SRIResponse.objects.filter(created_at__lt=cutoff_date)
        count = old_responses.count()
        
        if count > 0:
            old_responses.delete()
            logger.info(f"🗑️ [CELERY_CLEANUP] Deleted {count} old SRI responses")
        else:
            logger.info("ℹ️ [CELERY_CLEANUP] No old SRI responses to delete")
        
        return {'deleted_responses': count, 'cutoff_date': cutoff_date.isoformat()}
        
    except Exception as e:
        logger.error(f"❌ [CELERY_CLEANUP] Error in cleanup_old_sri_responses: {e}")
        return {'error': str(e)}

@shared_task
def send_authorization_notification_email(document_id):
    """
    ✅ TAREA: Enviar notificación por email cuando un documento es autorizado
    
    Args:
        document_id (int): ID del documento autorizado
    """
    try:
        logger.info(f"📧 [CELERY_EMAIL] Sending authorization notification for document {document_id}")
        
        document = ElectronicDocument.objects.get(id=document_id)
        
        if document.status != 'AUTHORIZED':
            logger.warning(f"⚠️ [CELERY_EMAIL] Document {document_id} is not authorized, skipping email")
            return {'sent': False, 'reason': 'Document not authorized'}
        
        # Importar EmailService aquí para evitar import circular
        from .services.email_service import EmailService
        
        email_service = EmailService(document.company)
        success, message = email_service.send_authorization_notification(document)
        
        if success:
            logger.info(f"✅ [CELERY_EMAIL] Authorization notification sent for document {document_id}")
            
            # Actualizar documento para marcar que se envió el email
            document.email_sent = True
            document.email_sent_date = timezone.now()
            document.save(update_fields=['email_sent', 'email_sent_date'])
        else:
            logger.error(f"❌ [CELERY_EMAIL] Failed to send notification for document {document_id}: {message}")
        
        return {
            'sent': success,
            'message': message,
            'document_id': document_id
        }
        
    except ElectronicDocument.DoesNotExist:
        error_msg = f"Document {document_id} not found for email notification"
        logger.error(f"❌ [CELERY_EMAIL] {error_msg}")
        return {'sent': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Error sending email notification for document {document_id}: {e}"
        logger.error(f"❌ [CELERY_EMAIL] {error_msg}")
        return {'sent': False, 'error': error_msg}

@shared_task
def bulk_process_documents(document_ids):
    """
    ✅ TAREA: Procesar múltiples documentos en lote
    
    Args:
        document_ids (list): Lista de IDs de documentos a procesar
        
    Returns:
        dict: Resumen del procesamiento en lote
    """
    try:
        logger.info(f"📦 [CELERY_BULK] Processing {len(document_ids)} documents in bulk")
        
        results = {
            'total': len(document_ids),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for doc_id in document_ids:
            try:
                # Procesar cada documento de forma asíncrona
                result = process_document_async.delay(doc_id)
                results['successful'] += 1
                
            except Exception as e:
                logger.error(f"❌ [CELERY_BULK] Error processing document {doc_id}: {e}")
                results['failed'] += 1
                results['errors'].append({
                    'document_id': doc_id,
                    'error': str(e)
                })
        
        logger.info(f"✅ [CELERY_BULK] Bulk processing completed: {results['successful']} successful, {results['failed']} failed")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ [CELERY_BULK] Error in bulk_process_documents: {e}")
        return {'error': str(e)}

@shared_task
def retry_failed_documents():
    """
    ✅ TAREA PERIÓDICA: Reintentar documentos que fallaron
    
    Busca documentos en estado ERROR y los reintenta automáticamente
    """
    try:
        logger.info("🔄 [CELERY_RETRY] Looking for failed documents to retry")
        
        # Buscar documentos en ERROR de las últimas 6 horas
        time_limit = timezone.now() - timedelta(hours=6)
        failed_docs = ElectronicDocument.objects.filter(
            status='ERROR',
            updated_at__gte=time_limit
        ).select_related('company')
        
        retry_count = 0
        for doc in failed_docs:
            try:
                # Resetear estado para reintento
                doc.status = 'GENERATED'
                doc.save(update_fields=['status'])
                
                # Procesar nuevamente
                process_document_async.delay(doc.id)
                retry_count += 1
                
                logger.info(f"🔄 [CELERY_RETRY] Scheduled retry for document {doc.id}")
                
            except Exception as e:
                logger.error(f"❌ [CELERY_RETRY] Error scheduling retry for document {doc.id}: {e}")
        
        logger.info(f"✅ [CELERY_RETRY] Scheduled {retry_count} document retries")
        
        return {
            'found_failed': failed_docs.count(),
            'scheduled_retries': retry_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [CELERY_RETRY] Error in retry_failed_documents: {e}")
        return {'error': str(e)}

@shared_task
def generate_daily_report():
    """
    ✅ TAREA PERIÓDICA: Generar reporte diario de documentos procesados
    
    Ejecutada automáticamente cada día a las 23:00
    """
    try:
        logger.info("📊 [CELERY_REPORT] Generating daily processing report")
        
        today = timezone.now().date()
        today_start = timezone.datetime.combine(today, timezone.datetime.min.time())
        today_end = timezone.datetime.combine(today, timezone.datetime.max.time())
        
        # Hacer timezone-aware
        if timezone.is_naive(today_start):
            today_start = timezone.make_aware(today_start)
        if timezone.is_naive(today_end):
            today_end = timezone.make_aware(today_end)
        
        # Estadísticas del día
        daily_docs = ElectronicDocument.objects.filter(
            created_at__range=[today_start, today_end]
        )
        
        stats = {
            'date': today.isoformat(),
            'total_created': daily_docs.count(),
            'authorized': daily_docs.filter(status='AUTHORIZED').count(),
            'sent': daily_docs.filter(status='SENT').count(),
            'error': daily_docs.filter(status='ERROR').count(),
            'pending': daily_docs.filter(status__in=['GENERATED', 'SIGNED']).count(),
        }
        
        # Calcular tasas de éxito
        if stats['total_created'] > 0:
            stats['success_rate'] = (stats['authorized'] / stats['total_created']) * 100
            stats['processing_rate'] = ((stats['authorized'] + stats['sent']) / stats['total_created']) * 100
        else:
            stats['success_rate'] = 0
            stats['processing_rate'] = 0
        
        logger.info(f"📈 [CELERY_REPORT] Daily stats: {stats['total_created']} created, "
                   f"{stats['authorized']} authorized ({stats['success_rate']:.1f}% success rate)")
        
        # Aquí podrías enviar el reporte por email a administradores
        # send_daily_report_email.delay(stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ [CELERY_REPORT] Error generating daily report: {e}")
        return {'error': str(e)}

# ==========================================
# FUNCIONES HELPER PARA USO EN VIEWS
# ==========================================

def schedule_authorization_check(document_id, delay_minutes=2):
    """
    ✅ FUNCIÓN HELPER: Programar verificación de autorización
    
    Args:
        document_id (int): ID del documento
        delay_minutes (int): Minutos de espera antes de verificar
        
    Returns:
        bool: True si se programó exitosamente
    """
    try:
        task = check_document_authorization_async.apply_async(
            args=[document_id],
            countdown=delay_minutes * 60
        )
        
        logger.info(f"📅 [HELPER] Authorization check scheduled for document {document_id} "
                   f"in {delay_minutes} minutes (task: {task.id})")
        return True
        
    except Exception as e:
        logger.error(f"❌ [HELPER] Error scheduling authorization check for document {document_id}: {e}")
        return False

def schedule_document_processing(document_id, delay_seconds=0):
    """
    ✅ FUNCIÓN HELPER: Programar procesamiento de documento
    
    Args:
        document_id (int): ID del documento
        delay_seconds (int): Segundos de espera antes de procesar
        
    Returns:
        tuple: (success, task_id)
    """
    try:
        task = process_document_async.apply_async(
            args=[document_id],
            countdown=delay_seconds
        )
        
        logger.info(f"📅 [HELPER] Document processing scheduled for document {document_id} "
                   f"in {delay_seconds} seconds (task: {task.id})")
        return True, task.id
        
    except Exception as e:
        logger.error(f"❌ [HELPER] Error scheduling document processing for document {document_id}: {e}")
        return False, None

def get_task_status(task_id):
    """
    ✅ FUNCIÓN HELPER: Obtener estado de una tarea
    
    Args:
        task_id (str): ID de la tarea Celery
        
    Returns:
        dict: Estado de la tarea
    """
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result,
            'successful': result.successful(),
            'failed': result.failed(),
            'ready': result.ready()
        }
        
    except Exception as e:
        logger.error(f"❌ [HELPER] Error getting task status for {task_id}: {e}")
        return {'error': str(e)}