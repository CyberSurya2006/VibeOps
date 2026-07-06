import os
import json
import mcp.types as types
from mcp.server import Server
from .sys_utils import get_system_health, get_process_list, kill_process_by_pid, get_git_status

# Initialize MCP Server
server = Server("vibeops-mcp-server")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    Exposes system metrics and git status as readable MCP resources.
    """
    return [
        types.Resource(
            uri="mcp://system/metrics",
            name="System Health Metrics",
            description="Real-time CPU, RAM, and disk utilization statistics.",
            mimeType="application/json"
        ),
        types.Resource(
            uri="mcp://git/status",
            name="Workspace Git Status",
            description="Overview of uncommitted changes and branch status in the current project.",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    Handles reading of the registered resources.
    """
    if uri == "mcp://system/metrics":
        return json.dumps(get_system_health())
    elif uri == "mcp://git/status":
        # Check current VibeOps root
        repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return json.dumps(get_git_status(repo_path))
    else:
        raise ValueError(f"Resource not found: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Registers developer-agent tools.
    """
    return [
        types.Tool(
            name="get_process_list",
            description="Lists active system processes sorted by RAM usage to identify memory leaks or resource-intensive tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum processes to return", "default": 10}
                }
            }
        ),
        types.Tool(
            name="reclaim_memory",
            description="Terminates a specific process by its PID to reclaim RAM/VRAM. Note: Requires explicit user approval on execution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID to terminate"}
                },
                "required": ["pid"]
            }
        ),
        types.Tool(
            name="git_diff_summary",
            description="Inspects active files in the local Git repository and provides branch information, unstaged files, and commit logs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Absolute path to the Git repository folder. If omitted, uses current workspace."}
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """
    Routes agent tool calls to local system operations.
    """
    arguments = arguments or {}
    
    if name == "get_process_list":
        limit = arguments.get("limit", 10)
        processes = get_process_list(limit)
        return [types.TextContent(type="text", text=json.dumps(processes, indent=2))]
        
    elif name == "reclaim_memory":
        pid = arguments.get("pid")
        if not pid:
            return [types.TextContent(type="text", text="Error: PID parameter is required.")]
        
        # Call termination helper
        result = kill_process_by_pid(pid)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
    elif name == "git_diff_summary":
        repo_path = arguments.get("repo_path")
        if not repo_path:
            # Fallback to local workspace
            repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        status = get_git_status(repo_path)
        return [types.TextContent(type="text", text=json.dumps(status, indent=2))]
        
    else:
        raise ValueError(f"Unknown tool: {name}")
