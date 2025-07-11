from django.shortcuts import render
from django.http import JsonResponse

def home(request):
    """Vista para la página de inicio"""
    return JsonResponse({
        'mensaje': '¡Bienvenido a Vendo SRI!',
        'status': 'success',
        'version': '1.0.0'
    })

def health_check(request):
    """Vista para verificar que el servicio está funcionando"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'vendo_sri'
    })