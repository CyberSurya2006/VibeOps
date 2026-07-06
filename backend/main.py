import re
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .sys_utils import get_system_health, get_process_list, kill_process_by_pid, get_git_status
from .agents import run_multi_agent_system

app = FastAPI(
    title="VibeOps Backend Service",
    description="Local developer agent workspace and resource management API.",
    version="1.0.0"
)

# Enable CORS for local web interface development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local file-system page loads to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Features: Input Sanitization & Guardrails ---

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
    Scans the incoming prompt for suspicious prompt injection patterns
    and strips hazardous characters to block CLI shell injection risks.
    """
    # 1. Check for prompt injection patterns
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt):
            raise HTTPException(
                status_code=400,
                detail="Security Gate Triggered: Detected suspicious command or instruction override attempt."
            )
            
    # 2. Prevent shell injection payload characters (block sequence operators)
    sanitized = re.sub(r"[;&|`$]", "", prompt)
    
    # 3. Limit length to prevent buffer/cost exhaustion
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
        
    return sanitized

# --- Request Models ---

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="The developer query to route through the multi-agent cockpit.")

class ActionRequest(BaseModel):
    pid: int = Field(..., description="Process ID to terminate.")

# --- Endpoints ---

@app.get("/api/system-stats")
async def read_system_stats():
    """
    Returns real-time CPU, RAM, and Disk metrics along with active process stats.
    """
    try:
        health = get_system_health()
        processes = get_process_list(limit=15)
        return {
            "status": "success",
            "health": health,
            "processes": processes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/git-status")
async def read_git_status(repo_path: Optional[str] = None):
    """
    Inspects git repository status in the current project or a specified folder.
    """
    import os
    if not repo_path:
        repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        status = get_git_status(repo_path)
        return {
            "status": "success",
            "git": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_console(request: ChatRequest, x_gemini_api_key: Optional[str] = Header(None)):
    """
    Chat endpoint routing user queries to the multi-agent system.
    Requires user-supplied Gemini API Key.
    """
    if not x_gemini_api_key:
        raise HTTPException(
            status_code=401,
            detail="Gemini API Key missing. Please provide a valid Gemini API Key in Settings."
        )
        
    # Sanitize and run security gate
    sanitized_message = sanitize_and_check_prompt(request.message)
    
    try:
        agent_reply = run_multi_agent_system(x_gemini_api_key, sanitized_message)
        return {
            "status": "success",
            "reply": agent_reply
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent Error: {str(e)}. Please check if your API key is valid."
        )

@app.post("/api/execute-action")
async def execute_system_action(request: ActionRequest):
    """
    Security Gate: Execute process termination only after explicit user approval.
    Sanitizes PID argument and enforces strict process checks.
    """
    pid = request.pid
    
    # Run the termination logic
    result = kill_process_by_pid(pid)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
        
    return {
        "status": "success",
        "message": result.get("message")
    }

@app.get("/api/health")
async def health_check():
    """
    Simple service status check.
    """
    return {"status": "online", "message": "VibeOps backend server is ready."}
