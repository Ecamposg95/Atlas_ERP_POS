/**
 * js/pos.js - Versión Final (Corrección SKU + Respuesta Backend)
 */
const API_URL = "/api";
let token = sessionStorage.getItem('token');
let allProducts = [];
let cart = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!token) return; // Navbar maneja redirect

    loadProducts();

    const searchInput = document.getElementById('pos-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => filterProducts(e.target.value));
        searchInput.focus();
    }

    // Reloj simple
    setInterval(() => {
        const el = document.getElementById('clock-display');
        if (el) el.textContent = new Date().toLocaleTimeString();
    }, 1000);
});

async function loadProducts() {
    try {
        const res = await fetch(`${API_URL}/products/?limit=1000`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Error API");

        allProducts = await res.json();
        renderProducts(allProducts);
    } catch (e) {
        console.error(e);
        const grid = document.getElementById('products-grid');
        if (grid) grid.innerHTML = '<p class="text-red-500 p-4">Error cargando productos.</p>';
    }
}

function renderProducts(products) {
    const grid = document.getElementById('products-grid');
    if (!grid) return;

    if (products.length === 0) {
        grid.innerHTML = '<p class="col-span-full text-center text-gray-500">No hay productos.</p>';
        return;
    }

    grid.innerHTML = products.map(p => {
        // SEGURIDAD: Validar existencia de variante
        const v = (p.variants && p.variants.length > 0) ? p.variants[0] : null;
        if (!v) return ''; // Saltar productos rotos

        const price = parseFloat(v.price || 0);
        const stock = p.stock_total || 0;

        return `
        <div onclick="addToCart(${p.id})" class="bg-white p-3 rounded shadow cursor-pointer hover:bg-blue-50 border border-gray-200 h-28 flex flex-col justify-between select-none transition-transform active:scale-95">
            <div>
                <div class="flex justify-between text-xs text-gray-500 mb-1">
                    <span>${v.sku || 'N/A'}</span>
                    <span class="${stock > 0 ? 'text-green-600' : 'text-red-600'} font-bold">${stock}</span>
                </div>
                <h3 class="font-bold text-sm leading-tight line-clamp-2">${p.name}</h3>
            </div>
            <div class="text-right font-black text-lg">$${price.toFixed(2)}</div>
        </div>`;
    }).join('');
}

function filterProducts(q) {
    const term = q.toLowerCase();
    const filtered = allProducts.filter(p => {
        const v = p.variants[0] || {};
        // Búsqueda por Nombre o SKU
        return p.name.toLowerCase().includes(term) || (v.sku && v.sku.toLowerCase().includes(term));
    });

    // Auto-add si es código exacto (Enter o escaneo rápido)
    const exact = filtered.find(p => p.variants[0]?.sku.toLowerCase() === term || p.variants[0]?.barcode === term);
    if (exact && filtered.length === 1) {
        addToCart(exact.id);
        document.getElementById('pos-search').value = '';
        renderProducts(allProducts);
    } else {
        renderProducts(filtered);
    }
}

// --- CARRITO ---
window.addToCart = (id) => {
    const prod = allProducts.find(p => p.id === id);
    const v = prod.variants[0];

    const existing = cart.find(i => i.id === v.id);
    if (existing) {
        existing.qty++;
    } else {
        cart.push({
            id: v.id,
            name: prod.name,
            price: parseFloat(v.price),
            qty: 1,
            sku: v.sku // Guardamos el SKU aquí para usarlo al enviar
        });
    }
    renderCart();
};

function renderCart() {
    const list = document.getElementById('cart-list');
    list.innerHTML = '';

    let total = 0;

    cart.forEach((item, idx) => {
        const subtotal = item.price * item.qty;
        total += subtotal;

        list.innerHTML += `
        <li class="p-3 flex justify-between items-center hover:bg-gray-50 border-b">
            <div class="flex-1">
                <div class="font-bold text-sm">${item.name}</div>
                <div class="text-xs text-gray-500 font-mono">${item.sku} | $${item.price.toFixed(2)} x ${item.qty}</div>
            </div>
            <div class="text-right">
                <div class="font-bold">$${subtotal.toFixed(2)}</div>
                <div class="text-xs mt-1">
                    <button onclick="updateQty(${idx}, -1)" class="px-2 bg-gray-200 rounded hover:bg-red-200 font-bold">-</button>
                    <button onclick="updateQty(${idx}, 1)" class="px-2 bg-gray-200 rounded hover:bg-green-200 font-bold">+</button>
                </div>
            </div>
        </li>`;
    });

    document.getElementById('cart-total').textContent = `$${total.toFixed(2)}`;
    window.currentTotal = total;
}

window.updateQty = (idx, delta) => {
    cart[idx].qty += delta;
    if (cart[idx].qty <= 0) cart.splice(idx, 1);
    renderCart();
};

// --- PAGOS Y PROCESAMIENTO ---
window.handleDirectPayment = async (method) => {
    if (cart.length === 0) {
        mostrarError("El ticket está vacío");
        return;
    }

    const input = document.getElementById('payment-input');
    let val = parseFloat(input.value);

    // Si no ingresó monto, asumimos pago exacto
    if (!val || val <= 0) val = window.currentTotal;

    // Validación básica de monto en Frontend
    if (val < window.currentTotal && method === 'CASH') {
        mostrarError(`Monto insuficiente. Faltan $${(window.currentTotal - val).toFixed(2)}`);
        return;
    }

    const payments = [{ method: method, amount: val }];

    // NOTA: El cambio real lo calcula el backend, pero lo estimamos aquí para payload si fuera necesario
    const estimatedChange = val - window.currentTotal;

    const saleData = {
        items: cart.map(i => ({
            variant_id: i.id,
            sku: i.sku,          // Corregido: Enviamos el SKU
            quantity: i.qty,
            unit_price: i.price,
            subtotal: i.qty * i.price
        })),
        payments: payments,
        total_amount: window.currentTotal,
        change_given: Math.max(0, estimatedChange), // Informativo
        customer_id: null // Aquí iría lógica de cliente si existiera
    };

    try {
        const res = await fetch(`${API_URL}/sales/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(saleData)
        });

        const data = await res.json();

        if (res.ok && data.status === 'success') {
            // --- AQUÍ ESTÁ LA CORRECCIÓN CLAVE ---
            // Usamos los datos reales retornados por Python
            const ticketId = data.sale_id;
            const cambioReal = parseFloat(data.change);

            // Mostrar Éxito (SweetAlert o Alert normal)
            mostrarExito(ticketId, cambioReal);

            // Resetear UI
            cart = [];
            input.value = '';
            renderCart();
            loadProducts(); // Recargar stock visualmente
        } else {
            // Manejar error del backend
            console.error(data);
            mostrarError(data.detail || "Error al procesar la venta");
        }
    } catch (e) {
        console.error(e);
        mostrarError("Error de conexión con el servidor");
    }
};

// Helpers para alertas (Detecta si existe SweetAlert o usa nativo)
function mostrarExito(ticketId, cambio) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: `Venta Exitosa #${ticketId}`,
            html: `
                <div style="font-size: 1.2em;">
                    Pago registrado.<br>
                    <b>Cambio: $${cambio.toFixed(2)}</b>
                </div>
            `,
            icon: 'success',
            timer: 3000,
            showConfirmButton: false
        });
    } else {
        alert(`✅ Venta Exitosa #${ticketId}\nCambio: $${cambio.toFixed(2)}`);
    }
}

function mostrarError(mensaje) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Atención',
            text: mensaje,
            icon: 'warning'
        });
    } else {
        alert("⚠️ " + mensaje);
    }
}