from fastapi import APIRouter, Depends, Header, HTTPException

ADMIN_API_KEY = "super-secret-key"

def admin_auth(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(admin_auth)],
)
