# -*- coding: utf-8 -*-
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Ruta para el monitoreo de colas SRI en tiempo real
    # Ejemplo: ws/queue/1/
    re_path(r'ws/queue/(?P<company_id>\d+)/$', consumers.QueueConsumer.as_asgi()),
]
