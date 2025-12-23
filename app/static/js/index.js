import { apiFetch } from "./api.js";

async function loadProducts() {
    const products = await apiFetch("/products");

    const tbody = document.getElementById("productsTable");
    tbody.innerHTML = "";

    products.forEach(p => {
        tbody.innerHTML += `
      <tr>
        <td>${p.sku}</td>
        <td>${p.name}</td>
        <td>$${p.price}</td>
        <td>${p.stock}</td>
      </tr>
    `;
    });
}

document.addEventListener("DOMContentLoaded", loadProducts);
