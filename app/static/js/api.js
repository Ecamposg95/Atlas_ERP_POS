// app/static/js/api.js
export async function apiFetch(url, options = {}) {
    const token = localStorage.getItem("access_token");

    const headers = {
        Accept: "application/json",
        ...(options.headers || {}),
    };

    // Si envías string body, asume JSON salvo que ya tengas content-type
    if (!headers["Content-Type"] && options.body && typeof options.body === "string") {
        headers["Content-Type"] = "application/json";
    }

    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(url, { ...options, headers });

    // Redirección segura a login si token expiró / inválido
    if (res.status === 401) {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
        return;
    }

    const ct = res.headers.get("content-type") || "";
    const isJson = ct.includes("application/json");

    if (!res.ok) {
        let errText = `HTTP ${res.status}`;
        try {
            if (isJson) {
                const data = await res.json();
                if (data?.detail) {
                    errText = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
                } else {
                    errText = JSON.stringify(data);
                }
            } else {
                errText = await res.text();
            }
        } catch {
            // noop
        }
        throw new Error(errText);
    }

    if (isJson) return res.json();
    return res.text();
}

// COMPATIBILIDAD LEGACY:
// Si algún script antiguo llama window.apiFetch(...), no se rompe.
window.apiFetch = apiFetch;
