import sqlite3
import os

DB_PATH = "d:\\Devs\\Atlas_ERP_POS\\sql_app.db"

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Checking for ticket columns in organization table...")
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(organization)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'ticket_header' not in columns:
            print("Adding 'ticket_header' column...")
            cursor.execute("ALTER TABLE organization ADD COLUMN ticket_header TEXT DEFAULT 'ATLAS POS - Nota de Venta'")
            
        if 'ticket_footer' not in columns:
            print("Adding 'ticket_footer' column...")
            cursor.execute("ALTER TABLE organization ADD COLUMN ticket_footer TEXT DEFAULT 'Gracias por su compra!'")
            
        conn.commit()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
