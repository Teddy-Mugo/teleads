from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Customer

router = APIRouter(prefix="/customer", tags=["Customer"])


def customer_auth(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db),
) -> Customer:
    customer = (
        db.query(Customer)
        .filter(Customer.api_key == x_api_key, Customer.is_active == True)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return customer
