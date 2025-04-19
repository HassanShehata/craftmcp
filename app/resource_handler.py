from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib
import json
from system_db_handler import SystemDBHandler
from fastapi.responses import JSONResponse

router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


def render_function_signature(param_dict: dict) -> str:
    params = []
    for name, val in param_dict.items():
        if isinstance(val, dict):
            type_str = val.get("type", "str")
            default = val.get("default")
            if isinstance(default, str):
                default = f'"{default}"'
            params.append(f"{name}: {type_str} = {default}")
        else:
            params.append(f"{name}: {val}")
    return ", ".join(params)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ResourceCreate(BaseModel):
    resource_name: str
    path_template: str
    snippet: str
    mcp_id: int | None = None
    params: dict = Field(default_factory=dict, description="Function parameters")


@router.post("/create-resource")
def create_resource(
    payload: ResourceCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    if payload.mcp_id is not None:
        mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
        if not mcp:
            raise HTTPException(status_code=404, detail="MCP not found")
        if not is_admin and mcp[0][3] != username:
            raise HTTPException(status_code=403, detail="Not allowed to link to this MCP")

    metadata = {
        "resource_name": payload.resource_name,
        "path_template": payload.path_template,
        "params": payload.params,
        "snippet": payload.snippet,
        "linked_mcp_ids": [payload.mcp_id] if payload.mcp_id else [],
        "owner": username,
        "created_at": datetime.utcnow().isoformat()
    }

    signature = render_function_signature(payload.params)
    skeleton_code = f'''@mcp.resource("{payload.path_template}")
def {payload.resource_name}({signature}) -> str:
    {payload.snippet.strip()}
'''

    db.create_record("resources", {
        "name": payload.resource_name,
        "owner": username,
        "mcp_id": None,
        "snippet": payload.snippet,
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": skeleton_code
    })
    return {"status": "success", "resource": payload.resource_name}


@router.get("/list-resources")
def list_resources(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    resources = db.fetch_records("resources") if is_admin else db.fetch_records("resources", f"owner='{username}'")

    return [{
        "id": r[0],
        "name": r[1],
        "owner": r[2],
        "linked_mcp_ids": json.loads(r[5]).get("linked_mcp_ids", [])
    } for r in resources]


class ResourceOps(BaseModel):
    resource_id: int


class ResourceLink(BaseModel):
    resource_id: int
    mcp_id: int


@router.post("/link-resource")
def link_resource(
    payload: ResourceLink,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    resource = db.fetch_records("resources", f"id={payload.resource_id}")
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not resource or not mcp:
        raise HTTPException(status_code=404, detail="Resource or MCP not found")

    if not is_admin and (resource[0][2] != username or mcp[0][3] != username):
        raise HTTPException(status_code=403, detail="Not allowed to link")

    metadata = json.loads(resource[0][5])
    linked_ids = metadata.get("linked_mcp_ids", [])
    if payload.mcp_id not in linked_ids:
        linked_ids.append(payload.mcp_id)

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("resources", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.resource_id}")

    return {"status": "linked", "resource_id": payload.resource_id, "linked_mcp_ids": linked_ids}


@router.post("/unlink-resource")
def unlink_resource(
    payload: ResourceLink | ResourceOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    resource = db.fetch_records("resources", f"id={payload.resource_id}")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not is_admin and resource[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to unlink")

    metadata = json.loads(resource[0][5])
    linked_ids = metadata.get("linked_mcp_ids", [])

    if isinstance(payload, ResourceLink) and payload.mcp_id is not None:
        if payload.mcp_id in linked_ids:
            linked_ids.remove(payload.mcp_id)
    else:
        linked_ids = []

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("resources", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.resource_id}")

    return {
        "status": "unlinked",
        "resource_id": payload.resource_id,
        "remaining_links": linked_ids
    }


class ResourcePatch(BaseModel):
    resource_name: str | None = None
    path_template: str | None = None
    snippet: str | None = None

@router.post("/modify-resource")
def modify_resource(
    patch: ResourcePatch,
    resource_id: int = Header(..., alias="resource-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    resource = db.fetch_records("resources", f"id={resource_id}")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not is_admin and resource[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to modify")

    metadata = json.loads(resource[0][5])
    if patch.resource_name:
        metadata["resource_name"] = patch.resource_name
    if patch.path_template:
        metadata["path_template"] = patch.path_template
    if patch.snippet:
        metadata["snippet"] = patch.snippet

    skeleton_code = f'''@mcp.resource("{metadata["path_template"]}")
def {metadata["resource_name"]}() -> str:
    """Generated resource"""
    {metadata["snippet"].strip()}
'''

    db.update_record("resources", {
        "name": metadata["resource_name"],
        "snippet": metadata["snippet"],
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": skeleton_code
    }, f"id={resource_id}")

    return {"status": "modified", "resource": metadata["resource_name"]}


@router.get("/export-resource")
def export_resource(
    resource_id: int = Header(..., alias="resource-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    resource = db.fetch_records("resources", f"id={resource_id}")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not is_admin and resource[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to export")

    return JSONResponse(content={
        "metadata.json": json.loads(resource[0][5]),
        "resource.py": resource[0][6]
    })


@router.post("/delete-resource")
def delete_resource(
    payload: ResourceOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    resource = db.fetch_records("resources", f"id={payload.resource_id}")
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    if not is_admin and resource[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to delete this resource")

    db.delete_record("resources", f"id={payload.resource_id}")
    return {"status": "deleted", "resource_id": payload.resource_id}