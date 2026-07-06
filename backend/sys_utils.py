import os
import re
import subprocess
import git
from typing import Dict, List, Any

# Regexes for scanning credentials/API keys
SECRET_PATTERNS = {
    "Google API Key": r"AIzaSy[A-Za-z0-9_-]{33}",
    "AWS Access Key": r"\bAKIA[A-Z0-9]{16}\b",
    "AWS Secret Key": r"aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]",
    "GitHub Personal Token": r"\bghp_[A-Za-z0-9_]{36,255}\b",
    "Slack Webhook URL": r"https://hooks\.slack\.com/services/[T][A-Za-z0-9_]{8}/[B][A-Za-z0-9_]{8}/[A-Za-z0-9_]{24}",
    "Generic Token/Key": r"(?i)(password|secret|api_key|token)\s*[:=]\s*['\"][A-Za-z0-9_-]{16,}['\"]"
}

# Directories to skip when scanning codebase
EXCLUDE_DIRS = {".git", "node_modules", "venv", "env", "dist", "build", "__pycache__", ".idea", ".vscode"}

def get_workspace_structure(root_path: str) -> Dict[str, Any]:
    """
    Scans the workspace folder to analyze language profiles and project config files.
    """
    if not os.path.exists(root_path):
        return {"error": "Workspace directory not found."}
        
    project_types = []
    files_list = []
    
    # Simple walk
    for root, dirs, files in os.walk(root_path):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_path)
            files_list.append(rel_path)
            
            # Detect project frameworks/languages based on config files
            if file == "package.json":
                project_types.append("Node.js (npm)")
            elif file in ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"]:
                project_types.append("Python")
            elif file.endswith(".csproj"):
                project_types.append(".NET Core (C#)")
            elif file == "Cargo.toml":
                project_types.append("Rust (Cargo)")
            elif file == "go.mod":
                project_types.append("Go")
                
    return {
        "workspace_root": root_path,
        "languages_detected": list(set(project_types)) if project_types else ["Unknown/Plain Text"],
        "total_files": len(files_list),
        "files_preview": files_list[:25]
    }

def scan_for_secrets(root_path: str) -> List[Dict[str, Any]]:
    """
    Scans the project files for leaked API keys, tokens, or hardcoded passwords.
    """
    findings = []
    if not os.path.exists(root_path):
        return findings
        
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            # Skip binary files, lock files, or config keys
            if file.endswith((".png", ".jpg", ".ico", ".pdf", ".zip", "package-lock.json", "poetry.lock")):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_path)
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        for name, pattern in SECRET_PATTERNS.items():
                            match = re.search(pattern, line)
                            if match:
                                # Mask the key for logs safety
                                raw_secret = match.group(0)
                                masked = raw_secret[:6] + "..." + raw_secret[-4:] if len(raw_secret) > 10 else "******"
                                findings.append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "type": name,
                                    "snippet": line.strip()[:100],
                                    "masked": masked
                                })
            except Exception:
                continue
                
    return findings

def get_git_status(repo_path: str) -> Dict[str, Any]:
    """
    Queries local Git repository details.
    """
    if not os.path.exists(repo_path):
        return {"error": "Workspace directory not found."}
        
    try:
        repo = git.Repo(repo_path, search_parent_directories=True)
        root_path = repo.working_tree_dir
        
        is_dirty = repo.is_dirty(untracked_files=True)
        current_branch = "Detached HEAD"
        try:
            current_branch = repo.active_branch.name
        except TypeError:
            pass
            
        untracked = [item for item in repo.untracked_files]
        changed_files = []
        for diff in repo.index.diff(None):
            changed_files.append({
                "file": diff.a_path,
                "change_type": diff.change_type
            })
            
        recent_commits = []
        for commit in list(repo.iter_commits(max_count=3)):
            recent_commits.append({
                "hexsha": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat()
            })
            
        return {
            "repo_root": root_path,
            "current_branch": current_branch,
            "is_dirty": is_dirty,
            "changed_files": changed_files,
            "untracked_files": untracked,
            "recent_commits": recent_commits
        }
    except git.exc.InvalidGitRepositoryError:
        return {"error": "Not a valid Git repository."}
    except Exception as e:
        return {"error": f"Git inspection failed: {str(e)}"}

# Safe shell command validator
ALLOWED_COMMANDS = {"npm", "pip", "python", "pytest", "cargo", "go", "dotnet", "git", "echo"}

def run_shell_command(command_str: str, cwd: str) -> Dict[str, Any]:
    """
    Executes a shell command after validating it against command injection risks.
    Limits execution to standard developer utilities.
    """
    # 1. Block command dividers
    if any(op in command_str for op in [";", "&&", "||", "|", "`"]):
        return {"success": False, "output": "Command blocked: Chained execution operators are not permitted."}
        
    tokens = command_str.strip().split()
    if not tokens:
        return {"success": False, "output": "Empty command string."}
        
    base_cmd = tokens[0].lower()
    if base_cmd not in ALLOWED_COMMANDS:
        return {"success": False, "output": f"Blocked command base: '{base_cmd}' is not in the permitted developer utility set."}
        
    # Execute safely
    try:
        result = subprocess.run(
            command_str,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30  # Cap command execution at 30 seconds
        )
        output = result.stdout + result.stderr
        return {
            "success": True,
            "output": output or "Command completed with no console outputs.",
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Execution timed out (Limit: 30 seconds)."}
    except Exception as e:
        return {"success": False, "output": f"Execution error: {str(e)}"}
