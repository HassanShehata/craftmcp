from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import json
import hashlib
from system_db_handler import SystemDBHandler


router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class MCPCreate(BaseModel):
    name: str
    description: str = ""
    imports: list[str] = Field(default_factory=list, description="Custom import statements (e.g., ['import httpx'])")
    globals: dict = Field(default_factory=dict, description="Global variables used in the MCP server file")


@router.post("/create-mcp")
def create_mcp(
    payload: MCPCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    # Resolve user from token hash
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Invalid or unauthorized token")
    
    username = user[0][1]  # column index 1 = username

    # Build MCP metadata
    metadata = {
        "name": payload.name,
        "description": payload.description,
        "imports": payload.imports,
        "globals": payload.globals,
        "created_at": datetime.utcnow().isoformat(),
        "owner": username
    }

    # Generate MCP skeleton code
    import_section = "\n".join(payload.imports)
    global_section = "\n".join(f"{k} = {json.dumps(v)}" for k, v in payload.globals.items())

    skeleton_code = f'''
# Custom Imports
{import_section}

# Required MCP Import
from mcp.server.fastmcp import FastMCP

# Global Variables
{global_section}

# Initialize MCP
mcp = FastMCP("{payload.name}")

# Tools, Resources, Prompts will be added dynamically...

if __name__ == "__main__":
    mcp.run(transport="stdio")
'''

    try:
        db.create_record("mcps", {
            "name": payload.name,
            "owner_token": token_hash,
            "owner": username,
            "metadata": json.dumps(metadata, indent=2),
            "skeleton_code": skeleton_code
        })

        # Retrieve MCP ID
        created = db.fetch_records("mcps", f"name='{payload.name}' AND owner='{username}'")
        mcp_id = created[0][0] if created else None

        return {"status": "success", "mcp": payload.name, "id": mcp_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"MCP creation failed: {str(e)}")


@router.get("/list-mcps")
def list_mcps(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)

    # Fetch user by hashed token
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCPs
    if is_admin:
        mcps = db.fetch_records("mcps")
    else:
        mcps = db.fetch_records("mcps", f"owner='{username}'")

    # Return summary including ID
    mcp_summaries = []
    for mcp in mcps:
        metadata = json.loads(mcp[4])  # index 4 = metadata
        mcp_summaries.append({
            "id": mcp[0],
            "name": mcp[1],
            "owner": mcp[3],
            "description": metadata.get("description", ""),
            "created_at": metadata.get("created_at", "")
        })

    return {"mcps": mcp_summaries}


class MCPPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    imports: list[str] | None = None
    globals: dict | None = None


@router.post("/modify-mcp")
def modify_mcp(
    patch: MCPPatch,
    mcp_id: int = Header(..., alias="mcp-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    # Fetch user
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCP
    mcp = db.fetch_records("mcps", f"id={mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    owner = mcp[0][3]
    metadata = json.loads(mcp[0][4])  # column 4 = metadata

    # Ownership check
    if not is_admin and owner != username:
        raise HTTPException(status_code=403, detail="Not allowed to modify this MCP")

    # Patch metadata
    if patch.name is not None:
        metadata["name"] = patch.name
    if patch.description is not None:
        metadata["description"] = patch.description
    if patch.imports is not None:
        metadata["imports"] = patch.imports
    if patch.globals is not None:
        metadata["globals"] = patch.globals

    # Regenerate skeleton code
    import_section = "\n".join(metadata.get("imports", []))
    global_section = "\n".join(f"{k} = {json.dumps(v)}" for k, v in metadata.get("globals", {}).items())

    skeleton_code = f'''
# Custom Imports
{import_section}

# Required MCP Import
from mcp.server.fastmcp import FastMCP

# Global Variables
{global_section}

# Initialize MCP
mcp = FastMCP("{metadata["name"]}")

# Tools, Resources, Prompts will be added dynamically...

if __name__ == "__main__":
    mcp.run(transport="stdio")
'''

    try:
        db.update_record(
            "mcps",
            {
                "metadata": json.dumps(metadata, indent=2),
                "skeleton_code": skeleton_code
            },
            f"id={mcp_id}"
        )
        return {"status": "success", "modified": metadata["name"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")


@router.post("/delete-mcp")
def delete_mcp(
    mcp_id: int = Header(..., alias="mcp-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    # Fetch user
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCP
    mcp = db.fetch_records("mcps", f"id={mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    owner = mcp[0][3]
    name = mcp[0][1]

    if not is_admin and owner != username:
        raise HTTPException(status_code=403, detail="Not allowed to delete this MCP")

    try:
        db.delete_record("mcps", f"id={mcp_id}")
        return {"status": "deleted", "mcp": name, "id": mcp_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Deletion failed: {str(e)}")


@router.get("/export-mcp")
def export_mcp(
    mcp_id: int = Header(..., alias="mcp-id"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    # Verify user
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCP
    mcp = db.fetch_records("mcps", f"id={mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    owner = mcp[0][3]
    name = mcp[0][1]

    if not is_admin and owner != username:
        raise HTTPException(status_code=403, detail="Not allowed to export this MCP")

    metadata = json.loads(mcp[0][4])
    skeleton_code = mcp[0][5]

    # Construct export payload
    export_data = {
        "metadata.json": metadata,
        "mcp.py": skeleton_code
    }

    return JSONResponse(content=export_data)