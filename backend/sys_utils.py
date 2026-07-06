import os
import psutil
from typing import Dict, List, Any
import git

def get_system_health() -> Dict[str, Any]:
    """
    Collects real-time OS resource metrics (CPU, RAM, Disk).
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        virtual_mem = psutil.virtual_memory()
        
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_usage,
            "ram_percent": virtual_mem.percent,
            "ram_used_gb": round(virtual_mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(virtual_mem.total / (1024 ** 3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        }
    except Exception as e:
        return {"error": f"Failed to get system health: {str(e)}"}

def get_process_list(limit: int = 15) -> List[Dict[str, Any]]:
    """
    Scans active OS processes, sorting them by memory consumption.
    Identifies chromium-based / dev-related background memory hogs.
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            info = proc.info
            mem_bytes = info['memory_info'].rss if info['memory_info'] else 0
            mem_mb = round(mem_bytes / (1024 * 1024), 2)
            
            # Label dev-related processes
            name = info['name'].lower() if info['name'] else ""
            category = "General"
            if any(k in name for k in ["node", "python", "dotnet", "java", "npm"]):
                category = "Development"
            elif any(k in name for k in ["chrome", "msedge", "brave", "firefox", "chromium"]):
                category = "Browser"
            elif any(k in name for k in ["slack", "discord", "spotify", "teams"]):
                category = "Communication/Media"
                
            processes.append({
                "pid": info['pid'],
                "name": info['name'],
                "memory_mb": mem_mb,
                "cpu_percent": info['cpu_percent'] or 0.0,
                "category": category
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    # Sort processes by memory usage descending
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    return processes[:limit]

def kill_process_by_pid(pid: int) -> Dict[str, Any]:
    """
    Gracefully terminates a running OS process by its PID.
    Protected by safety checks.
    """
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        
        # Prevent terminating critical system services or the python server itself
        current_pid = os.getpid()
        if pid == current_pid:
            return {"success": False, "message": "Cannot terminate VibeOps server process."}
            
        proc.terminate()
        return {"success": True, "message": f"Successfully terminated process '{name}' (PID: {pid})."}
    except psutil.NoSuchProcess:
        return {"success": False, "message": f"Process with PID {pid} not found."}
    except psutil.AccessDenied:
        return {"success": False, "message": f"Access denied to terminate PID {pid}."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def get_git_status(repo_path: str) -> Dict[str, Any]:
    """
    Queries a local Git repository path to analyze uncommitted changes,
    current branch, and git summary status.
    """
    if not os.path.exists(repo_path):
        return {"error": "Specified repository path does not exist."}
        
    try:
        repo = git.Repo(repo_path, search_parent_directories=True)
        # Get actual repository root
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
            
        # Get recent commit summary
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
        return {"error": f"Failed to inspect git repository: {str(e)}"}
