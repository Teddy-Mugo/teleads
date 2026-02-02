from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import TelegramAccount

router = APIRouter(prefix="/accounts")


@router.get("/")
def list_accounts(db: Session = Depends(get_db)):
    return db.query(TelegramAccount).all()


@router.post("/{account_id}/pause")
def pause_account(account_id: str, db: Session = Depends(get_db)):
    account = db.get(TelegramAccount, account_id)
    account.status = "paused"
    db.commit()
    return {"status": "paused"}


@router.post("/{account_id}/resume")
def resume_account(account_id: str, db: Session = Depends(get_db)):
    account = db.get(TelegramAccount, account_id)
    account.status = "active"
    db.commit()
    return {"status": "active"}
