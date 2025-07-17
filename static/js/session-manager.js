/**
 * Session Manager para VENDO_SRI
 * Gestiona el timeout de sesión y muestra advertencias
 */

class SessionManager {
    constructor(options = {}) {
        // Configuración
        this.options = {
            checkInterval: 60000,        // Verificar cada 60 segundos
            heartbeatInterval: 300000,   // Heartbeat cada 5 minutos
            warningTime: 300,            // Advertir 5 minutos antes
            enableHeartbeat: true,       // Habilitar heartbeat automático
            enableWarnings: true,        // Mostrar advertencias
            logoutUrl: '/accounts/logout/',
            loginUrl: '/accounts/login/',
            ...options
        };
        
        // Estado
        this.timeRemaining = null;
        this.warningShown = false;
        this.checkTimer = null;
        this.heartbeatTimer = null;
        this.countdownTimer = null;
        this.lastActivity = Date.now();
        
        // Elementos del DOM
        this.warningModal = null;
        this.countdownElement = null;
        
        // Inicializar
        this.init();
    }
    
    init() {
        // Crear modal de advertencia
        this.createWarningModal();
        
        // Detectar actividad del usuario
        this.setupActivityDetection();
        
        // Iniciar verificación de sesión
        this.startSessionCheck();
        
        // Iniciar heartbeat si está habilitado
        if (this.options.enableHeartbeat) {
            this.startHeartbeat();
        }
        
        // Interceptar respuestas AJAX para detectar sesión expirada
        this.setupAjaxInterceptor();
        
        console.log('SessionManager iniciado');
    }
    
    createWarningModal() {
        // Crear el HTML del modal
        const modalHtml = `
            <div class="modal fade" id="sessionWarningModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="fas fa-clock me-2"></i>
                                Tu sesión está por expirar
                            </h5>
                        </div>
                        <div class="modal-body text-center">
                            <div class="mb-3">
                                <i class="fas fa-hourglass-half fa-3x text-warning"></i>
                            </div>
                            <p class="lead">Tu sesión expirará en:</p>
                            <h2 class="text-danger" id="sessionCountdown">5:00</h2>
                            <p class="text-muted">
                                ¿Deseas continuar trabajando?
                            </p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="sessionManager.logout()">
                                <i class="fas fa-sign-out-alt me-2"></i>
                                Cerrar Sesión
                            </button>
                            <button type="button" class="btn btn-primary" onclick="sessionManager.extendSession()">
                                <i class="fas fa-sync me-2"></i>
                                Continuar Trabajando
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Agregar al body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Guardar referencias
        this.warningModal = new bootstrap.Modal(document.getElementById('sessionWarningModal'));
        this.countdownElement = document.getElementById('sessionCountdown');
    }
    
    setupActivityDetection() {
        // Eventos que cuentan como actividad
        const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart'];
        
        activityEvents.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
            }, { passive: true });
        });
    }
    
    setupAjaxInterceptor() {
        // Interceptar respuestas jQuery AJAX
        if (window.jQuery) {
            $(document).ajaxComplete((event, xhr, settings) => {
                if (xhr.status === 401 && xhr.responseJSON?.session_expired) {
                    this.handleSessionExpired();
                }
            });
        }
        
        // Interceptar fetch nativo
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const response = await originalFetch(...args);
            
            if (response.status === 401) {
                const data = await response.clone().json().catch(() => null);
                if (data?.session_expired) {
                    this.handleSessionExpired();
                }
            }
            
            return response;
        };
    }
    
    async checkSessionStatus() {
        try {
            const response = await fetch('/core/api/session/check/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.handleSessionExpired();
                }
                return;
            }
            
            const data = await response.json();
            this.timeRemaining = data.time_remaining;
            
            // Actualizar UI si existe un indicador
            this.updateSessionIndicator(data);
            
            // Mostrar advertencia si es necesario
            if (data.show_warning && !this.warningShown && this.options.enableWarnings) {
                this.showWarning();
            } else if (!data.show_warning && this.warningShown) {
                this.hideWarning();
            }
            
            // Si la sesión expiró
            if (data.status === 'expired') {
                this.handleSessionExpired();
            }
            
        } catch (error) {
            console.error('Error verificando sesión:', error);
        }
    }
    
    updateSessionIndicator(data) {
        // Actualizar indicador en la navbar si existe
        const indicator = document.getElementById('sessionTimeIndicator');
        if (indicator) {
            const minutes = Math.floor(data.time_remaining / 60);
            const seconds = data.time_remaining % 60;
            
            if (data.time_remaining <= this.options.warningTime) {
                indicator.classList.add('text-warning');
                indicator.innerHTML = `<i class="fas fa-clock"></i> ${minutes}:${seconds.toString().padStart(2, '0')}`;
            } else {
                indicator.classList.remove('text-warning');
                indicator.innerHTML = `<i class="fas fa-clock"></i> Sesión activa`;
            }
        }
    }
    
    showWarning() {
        this.warningShown = true;
        this.warningModal.show();
        this.startCountdown();
        
        // Reproducir sonido de notificación si está disponible
        this.playNotificationSound();
    }
    
    hideWarning() {
        this.warningShown = false;
        this.warningModal.hide();
        this.stopCountdown();
    }
    
    startCountdown() {
        this.stopCountdown();
        
        this.countdownTimer = setInterval(() => {
            if (this.timeRemaining <= 0) {
                this.handleSessionExpired();
                return;
            }
            
            const minutes = Math.floor(this.timeRemaining / 60);
            const seconds = this.timeRemaining % 60;
            this.countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            this.timeRemaining--;
        }, 1000);
    }
    
    stopCountdown() {
        if (this.countdownTimer) {
            clearInterval(this.countdownTimer);
            this.countdownTimer = null;
        }
    }
    
    async extendSession() {
        try {
            const response = await fetch('/core/api/session/extend/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Sesión extendida:', data);
                
                // Ocultar advertencia
                this.hideWarning();
                
                // Mostrar notificación de éxito
                this.showNotification('Sesión extendida exitosamente', 'success');
                
                // Reiniciar verificación
                this.checkSessionStatus();
            }
        } catch (error) {
            console.error('Error extendiendo sesión:', error);
            this.showNotification('Error al extender la sesión', 'error');
        }
    }
    
    async sendHeartbeat() {
        // Solo enviar heartbeat si ha habido actividad reciente
        const inactiveTime = Date.now() - this.lastActivity;
        if (inactiveTime > this.options.heartbeatInterval * 2) {
            return; // No enviar heartbeat si no hay actividad
        }
        
        try {
            const response = await fetch('/core/api/session/heartbeat/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok && response.status === 401) {
                this.handleSessionExpired();
            }
        } catch (error) {
            console.error('Error en heartbeat:', error);
        }
    }
    
    handleSessionExpired() {
        console.log('Sesión expirada');
        
        // Detener todos los timers
        this.stopAllTimers();
        
        // Mostrar mensaje
        this.showNotification('Tu sesión ha expirado. Redirigiendo al login...', 'warning');
        
        // Redirigir al login después de 2 segundos
        setTimeout(() => {
            window.location.href = this.options.loginUrl;
        }, 2000);
    }
    
    logout() {
        this.stopAllTimers();
        window.location.href = this.options.logoutUrl;
    }
    
    startSessionCheck() {
        // Verificar inmediatamente
        this.checkSessionStatus();
        
        // Luego verificar periódicamente
        this.checkTimer = setInterval(() => {
            this.checkSessionStatus();
        }, this.options.checkInterval);
    }
    
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            this.sendHeartbeat();
        }, this.options.heartbeatInterval);
    }
    
    stopAllTimers() {
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
            this.checkTimer = null;
        }
        
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
        
        this.stopCountdown();
    }
    
    getCsrfToken() {
        // Obtener CSRF token de Django
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        
        return cookie ? cookie.split('=')[1] : '';
    }
    
    showNotification(message, type = 'info') {
        // Crear notificación toast
        const toastHtml = `
            <div class="toast position-fixed top-0 end-0 m-3" role="alert" style="z-index: 9999;">
                <div class="toast-header bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} text-white">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                    <strong class="me-auto">Sistema</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.querySelector('.toast:last-child');
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remover después de ocultarse
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
    
    playNotificationSound() {
        // Reproducir sonido si el navegador lo permite
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBi2Gy/DWhDYgGGS27OmqWRkKSafh8cJvHAUzjdXxzHwwBCl+zPLaizsIGGS57OurWxUITKrh8cNwGgU2jdny1IgrARBpt+3qrGAVCEuq4/HEbxwFNI3Z8tSGLAEPaLvt6axiFQxGn+Hkv3keCy+JzO/BeiEG');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Ignorar si no se puede reproducir
            });
        } catch (e) {
            // Ignorar errores de audio
        }
    }
    
    destroy() {
        // Limpiar todos los timers y event listeners
        this.stopAllTimers();
        
        // Remover modal si existe
        const modal = document.getElementById('sessionWarningModal');
        if (modal) {
            modal.remove();
        }
        
        console.log('SessionManager destruido');
    }
}

// Inicializar automáticamente cuando el DOM esté listo
let sessionManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Solo inicializar si el usuario está autenticado
    if (document.body.dataset.authenticated === 'true') {
        sessionManager = new SessionManager({
            checkInterval: 60000,      // Verificar cada minuto
            heartbeatInterval: 300000, // Heartbeat cada 5 minutos
            warningTime: 300,          // Advertir 5 minutos antes
            enableHeartbeat: true,
            enableWarnings: true
        });
    }
});