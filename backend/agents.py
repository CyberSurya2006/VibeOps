import os
from google import genai
from google.genai import types
from .sys_utils import get_system_health, get_process_list, get_git_status

def call_sysadmin(client: genai.Client, user_query: str) -> str:
    """
    Invokes the SysAdmin agent with real-time OS metrics and process list context.
    """
    metrics = get_system_health()
    processes = get_process_list(limit=15)
    
    context = f"""
Current System Health Metrics:
- CPU Usage: {metrics.get('cpu_percent')}%
- RAM Usage: {metrics.get('ram_percent')}% ({metrics.get('ram_used_gb')} GB used / {metrics.get('ram_total_gb')} GB total)
- Disk Usage: {metrics.get('disk_percent')}%

Top 15 Resource-consuming Processes:
{processes}
"""
    
    sys_instruction = """You are the SysAdmin Agent. You specialize in OS resource diagnostics, RAM/VRAM optimizations, and process troubleshooting.
Analyze the system metrics and process list provided in the context to answer the developer's question.
If the developer asks to fix high memory, optimize RAM, or clean up, identify specific processes that are safe to terminate (e.g., idle background browsers, communication helpers, dev databases not in use) and recommend reclaiming memory by specifying their PID.
Safety Rule: Never recommend terminating critical system files (like kernel, system, svchost, or the python process running VibeOps).
Keep responses concise, professional, and action-oriented. Provide process names and PIDs clearly.
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"System Context:\n{context}\n\nDeveloper Query:\n{user_query}")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2
        )
    )
    return response.text

def call_devcopilot(client: genai.Client, user_query: str) -> str:
    """
    Invokes the DevCopilot agent with local workspace Git repository status.
    """
    # Use parent directory as the workspace repo path
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_status = get_git_status(repo_path)
    
    context = f"""
Git Repository Status (Workspace Root: {repo_path}):
- Current Branch: {git_status.get('current_branch', 'N/A')}
- Working Tree Dirty: {git_status.get('is_dirty', False)}
- Uncommitted Files: {git_status.get('changed_files', [])}
- Untracked Files: {git_status.get('untracked_files', [])}
- Recent Commits: {git_status.get('recent_commits', [])}
"""
    
    sys_instruction = """You are the DevCopilot Agent. You specialize in Git repository management, workspace tracking, commit summaries, and code reviews.
Analyze the repository status provided in the context to address the developer's request.
Help the user see what files they are working on, summarize recent changes, or recommend files that should be committed, discarded, or ignored.
Keep responses clear and focused on Git structure and file names. Use markdown formatting.
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Git Context:\n{context}\n\nDeveloper Query:\n{user_query}")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2
        )
    )
    return response.text

def run_multi_agent_system(api_key: str, user_message: str) -> str:
    """
    Orchestrates the multi-agent execution:
    1. Router analyzes query and tags the route.
    2. Coordinator calls appropriate specialists (SysAdmin, DevCopilot).
    3. Coordinator synthesizes final response with safety actions.
    """
    client = genai.Client(api_key=api_key)
    
    coordinator_instruction = """You are the OpsCoordinator, the central dispatcher of the VibeOps Multi-Agent Cockpit.
Your role is to analyze the developer's query and coordinate with your specialized agents:
- SysAdmin: Deals with CPU, RAM, disk, processes, PID management, and memory reclamation.
- DevCopilot: Deals with Git repositories, branches, commits, unstaged files, and code.

Select which agent to invoke based on the query. If the query requires both, invoke both.
To perform the delegation, you will respond with the agent name(s) in XML tags to route the query, like:
<route>sysadmin</route> if it's about system resources, memory, running apps, or PIDs.
<route>devcopilot</route> if it's about Git, branch, changes, diffs, or commits.
<route>both</route> if it covers both areas.
If the query is a general greeting or unrelated to systems/Git, route to <route>general</route>.

Output ONLY the routing tag in your response (e.g. <route>sysadmin</route>). Do not explain your choice.
"""
    
    route_response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[user_message],
        config=types.GenerateContentConfig(
            system_instruction=coordinator_instruction,
            temperature=0.1
        )
    )
    
    route_text = route_response.text.strip().lower()
    
    sys_response = ""
    dev_response = ""
    
    # Run agent workers based on route decision
    if "sysadmin" in route_text or "both" in route_text:
        sys_response = call_sysadmin(client, user_message)
        
    if "devcopilot" in route_text or "both" in route_text:
        dev_response = call_devcopilot(client, user_message)
        
    # Synthesis phase: Coordinator combines results
    synthesis_instruction = """You are the OpsCoordinator. Synthesize the findings from your specialist agents into a final response for the developer.
Make sure to present system suggestions, PID actions, or Git status details cleanly in a futuristic, helper tone.
If the SysAdmin agent recommended terminating a process, include a clear recommendation block at the bottom of your response in the format:
[RECOMMENDED_ACTION:TERMINATE:PID:PROCESS_NAME] (e.g., [RECOMMENDED_ACTION:TERMINATE:1234:chrome.exe]) so the frontend dashboard can render a safe action approval button.
If multiple processes are suggested, you can output multiple such action tags.
Use rich markdown, headers, lists, and bold text. Ensure the developer gets clear, actionable information.
"""
    
    synthesis_prompt = f"""
Developer original query: {user_message}

SysAdmin Agent report:
{sys_response or "Not consulted."}

DevCopilot Agent report:
{dev_response or "Not consulted."}
"""
    
    final_response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[synthesis_prompt],
        config=types.GenerateContentConfig(
            system_instruction=synthesis_instruction,
            temperature=0.4
        )
    )
    
    return final_response.text
