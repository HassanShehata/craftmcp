from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import secrets
import hashlib
from system_db_handler import SystemDBHandler


router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# Ensure admin user exists on first run
def _bootstrap_admin():
    users = db.fetch_records("users")
    if not users:
        token = secrets.token_hex(16)
        db.create_record("users", {
            "username": "admin",
            "token": hash_token(token),
            "is_admin": 1
        })
        print(f"[[ BOOTSTRAP TRIGGERED ]] Checking users...", flush=True)
        print(f"[INIT] Admin token: {token}")


_bootstrap_admin()


class UserCreate(BaseModel):
    username: str
    is_admin: bool = False


class UserOps(BaseModel):
    username: str


def _require_admin(token: str):
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}' AND is_admin=1")
    if not user:
        raise HTTPException(status_code=403, detail="Admin privileges required")


@router.post("/create-user")
def create_user(
    payload: UserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    _require_admin(token)
    new_token = secrets.token_hex(16)
    try:
        db.create_record("users", {
            "username": payload.username,
            "token": hash_token(new_token),
            "is_admin": int(payload.is_admin)
        })
        return {"username": payload.username, "token": new_token}
    except:
        raise HTTPException(status_code=400, detail="User already exists")


@router.get("/list-users")
def list_users():
    users = db.fetch_records("users")
    return [{"username": u[1], "is_admin": bool(u[3])} for u in users]


@router.post("/refresh-user-token")
def refresh_token(
    payload: UserOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    _require_admin(token)
    user = db.fetch_records("users", f"username='{payload.username}'")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_token = secrets.token_hex(16)
    db.update_record("users", {"token": hash_token(new_token)}, f"username='{payload.username}'")
    return {"username": payload.username, "new_token": new_token}



@router.post("/delete-user")
def delete_user(
    payload: UserOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    _require_admin(token)
    db.delete_record("users", f"username='{payload.username}'")
    return {"deleted": payload.username}
