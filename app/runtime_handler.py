from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from subprocess import Popen, PIPE
import os
import json
import hashlib
from datetime import datetime
from system_db_handler import SystemDBHandler
import re
from signal import SIGTERM
import shutil
import subprocess


router = APIRouter()
db = SystemDBHandler()
security = HTTPBearer()


MCP_DIR = "mcps_servers"
os.makedirs(MCP_DIR, exist_ok=True)


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

class RunRequest(BaseModel):
    mcp_id: int


@router.post("/export-full-mcp")
def export_full_mcp(
    payload: RunRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Get MCP
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")

    if not is_admin and mcp[0][3] != username:
        raise HTTPException(status_code=403, detail="Not allowed to build this MCP")

    mcp_metadata = json.loads(mcp[0][4])
    mcp_name = mcp_metadata["name"]
    imports = "\n".join(mcp_metadata.get("imports", []))
    globals_block = "\n".join(f"{k} = {json.dumps(v)}" for k, v in mcp_metadata.get("globals", {}).items())

    tools = db.fetch_records("tools", f"owner='{username}'" if not is_admin else None)
    resources = db.fetch_records("resources", f"owner='{username}'" if not is_admin else None)
    prompts = db.fetch_records("prompts", f"owner='{username}'" if not is_admin else None)


    #resources = db.fetch_records("resources")
    #prompts = db.fetch_records("prompts")


    def collect_code(table, kind):
        result = []
        for row in table:
            try:
                if kind == "tool":
                    metadata_idx = 6
                    code_idx = 7
                else:
                    metadata_idx = 5
                    code_idx = 6
        
                metadata = json.loads(row[metadata_idx])
                linked = metadata.get("linked_mcp_ids", [])
                if payload.mcp_id in linked:
                    params = metadata.get("params", {})
                    original_code = row[code_idx]
                    signature = render_function_signature(params)
        
                    # Replace function signature dynamically
                    modified_code = re.sub(r"def\s+\w+\(.*?\)", lambda m: f"def {m.group(0).split()[1].split('(')[0]}({signature})", original_code)
                    result.append(modified_code)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse {kind} id={row[0]}: {e}")
        return result


    tools_code = "\n\n".join(collect_code(tools, "tool"))
    resources_code = "\n\n".join(collect_code(resources, "resource"))
    prompts_code = "\n\n".join(collect_code(prompts, "prompt"))


    # Final file content
    full_code = f"""# Auto-generated MCP server
{imports}

from mcp.server.fastmcp import FastMCP

{globals_block}

mcp = FastMCP("{mcp_name}")

# Resources
{resources_code}

# Tools
{tools_code}

# Prompts
{prompts_code}

if __name__ == "__main__":
    mcp.run(transport="stdio")
"""

    return {
    "status": "success",
    "mcp_id": payload.mcp_id,
    "exported_code": full_code}



@router.post("/run-mcp")
def run_mcp(
    payload: RunRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    import shutil
    from subprocess import run, Popen
    import re

    print(">>> Step 1: Starting /run-mcp")

    token = credentials.credentials
    token_hash = hash_token(token)
    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    print(f">>> Step 2: Authenticated user: {username}, is_admin={is_admin}")

    # Fetch MCP
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    if not is_admin and mcp[0][3] != username:
        raise HTTPException(status_code=403, detail="Not allowed to run this MCP")

    print(f">>> Step 3: MCP found for ID {payload.mcp_id}")

    mcp_code_response = export_full_mcp(payload, credentials)
    code = mcp_code_response["exported_code"]

    print(">>> Step 4: Full MCP code exported")

    # Save path
    folder_path = os.path.join(MCP_DIR, f"mcp_{payload.mcp_id}")
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, f"mcp_{payload.mcp_id}.py")

    with open(file_path, "w") as f:
        f.write(code)

    print(f">>> Step 5: MCP file written to {file_path}")

    # Init uv project & venv (if not already done)
    if not os.path.exists(os.path.join(folder_path, "pyproject.toml")):
        with open(os.path.join(folder_path, "pyproject.toml"), "w") as f:
            f.write('[project]\nname = "mcp_project"\nversion = "0.1.0"\n')

    print(">>> Step 6: pyproject.toml ensured")

    # Init virtual env & install (can comment out pip install for now)
    try:
        print(">>> Step 7: Running uv venv")
        run(["uv", "venv"], cwd=folder_path, check=True)

        run(["uv", "pip", "install", "mcp"], cwd=folder_path, check=True)

        # Re-install user libraries inside this MCP's venv
        user_libs = db.fetch_records("libraries", f"installed_by='{username}'")
        for lib in user_libs:
            lib_name = lib[1]
            print(f">>> Installing {lib_name} into MCP venv...")
            run(["uv", "pip", "install", lib_name], cwd=folder_path, check=True)

        print(">>> Step 8: Running uv script")
        process = Popen(
            ["uv", "run", f"mcp_{payload.mcp_id}.py"],
            cwd=folder_path,
            stdout=PIPE,
            stderr=PIPE
        )

        #Check for crash within 3 seconds
        try:
            output, error = process.communicate(timeout=5)
            if process.returncode != 0:
                #Script failed immediately — track as failed
                db.update_record("mcp_status", {
                    "status": "failed",
                    "pid": process.pid
                }, f"mcp_id={payload.mcp_id}") if db.fetch_records("mcp_status", f"mcp_id={payload.mcp_id}") \
                    else db.create_record("mcp_status", {
                        "mcp_id": payload.mcp_id,
                        "status": "failed",
                        "pid": process.pid
                    })

                # Delete environment folder
                mcp_folder = os.path.join(MCP_DIR, f"mcp_{payload.mcp_id}")
                try:
                    shutil.rmtree(mcp_folder)
                    print(f">>> Cleaned up failed MCP folder: {mcp_folder}")
                except Exception as e:
                    print(f">>> Cleanup failed: {e}")


                return {
                    "status": "failed",
                    "pid": process.pid,
                    "path": file_path,
                    "error": error.decode().strip()
                }

        except subprocess.TimeoutExpired:
            #Still running — mark as running
            existing_status = db.fetch_records("mcp_status", f"mcp_id={payload.mcp_id}")
            if existing_status:
                db.update_record("mcp_status", {
                    "status": "running",
                    "pid": process.pid
                }, f"mcp_id={payload.mcp_id}")
            else:
                db.create_record("mcp_status", {
                    "mcp_id": payload.mcp_id,
                    "status": "running",
                    "pid": process.pid
                })

            print(f">>> Step 9: MCP server launched with PID {process.pid}")

            return {
                "status": "started",
                "pid": process.pid,
                "path": file_path
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"uv or script failed: {e}")


@router.get("/mcps-status")
def mcps_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch all MCPs the user owns (or all if admin)
    mcps = db.fetch_records("mcps") if is_admin else db.fetch_records("mcps", f"owner='{username}'")
    
    result = []
    for mcp in mcps:
        mcp_id = mcp[0]
        mcp_name = mcp[1]
        status_row = db.fetch_records("mcp_status", f"mcp_id={mcp_id}")
        status = status_row[0][1] if status_row else "stopped"

        result.append({
            "id": mcp_id,
            "name": mcp_name,
            "status": status
        })
    
    return result


@router.post("/stop-mcp")
def stop_mcp(
    payload: RunRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    token_hash = hash_token(token)

    user = db.fetch_records("users", f"token='{token_hash}'")
    if not user:
        raise HTTPException(status_code=403, detail="Unauthorized")

    username = user[0][1]
    is_admin = bool(user[0][3])

    # Fetch MCP
    mcp = db.fetch_records("mcps", f"id={payload.mcp_id}")
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")

    if not is_admin and mcp[0][3] != username:
        raise HTTPException(status_code=403, detail="Not allowed to stop this MCP")

    # Get status and PID
    status_row = db.fetch_records("mcp_status", f"mcp_id={payload.mcp_id}")
    if not status_row:
        return {"status": "already stopped", "mcp_id": payload.mcp_id}

    current_status = status_row[0][1]
    pid = status_row[0][2]

    if current_status in ["stopped", "failed"]:
        return {"status": f"already {current_status}", "mcp_id": payload.mcp_id}

    # Attempt kill
    if pid:
        try:
            os.kill(pid, SIGTERM)
            print(f">>> Killed PID {pid}")
        except ProcessLookupError:
            print(f">>> PID {pid} not found, already exited")

    # Mark stopped
    db.update_record("mcp_status", {"status": "stopped", "pid": None}, f"mcp_id={payload.mcp_id}")

    # Delete environment
    mcp_folder = os.path.join(MCP_DIR, f"mcp_{payload.mcp_id}")
    try:
        shutil.rmtree(mcp_folder)
        print(f">>> Deleted MCP folder {mcp_folder}")
    except Exception as e:
        print(f">>> Failed to delete: {e}")

    return {
        "status": "stopped",
        "pid": pid,
        "mcp_id": payload.mcp_id,
        "env_cleaned": not os.path.exists(mcp_folder)
    }
