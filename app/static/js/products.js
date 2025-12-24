// app/static/js/products.js
const API_BASE = "/api";

const els = {
    tableBody: document.getElementById("productsTableBody"),
    loading: document.getElementById("loading"),
    productSearch: document.getElementById("productSearch"),
    btnSearch: document.getElementById("btnSearch"),
    btnAddProduct: document.getElementById("btnAddProduct"),

    // Modal
    modalOverlay: document.getElementById("modalOverlay"),
    productForm: document.getElementById("productForm"),
    btnCancel: document.getElementById("btnCancel"),
    modalTitle: document.getElementById("modalTitle"),
};

// Utils
function token() {
    return localStorage.getItem("access_token");
}

async function apiFetch(path, options = {}) {
    const headers = {
        "Authorization": `Bearer ${token()}`,
        "Content-Type": "application/json",
        ...options.headers
    };

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        window.location.href = "/login";
        return;
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }

    return res.json();
}

function money(n) {
    return `$${Number(n || 0).toFixed(2)}`;
}

// Logic
async function loadProducts(query = "") {
    els.loading.style.display = "block";
    els.tableBody.innerHTML = "";

    try {
        // Usa el endpoint de búsqueda si hay query, o el listado normal
        let url = "/products/";
        if (query.trim()) {
            url = `/products/search?q=${encodeURIComponent(query)}`;
        }

        const data = await apiFetch(url);
        renderTable(data);
    } catch (e) {
        console.error(e);
        alert("Error al cargar productos: " + e.message);
    } finally {
        els.loading.style.display = "none";
    }
}

function renderTable(products) {
    els.tableBody.innerHTML = "";

    if (!products || products.length === 0) {
        els.tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem;">No se encontraron productos.</td></tr>`;
        return;
    }

    products.forEach(p => {
        const v = p.variants?.[0] || {};
        const tr = document.createElement("tr");
        tr.style.borderBottom = "1px solid var(--slate-100)";

        tr.innerHTML = `
            <td>
                <div style="font-weight:600;">${p.name}</div>
                <div class="text-sm text-muted">${p.description || ""}</div>
            </td>
            <td>${v.sku || "-"}</td>
            <td style="text-align:right;">${money(v.price)}</td>
            <td style="text-align:center;">
                <span style="background: var(--slate-100); padding: 2px 8px; border-radius: 99px; font-size: 0.75rem;">
                    ${parseFloat(p.stock_total || 0)}
                </span>
            </td>
            <td style="text-align:right;">
                <button class="btn btn-secondary" style="padding: 4px 8px;" onclick="alert('Edición pendiente')">✏️</button>
            </td>
        `;
        els.tableBody.appendChild(tr);
    });
}

// Modal
function showModal(show = true) {
    els.modalOverlay.style.display = show ? "flex" : "none";
    if (!show) els.productForm.reset();
}

async function handleCreate(e) {
    e.preventDefault();
    const fd = new FormData(els.productForm);
    const data = Object.fromEntries(fd.entries());

    // Transform types
    const payload = {
        name: data.name,
        sku: data.sku,
        barcode: data.barcode || null,
        price: parseFloat(data.price),
        cost: parseFloat(data.cost || 0),
        initial_stock: parseFloat(data.initial_stock || 0),
        unit: data.unit || "pza",
        // department_id? Ignoramos por ahora o hardcodeamos 1 si es obligatorio, pero el API parece manejarlo.
        // Si el API requiere department_id, esto fallará. Asumamos que el backend lo maneja o es opcional.
    };

    try {
        await apiFetch("/products/", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        showModal(false);
        loadProducts(); // Reload
        alert("Producto creado correctamente");
    } catch (err) {
        alert("Error al crear: " + err.message);
    }
}

// Init
function init() {
    loadProducts();

    els.btnSearch.addEventListener("click", () => loadProducts(els.productSearch.value));
    els.productSearch.addEventListener("keydown", (e) => {
        if (e.key === "Enter") loadProducts(els.productSearch.value);
    });

    els.btnAddProduct.addEventListener("click", () => showModal(true));
    els.btnCancel.addEventListener("click", () => showModal(false));
    els.productForm.addEventListener("submit", handleCreate);

    // Close modal on outside click
    els.modalOverlay.addEventListener("click", (e) => {
        if (e.target === els.modalOverlay) showModal(false);
    });
}

init();
