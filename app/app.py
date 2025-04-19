from fastapi import FastAPI
from user_handler import router as user_router
from mcp_handler import router as mcp_router
from tool_handler import router as tool_router
from resource_handler import router as resource_router
from prompt_handler import router as prompt_router
from library_handler import router as library_router
from runtime_handler import router as runtime_router
from inference_handler import router as inference_router


app = FastAPI(title="CraftMCP API", version="0.1")


# Register routers
app.include_router(user_router)
app.include_router(mcp_router)
app.include_router(tool_router)
app.include_router(resource_router)
app.include_router(prompt_router)
app.include_router(library_router)
app.include_router(runtime_router)
app.include_router(inference_router)