import os
import json
from google import genai
from google.genai import types
from .sys_utils import get_workspace_structure, get_git_status, scan_for_secrets

def call_buildtest(client: genai.Client, user_query: str) -> str:
    """
    Invokes the BuildTest agent with workspace file targets.
    Formulates safe compiler or testing terminal commands.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    structure = get_workspace_structure(root_path)
    
    context = f"""
Workspace Directory Structure:
- Detected Language Profiles: {structure.get('languages_detected', [])}
- Total files: {structure.get('total_files', 0)}
- Files preview: {structure.get('files_preview', [])}
"""
    
    sys_instruction = """You are the BuildTest Agent. You specialize in build pipelines, compilers, and test orchestration.
Examine the workspace files provided in the context to answer the query.
If the developer asks to run tests, build the project, or compile, construct the appropriate terminal command (e.g. pytest, npm test, cargo test, dotnet build) and suggest it.
Rules: Recommending commands must use exactly one of the supported base tools: npm, pip, python, pytest, cargo, go, dotnet, git, echo. Never suggest command chaining or pipelines using dividers.
Explain briefly what the command will do.
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Workspace Context:\n{context}\n\nDeveloper Query:\n{user_query}")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2
        )
    )
    return response.text

def call_secretshield(client: genai.Client, user_query: str) -> str:
    """
    Invokes the SecretShield agent to scan for credentials leaks.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = scan_for_secrets(root_path)
    
    context = f"""
Codebase Secret Scan Findings:
{json.dumps(findings, indent=2)}
"""
    
    sys_instruction = """You are the SecretShield Agent. You specialize in scanning codebases for leaked credentials, passwords, and hardcoded API tokens.
Analyze the scan findings provided in the context.
Report any leaked items (Google API Keys, AWS secrets, GitHub tokens, generic secrets).
List the file name and line number, but always use the 'masked' token format to avoid displaying the secret in logs.
If no leaks are found, report that the codebase is clean and secure.
"""
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"Scan Context:\n{context}\n\nDeveloper Query:\n{user_query}")
                ]
            )
        ],
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2
        )
    )
    return response.text

def call_gitops(client: genai.Client, user_query: str) -> str:
    """
    Invokes the GitOps agent to review code modifications.
    """
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_status = get_git_status(root_path)
    
    context = f"""
Git Repository Status:
- Branch: {git_status.get('current_branch', 'N/A')}
- Dirty: {git_status.get('is_dirty', False)}
- Uncommitted changes: {git_status.get('changed_files', [])}
- Untracked files: {git_status.get('untracked_files', [])}
- Recent history: {git_status.get('recent_commits', [])}
"""
    
    sys_instruction = """You are the GitOps Agent. You specialize in git commands, committing code, and tracking repository changes.
Analyze the git repository status provided in the context to address the developer's question.
If they ask to summarize work, check changes, or compile a commit, write a descriptive, semantic git commit message, list changed files, and recommend staging actions.
Use standard git workflows. Keep responses clear and formatted in markdown.
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
    Orchestrates the multi-agent automation workspace cockpit:
    1. Coordinator routes the request via route tags.
    2. Invokes BuildTest, SecretShield, or GitOps.
    3. Coordinator synthesizes final response with execution blocks.
    """
    client = genai.Client(api_key=api_key)
    
    coordinator_instruction = """You are the OpsCoordinator, the dispatcher of the VibeOps Development Cockpit.
Analyze the developer query and delegate to specialists:
- BuildTest: Compile code, run test suites, executing build targets.
- SecretShield: Scanning files for API keys, passwords, leaked credentials, security checks.
- GitOps: Git diffs, commits, branches, modified files.

Select which agent to invoke. You must respond with the agent name in XML tags:
<route>buildtest</route> if it's about building, tests, or compilers.
<route>secretshield</route> if it's about secrets, keys, or security audits.
<route>gitops</route> if it's about git branches, commits, staging, or changes.
<route>both</route> if it covers multiple topics.
<route>general</route> if it's unrelated to coding tasks.

Output ONLY the route XML tag in your response.
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
    
    build_resp = ""
    secret_resp = ""
    git_resp = ""
    
    # Trigger appropriate workers
    if "buildtest" in route_text or "both" in route_text:
        build_resp = call_buildtest(client, user_message)
    if "secretshield" in route_text or "both" in route_text:
        secret_resp = call_secretshield(client, user_message)
    if "gitops" in route_text or "both" in route_text:
        git_resp = call_gitops(client, user_message)
        
    # Synthesis phase
    synthesis_instruction = """You are the OpsCoordinator. Synthesize reports from your worker agents.
Always maintain a helpful developer persona.
If a worker recommended running a build/test or git command, you MUST include a clean terminal run action tag at the bottom of your response in the format:
[RECOMMENDED_ACTION:RUN_COMMAND:SHELL_COMMAND] (e.g. [RECOMMENDED_ACTION:RUN_COMMAND:pytest] or [RECOMMENDED_ACTION:RUN_COMMAND:npm test]) so the frontend dashboard can render a command execution button.
Ensure the command matches our allowed set: npm, pip, python, pytest, cargo, go, dotnet, git, echo.
Use rich markdown formatting, headers, tables, and lists.
"""
    
    synthesis_prompt = f"""
Developer Query: {user_message}

BuildTest Report:
{build_resp or "Not consulted."}

SecretShield Report:
{secret_resp or "Not consulted."}

GitOps Report:
{git_resp or "Not consulted."}
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
