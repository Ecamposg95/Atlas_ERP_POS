from sqlalchemy.orm import Session
from app.models import Customer
from app.schemas.crm import CustomerCreate

def get_customer(db: Session, customer_id: int):
    return db.query(Customer).filter(Customer.id == customer_id).first()

def get_customer_by_tax_id(db: Session, tax_id: str):
    return db.query(Customer).filter(Customer.tax_id == tax_id).first()

def get_customers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Customer).filter(Customer.is_active == True).offset(skip).limit(limit).all()

def create_customer(db: Session, customer: CustomerCreate):
    db_customer = Customer(
        name=customer.name,
        tax_id=customer.tax_id,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        has_credit=customer.has_credit,
        credit_limit=customer.credit_limit,
        credit_days=customer.credit_days
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer