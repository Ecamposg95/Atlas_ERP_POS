/**
 * js/products.js - Versión Funcional
 */
const API_URL = "/api";
let token = sessionStorage.getItem('token');
let allProducts = [];

document.addEventListener('DOMContentLoaded', () => {
    if (!token) return;
    loadTable();

    const search = document.getElementById('search-input');
    if (search) {
        search.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            const filtered = allProducts.filter(p => p.name.toLowerCase().includes(term));
            renderTable(filtered);
        });
    }
});

async function loadTable() {
    try {
        const res = await fetch(`${API_URL}/products/?limit=1000`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            allProducts = await res.json();
            renderTable(allProducts);
        }
    } catch (e) {
        console.error(e);
    }
}

function renderTable(products) {
    const tbody = document.getElementById('products-table-body');
    if (!tbody) return;

    tbody.innerHTML = products.map(p => {
        const v = (p.variants && p.variants.length > 0) ? p.variants[0] : null;
        if (!v) return '';

        return `
        <tr class="hover:bg-gray-50">
            <td class="p-3 font-medium">${p.name}</td>
            <td class="p-3 font-mono text-gray-500">${v.sku || '-'}</td>
            <td class="p-3 text-right font-bold">$${v.price}</td>
            <td class="p-3 text-center">
                <span class="${p.stock_total > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'} px-2 py-1 rounded text-xs font-bold">
                    ${p.stock_total}
                </span>
            </td>
        </tr>`;
    }).join('');
}