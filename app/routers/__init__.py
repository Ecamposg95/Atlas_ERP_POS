# app/routers/__init__.py

# Esto expone los módulos para que "from app.routers import users" funcione
from . import auth
from . import products
from . import inventory
from . import sales
from . import cash
from . import printer
from . import users
from . import customers
from . import branches
from . import departments
# from . import crm # Si ya no usas crm, quítalo