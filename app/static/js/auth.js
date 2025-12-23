// app/static/js/auth.js
const form = document.getElementById("loginForm");
const msg = document.getElementById("loginMsg");

function setMsg(t) { if (msg) msg.textContent = t || ""; }

if (localStorage.getItem("access_token")) {
    window.location.href = "/pos";
}

form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    setMsg("Autenticando...");

    const username = form.username.value.trim();
    const password = form.password.value;

    const data = new URLSearchParams();
    data.append("username", username);
    data.append("password", password);

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: data,
        });

        if (!res.ok) {
            const txt = await res.text();
            throw new Error(txt || "Credenciales inválidas");
        }

        const json = await res.json();
        if (!json?.access_token) throw new Error("Respuesta inválida: falta access_token");

        localStorage.setItem("access_token", json.access_token);
        setMsg("OK. Redirigiendo...");
        window.location.href = "/pos";
    } catch (err) {
        setMsg(`Error: ${String(err.message || err)}`);
    }
});
