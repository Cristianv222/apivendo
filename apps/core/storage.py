import os
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings

@deconstructible
class DynamicMediaStorage(Storage):
    def __init__(self, *args, **kwargs):
        self._local_storage = FileSystemStorage()
        self._s3_storage = None
        self._is_s3_active = None
        self._last_bucket = None
        
    def _initialize_s3(self):
        try:
            from apps.settings.models import SystemSetting
            
            # Obtener configuraciones de la base de datos
            active_setting = SystemSetting.objects.filter(key='STORAGE_ACTIVE').first()
            if not active_setting or active_setting.value.lower() != 'true':
                self._is_s3_active = False
                return None

            bucket_name = SystemSetting.objects.filter(key='S3_BUCKET_NAME').first()
            region = SystemSetting.objects.filter(key='S3_REGION').first()
            access_key = SystemSetting.objects.filter(key='S3_ACCESS_KEY').first()
            secret_key = SystemSetting.objects.filter(key='S3_SECRET_KEY').first()
            endpoint = SystemSetting.objects.filter(key='S3_ENDPOINT_URL').first()
            cdn_domain = SystemSetting.objects.filter(key='S3_CDN_DOMAIN').first()

            if not all([bucket_name, access_key, secret_key, endpoint]):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("[STORAGE] Faltan configuraciones críticas para S3 en SystemSetting")
                self._is_s3_active = False
                return None

            # Solo recrear si cambió el bucket (optimización simple)
            if self._s3_storage and getattr(self, '_last_bucket', None) == bucket_name.value:
                self._is_s3_active = True
                return self._s3_storage

            import boto3
            from storages.backends.s3boto3 import S3Boto3Storage
            
            # Configuración para DigitalOcean Spaces / S3
            # Nota: Usamos aws_access_key_id y aws_secret_access_key que son los nombres estándar
            kwargs = {
                'access_key': access_key.value.strip(),
                'secret_key': secret_key.value.strip(),
                'bucket_name': bucket_name.value.strip(),
                'location': 'facturacion',  # Carpeta raíz en el bucket
                'region_name': region.value.strip() if region else None,
                'endpoint_url': endpoint.value.strip(),
                'default_acl': 'public-read',
                'file_overwrite': False,
                'custom_domain': cdn_domain.value.strip() if cdn_domain and cdn_domain.value else None,
            }

            self._s3_storage = S3Boto3Storage(**kwargs)
            self._is_s3_active = True
            self._last_bucket = bucket_name.value
            
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[STORAGE] Motor S3 inicializado correctamente en bucket: {bucket_name.value}")
            
            return self._s3_storage

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[STORAGE] Error crítico inicializando S3: {str(e)}")
            self._is_s3_active = False
            return None

    @property
    def current(self):
        s3 = self._initialize_s3()
        if s3:
            return s3
        return self._local_storage

    def _open(self, name, mode='rb'):
        return self.current._open(name, mode)

    def _save(self, name, content):
        import logging
        logger = logging.getLogger(__name__)
        engine = "S3" if self._is_s3_active else "LOCAL"
        # Usamos warning para asegurar que se vea en los logs de Docker con LOG_LEVEL=INFO
        logger.warning(f"[STORAGE] Guardando {name} en motor {engine}")
        return self.current._save(name, content)

    def path(self, name):
        # S3 does not have a local path
        if self._is_s3_active:
            raise NotImplementedError("This backend doesn't support absolute paths.")
        return self.current.path(name)

    def delete(self, name):
        return self.current.delete(name)

    def exists(self, name):
        return self.current.exists(name)

    def listdir(self, path):
        return self.current.listdir(path)

    def size(self, name):
        return self.current.size(name)

    def url(self, name):
        return self.current.url(name)
        
    def get_accessed_time(self, name):
        return self.current.get_accessed_time(name)

    def get_created_time(self, name):
        return self.current.get_created_time(name)

    def get_modified_time(self, name):
        return self.current.get_modified_time(name)
    
    def get_valid_name(self, name):
        return self.current.get_valid_name(name)

    def get_available_name(self, name, max_length=None):
        return self.current.get_available_name(name, max_length=max_length)

    def generate_filename(self, filename):
        return self.current.generate_filename(filename)
