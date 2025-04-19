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


class ToolCreate(BaseModel):
    tool_name: str
    snippet: str
    is_async: bool
    mcp_id: int | None = None
    params: dict = Field(default_factory=dict, description="Function parameters")


class ToolPatch(BaseModel):
    tool_name: str | None = None
    snippet: str | None = None
    is_async: bool | None = None


@router.post("/create-tool")
def create_tool(
    payload: ToolCreate,
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
        "tool_name": payload.tool_name,
        "snippet": payload.snippet,
        "is_async": payload.is_async,
        "params": payload.params,
        "linked_mcp_ids": [payload.mcp_id] if payload.mcp_id else [],
        "owner": username,
        "created_at": datetime.utcnow().isoformat()
    }

    fn_def = "async def" if payload.is_async else "def"
    signature = render_function_signature(payload.params)
    skeleton_code = f'''@mcp.tool()
{fn_def} {payload.tool_name}({signature}) -> str:
    {payload.snippet.strip()}
'''

    db.create_record("tools", {
        "name": payload.tool_name,
        "owner": username,
        "mcp_id": None,
        "is_async": int(payload.is_async),
        "snippet": payload.snippet,
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": skeleton_code
    })

    return {"status": "success", "tool": payload.tool_name}


@router.get("/list-tools")
def list_tools(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    tools = db.fetch_records("tools") if is_admin else db.fetch_records("tools", f"owner='{username}'")

    return [{
        "id": t[0],
        "name": t[1],
        "linked_mcp_ids": json.loads(t[6]).get("linked_mcp_ids", []),
        "is_async": bool(t[4]),
        "owner": t[2]
    } for t in tools]


class ToolOps(BaseModel):
    tool_id: int


class ToolLink(BaseModel):
    tool_id: int
    mcp_id: int


@router.post("/link-tool")
def link_tool(
    payload: ToolLink,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    tool = db.fetch_records("tools", f"id={payload.tool_id}")
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not tool or not mcp:
        raise HTTPException(status_code=404, detail="Tool or MCP not found")

    if not is_admin and (tool[0][2] != username or mcp[0][3] != username):
        raise HTTPException(status_code=403, detail="Not allowed to link")

    metadata = json.loads(tool[0][6])
    linked_ids = metadata.get("linked_mcp_ids", [])
    if payload.mcp_id not in linked_ids:
        linked_ids.append(payload.mcp_id)

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("tools", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.tool_id}")

    return {"status": "linked", "tool_id": payload.tool_id, "linked_mcp_ids": linked_ids}


@router.post("/unlink-tool")
def unlink_tool(
    payload: ToolLink | ToolOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    tool = db.fetch_records("tools", f"id={payload.tool_id}")
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not is_admin and tool[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to unlink")

    metadata = json.loads(tool[0][6])
    linked_ids = metadata.get("linked_mcp_ids", [])

    if isinstance(payload, ToolLink) and payload.mcp_id is not None:
        if payload.mcp_id in linked_ids:
            linked_ids.remove(payload.mcp_id)
    else:
        linked_ids = []

    metadata["linked_mcp_ids"] = linked_ids

    db.update_record("tools", {
        "metadata": json.dumps(metadata, indent=2)
    }, f"id={payload.tool_id}")

    return {
        "status": "unlinked",
        "tool_id": payload.tool_id,
        "remaining_links": linked_ids
    }


@router.get("/export-tool")
def export_tool(
    tool_id: int = Header(..., alias="tool-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    tool = db.fetch_records("tools", f"id={tool_id}")
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not is_admin and tool[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to export")

    metadata = json.loads(tool[0][6])
    skeleton_code = tool[0][7]

    return JSONResponse(content={
        "metadata.json": metadata,
        "tool.py": skeleton_code
    })


@router.post("/modify-tool")
def modify_tool(
    patch: ToolPatch,
    tool_id: int = Header(..., alias="tool-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    tool = db.fetch_records("tools", f"id={tool_id}")
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not is_admin and tool[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to modify")

    metadata = json.loads(tool[0][6])

    if patch.tool_name:
        metadata["tool_name"] = patch.tool_name
    if patch.snippet:
        metadata["snippet"] = patch.snippet
    if patch.is_async is not None:
        metadata["is_async"] = patch.is_async

    fn_def = "async def" if metadata["is_async"] else "def"
    snippet = metadata["snippet"].strip()
    new_code = f'''@mcp.tool()
{fn_def} {metadata["tool_name"]}(message: str) -> str:
    """Generated tool"""
    {snippet}
'''

    db.update_record("tools", {
        "name": metadata["tool_name"],
        "snippet": metadata["snippet"],
        "is_async": int(metadata["is_async"]),
        "metadata": json.dumps(metadata, indent=2),
        "skeleton_code": new_code
    }, f"id={tool_id}")

    return {"status": "modified", "tool": metadata["tool_name"]}


@router.post("/delete-tool")
def delete_tool(
    payload: ToolOps,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    username = user[0][1]
    is_admin = bool(user[0][3])

    tool = db.fetch_records("tools", f"id={payload.tool_id}")
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    if not is_admin and tool[0][2] != username:
        raise HTTPException(status_code=403, detail="Not allowed to delete this tool")

    db.delete_record("tools", f"id={payload.tool_id}")
    return {"status": "deleted", "tool_id": payload.tool_id}