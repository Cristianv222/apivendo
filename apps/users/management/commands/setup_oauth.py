# -*- coding: utf-8 -*-
"""
Comando para configurar OAuth providers en VENDO_SRI
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Configurar OAuth providers para autenticación social en VENDO_SRI'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--google-client-id',
            type=str,
            help='Google Client ID',
        )
        parser.add_argument(
            '--google-client-secret',
            type=str,
            help='Google Client Secret',
        )
        parser.add_argument(
            '--site-domain',
            type=str,
            default='localhost:8000',
            help='Dominio del sitio (default: localhost:8000)',
        )
        parser.add_argument(
            '--site-name',
            type=str,
            default='VENDO_SRI',
            help='Nombre del sitio (default: VENDO_SRI)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recreación de la configuración OAuth',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Configurando OAuth para VENDO_SRI...\n')
        )
        
        try:
            # 1. Configurar el sitio
            self.setup_site(options)
            
            # 2. Configurar Google OAuth
            self.setup_google_oauth(options)
            
            # 3. Mostrar resumen
            self.show_summary()
            
            self.stdout.write(
                self.style.SUCCESS('\n✅ Configuración OAuth completada exitosamente!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error durante la configuración: {str(e)}')
            )
            raise
    
    def setup_site(self, options):
        """Configurar el sitio de Django"""
        self.stdout.write('🌐 Configurando sitio...')
        
        site_domain = options['site_domain']
        site_name = options['site_name']
        
        try:
            site = Site.objects.get(pk=settings.SITE_ID)
            site.domain = site_domain
            site.name = site_name
            site.save()
            
            self.stdout.write(f'  ✅ Sitio actualizado: {site_name} ({site_domain})')
            
        except Site.DoesNotExist:
            site = Site.objects.create(
                pk=settings.SITE_ID,
                domain=site_domain,
                name=site_name
            )
            self.stdout.write(f'  ✅ Sitio creado: {site_name} ({site_domain})')
    
    def setup_google_oauth(self, options):
        """Configurar Google OAuth"""
        self.stdout.write('\n🔐 Configurando Google OAuth...')
        
        # Obtener credenciales de argumentos o variables de entorno
        client_id = (
            options.get('google_client_id') or 
            os.getenv('GOOGLE_CLIENT_ID')
        )
        client_secret = (
            options.get('google_client_secret') or 
            os.getenv('GOOGLE_CLIENT_SECRET')
        )
        
        if not client_id or not client_secret:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠️  Credenciales de Google no encontradas.\n'
                    '     Usa --google-client-id y --google-client-secret\n'
                    '     o configura GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en .env\n'
                    '     La configuración continuará pero OAuth no funcionará hasta que agregues las credenciales.'
                )
            )
            return
        
        # Verificar si ya existe configuración
        existing_app = SocialApp.objects.filter(provider='google').first()
        
        if existing_app and not options['force']:
            self.stdout.write(f'  ℹ️  Google OAuth ya está configurado (ID: {existing_app.client_id[:20]}...)')
            self.stdout.write('     Usa --force para recrear la configuración')
            return
        
        # Crear o actualizar SocialApp para Google
        social_app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google OAuth - VENDO_SRI',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        
        # Asignar al sitio actual
        site = Site.objects.get(pk=settings.SITE_ID)
        social_app.sites.clear()
        social_app.sites.add(site)
        
        if created or options['force']:
            self.stdout.write('  ✅ Google OAuth configurado')
        else:
            self.stdout.write('  ✅ Google OAuth actualizado')
            
        self.stdout.write(f'     Client ID: {client_id[:20]}...')
    
    def show_summary(self):
        """Mostrar resumen de la configuración"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE CONFIGURACIÓN OAUTH'))
        self.stdout.write('='*60)
        
        # Información del sitio
        site = Site.objects.get(pk=settings.SITE_ID)
        self.stdout.write(f'🌐 Sitio: {site.name} ({site.domain})')
        
        # Providers configurados
        social_apps = SocialApp.objects.all()
        self.stdout.write(f'🔐 Providers OAuth: {social_apps.count()}')
        
        for app in social_apps:
            self.stdout.write(f'   • {app.provider.upper()}: {app.name}')
            self.stdout.write(f'     Client ID: {app.client_id[:20]}...')
        
        # URLs disponibles
        self.stdout.write('\n📍 URLs de autenticación disponibles:')
        self.stdout.write(f'   • Login: http://{site.domain}/accounts/login/')
        self.stdout.write(f'   • Google OAuth: http://{site.domain}/accounts/google/login/')
        self.stdout.write(f'   • Dashboard: http://{site.domain}/dashboard/')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('🔧 CONFIGURACIÓN DE GOOGLE CLOUD CONSOLE:'))
        self.stdout.write('='*60)
        self.stdout.write('1. Ve a https://console.cloud.google.com/')
        self.stdout.write('2. Crea un proyecto o selecciona uno existente')
        self.stdout.write('3. Habilita la Google+ API o Google Identity Services')
        self.stdout.write('4. Ve a "APIs y servicios" > "Credenciales"')
        self.stdout.write('5. Crea credenciales OAuth 2.0')
        self.stdout.write('6. Agrega estas URLs de redirección autorizadas:')
        self.stdout.write(f'   • http://{site.domain}/accounts/google/login/callback/')
        
        if site.domain == 'localhost:8000':
            self.stdout.write('   • http://127.0.0.1:8000/accounts/google/login/callback/')
        
        # URLs para producción
        if 'localhost' not in site.domain:
            self.stdout.write(f'   • https://{site.domain}/accounts/google/login/callback/')
        
        self.stdout.write('7. Copia el Client ID y Client Secret generados')
        self.stdout.write('8. Configúralos en tu archivo .env:')
        self.stdout.write('   GOOGLE_CLIENT_ID=tu_client_id_aqui')
        self.stdout.write('   GOOGLE_CLIENT_SECRET=tu_client_secret_aqui')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('🚀 PRÓXIMOS PASOS:'))
        self.stdout.write('='*60)
        self.stdout.write('1. python manage.py migrate')
        self.stdout.write('2. python manage.py createsuperuser (si no existe)')
        self.stdout.write('3. python manage.py collectstatic')
        self.stdout.write('4. python manage.py runserver')
        self.stdout.write('5. Prueba el login en http://localhost:8000/accounts/login/')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎯 URLS DE PRUEBA:'))
        self.stdout.write('='*60)
        self.stdout.write(f'• Inicio: http://{site.domain}/')
        self.stdout.write(f'• Login: http://{site.domain}/accounts/login/')
        self.stdout.write(f'• Admin: http://{site.domain}/admin/')
        self.stdout.write(f'• Dashboard: http://{site.domain}/dashboard/')
        self.stdout.write(f'• Health Check: http://{site.domain}/health/')
        
        if social_apps.filter(provider='google').exists():
            self.stdout.write(f'• Google Login: http://{site.domain}/accounts/google/login/')
        
        self.stdout.write('='*60)
        
        # Información sobre usuarios pendientes
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            pending_users = User.objects.filter(approval_status='pending').count()
            total_users = User.objects.count()
            
            if total_users > 0:
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.WARNING('👥 INFORMACIÓN DE USUARIOS:'))
                self.stdout.write('='*60)
                self.stdout.write(f'• Total de usuarios: {total_users}')
                self.stdout.write(f'• Usuarios pendientes: {pending_users}')
                
                if pending_users > 0:
                    self.stdout.write(f'• Gestionar usuarios: http://{site.domain}/accounts/pending-approval/')
                
        except Exception as e:
            self.stdout.write(f'ℹ️  No se pudo obtener información de usuarios: {e}')
    
    def validate_configuration(self):
        """Validar que la configuración sea correcta"""
        errors = []
        
        # Verificar que SITE_ID esté configurado
        if not hasattr(settings, 'SITE_ID'):
            errors.append('SITE_ID no está configurado en settings.py')
        
        # Verificar que allauth esté en INSTALLED_APPS
        required_apps = [
            'allauth',
            'allauth.account',
            'allauth.socialaccount',
            'allauth.socialaccount.providers.google'
        ]
        
        for app in required_apps:
            if app not in settings.INSTALLED_APPS:
                errors.append(f'{app} no está en INSTALLED_APPS')
        
        # Verificar que AccountMiddleware esté configurado
        if 'allauth.account.middleware.AccountMiddleware' not in settings.MIDDLEWARE:
            errors.append('allauth.account.middleware.AccountMiddleware no está en MIDDLEWARE')
        
        if errors:
            self.stdout.write(self.style.ERROR('❌ Errores de configuración encontrados:'))
            for error in errors:
                self.stdout.write(f'   • {error}')
            return False
        
        return True