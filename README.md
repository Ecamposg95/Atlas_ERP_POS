# 🧩 Atlas ERP — Backend en Python
> Reimplementación moderna del backend original **DataX POS** desarrollado en Java (Spring Boot), ahora impulsado por **FastAPI** ⚡

---

## 🧠 Prompt de Desarrollo

### 🎯 Objetivo del Proyecto
Replicar el backend de la aplicación **DataX POS**, originalmente desarrollada en **Java (Spring Boot)**, utilizando un stack moderno en **Python**.

Se busca una **API REST modular, eficiente y escalable** que funcione como el núcleo de un **sistema de punto de venta (POS)** orientado a **mayoristas**, con posibilidad de expansión hacia **retail**.

---

## 🧱 Stack Tecnológico Recomendado

- 🐍 **Python 3.10+**
- ⚡ **FastAPI**
- 🧬 **SQLAlchemy 2.0**
- 🧱 **Alembic**
- 🐘 **PostgreSQL**
- 🔐 **JWT Authentication**
- 🚀 **Uvicorn (ASGI Server)**

---

## ⚙️ Estructura General del Proyecto (Python)

```bash
app/
├── main.py                # Punto de entrada FastAPI
├── core/                  # Configuración global, seguridad, dependencias
├── modules/               # Dominios del negocio (ERP)
│   ├── org/               # Usuarios, sucursales, roles
│   ├── catalog/           # Productos, variantes, empaques
│   ├── pricing/           # Listas y reglas de precios
│   ├── inventory/         # Stock, kardex, conteos
│   ├── sales/             # Ventas, cotizaciones, devoluciones
│   ├── payments/          # Caja, pagos mixtos
│   ├── crm/               # Clientes y crédito
│   └── audit/             # Auditoría
├── schemas/               # DTOs (Pydantic)
├── alembic/               # Migraciones
└── tests/
```

---

## 🧩 Contexto Original — DataX POS (Java)

**Fecha de exportación:** 2025-10-25  
**Stack original:** Spring Boot 3 · Java 17 · JPA · PostgreSQL

DataX POS es un sistema de **punto de venta inteligente**, diseñado inicialmente para **mayoristas**, con una arquitectura modular que integra:

- Gestión de ventas y pedidos
- Pagos y caja
- Control de inventario
- Roles operativos

---

## 🔐 Roles del Sistema

| Rol | Descripción |
|---|---|
| 👑 Administrador | Configuración global y control total |
| 🧾 Gerente | Inventario, reportes, autorizaciones |
| 💼 Vendedor | Pedidos y cotizaciones |
| 💰 Cajero | Cobros y cierre de caja |
| 📊 Dueño | Dashboards (solo lectura) |

---

## 🔁 Flujo de Venta

```
DRAFT → READY_TO_PAY → PAID
        ↘ CANCELED
```

---

## 💳 Métodos de Pago Soportados

- 💵 Efectivo
- 💳 Tarjeta
- 🏦 Transferencia
- 🎟️ Vales
- 🔀 Pago mixto (combinación de métodos)

---

## 📦 Inventario por Piezas y Cajas

- El inventario se almacena en **unidad base (piezas)**
- Las **cajas** son presentaciones que convierten automáticamente:
  - 1 caja = N piezas
- Venta y compra soportadas **por pieza o por caja**

---

## 🚀 Inicio Rápido

```bash
# Clonar repositorio
git clone https://github.com/Ecamposg95/Atlas_ERP_POS
cd atlas-erp-backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate    # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --reload
```

Acceder a la documentación interactiva:
👉 http://localhost:8000/docs

---

## 👨‍💻 Autor

**Emmanuel Campos Genaro**  
CTO — Atlas Technologies  

> Atlas ERP es la evolución natural de DataX POS: un núcleo moderno, modular y preparado para crecer.
