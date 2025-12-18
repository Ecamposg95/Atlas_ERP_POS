/**
 * app/static/js/navbar.js
 * Componente Global de UI: Sidebar y Footer.
 * Actualizado para Atlas Technologies + FastAPI
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. RENDERIZADO DEL SIDEBAR ---
    const sidebarContainer = document.getElementById('global-sidebar');
    
    if (sidebarContainer) {
        // Recuperar sesión guardada
        const storedUser = sessionStorage.getItem('CURRENT_USER');
        
        if (storedUser) {
            const user = JSON.parse(storedUser);

            // Definición de Menú (Fusionado: Iconos de tu archivo + Rutas de FastAPI)
            const menuOptions = [
                {
                    label: 'Dashboard',
                    url: '#', // Pendiente de implementar
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>',
                    roles: ['ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Punto de Venta',
                    url: '/', // Ruta Raíz FastAPI
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
                    roles: ['CAJERO', 'GERENTE', 'ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Catálogo Productos',
                    url: '/products', // Ruta CRUD Productos FastAPI
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>',
                    roles: ['GERENTE', 'ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Corte de Caja',
                    url: '#', 
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>',
                    roles: ['CAJERO', 'GERENTE', 'ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Inventario',
                    url: '#',
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>',
                    roles: ['ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Historial Ventas',
                    url: '#',
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
                    roles: ['GERENTE', 'ADMINISTRADOR', 'DUEÑO']
                },
                {
                    label: 'Usuarios',
                    url: '#',
                    icon: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>',
                    roles: ['ADMINISTRADOR', 'DUEÑO']
                }
            ];

            // Filtrar opciones por rol del usuario
            const allowedOptions = menuOptions.filter(opt => opt.roles.includes(user.role));
            
            // Detectar ruta actual para resaltar activo
            const currentPath = window.location.pathname;

            const linksHTML = allowedOptions.map(opt => {
                // Lógica de activo: Coincidencia exacta o parcial si no es raíz
                const isActive = (opt.url === '/' && currentPath === '/') || 
                                 (opt.url !== '/' && opt.url !== '#' && currentPath.startsWith(opt.url));
                
                const activeClass = isActive 
                    ? 'bg-violet-600 text-white shadow-lg shadow-violet-900/20 border-r-4 border-violet-800' 
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800 border-r-4 border-transparent';
                
                return `
                    <a href="${opt.url}" class="${activeClass} flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group mb-1 mx-2">
                        <span class="${isActive ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'} transition-colors">
                            ${opt.icon}
                        </span>
                        <span class="font-medium text-sm tracking-wide">${opt.label}</span>
                    </a>
                `;
            }).join('');

            // Inyectar HTML del Sidebar
            sidebarContainer.innerHTML = `
                <aside class="flex flex-col w-64 h-full bg-slate-950 border-r border-slate-800 shrink-0 shadow-2xl relative z-50 transition-all duration-300">
                    <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950">
                        <div class="w-8 h-8 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-lg mr-3">AT</div>
                        <div>
                            <h1 class="font-bold text-slate-100 tracking-tight text-lg leading-none">Atlas ERP</h1>
                            <p class="text-[9px] text-slate-500 uppercase tracking-widest font-semibold mt-1">Technologies</p>
                        </div>
                    </div>
                    <nav class="flex-1 overflow-y-auto py-4 custom-scrollbar">
                        <p class="px-6 text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-3 mt-2">Menú Principal</p>
                        ${linksHTML}
                    </nav>
                    <div class="p-4 border-t border-slate-800 bg-slate-900/50">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 border border-slate-700 shrink-0">
                                <span class="font-bold text-xs">${user.sub.substring(0,2).toUpperCase()}</span>
                            </div>
                            <div class="flex-1 overflow-hidden">
                                <p class="text-sm font-bold text-slate-200 truncate" title="${user.sub}">${user.sub}</p>
                                <p class="text-[10px] text-slate-500 uppercase font-bold truncate">${user.role}</p>
                            </div>
                        </div>
                    </div>
                </aside>
            `;
        }
    }

    // --- 2. RENDERIZADO DEL FOOTER ---
    const footerContainer = document.getElementById('global-footer');
    
    if (footerContainer) {
        footerContainer.innerHTML = `
            <footer class="h-8 bg-slate-100 dark:bg-slate-950 border-t border-gray-200 dark:border-slate-800 flex justify-between items-center px-6 text-[10px] text-slate-500 shrink-0 select-none transition-colors duration-300">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-700 dark:text-slate-300">Powered by Atlas Technologies</span>
                    <span class="hidden sm:inline text-slate-300 dark:text-slate-700 mx-2">|</span>
                    <span class="hidden sm:inline">v2.1.0</span>
                </div>
                <div class="font-mono font-medium flex items-center gap-4">
                    <span id="global-clock-date" class="hidden sm:inline text-slate-400"></span>
                    <span id="global-clock-time" class="text-slate-800 dark:text-slate-200 font-bold bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded"></span>
                </div>
            </footer>
        `;

        function updateClock() {
            const now = new Date();
            const dateStr = now.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric', month: 'short' });
            const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            
            const dateEl = document.getElementById('global-clock-date');
            const timeEl = document.getElementById('global-clock-time');
            if(dateEl) dateEl.textContent = dateStr;
            if(timeEl) timeEl.textContent = timeStr;
        }
        setInterval(updateClock, 1000);
        updateClock(); 
    }
});