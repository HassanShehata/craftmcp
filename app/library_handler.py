from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
import subprocess
import hashlib
from system_db_handler import SystemDBHandler

router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LibraryOp(BaseModel):
    name: str


@router.post("/install-library")
def install_library(
    payload: LibraryOp,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]

    # Check if already tracked
    existing = db.fetch_records("libraries", f"name='{payload.name}' AND installed_by='{username}'")
    if existing:
        raise HTTPException(status_code=400, detail="Library already installed by this user")

    # Try installing using pip
    try:
        subprocess.run(["pip", "install", payload.name], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Install failed: {e.stderr.decode()}")

    # Track it in DB
    db.create_record("libraries", {
        "name": payload.name,
        "installed_by": username,
        "installed_at": datetime.utcnow().isoformat()
    })

    return {"status": "installed", "library": payload.name}


@router.post("/list-libraries")
def list_libraries(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    libraries = db.fetch_records("libraries") if is_admin else db.fetch_records("libraries", f"installed_by='{username}'")

    return [{
        "id": l[0],
        "name": l[1],
        "installed_by": l[2],
        "installed_at": l[3]
    } for l in libraries]


@router.post("/delete-library")
def delete_library(
    payload: LibraryOp,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    records = db.fetch_records("libraries", f"name='{payload.name}'")
    if not records:
        raise HTTPException(status_code=404, detail="Library not found")

    if not is_admin and records[0][2] != username:
        raise HTTPException(status_code=403, detail="Cannot delete library installed by another user")

    # Try uninstalling
    try:
        subprocess.run(["pip", "uninstall", "-y", payload.name], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Uninstall failed: {e.stderr.decode()}")

    db.delete_record("libraries", f"name='{payload.name}' AND installed_by='{records[0][2]}'")
    return {"status": "uninstalled", "library": payload.name}
