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


class PromptCreate(BaseModel):
    prompt_name: str
    snippet: str
    mcp_id: int | None = None
    params: dict = Field(default_factory=dict, description="Function parameters")


@router.post("/create-prompt")
def create_prompt(
    payload: PromptCreate,
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
            raise HTTPException(status_code=403, detail="Not allowed to link")

    metadata = {
        "prompt_name": payload.prompt_name,
        "params": payload.params,
        "snippet": payload.snippet,
        "linked_mcp_ids": [payload.mcp_id] if payload.mcp_id else [],
        "owner": username,
        "created_at": datetime.utcnow().isoformat()
    }

    signature = render_function_signature(payload.params)
    skeleton_code = f'''@mcp.prompt()
def {payload.prompt_name}({signature}) -> str:
    {payload.snippet.strip()}
'''

    db.create_record("prompts", {
        "name": payload.prompt_name,
        "owner": username,
        "mcp_id": None,
        "snippet": payload.snippet,
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": skeleton_code
    })

    return {"status": "success", "prompt": payload.prompt_name}

@router.get("/list-prompts")
def list_prompts(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    prompts = db.fetch_records("prompts") if is_admin else db.fetch_records("prompts", f"owner='{username}'")

    return [{
        "id": p[0],
        "name": p[1],
        "owner": p[2],
        "linked_mcp_ids": json.loads(p[5]).get("linked_mcp_ids", [])
    } for p in prompts]

class PromptOps(BaseModel):
    prompt_id: int

class PromptLink(BaseModel):
    prompt_id: int
    mcp_id: int

@router.post("/link-prompt")
def link_prompt(
    payload: PromptLink,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    prompt = db.fetch_records("prompts", f"id={payload.prompt_id}")
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not prompt or not mcp:
        raise HTTPException(status_code=404, detail="Prompt or MCP not found")

    if not is_admin and (prompt[0][2] != username or mcp[0][3] != username):
        raise HTTPException(status_code=403, detail="Not allowed to link")

    metadata = json.loads(prompt[0][5])
    linked_ids = metadata.get("linked_mcp_ids", [])
    if payload.mcp_id not in linked_ids:
        linked_ids.append(payload.mcp_id)

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("prompts", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.prompt_id}")

    return {"status": "linked", "prompt_id": payload.prompt_id, "linked_mcp_ids": linked_ids}

@router.post("/unlink-prompt")
def unlink_prompt(
    payload: PromptLink | PromptOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    prompt = db.fetch_records("prompts", f"id={payload.prompt_id}")
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not is_admin and prompt[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to unlink")

    metadata = json.loads(prompt[0][5])
    linked_ids = metadata.get("linked_mcp_ids", [])

    if isinstance(payload, PromptLink) and payload.mcp_id is not None:
        if payload.mcp_id in linked_ids:
            linked_ids.remove(payload.mcp_id)
    else:
        linked_ids = []

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("prompts", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.prompt_id}")

    return {
        "status": "unlinked",
        "prompt_id": payload.prompt_id,
        "remaining_links": linked_ids
    }

class PromptPatch(BaseModel):
    prompt_name: str | None = None
    snippet: str | None = None

@router.post("/modify-prompt")
def modify_prompt(
    patch: PromptPatch,
    prompt_id: int = Header(..., alias="prompt-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    prompt = db.fetch_records("prompts", f"id={prompt_id}")
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not is_admin and prompt[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to modify")

    metadata = json.loads(prompt[0][5])
    if patch.prompt_name:
        metadata["prompt_name"] = patch.prompt_name
    if patch.snippet:
        metadata["snippet"] = patch.snippet

    skeleton_code = f'''@mcp.prompt()
def {metadata["prompt_name"]}(message: str) -> str:
    """Generated prompt"""
    {metadata["snippet"].strip()}
'''

    db.update_record("prompts", {
        "name": metadata["prompt_name"],
        "snippet": metadata["snippet"],
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": skeleton_code
    }, f"id={prompt_id}")

    return {"status": "modified", "prompt": metadata["prompt_name"]}

@router.get("/export-prompt")
def export_prompt(
    prompt_id: int = Header(..., alias="prompt-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    prompt = db.fetch_records("prompts", f"id={prompt_id}")
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not is_admin and prompt[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to export")

    return JSONResponse(content={
        "metadata.json": json.loads(prompt[0][5]),
        "prompt.py": prompt[0][6]
    })


@router.post("/delete-prompt")
def delete_prompt(
    payload: PromptOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    username = user[0][1]
    is_admin = bool(user[0][3])

    prompt = db.fetch_records("prompts", f"id={payload.prompt_id}")
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if not is_admin and prompt[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to delete this prompt")

    db.delete_record("prompts", f"id={payload.prompt_id}")
    return {"status": "deleted", "prompt_id": payload.prompt_id}