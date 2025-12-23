// app/static/js/pos.js
import { apiFetch } from "./api.js";

const els = {
    cashStatus: document.getElementById("cashStatus"),
    sessionPill: document.getElementById("sessionPill"),
    btnLogout: document.getElementById("btnLogout"),

    btnOpenCash: document.getElementById("btnOpenCash"),
    btnCloseCash: document.getElementById("btnCloseCash"),

    searchInput: document.getElementById("searchInput"),
    btnClearSearch: document.getElementById("btnClearSearch"),
    suggestions: document.getElementById("suggestions"),

    cartTbody: document.getElementById("cartTbody"),
    cartMeta: document.getElementById("cartMeta"),
    subtotal: document.getElementById("subtotal"),
    total: document.getElementById("total"),

    paymentMethod: document.getElementById("paymentMethod"),
    cashReceived: document.getElementById("cashReceived"),
    changeDue: document.getElementById("changeDue"),
    cashWarn: document.getElementById("cashWarn"),

    btnPay: document.getElementById("btnPay"),
    btnVoid: document.getElementById("btnVoid"),

    msg: document.getElementById("posMsg"),
};

let cashSession = null; // /api/cash/status -> objeto o null
let cart = [];          // { product, qty, unit_price, sku }

function money(n) {
    const x = Number(n || 0);
    return x.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function setMsg(t) { els.msg.textContent = t || ""; }

function isCashOpen(session) {
    if (!session) return false;
    const st = String(session.status || "").toUpperCase();
    return st === "OPEN" && (session.closed_at === null || session.closed_at === undefined);
}

function getBestPrice(product) {
    if (product?.price != null) return Number(product.price);
    if (product?.sale_price != null) return Number(product.sale_price);
    if (product?.base_price != null) return Number(product.base_price);
    if (product?.unit_price != null) return Number(product.unit_price);

    const prices = product?.prices;
    if (Array.isArray(prices) && prices.length) {
        const p0 = prices[0];
        const v = p0?.price ?? p0?.amount ?? p0?.sale_price ?? p0?.unit_price ?? p0?.value ?? 0;
        return Number(v || 0);
    }

    const variants = product?.variants;
    if (Array.isArray(variants) && variants.length) {
        const v0 = variants[0];
        if (v0?.price != null) return Number(v0.price);
        if (v0?.sale_price != null) return Number(v0.sale_price);
    }

    return 0;
}

function getTotal() {
    return cart.reduce((a, x) => a + Number(x.unit_price || 0) * Number(x.qty || 0), 0);
}

function updateChangeAndWarnings() {
    const method = els.paymentMethod.value;
    const total = getTotal();
    const received = Number(els.cashReceived.value || 0);

    if (method === "CASH") {
        const change = received - total;
        els.changeDue.textContent = money(Math.max(0, change));

        if (received > 0 && received < total) {
            els.cashWarn.textContent = "Efectivo insuficiente.";
            els.cashWarn.className = "muted danger";
        } else {
            els.cashWarn.textContent = "";
            els.cashWarn.className = "muted";
        }
    } else {
        els.changeDue.textContent = money(0);
        els.cashWarn.textContent = "";
        els.cashWarn.className = "muted";
    }
}

async function refreshCashStatus() {
    cashSession = await apiFetch("/api/cash/status");
    const open = isCashOpen(cashSession);

    els.cashStatus.textContent = open ? "Caja: ABIERTA" : "Caja: CERRADA (requiere apertura)";
    els.btnOpenCash.disabled = open;
    els.btnCloseCash.disabled = !open;
    els.btnPay.disabled = !open;
}

async function openCash() {
    const opening = prompt("Saldo inicial (apertura):", "0");
    if (opening === null) return;

    const opening_balance = Number(opening);

    try {
        await apiFetch("/api/cash/open", {
            method: "POST",
            body: JSON.stringify({ opening_balance }),
        });

        setMsg("Caja abierta.");
        await refreshCashStatus();
    } catch (e) {
        setMsg(`No se pudo abrir caja: ${String(e.message || e)}`);
        console.error("OPEN CASH ERROR:", e);
    }
}

async function closeCash() {
    const closing = prompt("Saldo final (cierre):", "0");
    if (closing === null) return;

    const closing_balance = Number(closing);
    const notes = prompt("Notas (opcional):", "") ?? "";

    try {
        await apiFetch("/api/cash/close", {
            method: "POST",
            body: JSON.stringify({ closing_balance, notes }),
        });

        setMsg("Caja cerrada.");
        await refreshCashStatus();
    } catch (e) {
        setMsg(`No se pudo cerrar caja: ${String(e.message || e)}`);
        console.error("CLOSE CASH ERROR:", e);
    }
}

function computeTotals() {
    const total = getTotal();
    els.subtotal.textContent = money(total);
    els.total.textContent = money(total);
    els.cartMeta.textContent = `${cart.reduce((a, x) => a + x.qty, 0)} ítems`;
    updateChangeAndWarnings();
}

function renderCart() {
    els.cartTbody.innerHTML = "";

    cart.forEach((line, idx) => {
        const name = line.product?.name ?? "Producto";
        const sku = line.sku ?? "";
        const price = Number(line.unit_price || 0);

        const tr = document.createElement("tr");
        tr.innerHTML = `
      <td>
        <div style="font-weight:900;">${name}</div>
        <div style="opacity:.65;font-size:12px;">SKU: ${sku}</div>
      </td>
      <td class="right">
        <input data-idx="${idx}" class="qtyInput" value="${line.qty}" inputmode="numeric"
               style="width:70px; text-align:right;" />
      </td>
      <td class="right">${money(price)}</td>
      <td class="right">
        <button data-idx="${idx}" class="rmBtn" title="Quitar">X</button>
      </td>
    `;
        els.cartTbody.appendChild(tr);
    });

    document.querySelectorAll(".qtyInput").forEach((inp) => {
        inp.addEventListener("change", (e) => {
            const i = Number(e.target.dataset.idx);
            cart[i].qty = Math.max(1, Number(e.target.value || 1));
            computeTotals();
            renderCart();
        });
    });

    document.querySelectorAll(".rmBtn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            cart.splice(Number(e.target.dataset.idx), 1);
            computeTotals();
            renderCart();
        });
    });
}

function addToCart(product) {
    console.log("PRODUCT RAW:", product);

    const id = product?.id ?? product?.product_id;
    if (id == null) { setMsg("Producto inválido (sin id)."); return; }

    // Fallback para no bloquear pruebas si tu catálogo viene sin sku
    const sku = String(product?.sku || product?.barcode || `ID-${id}` || "").trim();
    const unit_price = getBestPrice(product);

    const found = cart.find((x) => (x.product?.id ?? x.product?.product_id) === id);
    if (found) found.qty += 1;
    else cart.push({ product, qty: 1, unit_price, sku });

    computeTotals();
    renderCart();
}

let searchTimer = null;

async function searchProducts(q) {
    const data = await apiFetch(`/api/products/search?q=${encodeURIComponent(q)}`);
    return Array.isArray(data) ? data : (data.items || []);
}

function renderSuggestions(items) {
    if (!items.length) {
        els.suggestions.style.display = "none";
        els.suggestions.innerHTML = "";
        return;
    }

    els.suggestions.style.display = "block";
    els.suggestions.innerHTML = "";

    items.forEach((p) => {
        const btn = document.createElement("button");
        btn.type = "button";

        const name = p.name ?? "Producto";
        const sku = String(p.sku || p.barcode || "").trim();
        const price = getBestPrice(p);

        btn.textContent = `${name}${sku ? " · " + sku : ""} · ${money(price)}`;
        btn.addEventListener("click", () => {
            addToCart(p);
            els.searchInput.value = "";
            renderSuggestions([]);
            els.searchInput.focus();
        });

        els.suggestions.appendChild(btn);
    });
}

async function submitSale() {
    if (!isCashOpen(cashSession)) { setMsg("Caja cerrada: abre caja para cobrar."); return; }
    if (!cart.length) { setMsg("Carrito vacío."); return; }

    const method = els.paymentMethod.value;
    const total = getTotal();

    const received = Number(els.cashReceived.value || 0);
    const change = method === "CASH" ? Math.max(0, received - total) : 0;

    if (method === "CASH" && received < total) { setMsg("Efectivo insuficiente."); return; }

    const items = cart.map((x) => ({
        product_id: x.product.id ?? x.product.product_id,
        sku: x.sku,
        quantity: x.qty,
        unit_price: Number(x.unit_price || 0),
    }));

    const payments = [
        { method, amount: total, cash_received: method === "CASH" ? received : null, change },
    ];

    // Incluimos branch_id/cash_session_id por si tu backend lo requiere
    const payload = {
        total,
        items,
        payments,
        branch_id: cashSession?.branch_id ?? null,
        cash_session_id: cashSession?.id ?? null,
    };

    console.log("SALE PAYLOAD:", payload);

    try {
        const sale = await apiFetch("/api/sales/", { method: "POST", body: JSON.stringify(payload) });

        cart = [];
        els.cashReceived.value = "";
        computeTotals();
        renderCart();
        setMsg(`Venta registrada. Folio: ${sale?.id ?? sale?.sale_id ?? "OK"}`);
    } catch (e) {
        setMsg(`Error al cobrar: ${String(e.message || e)}`);
        console.error("SALE ERROR:", e);
    }
}

function clearAll() {
    cart = [];
    els.searchInput.value = "";
    els.cashReceived.value = "";
    renderSuggestions([]);
    computeTotals();
    renderCart();
    setMsg("");
}

function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
}

/* INIT */
document.addEventListener("DOMContentLoaded", async () => {
    els.sessionPill.textContent = "Sesión activa";
    try {
        setMsg("Inicializando POS...");
        await refreshCashStatus();
        computeTotals();
        renderCart();
        setMsg("");
    } catch (e) {
        setMsg(`Error inicializando POS: ${String(e.message || e)}`);
    }
});

/* EVENTS */
els.btnLogout?.addEventListener("click", logout);
els.btnOpenCash?.addEventListener("click", openCash);
els.btnCloseCash?.addEventListener("click", closeCash);

els.btnPay?.addEventListener("click", async () => {
    setMsg("Procesando venta...");
    await submitSale();
});

els.btnVoid?.addEventListener("click", clearAll);

els.btnClearSearch?.addEventListener("click", () => {
    els.searchInput.value = "";
    renderSuggestions([]);
    els.searchInput.focus();
});

els.paymentMethod?.addEventListener("change", () => {
    if (els.paymentMethod.value !== "CASH") els.cashReceived.value = "";
    updateChangeAndWarnings();
});

els.cashReceived?.addEventListener("input", updateChangeAndWarnings);

els.searchInput?.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    clearTimeout(searchTimer);

    if (q.length < 2) { renderSuggestions([]); return; }

    searchTimer = setTimeout(async () => {
        try {
            const items = await searchProducts(q);
            renderSuggestions(items);
        } catch {
            renderSuggestions([]);
        }
    }, 200);
});
