from app.database import SessionLocal
from app.models.users import User, Role
from sqlalchemy import text

db = SessionLocal()

print("--- INSPECTING RAW DATA ---")
# Use raw SQL to see what's actually in the DB, bypassing SQLAlchemy Enum mapping which might crash
try:
    result = db.execute(text("SELECT id, username, role FROM users"))
    users = result.fetchall()
    
    print(f"Found {len(users)} users.")
    display_users = []
    
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Role (Raw): {u.role}")
        
        # Mapping logic
        new_role = None
        current_role = str(u.role)
        
        if current_role.lower() == 'admin':
            new_role = "ADMINISTRADOR"
        elif current_role.lower() == 'manager':
            new_role = "GERENTE"
        elif current_role.lower() == 'cashier' or current_role.lower() == 'seller':
            new_role = "CAJERO"
            
        display_users.append({"id": u.id, "current": current_role, "new": new_role})

    print("\n--- ATTEMPTING FIX ---")
    for item in display_users:
        if item["new"] and item["current"] != item["new"]:
            print(f"Fixing User {item['id']}: {item['current']} -> {item['new']}")
            # Execute raw update to avoid SQLAlchemy object loading issues
            db.execute(
                text("UPDATE users SET role = :new_role WHERE id = :id"),
                {"new_role": item["new"], "id": item["id"]}
            )
            
    db.commit()
    print("Fixes applied successfully.")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
