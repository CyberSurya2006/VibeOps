# 🎬 VibeOps Demo Walkthrough Storyboard

This interactive storyboard walks you through a complete, step-by-step demonstration of the **VibeOps Cockpit** in action. You can use these steps and images to structure your YouTube demo video!

````carousel
### 🖥️ Step 1: The Dev Cockpit Dashboard
This is the main landing dashboard of the VibeOps cockpit. It displays real-time system metrics (CPU, RAM, Disk load) and a table of the top memory-hogging processes sorted by RSS usage.

![VibeOps Dashboard](file:///C:/Users/Suryadeep/.gemini/antigravity/brain/5aa821bc-4dd5-4368-bb6a-8b6547aa6c61/vibeops_thumbnail_1783354306809.png)

*   **Key Highlights to Pitch**: Real-time canvas updating, glassmorphism card widgets, neon status indicator connecting to local FastAPI.
<!-- slide -->
### 💬 Step 2: Querying the Multi-Agent Console
The developer opens the Agent Console and inputs: *"Clean up my system memory"*. The coordinator agent routes the request to the `SysAdmin` specialist.

![VibeOps Agent Chat Console](file:///C:/Users/Suryadeep/.gemini/antigravity/brain/5aa821bc-4dd5-4368-bb6a-8b6547aa6c61/vibeops_agent_chat_1783355373783.png)

*   **Key Highlights to Pitch**: Multi-agent orchestration, contextual input feeds (injecting process list into LLM prompt via MCP server).
<!-- slide -->
### 🔒 Step 3: Human-in-the-Loop Execution
The SysAdmin agent identifies chrome helper processes as safe to terminate and returns action tags. The frontend captures this and renders the glowing **"Approve Action"** button.

```html
<!-- Interactive Safety Gate Element rendered in UI -->
<div class="recommendation-action-block">
    <div class="rec-details">
        <h4><i class="ph-fill ph-warning-circle"></i> Clean memory leak: chrome.exe</h4>
        <p>Terminate Process PID 1234 to optimize memory.</p>
    </div>
    <button class="btn-action-execute" onclick="executeKill(1234)">Approve Action</button>
</div>
```

*   **Key Highlights to Pitch**: **Security Gate**. The agent suggests action but requires the user's manual approval. Once clicked, it executes process termination securely via FastAPI.
<!-- slide -->
### 📂 Step 4: Workspace Git Audit
The developer switches to the **Workspace Git** view to check project repository details. The `DevCopilot` specialist scans uncommitted changes, modified paths, and prints commit history.

![VibeOps Git Status View](file:///C:/Users/Suryadeep/.gemini/antigravity/brain/5aa821bc-4dd5-4368-bb6a-8b6547aa6c61/vibeops_git_status_1783355390362.png)

*   **Key Highlights to Pitch**: Model Context Protocol (MCP) Git status resource, recent commit timelines.
<!-- slide -->
### ⌨️ Step 5: Standalone Terminal Agent Skill (CLI)
Developers can perform local system scans directly from their favorite code terminal without running the server dashboard:

```bash
$ set GEMINI_API_KEY=AIzaSy...
$ python vibeops-cli.py "Summarize my active uncommitted files"

Routing query to VibeOps agents: 'Summarize my active uncommitted files'
Hold on while the agents inspect your workspace...

=== RESPONSE (via Standalone Local Agents) ===
### Git Repository Analysis
You are currently on branch `main`. The workspace has **1 modified file**:
*   `backend/agents.py` (Modified)

*Recommendation:* Commit these changes before pulling updates from upstream.
```

*   **Key Highlights to Pitch**: Standalone console skill, seamless offline fallback, environment variable integration.
````
