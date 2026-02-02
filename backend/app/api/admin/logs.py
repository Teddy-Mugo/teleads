from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import MessageLog

router = APIRouter(prefix="/logs")


@router.get("/")
def list_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return (
        db.query(MessageLog)
        .order_by(MessageLog.sent_at.desc())
        .limit(limit)
        .all()
    )


