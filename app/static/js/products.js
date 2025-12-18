/**
 * js/products.js
 * Gestión de Productos con KPIs, Vistas y CRUD.
 */

const API_URL = "http://127.0.0.1:8000/api";
const token = sessionStorage.getItem('token');

// Estado Global
let CURRENT_VIEW = 'table'; // 'table' | 'cards'
let ALL_PRODUCTS = [];

// --- INICIALIZACIÓN ---
document.addEventListener('DOMContentLoaded', () => {
    if(!token) window.location.href = '/';
    
    // 1. Cargar Usuario
    const userStr = sessionStorage.getItem('CURRENT_USER');
    if(userStr) {
        const u = JSON.parse(userStr);
        document.getElementById('user-name-display').textContent = u.sub;
        document.getElementById('user-role-display').textContent = u.role;
    }

    // 2. Tema
    initTheme();
    document.getElementById('theme-toggle').onclick = toggleTheme;

    // 3. Cargar Datos
    loadProducts();

    // 4. Event Listeners
    document.getElementById('search-input').addEventListener('input', (e) => {
        loadProducts(e.target.value);
    });
    
    document.getElementById('toggle-view-button').onclick = toggleView;
    document.getElementById('export-button').onclick = exportToCSV;
});

// --- TEMA (Dark/Light) ---
function initTheme() {
    // Revisar preferencia guardada o sistema
    if (localStorage.getItem('theme') === 'light') {
        document.documentElement.classList.remove('dark');
        document.getElementById('icon-sun').classList.remove('hidden');
        document.getElementById('icon-moon').classList.add('hidden');
    } else {
        document.documentElement.classList.add('dark');
        document.getElementById('icon-sun').classList.add('hidden');
        document.getElementById('icon-moon').classList.remove('hidden');
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
        document.getElementById('icon-sun').classList.remove('hidden');
        document.getElementById('icon-moon').classList.add('hidden');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
        document.getElementById('icon-sun').classList.add('hidden');
        document.getElementById('icon-moon').classList.remove('hidden');
    }
}

// --- CARGA DE DATOS ---
async function loadProducts(query = "") {
    try {
        const res = await fetch(`${API_URL}/products/?search=${query}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if(!res.ok) throw new Error("Error cargando productos");
        
        const products = await res.json();
        ALL_PRODUCTS = products;
        
        updateKPIs(products); // Actualizar los bloques de arriba
        render();             // Renderizar tabla o cards
    } catch (e) { console.error(e); }
}

// --- KPIs ---
function updateKPIs(products) {
    // 1. Total
    document.getElementById('stat-total').textContent = products.length;

    // 2. Sin Stock (qty <= 0)
    const noStock = products.filter(p => p.stock_total <= 0).length;
    document.getElementById('stat-no-stock').textContent = noStock;

    // 3. Valor Inventario (Costo * Stock)
    let totalValue = 0;
    products.forEach(p => {
        const v = p.variants[0] || {cost: 0};
        totalValue += (v.cost * p.stock_total);
    });
    document.getElementById('stat-value').textContent = `$${totalValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    // 4. Recientes (últimos 7 días - simulado si no hay fecha, o basado en ID alto)
    // Asumiremos que IDs altos son recientes por ahora
    // En un sistema real usaríamos p.created_at
    const recent = products.length > 5 ? 5 : products.length; // Placeholder
    document.getElementById('stat-new').textContent = recent; 
}

// --- RENDERIZADO ---
function render() {
    if (CURRENT_VIEW === 'table') {
        renderTable(ALL_PRODUCTS);
        document.getElementById('table-view').classList.remove('hidden');
        document.getElementById('cards-view').classList.add('hidden');
        
        document.getElementById('view-icon').textContent = '🗂️';
        document.getElementById('view-label').textContent = 'Vista Cards';
    } else {
        renderCards(ALL_PRODUCTS);
        document.getElementById('table-view').classList.add('hidden');
        document.getElementById('cards-view').classList.remove('hidden');
        
        document.getElementById('view-icon').textContent = '📋';
        document.getElementById('view-label').textContent = 'Vista Tabla';
    }
}

function renderTable(products) {
    const tbody = document.getElementById('products-table-body');
    if(products.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-10 text-gray-500 italic">No se encontraron productos</td></tr>`;
        return;
    }

    tbody.innerHTML = products.map(p => {
        const v = p.variants[0] || {};
        const stockClass = (p.stock_total > 0) 
            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400' 
            : 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';

        return `
        <tr class="hover:bg-gray-50 dark:hover:bg-slate-800/50 transition border-b border-gray-100 dark:border-slate-800 last:border-0">
            <td class="px-6 py-4">
                <div class="font-mono text-xs font-bold text-slate-500 dark:text-slate-400">${v.sku || '-'}</div>
                <div class="text-[10px] text-slate-400">${v.barcode || ''}</div>
            </td>
            <td class="px-6 py-4">
                <div class="font-bold text-gray-800 dark:text-gray-200 text-sm">${p.name}</div>
            </td>
            <td class="px-6 py-4 text-right font-bold text-emerald-600 dark:text-emerald-400 text-sm">$${v.price}</td>
            <td class="px-6 py-4 text-right text-gray-500 text-sm">$${v.cost}</td>
            <td class="px-6 py-4 text-center">
                <span class="px-2 py-1 rounded text-[10px] font-bold ${stockClass}">${p.stock_total || 0}</span>
            </td>
            <td class="px-6 py-4 text-center">
                <div class="flex items-center justify-center gap-2">
                    <button onclick="editProduct(${p.id})" class="text-violet-500 hover:text-violet-400 font-bold text-xs">EDITAR</button>
                    <button onclick="deleteProduct(${p.id})" class="text-rose-500 hover:text-rose-400 font-bold text-xs">✕</button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function renderCards(products) {
    const container = document.getElementById('cards-view');
    if(products.length === 0) {
        container.innerHTML = `<div class="col-span-full text-center py-10 text-gray-500 italic">No se encontraron productos</div>`;
        return;
    }

    container.innerHTML = products.map(p => {
        const v = p.variants[0] || {};
        return `
        <div class="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm hover:shadow-md transition group relative overflow-hidden flex flex-col justify-between h-48">
            <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-violet-500/10 to-fuchsia-500/10 rounded-bl-full -mr-4 -mt-4 transition group-hover:scale-110"></div>
            
            <div>
                <div class="flex justify-between items-start mb-2">
                    <span class="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-500 px-2 py-0.5 rounded">${v.sku || 'N/A'}</span>
                    <div class="flex gap-1 relative z-10">
                        <button onclick="editProduct(${p.id})" class="p-1 text-slate-400 hover:text-violet-500 transition"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>
                        <button onclick="deleteProduct(${p.id})" class="p-1 text-slate-400 hover:text-rose-500 transition"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
                    </div>
                </div>
                <h3 class="font-bold text-gray-800 dark:text-white text-sm mb-1 line-clamp-2 leading-snug" title="${p.name}">${p.name}</h3>
            </div>
            
            <div class="flex items-end justify-between border-t border-dashed border-gray-100 dark:border-slate-800 pt-3 mt-2">
                <div>
                    <span class="block text-[10px] text-slate-400 uppercase font-bold">Precio</span>
                    <span class="text-lg font-black text-emerald-600 dark:text-emerald-400">$${v.price}</span>
                </div>
                <div class="text-right">
                    <span class="block text-[10px] text-slate-400 uppercase font-bold">Stock</span>
                    <span class="text-sm font-bold ${p.stock_total > 0 ? 'text-slate-700 dark:text-slate-300' : 'text-red-500'}">${p.stock_total || 0}</span>
                </div>
            </div>
        </div>`;
    }).join('');
}

function toggleView() {
    CURRENT_VIEW = (CURRENT_VIEW === 'table') ? 'cards' : 'table';
    render();
}

function exportToCSV() {
    if(!ALL_PRODUCTS.length) return alert('Nada que exportar');
    
    // Encabezados
    let csv = 'ID,SKU,Nombre,Precio,Costo,Stock\n';
    
    // Filas
    ALL_PRODUCTS.forEach(p => {
        const v = p.variants[0] || {};
        csv += `${p.id},"${v.sku}","${p.name}",${v.price},${v.cost},${p.stock_total}\n`;
    });

    const blob = new Blob([csv], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); 
    a.href = url; 
    a.download = `productos_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
}

// --- CRUD MODAL ---
const modal = document.getElementById('product-modal');
const form = document.getElementById('product-form');

window.openModal = () => {
    form.reset();
    document.getElementById('prod-id').value = '';
    document.getElementById('modal-title').innerText = "Nuevo Producto";
    document.getElementById('stock-field-container').classList.remove('hidden');
    modal.classList.add('active');
};

window.closeModal = () => modal.classList.remove('active');

window.editProduct = (id) => {
    const p = ALL_PRODUCTS.find(x => x.id === id);
    if(!p) return;
    const v = p.variants[0] || {};

    document.getElementById('prod-id').value = p.id;
    document.getElementById('prod-name').value = p.name;
    document.getElementById('prod-sku').value = v.sku;
    document.getElementById('prod-barcode').value = v.barcode || '';
    document.getElementById('prod-price').value = v.price;
    document.getElementById('prod-cost').value = v.cost;
    
    document.getElementById('modal-title').innerText = "Editar Producto";
    document.getElementById('stock-field-container').classList.add('hidden');
    modal.classList.add('active');
};

window.generateSKU = () => {
    document.getElementById('prod-sku').value = 'GEN-' + Math.floor(Math.random()*1000000);
}

// Guardar
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('prod-id').value;
    const isEdit = !!id;
    
    const payload = {
        name: document.getElementById('prod-name').value,
        sku: document.getElementById('prod-sku').value,
        barcode: document.getElementById('prod-barcode').value,
        price: parseFloat(document.getElementById('prod-price').value),
        cost: parseFloat(document.getElementById('prod-cost').value),
    };

    if (!isEdit) {
        payload.initial_stock = parseFloat(document.getElementById('prod-stock').value) || 0;
    }

    const url = isEdit ? `${API_URL}/products/${id}` : `${API_URL}/products/`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeModal();
            loadProducts();
        } else {
            const err = await res.json();
            alert("Error: " + (err.detail || "Error desconocido"));
        }
    } catch(e) { alert("Error de conexión"); }
});

// Borrar
window.deleteProduct = async (id) => {
    if(!confirm("¿Seguro que quieres borrar este producto?")) return;
    try {
        const res = await fetch(`${API_URL}/products/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if(res.ok) loadProducts();
        else alert("No se pudo borrar");
    } catch(e) { alert("Error al borrar"); }
};