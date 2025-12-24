// app/static/js/pos.js
// ES Module (cargado con <script type="module">)

const API_BASE = "/api";

const els = {
    cashStatus: document.getElementById("cashStatus"),
    sessionPill: document.getElementById("sessionPill"),
    btnLogout: document.getElementById("btnLogout"),

    btnOpenCash: document.getElementById("btnOpenCash"),
    btnCloseCash: document.getElementById("btnCloseCash"),

    searchInput: document.getElementById("searchInput"),
    btnClearSearch: document.getElementById("btnClearSearch"),
    suggestions: document.getElementById("suggestions"),
    posMsg: document.getElementById("posMsg"),

    cartMeta: document.getElementById("cartMeta"),
    cartTbody: document.getElementById("cartTbody"),
    subtotal: document.getElementById("subtotal"),
    total: document.getElementById("total"),

    paymentMethod: document.getElementById("paymentMethod"),
    cashReceived: document.getElementById("cashReceived"),
    changeDue: document.getElementById("changeDue"),
    cashWarn: document.getElementById("cashWarn"),

    btnPay: document.getElementById("btnPay"),
    btnVoid: document.getElementById("btnVoid"),
};

let cashSession = null;

// Carrito: trabajamos por VARIANT (tu precio y sku viven en ProductVariant)
let cart = []; // items: { product_id, variant_id, name, sku, unit_price, quantity }

let debounceTimer = null;

// ------------------------------
// Utilidades
// ------------------------------
function token() {
    return localStorage.getItem("access_token");
}

function authHeaders(extra = {}) {
    return {
        Authorization: `Bearer ${token()}`,
        ...extra,
    };
}

async function apiFetch(path, { method = "GET", headers = {}, body } = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        method,
        headers: {
            Accept: "application/json",
            ...authHeaders(headers),
        },
        body,
    });

    // Manejo de sesión expirada / no autorizado
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
        return;
    }

    let data = null;
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        data = await res.json();
    } else {
        data = await res.text();
    }

    if (!res.ok) {
        const err = new Error(`HTTP ${res.status}`);
        err.status = res.status;
        err.data = data;
        throw err;
    }

    return data;
}

function money(n) {
    const num = Number(n || 0);
    return `$${num.toFixed(2)}`;
}

function num(n) {
    const x = Number(n);
    return Number.isFinite(x) ? x : 0;
}

function setMsg(text, isError = false) {
    els.posMsg.textContent = text || "";
    els.posMsg.className = isError ? "danger" : "muted";
}

function showSuggestions(show) {
    els.suggestions.style.display = show ? "block" : "none";
    if (!show) els.suggestions.innerHTML = "";
}

// ------------------------------
// Caja
// ------------------------------
async function loadCashStatus() {
    try {
        cashSession = await apiFetch("/cash/status");
        renderCashStatus();
    } catch (e) {
        cashSession = null;
        renderCashStatus();
        setMsg("No se pudo validar caja (revisa auth o backend).", true);
        console.error("cash/status error:", e);
    }
}

function renderCashStatus() {
    const open = !!cashSession && cashSession.status === "OPEN";
    els.cashStatus.textContent = open ? "Caja: ABIERTA" : "Caja: CERRADA (requiere apertura)";
    els.sessionPill.textContent = "Sesión activa";

    // Botones caja
    els.btnOpenCash.disabled = open;
    els.btnCloseCash.disabled = !open;

    els.btnOpenCash.style.opacity = open ? 0.5 : 1;
    els.btnCloseCash.style.opacity = !open ? 0.5 : 1;
}

async function openCash() {
    const opening = prompt("Monto de apertura (ej: 100.00):", "0");
    if (opening === null) return;

    const opening_balance = num(opening);

    try {
        cashSession = await apiFetch("/cash/open", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ opening_balance }),
        });
        renderCashStatus();
        setMsg("Caja abierta correctamente.");
    } catch (e) {
        console.error("cash/open error:", e);
        setMsg(e?.data?.detail || "Error al abrir caja.", true);
    }
}

async function closeCash() {
    const closing = prompt("Monto de cierre (ej: 250.00):", "0");
    if (closing === null) return;

    const notes = prompt("Notas de cierre (opcional):", "") ?? "";
    const closing_balance = num(closing);

    try {
        cashSession = await apiFetch("/cash/close", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ closing_balance, notes }),
        });
        renderCashStatus();
        setMsg("Caja cerrada correctamente.");
    } catch (e) {
        console.error("cash/close error:", e);
        setMsg(e?.data?.detail || "Error al cerrar caja.", true);
    }
}

// ------------------------------
// Productos - búsqueda
// ------------------------------
async function searchProducts(q) {
    const query = (q || "").trim();
    if (query.length < 2) {
        showSuggestions(false);
        return;
    }

    try {
        const list = await apiFetch(`/products/search?q=${encodeURIComponent(query)}`);

        if (!Array.isArray(list) || list.length === 0) {
            els.suggestions.innerHTML = `<div style="padding:12px;" class="muted">Sin resultados</div>`;
            showSuggestions(true);
            return;
        }

        els.suggestions.innerHTML = "";
        list.forEach((p) => {
            // Tu API ya devuelve variants[0].sku y variants[0].price
            const v = p?.variants?.[0];

            // Fallbacks defensivos
            const sku = v?.sku || `ID-${p.id}`;
            const price = num(v?.price);
            const name = p?.name || "(Sin nombre)";

            const btn = document.createElement("button");
            btn.type = "button";
            btn.innerHTML = `<strong>${name}</strong> · ${money(price)} <span class="muted">(${sku})</span>`;
            btn.addEventListener("click", () => {
                addToCartFromApiProduct(p);
                els.searchInput.value = "";
                showSuggestions(false);
            });
            els.suggestions.appendChild(btn);
        });

        showSuggestions(true);
    } catch (e) {
        console.error("products/search error:", e);
        setMsg("Error al buscar productos.", true);
        showSuggestions(false);
    }
}

function addToCartFromApiProduct(p) {
    const v = p?.variants?.[0];
    if (!v?.id) {
        // Esto ya no debería pasar con tu endpoint corregido
        setMsg("Producto sin variante principal. Revisa catálogo (variants).", true);
        return;
    }

    const item = {
        product_id: p.id,
        variant_id: v.id,
        name: p.name,
        sku: v.sku,
        unit_price: num(v.price),
        quantity: 1,
    };

    const found = cart.find((x) => x.variant_id === item.variant_id);
    if (found) {
        found.quantity += 1;
    } else {
        cart.push(item);
    }

    renderCart();
    setMsg("");
}

// ------------------------------
// Carrito - render, totales
// ------------------------------
function cartCount() {
    return cart.reduce((acc, it) => acc + num(it.quantity), 0);
}

function cartSubtotal() {
    return cart.reduce((acc, it) => acc + num(it.unit_price) * num(it.quantity), 0);
}

function renderCart() {
    els.cartTbody.innerHTML = "";

    cart.forEach((it) => {
        const tr = document.createElement("tr");

        const tdProd = document.createElement("td");
        tdProd.innerHTML = `
      <div style="font-weight:800;">${it.name}</div>
      <div class="muted">SKU: ${it.sku || "-"}</div>
    `;

        const tdQty = document.createElement("td");
        tdQty.className = "right";

        const qtyInput = document.createElement("input");
        qtyInput.type = "number";
        qtyInput.min = "1";
        qtyInput.step = "1";
        qtyInput.value = String(it.quantity);
        qtyInput.style.width = "80px";
        qtyInput.addEventListener("change", () => {
            const q = Math.max(1, Math.floor(num(qtyInput.value)));
            it.quantity = q;
            renderCart();
        });

        tdQty.appendChild(qtyInput);

        const tdPrice = document.createElement("td");
        tdPrice.className = "right";
        tdPrice.textContent = money(num(it.unit_price) * num(it.quantity));

        const tdX = document.createElement("td");
        tdX.className = "right";

        const btnX = document.createElement("button");
        btnX.className = "btn-muted";
        btnX.textContent = "X";
        btnX.style.padding = "8px 10px";
        btnX.addEventListener("click", () => {
            cart = cart.filter((x) => x.variant_id !== it.variant_id);
            renderCart();
        });

        tdX.appendChild(btnX);

        tr.appendChild(tdProd);
        tr.appendChild(tdQty);
        tr.appendChild(tdPrice);
        tr.appendChild(tdX);

        els.cartTbody.appendChild(tr);
    });

    const items = cartCount();
    els.cartMeta.textContent = `${items} ítems`;

    const sub = cartSubtotal();
    els.subtotal.textContent = money(sub);
    els.total.textContent = money(sub);

    updateChange();
}

function clearCart() {
    cart = [];
    renderCart();
    setMsg("");
}

// ------------------------------
// Pago / Cambio
// ------------------------------
function updateChange() {
    const total = cartSubtotal();
    const method = els.paymentMethod.value;

    // Solo efectivo calcula cambio; otros métodos fuerzan recibido == total
    if (method !== "CASH") {
        els.cashReceived.value = total ? String(total.toFixed(2)) : "";
        els.changeDue.textContent = money(0);
        els.cashWarn.textContent = "";
        return;
    }

    const received = num(els.cashReceived.value);
    const change = received - total;

    els.changeDue.textContent = money(Math.max(0, change));

    if (total === 0) {
        els.cashWarn.textContent = "";
        return;
    }

    if (received < total) {
        els.cashWarn.textContent = "Recibido insuficiente.";
        els.cashWarn.className = "danger";
    } else {
        els.cashWarn.textContent = "";
        els.cashWarn.className = "muted";
    }
}

// ------------------------------
// Cobro (POST /api/sales)
// IMPORTANTE: aquí hay 2 posibles contratos.
// Sin ver tu sales.py, dejo 2 payloads; usaremos el #1 por default.
// Si te vuelve a dar 422, pegas el error y ajusto el payload exacto.
// ------------------------------
async function submitSale() {
    if (!cashSession || cashSession.status !== "OPEN") {
        setMsg("Caja cerrada. Abre caja antes de cobrar.", true);
        return;
    }

    if (cart.length === 0) {
        setMsg("Carrito vacío.", true);
        return;
    }

    const total = cartSubtotal();
    const method = els.paymentMethod.value;

    let received = num(els.cashReceived.value);
    if (method !== "CASH") received = total;

    if (method === "CASH" && received < total) {
        setMsg("Recibido insuficiente para cobrar.", true);
        return;
    }

    // Payload #1 (probable, por tu error previo: items[*].sku requerido + payments requerido)
    const payload = {
        items: cart.map((it) => ({
            product_id: it.product_id,
            variant_id: it.variant_id,
            sku: it.sku,
            quantity: it.quantity,
            unit_price: it.unit_price,
        })),
        payments: [
            {
                method: method,
                amount: total,
                cash_received: method === "CASH" ? received : undefined,
            },
        ],
    };

    // Limpia undefined para no romper validaciones estrictas
    payload.payments = payload.payments.map((p) => {
        const clean = {};
        Object.keys(p).forEach((k) => {
            if (p[k] !== undefined) clean[k] = p[k];
        });
        return clean;
    });

    try {
        const sale = await apiFetch("/sales/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        console.log("SALE OK:", sale);
        setMsg("Venta realizada correctamente.");
        clearCart();
        els.cashReceived.value = "";
        updateChange();
    } catch (e) {
        console.error("SALE ERROR:", e?.data || e);
        // Mostrar detalle útil
        const detail = e?.data?.detail ? JSON.stringify(e.data.detail) : (e?.data?.message || "");
        setMsg(`Error al cobrar. ${detail}`.trim(), true);
    }
}

// ------------------------------
// Eventos UI
// ------------------------------
function bindEvents() {
    els.btnLogout.addEventListener("click", () => {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
    });

    els.btnOpenCash.addEventListener("click", openCash);
    els.btnCloseCash.addEventListener("click", closeCash);

    els.btnClearSearch.addEventListener("click", () => {
        els.searchInput.value = "";
        showSuggestions(false);
        setMsg("");
        els.searchInput.focus();
    });

    els.searchInput.addEventListener("input", () => {
        const q = els.searchInput.value;
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => searchProducts(q), 160);
    });

    els.searchInput.addEventListener("keydown", (ev) => {
        // Escape cierra sugerencias
        if (ev.key === "Escape") {
            showSuggestions(false);
            return;
        }
    });

    document.addEventListener("click", (ev) => {
        // Cerrar sugerencias si das click fuera del input/sugerencias
        const t = ev.target;
        if (!els.suggestions.contains(t) && t !== els.searchInput) {
            showSuggestions(false);
        }
    });

    els.paymentMethod.addEventListener("change", updateChange);
    els.cashReceived.addEventListener("input", updateChange);

    els.btnVoid.addEventListener("click", clearCart);
    els.btnPay.addEventListener("click", submitSale);
}

// ------------------------------
// Init
// ------------------------------
async function init() {
    bindEvents();
    await loadCashStatus();
    renderCart();
    els.searchInput.focus();
}

init();
