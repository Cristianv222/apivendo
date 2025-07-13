# -*- coding: utf-8 -*-
from django.urls import path
from django.http import JsonResponse

def api_status(request):
    return JsonResponse({'status': 'OK', 'message': 'API básica funcionando'})

app_name = 'api'
urlpatterns = [
    path('v1/status/', api_status, name='status'),
]
