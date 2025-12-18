/**
 * js/products.js
 * Lógica completa para Gestión de Productos:
 * - CRUD (Crear, Leer, Actualizar, Borrar)
 * - Vistas (Tabla vs Cards)
 * - Filtros y Buscador
 * - KPIs (Estadísticas)
 * - Importación Masiva (Excel) y Exportación CSV
 */

const API_URL = "http://127.0.0.1:8000/api";
// Intentamos recuperar el token con ambos nombres posibles por compatibilidad
const token = sessionStorage.getItem('token') || sessionStorage.getItem('ACCESS_TOKEN');

// Estado Global
let ALL_PRODUCTS = [];
let FILTERED_PRODUCTS = [];
let CURRENT_VIEW = 'cards'; // 'table' | 'cards'
let CURRENT_PAGE = 1;
const PAGE_SIZE = 24;
let DELETING_PRODUCT_ID = null;

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    // 1. Verificar Sesión
    if (!token) {
        window.location.href = '/';
        return;
    }

    // 2. Cargar Info Usuario
    const userStr = sessionStorage.getItem('CURRENT_USER');
    if (userStr) {
        const u = JSON.parse(userStr);
        const nameEl = document.getElementById('user-name-display');
        const roleEl = document.getElementById('user-role-display');
        if (nameEl) nameEl.textContent = u.sub || u.username;
        if (roleEl) roleEl.textContent = u.role;
    }

    // 3. Inicializar Tema
    initTheme();
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    // 4. Cargar Datos Iniciales
    loadDepartments();
    loadProducts();

    // 5. Configurar Listeners Globales
    setupEventListeners();
});

function setupEventListeners() {
    // Buscador y Filtros
    document.getElementById('search-input').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('department-filter').addEventListener('change', applyFilters);

    // Botones de Acción
    document.getElementById('toggle-view-button').addEventListener('click', toggleView);
    document.getElementById('export-button').addEventListener('click', exportToCSV);

    // Paginación
    document.getElementById('prev-page-btn').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page-btn').addEventListener('click', () => changePage(1));
    document.getElementById('prev-page-btn-cards').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page-btn-cards').addEventListener('click', () => changePage(1));

    // Modales (Abrir)
    document.getElementById('import-excel-button').addEventListener('click', openUploadModal);
    // Nota: El botón "Nuevo" puede tener ID 'new-product-button' o llamar a openModal() directamente en HTML
    const newBtn = document.getElementById('new-product-button');
    if (newBtn) newBtn.addEventListener('click', openCreateModal);

    // Formularios
    document.getElementById('product-form').addEventListener('submit', handleSaveProduct);
    document.getElementById('upload-form').addEventListener('submit', handleUpload);

    // Cerrar Modales
    document.querySelectorAll('.modal .close-modal-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Buscamos el modal padre más cercano
            const modal = e.target.closest('.modal');
            hideModal(modal);
        });
    });

    // Confirmar Eliminación
    document.getElementById('confirm-delete-button').addEventListener('click', handleDeleteConfirm);

    // Helpers Formulario Producto
    document.getElementById('add-price-tier-button').addEventListener('click', () => addPriceRow());
}

// --- TEMA (OSCURO/CLARO) ---
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const iconSun = document.getElementById('icon-sun');
    const iconMoon = document.getElementById('icon-moon');

    if (savedTheme === 'light') {
        document.documentElement.classList.remove('dark');
        iconSun.classList.remove('hidden');
        iconMoon.classList.add('hidden');
    } else {
        document.documentElement.classList.add('dark');
        iconSun.classList.add('hidden');
        iconMoon.classList.remove('hidden');
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    }
    initTheme();
}

// --- API FETCH HELPER ---
async function apiFetch(endpoint, options = {}) {
    const headers = { 'Authorization': `Bearer ${token}`, ...options.headers };

    // Si es FormData no ponemos Content-Type (el navegador lo pone)
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API_URL}${endpoint}`, { ...options, headers });

    if (res.status === 401) {
        alert("Sesión expirada");
        sessionStorage.clear();
        window.location.href = '/';
        return;
    }

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
        throw new Error(data.detail || "Error en el servidor");
    }
    return data;
}

// --- CARGA DE DATOS ---
async function loadProducts() {
    try {
        // Pedimos un límite alto para tener todo en memoria y filtrar rápido en cliente
        const data = await apiFetch('/products/?limit=2000');
        ALL_PRODUCTS = data;
        applyFilters(); // Esto llama a render() y updateStats()
    } catch (e) {
        console.error("Error cargando productos:", e);
    }
}

async function loadDepartments() {
    try {
        const depts = await apiFetch('/products/departments');
        const selForm = document.getElementById('product-department'); // Select del Modal
        const selFilter = document.getElementById('department-filter'); // Select del Filtro

        // Limpiar
        if (selForm) selForm.innerHTML = '<option value="">(Ninguno)</option>';
        if (selFilter) selFilter.innerHTML = '<option value="ALL">Todos los Deptos</option>';

        depts.forEach(d => {
            if (selForm) selForm.insertAdjacentHTML('beforeend', `<option value="${d.id}">${d.name}</option>`);
            if (selFilter) selFilter.insertAdjacentHTML('beforeend', `<option value="${d.name}">${d.name}</option>`); // Filtramos por nombre en el front
        });
    } catch (e) {
        console.error("Error cargando departamentos:", e);
    }
}

// --- FILTROS Y ESTADÍSTICAS ---
function applyFilters() {
    const q = document.getElementById('search-input').value.toLowerCase();
    const deptVal = document.getElementById('department-filter').value;

    FILTERED_PRODUCTS = ALL_PRODUCTS.filter(p => {
        // Filtro Texto (Nombre, SKU, Barras)
        const v = p.variants && p.variants[0] ? p.variants[0] : {};
        const textMatch = p.name.toLowerCase().includes(q) ||
            (v.sku && v.sku.toLowerCase().includes(q)) ||
            (v.barcode && v.barcode.includes(q));

        // Filtro Depto
        const deptMatch = deptVal === 'ALL' || (p.department && p.department.name === deptVal);

        return textMatch && deptMatch;
    });

    CURRENT_PAGE = 1;
    updateStats();
    renderView();
}

function updateStats() {
    // Total
    document.getElementById('stat-total-products').textContent = ALL_PRODUCTS.length;

    // Sin Stock
    const noStock = ALL_PRODUCTS.filter(p => p.stock_total <= 0).length;
    document.getElementById('stat-no-price').textContent = noStock; // Usando el espacio de "Sin Precio" para "Sin Stock" o ajustar HTML

    // Valor Inventario (Costo * Stock)
    let totalVal = 0;
    ALL_PRODUCTS.forEach(p => {
        const v = p.variants[0] || { cost: 0 };
        totalVal += (v.cost * p.stock_total);
    });
    // Ajuste si tienes un elemento para valor, si no usamos otro stat
    const statValEl = document.getElementById('stat-value');
    if (statValEl) statValEl.textContent = `$${totalVal.toLocaleString('en-US')}`;

    // Recientes (Dummy: últimos 5 agregados al final del array)
    // O filtrar por ID si es autoincremental
    document.getElementById('stat-new-products').textContent = ALL_PRODUCTS.length > 5 ? 5 : ALL_PRODUCTS.length;
}

// --- RENDERIZADO (VISTAS) ---
function renderView() {
    const start = (CURRENT_PAGE - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const pageData = FILTERED_PRODUCTS.slice(start, end);
    const totalPages = Math.ceil(FILTERED_PRODUCTS.length / PAGE_SIZE) || 1;

    // Actualizar Textos Paginación
    const infoText = `Mostrando ${Math.min(start + 1, FILTERED_PRODUCTS.length)}-${Math.min(end, FILTERED_PRODUCTS.length)} de ${FILTERED_PRODUCTS.length}`;
    const pageText = `${CURRENT_PAGE} / ${totalPages}`;

    document.getElementById('pagination-info').textContent = infoText;
    document.getElementById('current-page-label').textContent = pageText;

    const infoCards = document.getElementById('pagination-info-cards');
    const labelCards = document.getElementById('current-page-label-cards');
    if (infoCards) infoCards.textContent = infoText;
    if (labelCards) labelCards.textContent = pageText;

    if (CURRENT_VIEW === 'table') {
        renderTable(pageData);
        document.getElementById('table-view').classList.remove('hidden');
        document.getElementById('cards-view').classList.add('hidden');

        document.getElementById('view-icon').textContent = '🗂️';
        document.getElementById('view-label').textContent = 'Cards';
    } else {
        renderCards(pageData);
        document.getElementById('table-view').classList.add('hidden');
        document.getElementById('cards-view').classList.remove('hidden');

        document.getElementById('view-icon').textContent = '📋';
        document.getElementById('view-label').textContent = 'Tabla';
    }
}

function renderTable(products) {
    const tbody = document.getElementById('products-table-body');
    if (!products.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-10 text-gray-500 italic">No se encontraron productos</td></tr>`;
        return;
    }

    tbody.innerHTML = products.map(p => {
        const v = p.variants[0] || {};
        const pricesHtml = (p.prices || []).map(pr =>
            `<div class="text-[10px] whitespace-nowrap"><span class="text-slate-400">${pr.min_quantity}+:</span> <span class="font-bold text-emerald-500">$${pr.unit_price}</span></div>`
        ).join('');

        const stockClass = p.stock_total > 0
            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
            : 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';

        return `
        <tr class="hover:bg-gray-50 dark:hover:bg-slate-800/50 transition border-b border-gray-100 dark:border-slate-800">
            <td class="px-6 py-4">
                <div class="font-mono text-xs font-bold text-slate-500 dark:text-slate-400">${v.sku || '-'}</div>
                <div class="text-[10px] text-slate-400">${v.barcode || ''}</div>
            </td>
            <td class="px-6 py-4">
                <div class="font-bold text-gray-800 dark:text-white text-sm">${p.name}</div>
            </td>
            <td class="px-6 py-4 text-xs text-slate-500">${p.department ? p.department.name : '-'}</td>
            <td class="px-6 py-4 text-xs">${pricesHtml || `<span class="font-bold text-emerald-600">$${v.price}</span>`}</td>
            <td class="px-6 py-4 text-center">
                <span class="px-2 py-1 rounded text-[10px] font-bold ${stockClass}">${p.stock_total}</span>
            </td>
            <td class="px-6 py-4 text-center space-x-2">
                <button onclick="openEditModal(${p.id})" class="text-violet-500 hover:text-violet-400 font-bold text-xs">EDITAR</button>
                <button onclick="openDeleteModal(${p.id}, '${p.name}')" class="text-rose-500 hover:text-rose-400 font-bold text-xs">✕</button>
            </td>
        </tr>`;
    }).join('');
}

function renderCards(products) {
    const container = document.getElementById('products-cards-container'); // Ojo al ID
    if (!products.length) {
        container.innerHTML = `<div class="col-span-full text-center py-10 text-gray-500 italic">No se encontraron productos</div>`;
        return;
    }

    container.innerHTML = products.map(p => {
        const v = p.variants[0] || {};
        const stockColor = p.stock_total > 0 ? 'text-slate-700 dark:text-slate-300' : 'text-rose-500';

        return `
        <div class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm hover:shadow-md transition group relative overflow-hidden flex flex-col justify-between h-48">
            <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 rounded-bl-full -mr-4 -mt-4 transition group-hover:scale-110"></div>
            
            <div>
                <div class="flex justify-between items-start mb-2">
                    <span class="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 px-2 py-0.5 rounded">${v.sku || 'N/A'}</span>
                    <div class="flex gap-1 relative z-10">
                        <button onclick="openEditModal(${p.id})" class="p-1 text-slate-400 hover:text-violet-500 transition"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>
                        <button onclick="openDeleteModal(${p.id}, '${p.name}')" class="p-1 text-slate-400 hover:text-rose-500 transition"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
                    </div>
                </div>
                <h3 class="font-bold text-gray-800 dark:text-white text-sm mb-1 line-clamp-2 leading-snug" title="${p.name}">${p.name}</h3>
                <p class="text-xs text-slate-500">${p.department ? p.department.name : 'General'}</p>
            </div>
            
            <div class="flex items-end justify-between border-t border-dashed border-gray-100 dark:border-slate-800 pt-3 mt-2">
                <div>
                    <span class="block text-[10px] text-slate-400 uppercase font-bold">Precio</span>
                    <span class="text-lg font-black text-emerald-600 dark:text-emerald-400">$${v.price}</span>
                </div>
                <div class="text-right">
                    <span class="block text-[10px] text-slate-400 uppercase font-bold">Stock</span>
                    <span class="text-sm font-bold ${stockColor}">${p.stock_total}</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

function toggleView() {
    CURRENT_VIEW = (CURRENT_VIEW === 'table') ? 'cards' : 'table';
    renderView();
}

function changePage(delta) {
    const totalPages = Math.ceil(FILTERED_PRODUCTS.length / PAGE_SIZE) || 1;
    const newPage = CURRENT_PAGE + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        CURRENT_PAGE = newPage;
        renderView();
    }
}

// --- CRUD: CREAR / EDITAR ---
const prodModal = document.getElementById('product-modal');
const priceContainer = document.getElementById('price-tiers-container');

// Necesario exponer globalmente para onclick en HTML generado dinámicamente
window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.openDeleteModal = openDeleteModal;
// Generador SKU global
window.generateSKU = () => {
    document.getElementById('product-sku').value = 'GEN-' + Math.floor(Math.random() * 1000000);
};

function openCreateModal() {
    document.getElementById('product-form').reset();
    document.getElementById('product-id').value = '';
    document.getElementById('product-modal-title').textContent = "Nuevo Producto";
    document.getElementById('stock-field-container').classList.remove('hidden');
    priceContainer.innerHTML = '';
    addPriceRow(); // Agrega una fila vacía por defecto
    showModal(prodModal);
}

function openEditModal(id) {
    const p = ALL_PRODUCTS.find(x => x.id === id);
    if (!p) return;
    const v = p.variants[0] || {};

    document.getElementById('product-id').value = p.id;
    document.getElementById('product-name').value = p.name;
    document.getElementById('product-sku').value = v.sku;
    document.getElementById('product-barcode').value = v.barcode || '';
    document.getElementById('product-unit').value = p.unit || '';
    document.getElementById('product-department').value = p.department ? p.department.id : '';
    document.getElementById('product-base-price').value = v.price;
    document.getElementById('product-cost').value = v.cost;
    document.getElementById('product-description').value = p.description || '';
    document.getElementById('product-active').checked = p.is_active;

    // Stock no editable directamente en update, ocultar
    document.getElementById('stock-field-container').classList.add('hidden');

    // Precios Escalonados
    priceContainer.innerHTML = '';
    if (p.prices && p.prices.length) {
        p.prices.forEach(pr => addPriceRow(pr.price_name, pr.min_quantity, pr.unit_price));
    } else {
        addPriceRow();
    }

    document.getElementById('product-modal-title').textContent = "Editar Producto";
    showModal(prodModal);
}

function addPriceRow(name = '', qty = 1, val = '') {
    const div = document.createElement('div');
    div.className = 'grid grid-cols-3 gap-2 price-row mb-2';
    div.innerHTML = `
        <input type="text" value="${name}" class="p-name px-3 py-2 bg-gray-50 dark:bg-slate-950 border border-gray-300 dark:border-slate-700 rounded-lg text-xs outline-none" placeholder="Nombre (ej. Mayoreo)">
        <input type="number" value="${qty}" class="p-qty px-3 py-2 bg-gray-50 dark:bg-slate-950 border border-gray-300 dark:border-slate-700 rounded-lg text-xs outline-none" placeholder="Mínimo">
        <input type="number" value="${val}" class="p-val px-3 py-2 bg-gray-50 dark:bg-slate-950 border border-gray-300 dark:border-slate-700 rounded-lg text-xs font-bold text-emerald-500 outline-none" placeholder="Precio">
    `;
    priceContainer.appendChild(div);
}

async function handleSaveProduct(e) {
    e.preventDefault();
    const id = document.getElementById('product-id').value;
    const isEdit = !!id;

    // Recolectar precios extra
    const rows = document.querySelectorAll('.price-row');
    const pricesList = Array.from(rows).map(r => ({
        price_name: r.querySelector('.p-name').value,
        min_quantity: parseFloat(r.querySelector('.p-qty').value) || 1,
        unit_price: parseFloat(r.querySelector('.p-val').value) || 0
    })).filter(x => x.unit_price > 0);

    const payload = {
        name: document.getElementById('product-name').value,
        sku: document.getElementById('product-sku').value,
        barcode: document.getElementById('product-barcode').value,
        department_id: document.getElementById('product-department').value || null,
        unit: document.getElementById('product-unit').value,
        price: parseFloat(document.getElementById('product-base-price').value) || 0,
        cost: parseFloat(document.getElementById('product-cost').value) || 0,
        description: document.getElementById('product-description').value,
        prices: pricesList
    };

    if (!isEdit) {
        payload.initial_stock = parseFloat(document.getElementById('prod-stock').value) || 0;
    }

    try {
        const url = isEdit ? `/products/${id}` : `/products/`;
        const method = isEdit ? 'PUT' : 'POST';

        await apiFetch(url, {
            method: method,
            body: JSON.stringify(payload)
        });

        hideModal(prodModal);
        loadProducts(); // Recargar tabla
    } catch (e) {
        alert("Error al guardar: " + e.message);
    }
}

// --- CRUD: BORRAR ---
const deleteModal = document.getElementById('delete-modal');

function openDeleteModal(id, name) {
    DELETING_PRODUCT_ID = id;
    document.getElementById('delete-product-name').textContent = name;
    showModal(deleteModal);
}

async function handleDeleteConfirm() {
    if (!DELETING_PRODUCT_ID) return;
    try {
        await apiFetch(`/products/${DELETING_PRODUCT_ID}`, { method: 'DELETE' });
        hideModal(deleteModal);
        loadProducts();
    } catch (e) {
        alert("Error al borrar: " + e.message);
    }
}

// --- IMPORTAR EXCEL ---
const uploadModal = document.getElementById('upload-modal');

function openUploadModal() {
    document.getElementById('upload-step-1').classList.remove('hidden');
    document.getElementById('upload-step-2').classList.add('hidden');
    document.getElementById('upload-step-3').classList.add('hidden');
    document.getElementById('upload-modal-error').textContent = '';
    document.getElementById('upload-modal-error').classList.add('hidden');
    document.getElementById('excel-file-input').value = '';
    showModal(uploadModal);
}

// Botones cancelar y cerrar del modal upload
document.getElementById('cancel-upload-button').addEventListener('click', () => hideModal(uploadModal));
document.getElementById('close-results-button').addEventListener('click', () => hideModal(uploadModal));

async function handleUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('excel-file-input');
    const file = fileInput.files[0];
    const errorEl = document.getElementById('upload-modal-error');

    if (!file) {
        errorEl.textContent = "Selecciona un archivo primero.";
        errorEl.classList.remove('hidden');
        return;
    }

    // Paso 1 -> Paso 2 (Spinner)
    document.getElementById('upload-step-1').classList.add('hidden');
    document.getElementById('upload-step-2').classList.remove('hidden');
    errorEl.classList.add('hidden');

    const fd = new FormData();
    fd.append('file', file);

    try {
        const data = await apiFetch('/products/upload', {
            method: 'POST',
            body: fd // apiFetch detectará FormData y no pondrá JSON header
        });

        // Paso 2 -> Paso 3 (Resultados)
        document.getElementById('upload-step-2').classList.add('hidden');
        document.getElementById('upload-step-3').classList.remove('hidden');

        document.getElementById('upload-results-summary').textContent =
            `Procesados: ${data.created_count}, Fallidos: ${data.failed_count}`;

        loadProducts(); // Recargar datos de fondo

    } catch (err) {
        // Error -> Regresar a Paso 1
        console.error(err);
        document.getElementById('upload-step-2').classList.add('hidden');
        document.getElementById('upload-step-1').classList.remove('hidden');
        errorEl.textContent = err.message;
        errorEl.classList.remove('hidden');
    }
}

// --- EXPORTAR CSV ---
function exportToCSV() {
    if (!FILTERED_PRODUCTS.length) {
        alert("No hay productos para exportar");
        return;
    }

    let csv = 'ID,SKU,Nombre,Departamento,Precio,Costo,Stock\n';

    FILTERED_PRODUCTS.forEach(p => {
        const v = p.variants[0] || {};
        const dept = p.department ? p.department.name : 'General';
        // Escapar comillas para CSV
        const safeName = p.name.replace(/"/g, '""');

        csv += `${p.id},"${v.sku}","${safeName}","${dept}",${v.price},${v.cost},${p.stock_total}\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `productos_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
}

// --- UTILS ---
function showModal(el) {
    el.classList.remove('hidden');
    el.classList.add('flex'); // Centrado flex
    // Pequeño delay para la transición de opacidad
    setTimeout(() => el.classList.add('active'), 10);
}

function hideModal(el) {
    if (!el) return;
    el.classList.remove('active');
    setTimeout(() => {
        el.classList.add('hidden');
        el.classList.remove('flex');
    }, 200); // Coincide con CSS transition
}

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}