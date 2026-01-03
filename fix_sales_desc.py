from app.database import SessionLocal
from app.models.sales import SalesLineItem
from app.models.products import ProductVariant, Product
from sqlalchemy.orm import joinedload

def fix_descriptions():
    db = SessionLocal()
    try:
        print("--- Fixing Sales Descriptions ---")
        # Fetch all lines
        lines = db.query(SalesLineItem).options(
            joinedload(SalesLineItem.variant).joinedload(ProductVariant.product)
        ).all()

        count = 0
        for line in lines:
            if not line.variant or not line.variant.product:
                continue

            # Check if description is "bad" (starts with SKU usually, or doesn't contain product name)
            # Or just update ALL to be safe and consistent.
            # Current bad format: "SKU - Variant" e.g. "21516 - Estándar"
            # New format: "Product Name (Variant)" or "Product Name"
            
            p_name = line.variant.product.name
            v_name = line.variant.variant_name
            
            variant_label = f" ({v_name})" if v_name and v_name != "Estándar" else ""
            new_desc = f"{p_name}{variant_label}"

            if line.description != new_desc:
                print(f"Updating ID {line.id}: '{line.description}' -> '{new_desc}'")
                line.description = new_desc
                count += 1
        
        db.commit()
        print(f"--- Updated {count} lines ---")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_descriptions()
