/**
 * app/static/js/auth.js
 * Gestiona la sesión, protección de rutas y decodificación de usuario.
 */

// Configuración Global
const AUTH_REDIRECT = "/login";
const PUBLIC_ROUTES = ["/login", "/register"]; // Rutas que no requieren token

// 1. Ejecución Inmediata (Autoprotección)
(function protectRoute() {
    const token = sessionStorage.getItem('token');
    const path = window.location.pathname;

    // Si estamos en una ruta pública, no hacemos nada
    if (PUBLIC_ROUTES.includes(path)) return;

    // Si no hay token, fuera
    if (!token) {
        console.warn("Acceso denegado: No token found");
        window.location.href = AUTH_REDIRECT;
    }
})();

// 2. Funciones Públicas (Globales)
window.auth = {
    // Cerrar sesión
    logout: () => {
        sessionStorage.clear();
        window.location.href = AUTH_REDIRECT;
    },

    // Obtener header de autorización
    getHeader: () => {
        const token = sessionStorage.getItem('token');
        return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
    },

    // Obtener datos del usuario (Decodificando el Payload del JWT sin librería externa)
    getUser: () => {
        const token = sessionStorage.getItem('token');
        if (!token) return null;
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error("Error parsing token", e);
            return null;
        }
    }
};