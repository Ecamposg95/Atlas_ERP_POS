/**
 * js/navbar.js - Versión Simplificada y Funcional
 */
document.addEventListener('DOMContentLoaded', () => {
    const token = sessionStorage.getItem('token');
    const path = window.location.pathname;

    // Protección básica de rutas
    if (!token && path !== '/login') {
        window.location.href = '/login';
        return;
    }

    if (path === '/login') return; // No renderizar navbar en login

    const container = document.getElementById('global-sidebar');
    if (container) {
        const username = sessionStorage.getItem('username') || 'Admin';

        container.innerHTML = `
        <aside class="w-64 bg-slate-900 text-white h-screen flex flex-col shrink-0">
            <div class="h-16 flex items-center px-6 font-bold text-xl border-b border-slate-700">
                Atlas ERP
            </div>
            <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
                <a href="/" class="block px-4 py-3 rounded hover:bg-slate-700">📊 Dashboard</a>
                <a href="/pos" class="block px-4 py-3 rounded hover:bg-slate-700 bg-blue-900">🛒 Punto de Venta</a>
                <a href="/products" class="block px-4 py-3 rounded hover:bg-slate-700">📦 Catálogo</a>
                <a href="/inventory" class="block px-4 py-3 rounded hover:bg-slate-700">📋 Inventario</a>
                <a href="/cash" class="block px-4 py-3 rounded hover:bg-slate-700">💵 Caja</a>
            </nav>
            <div class="p-4 border-t border-slate-700">
                <p class="text-sm text-gray-400">Usuario: ${username}</p>
                <button onclick="sessionStorage.clear(); window.location.href='/login'" class="text-red-400 text-sm hover:underline mt-1">Cerrar Sesión</button>
            </div>
        </aside>`;
    }
});