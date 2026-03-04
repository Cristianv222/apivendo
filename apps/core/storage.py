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
            from storages.backends.s3boto3 import S3Boto3Storage
            
            # Chequear activo
            active_setting = SystemSetting.objects.filter(key='STORAGE_ACTIVE').first()
            if not active_setting or active_setting.value != 'true':
                self._is_s3_active = False
                return None
                
            provider = SystemSetting.objects.filter(key='S3_PROVIDER').first()
            region = SystemSetting.objects.filter(key='S3_REGION').first()
            access_key = SystemSetting.objects.filter(key='S3_ACCESS_KEY').first()
            secret_key = SystemSetting.objects.filter(key='S3_SECRET_KEY').first()
            bucket_name = SystemSetting.objects.filter(key='S3_BUCKET_NAME').first()
            endpoint_url = SystemSetting.objects.filter(key='S3_ENDPOINT_URL').first()
            cdn_domain = SystemSetting.objects.filter(key='S3_CDN_DOMAIN').first()
            
            if not all([access_key, secret_key, bucket_name, endpoint_url]):
                self._is_s3_active = False
                return None
                
            # Solo recrear si cambió el bucket (optimización simple)
            if self._s3_storage and self._last_bucket == bucket_name.value:
                self._is_s3_active = True
                return self._s3_storage
                
            import boto3
            from botocore.client import Config
            
            kwargs = {
                'access_key': access_key.value.strip(),
                'secret_key': secret_key.value.strip(),
                'bucket_name': bucket_name.value.strip(),
                'endpoint_url': endpoint_url.value.strip(),
                'location': 'apivendo',  # Carpeta raíz en el bucket
                'default_acl': 'public-read',
                'querystring_auth': False,
                'config': Config(signature_version='s3v4'),
            }
            if region and region.value:
                kwargs['region_name'] = region.value.strip()
            if cdn_domain and cdn_domain.value:
                kwargs['custom_domain'] = cdn_domain.value.strip()
                
            self._s3_storage = S3Boto3Storage(**kwargs)
            self._last_bucket = bucket_name.value
            self._is_s3_active = True
            return self._s3_storage
        except Exception as e:
            self._is_s3_active = False
            return None

    @property
    def current(self):
        s3 = self._initialize_s3()
        return s3 if s3 else self._local_storage

    def _open(self, name, mode='rb'):
        return self.current._open(name, mode)

    def _save(self, name, content):
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
