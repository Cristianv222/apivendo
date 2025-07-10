from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/', include('apps.api.urls')),  # Agregar cuando tengamos URLs
    # path('health/', include('apps.core.urls')),  # Para health check
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personalizar admin
admin.site.site_header = "Vendo SRI Administration"
admin.site.site_title = "Vendo SRI Admin"
admin.site.index_title = "Sistema de Facturación Electrónica"