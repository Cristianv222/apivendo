    /**
 * Auto Logout - Cierre automático de sesión
 * Recarga la página automáticamente cuando la sesión expire
 */

(function() {
    // Solo ejecutar si el usuario está autenticado
    if (!document.body.dataset.authenticated) {
        return;
    }

    // Configuración
    const SESSION_TIMEOUT = 3600; // 1 hora en segundos
    const CHECK_INTERVAL = 60000; // Verificar cada 60 segundos
    const WARNING_TIME = 300; // Advertir 5 minutos antes (opcional)
    
    let lastActivity = Date.now();
    let warningShown = false;

    // Detectar actividad del usuario
    const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    
    function updateActivity() {
        lastActivity = Date.now();
        warningShown = false; // Reset warning cuando hay actividad
    }

    // Registrar eventos de actividad
    activityEvents.forEach(event => {
        document.addEventListener(event, updateActivity, { passive: true });
    });

    // Función para verificar el tiempo de inactividad
    function checkInactivity() {
        const now = Date.now();
        const inactiveTime = (now - lastActivity) / 1000; // Convertir a segundos
        const timeRemaining = SESSION_TIMEOUT - inactiveTime;

        console.log(`[Auto-Logout] Inactivo por: ${Math.floor(inactiveTime)} segundos, Restante: ${Math.floor(timeRemaining)} segundos`);

        // Si el tiempo se agotó, recargar la página
        if (timeRemaining <= 0) {
            console.log('[Auto-Logout] Sesión expirada. Recargando página...');
            
            // Mostrar mensaje antes de recargar (opcional)
            const message = document.createElement('div');
            message.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #dc3545;
                color: white;
                padding: 20px 40px;
                border-radius: 8px;
                font-size: 18px;
                z-index: 9999;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            `;
            message.textContent = 'Tu sesión ha expirado. Redirigiendo...';
            document.body.appendChild(message);

            // Recargar después de 2 segundos
            setTimeout(() => {
                window.location.reload();
            }, 2000);
            
            // Detener el interval
            clearInterval(checkTimer);
        }
        // Advertencia opcional 5 minutos antes
        else if (timeRemaining <= WARNING_TIME && !warningShown) {
            warningShown = true;
            const minutes = Math.floor(timeRemaining / 60);
            
            // Crear notificación de advertencia
            const warning = document.createElement('div');
            warning.id = 'session-warning';
            warning.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ffc107;
                color: #000;
                padding: 15px 20px;
                border-radius: 8px;
                font-size: 16px;
                z-index: 9999;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                max-width: 350px;
            `;
            warning.innerHTML = `
                <strong>⚠️ Advertencia de sesión</strong><br>
                Tu sesión expirará en ${minutes} minutos por inactividad.<br>
                <small>Mueve el mouse o presiona una tecla para continuar.</small>
            `;
            document.body.appendChild(warning);

            // Remover advertencia después de 10 segundos
            setTimeout(() => {
                const warn = document.getElementById('session-warning');
                if (warn) warn.remove();
            }, 10000);
        }
    }

    // Verificar inmediatamente
    checkInactivity();

    // Luego verificar periódicamente
    const checkTimer = setInterval(checkInactivity, CHECK_INTERVAL);

    // También verificar con peticiones AJAX periódicas (opcional pero más preciso)
    function checkSessionStatus() {
        fetch(window.location.href, {
            method: 'HEAD',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(response => {
            if (response.status === 401 || response.redirected) {
                console.log('[Auto-Logout] Servidor confirmó sesión expirada');
                window.location.reload();
            }
        }).catch(error => {
            console.error('[Auto-Logout] Error verificando sesión:', error);
        });
    }

    // Verificar con el servidor cada 5 minutos
    setInterval(checkSessionStatus, 300000);

    console.log('[Auto-Logout] Sistema de cierre automático activado');
    console.log(`[Auto-Logout] Timeout configurado: ${SESSION_TIMEOUT} segundos (${SESSION_TIMEOUT/60} minutos)`);
})();