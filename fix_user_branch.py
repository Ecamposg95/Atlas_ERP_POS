from app.database import SessionLocal
from app.models.users import User
from app.models.organization import Branch

db = SessionLocal()

try:
    # 1. Check User
    u = db.query(User).filter(User.id == 4).first()
    if not u:
        print("User 4 not found!")
        exit()

    print(f"Found User: {u.username} (ID: 4), Current Branch: {u.branch_id}")

    # 2. Check Branch
    b = db.query(Branch).first()
    if not b:
        print("No branches found in system!")
        # Create one? excessive for now.
        exit()
    
    print(f"Assigning Branch: {b.name} (ID: {b.id})")

    # 3. Assign
    u.branch_id = b.id
    db.commit()
    print("SUCCESS: Branch assigned.")

except Exception as e:
    print(f"ERROR: {e}")
finally:
    db.close()
