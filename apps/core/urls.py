# -*- coding: utf-8 -*-
"""
URLs del módulo Users para VENDO_SRI
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # ===================================
    # AUTENTICACIÓN BÁSICA
    # ===================================
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # ===================================
    # SALA DE ESPERA Y APROBACIONES
    # ===================================
    
    # Vista para usuarios pendientes de aprobación
    path('waiting-room/', views.WaitingRoomView.as_view(), name='waiting_room'),
    
    # Vista para usuarios rechazados
    path('account-rejected/', views.AccountRejectedView.as_view(), name='account_rejected'),
    
    # Vista para administradores - gestionar usuarios pendientes
    path('pending-approval/', views.PendingUsersView.as_view(), name='pending_users'),
    
    # APIs AJAX para aprobación/rechazo
    path('approve/<uuid:user_id>/', views.approve_user_ajax, name='approve_user'),
    path('reject/<uuid:user_id>/', views.reject_user_ajax, name='reject_user'),
    
    # API para obtener conteo de usuarios pendientes
    path('api/pending-count/', views.pending_users_count_ajax, name='pending_count'),
    
    # ===================================
    # PASSWORD RESET
    # ===================================
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/emails/password_reset.html',
             subject_template_name='users/emails/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url='/accounts/reset/done/'
         ), 
         name='password_reset_confirm'),
    
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]