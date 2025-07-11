# -*- coding: utf-8 -*-
"""
URL configuration for users app
URLs para la gestión de usuarios en VENDO_SRI
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard-class/', views.DashboardView.as_view(), name='dashboard_class'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    
    # Auth (opcional, django-allauth maneja la mayoría)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/user-info/', views.user_info_api, name='user_info_api'),
    
    # Home redirect
    path('', views.home_view, name='home'),
]