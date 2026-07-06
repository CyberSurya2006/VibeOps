import re
import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .sys_utils import get_workspace_structure, scan_for_secrets, get_git_status, run_shell_command
from .agents import run_multi_agent_system

app = FastAPI(
    title="VibeOps Code Automation Backend",
    description="Secure multi-agent assistant automating builds, tests, and repository operations.",
    version="2.0.0"
)

# CORS configuration to allow local dashboard connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Features: Prompt Injection & Sanitization Gates ---

PROMPT_INJECTION_PATTERNS = [
    r"(?i)\bignore previous instructions\b",
    r"(?i)\bignore the system prompt\b",
    r"(?i)\byou are now an evil\b",
    r"(?i)\bsystem override\b",
    r"(?i)\bdelete all files\b",
    r"(?i)\brm\s+-rf\b"
]

def sanitize_and_check_prompt(prompt: str) -> str:
    """
    Blocks jailbreak attempts and sanitizes input to avoid shell command injections.
    """
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt):
            raise HTTPException(
                status_code=400,
                detail="Security Gate Triggered: Detected suspicious command or jailbreak override attempt."
            )
            
    # Clean shell operators
    sanitized = re.sub(r"[;&|`$]", "", prompt)
    
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
        
    return sanitized

# --- Request Models ---

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="User request.")

class CommandRequest(BaseModel):
    command: str = Field(..., description="Terminal command to execute.")

# --- Endpoints ---

@app.get("/api/workspace-status")
async def read_workspace_status():
    """
    Returns the workspace file profile and lists any detected secret key leaks.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        structure = get_workspace_structure(root_path)
        secrets = scan_for_secrets(root_path)
        return {
            "status": "success",
            "structure": structure,
            "secrets_count": len(secrets),
            "secrets": secrets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/git-status")
async def read_git_status():
    """
    Inspects current workspace git status.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        status = get_git_status(root_path)
        return {
            "status": "success",
            "git": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_console(request: ChatRequest, x_gemini_api_key: Optional[str] = Header(None)):
    """
    Routes queries to the coordinator, build, and secret worker agents.
    """
    if not x_gemini_api_key:
        raise HTTPException(
            status_code=401,
            detail="Gemini API Key missing. Please provide your API Key in Settings."
        )
        
    sanitized_message = sanitize_and_check_prompt(request.message)
    
    try:
        reply = run_multi_agent_system(x_gemini_api_key, sanitized_message)
        return {
            "status": "success",
            "reply": reply
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent Cockpit Error: {str(e)}. Please check if your API Key is valid."
        )

@app.post("/api/run-command")
async def execute_command(request: CommandRequest):
    """
    Security Gate: Execute shell commands (builds/tests) ONLY after user approval.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    command = request.command
    
    # Run the secure execution engine
    result = run_shell_command(command, root_path)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("output"))
        
    return {
        "status": "success",
        "output": result.get("output"),
        "returncode": result.get("returncode")
    }

@app.get("/api/health")
async def health_check():
    """
    Backend service status.
    """
    return {"status": "online", "message": "VibeOps backend server is ready."}
