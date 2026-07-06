import os
import json
import mcp.types as types
from mcp.server import Server
from .sys_utils import get_workspace_structure, get_git_status, scan_for_secrets

# Initialize MCP Server
server = Server("vibeops-mcp-server")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    Registers the workspace layout and git status as readable MCP resources.
    """
    return [
        types.Resource(
            uri="mcp://workspace/files",
            name="Workspace Directory Details",
            description="Exposes languages detected and file structure preview.",
            mimeType="application/json"
        ),
        types.Resource(
            uri="mcp://git/diff",
            name="Git Repository State",
            description="Exposes current branch, dirty state, and uncommitted changes list.",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    Reads the content of the requested MCP resources.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if uri == "mcp://workspace/files":
        return json.dumps(get_workspace_structure(root_path))
    elif uri == "mcp://git/diff":
        return json.dumps(get_git_status(root_path))
    else:
        raise ValueError(f"Resource not found: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Registers developer agent operational tools.
    """
    return [
        types.Tool(
            name="scan_for_secrets",
            description="Performs regex scanning over project source files to verify there are no leaked API keys or credentials.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_build_targets",
            description="Inspects active files to recommend build and test commands (e.g. pytest for Python, npm test for Node).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """
    Routes agent tool requests to system calls.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arguments = arguments or {}
    
    if name == "scan_for_secrets":
        findings = scan_for_secrets(root_path)
        return [types.TextContent(type="text", text=json.dumps(findings, indent=2))]
        
    elif name == "get_build_targets":
        structure = get_workspace_structure(root_path)
        langs = structure.get("languages_detected", [])
        
        targets = []
        for lang in langs:
            if "Python" in lang:
                targets.append({"target": "pytest", "command": "pytest", "description": "Run Python unit tests."})
                targets.append({"target": "python-script", "command": "python vibeops-cli.py --help", "description": "Verify python script syntax."})
            elif "Node.js" in lang:
                targets.append({"target": "npm-test", "command": "npm test", "description": "Run Node project test suites."})
                targets.append({"target": "npm-build", "command": "npm run build", "description": "Compile Node codebase assets."})
            elif ".NET" in lang:
                targets.append({"target": "dotnet-build", "command": "dotnet build", "description": "Compile C# assemblies."})
                targets.append({"target": "dotnet-test", "command": "dotnet test", "description": "Run dotnet tests."})
                
        if not targets:
            targets.append({"target": "generic-echo", "command": "echo 'No build target found'", "description": "Verify terminal functionality."})
            
        return [types.TextContent(type="text", text=json.dumps(targets, indent=2))]
        
    else:
        raise ValueError(f"Unknown tool: {name}")
