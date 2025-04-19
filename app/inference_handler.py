from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import hashlib
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from system_db_handler import SystemDBHandler


router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


MCP_DIR = "mcps_servers"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class InfereRequest(BaseModel):
    mcp_id: int
    type: str                 # tool | prompt | resource
    name: str | None = None   # optional, only for inference
    arguments: dict = {}      # optional, only for inference


@router.post("/infere-mcp")
async def infere_mcp(
    payload: InfereRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")

    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCP record
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    if not is_admin and mcp[0][3] != username:
        raise HTTPException(status_code=403, detail="You do not own this MCP")

    mcp_file = os.path.join(MCP_DIR, f"mcp_{payload.mcp_id}", f"mcp_{payload.mcp_id}.py")
    if not os.path.exists(mcp_file):
        raise HTTPException(status_code=500, detail="MCP file not found or not exported")

    server_params = StdioServerParameters(
        command="uv",
        args=["run", f"mcp_{payload.mcp_id}.py"],
        cwd=os.path.dirname(mcp_file)
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 🔁 LISTING MODE
            if not payload.name:
                if payload.type == "tool":
                    return {"status": "available", "type": "tool", "items": await session.list_tools()}
                elif payload.type == "prompt":
                    return {"status": "available", "type": "prompt", "items": await session.list_prompts()}
                elif payload.type == "resource":
                    return {"status": "available", "type": "resource", "items": await session.list_resources()}
                else:
                    raise HTTPException(status_code=400, detail="Invalid type for listing")

            # 🚀 INFERENCE MODE
            try:
                if payload.type == "tool":
                    result = await session.call_tool(payload.name, payload.arguments)
                elif payload.type == "prompt":
                    result = await session.call_prompt(payload.name, payload.arguments)
                elif payload.type == "resource":
                    result, _ = await session.read_resource(payload.name)
                else:
                    raise HTTPException(status_code=400, detail="Invalid type for invocation")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

            return {"status": "success", "result": result}