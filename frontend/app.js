const BACKEND_URL = 'http://localhost:8000';
let statusPoll = null;
let gitPoll = null;

const state = {
    apiKey: localStorage.getItem('vibeops_gemini_key') || '',
    activeView: 'dashboard',
    workspace: {
        languages: [],
        totalFiles: 0,
        filesPreview: [],
        secrets: []
    }
};

const elements = {
    navLinks: document.querySelectorAll('.nav-links li'),
    views: document.querySelectorAll('.view-section'),
    backendStatus: document.getElementById('backend-status'),
    statusDot: document.querySelector('.indicator-dot'),
    keyBadge: document.getElementById('key-badge'),
    keyBadgeText: document.getElementById('key-badge-text'),
    
    // Settings
    formSettings: document.getElementById('form-settings'),
    settingsKey: document.getElementById('settings-key'),
    
    // Workspace profile
    frameworksVal: document.getElementById('frameworks-val'),
    filesCount: document.getElementById('files-count'),
    filesPreviewList: document.getElementById('files-preview-list'),
    
    // Secrets
    secretsSummary: document.getElementById('secrets-summary'),
    secretsTableBody: document.getElementById('secrets-table-body'),
    btnRunScan: document.getElementById('btn-run-scan'),
    
    // Git
    gitSummaryContent: document.getElementById('git-summary-content'),
    gitPath: document.getElementById('git-path'),
    gitBranch: document.getElementById('git-branch'),
    gitDirtyStatus: document.getElementById('git-dirty-status'),
    gitChangesList: document.getElementById('git-changes-list'),
    gitUntrackedList: document.getElementById('git-untracked-list'),
    gitCommitsTimeline: document.getElementById('git-commits-timeline'),
    
    // Agent Console
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    chatMessagesBox: document.getElementById('chat-messages-box'),
    suggestBtns: document.querySelectorAll('.suggest-btn'),
    
    toast: document.getElementById('toast')
};

function init() {
    setupEventListeners();
    checkApiKey();
    checkBackendHealth();
    
    // Initial fetches
    updateWorkspaceStatus();
    updateGitStatus();
    
    // Start polling loops
    statusPoll = setInterval(updateWorkspaceStatus, 5000);
    gitPoll = setInterval(updateGitStatus, 10000);
}

function setupEventListeners() {
    // Navigation / View Switching
    elements.navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const viewName = link.dataset.view;
            if (!viewName) return;
            switchView(viewName);
        });
    });

    // Form settings submission
    elements.formSettings.addEventListener('submit', (e) => {
        e.preventDefault();
        const key = elements.settingsKey.value.trim();
        if (key) {
            localStorage.setItem('vibeops_gemini_key', key);
            state.apiKey = key;
            showToast('Gemini API Key saved successfully!');
            checkApiKey();
            switchView('dashboard');
        }
    });

    // Chat submit
    elements.chatForm.addEventListener('submit', handleChatSubmit);

    // Suggestion chips
    elements.suggestBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.dataset.prompt;
            switchView('agent');
            elements.chatInput.value = prompt;
            elements.chatForm.dispatchEvent(new Event('submit'));
        });
    });

    // Refresh secrets scanner
    elements.btnRunScan.addEventListener('click', () => {
        showToast('Running comprehensive codebase secrets check...');
        updateWorkspaceStatus();
    });
}

// Routing
function switchView(viewName) {
    state.activeView = viewName;
    
    elements.navLinks.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) {
            item.classList.add('active');
        }
    });

    elements.views.forEach(section => {
        section.classList.remove('active');
        if (section.id === `view-${viewName}`) {
            section.classList.add('active');
        }
    });
    
    if (viewName === 'security') {
        updateWorkspaceStatus();
    } else if (viewName === 'git') {
        updateGitStatus();
    }
}

// API Key Logic
function checkApiKey() {
    if (state.apiKey) {
        elements.keyBadge.classList.add('active');
        elements.keyBadgeText.textContent = 'API Key Set';
        elements.settingsKey.value = state.apiKey;
    } else {
        elements.keyBadge.classList.remove('active');
        elements.keyBadgeText.textContent = 'API Key Missing';
    }
}

// Backend Health status
async function checkBackendHealth() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/health`);
        const data = await response.json();
        if (data.status === 'online') {
            elements.statusDot.className = 'indicator-dot online';
            elements.backendStatus.textContent = 'Agent Backend Online';
        }
    } catch (err) {
        elements.statusDot.className = 'indicator-dot offline';
        elements.backendStatus.textContent = 'Backend Offline';
    }
}

// Poll workspace configuration and secrets leaks
async function updateWorkspaceStatus() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/workspace-status`);
        const data = await response.json();
        if (data.status === 'success') {
            const struct = data.structure;
            
            // Render languages profile
            elements.frameworksVal.textContent = struct.languages_detected.join(', ') || 'Plain Codebase';
            elements.filesCount.textContent = struct.total_files;
            
            // Populate file preview list
            elements.filesPreviewList.innerHTML = '';
            struct.files_preview.forEach(file => {
                const li = document.createElement('li');
                li.textContent = file;
                elements.filesPreviewList.appendChild(li);
            });
            
            // Populate secrets summary and details
            renderSecrets(data.secrets_count, data.secrets);
        }
    } catch (err) {
        console.error('Failed to query workspace structure:', err);
    }
}

// Render secrets audit tables
function renderSecrets(count, secrets) {
    if (count === 0) {
        elements.secretsSummary.innerHTML = `
            <p class="tag-green" style="padding: 0.8rem; border-radius: 8px; text-align: center; font-weight: 500;">
                <i class="ph ph-check-circle" style="font-size: 1.2rem; vertical-align: middle;"></i> Clean: No leaked credentials detected.
            </p>
        `;
        elements.secretsTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No hardcoded secrets found. Your codebase is secure!</td></tr>`;
    } else {
        elements.secretsSummary.innerHTML = `
            <p class="tag-red" style="padding: 0.8rem; border-radius: 8px; text-align: center; font-weight: 600;">
                <i class="ph ph-warning-octagon" style="font-size: 1.2rem; vertical-align: middle;"></i> Warn: Found ${count} leaked API keys!
            </p>
        `;
        
        elements.secretsTableBody.innerHTML = '';
        secrets.forEach(sec => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code>${sec.file}</code></td>
                <td><code>Line ${sec.line}</code></td>
                <td><span class="tag tag-red">${sec.type}</span></td>
                <td><code>${sec.masked}</code></td>
            `;
            elements.secretsTableBody.appendChild(tr);
        });
    }
}

// Action executor trigger (Safety command execution gate)
async function runSystemCommand(commandBtn, commandString) {
    commandBtn.disabled = true;
    commandBtn.textContent = 'Executing...';
    commandBtn.style.boxShadow = '0 0 15px var(--amber)';
    
    // Add logs window to chat stream
    const outputLogBox = document.createElement('div');
    outputLogBox.style.cssText = 'background:#000; border: 1px solid var(--border-glass); border-radius: 8px; padding: 1rem; margin-top: 0.5rem; font-family: "JetBrains Mono", monospace; font-size: 0.85rem; max-height: 200px; overflow-y: auto; white-space: pre-wrap; color: #fff;';
    outputLogBox.textContent = 'Connecting terminal shell...';
    commandBtn.parentElement.appendChild(outputLogBox);

    try {
        const response = await fetch(`${BACKEND_URL}/api/run-command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: commandString })
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            commandBtn.textContent = 'Success!';
            commandBtn.style.background = 'var(--green)';
            commandBtn.style.boxShadow = 'none';
            outputLogBox.textContent = data.output;
            showToast('Terminal command executed successfully!');
        } else {
            commandBtn.textContent = 'Failed';
            commandBtn.style.background = 'var(--red)';
            outputLogBox.textContent = `Error: ${data.detail}`;
            showToast('Command execution failed.');
        }
    } catch (err) {
        commandBtn.textContent = 'Error';
        commandBtn.style.background = 'var(--red)';
        outputLogBox.textContent = 'Failed to connect to backend execution gate.';
    }
}

// Git Status update
async function updateGitStatus() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/git-status`);
        const data = await response.json();
        if (data.status === 'success') {
            const git = data.git;
            
            if (git.error) {
                elements.gitSummaryContent.innerHTML = `<p class="git-status-deleted"><i class="ph ph-warning"></i> Git Workspace Not Detected: ${git.error}</p>`;
                return;
            }
            
            // Dashboard summary widget
            const dirtyLabel = git.is_dirty ? '<span class="git-status-modified">Uncommitted Changes</span>' : '<span class="tag-green">Clean</span>';
            elements.gitSummaryContent.innerHTML = `
                <div class="git-meta-details" style="margin-bottom:0; padding-bottom:0; border:none;">
                    <div class="meta-item"><span>Branch:</span><span class="branch-tag"><i class="ph ph-git-branch"></i> ${git.current_branch}</span></div>
                    <div class="meta-item"><span>Status:</span><span>${dirtyLabel}</span></div>
                    <div class="meta-item"><span>Modified Files:</span><span>${git.changed_files.length} files</span></div>
                </div>
            `;
            
            // Full Git Status page view
            elements.gitPath.textContent = git.repo_root;
            elements.gitBranch.textContent = git.current_branch;
            elements.gitDirtyStatus.innerHTML = git.is_dirty ? '<span class="git-status-modified">Modified Workspace (Dirty)</span>' : '<span class="tag-green" style="padding:0.25rem 0.5rem; border-radius:4px;">Workspace Clean</span>';
            
            // Modified list
            elements.gitChangesList.innerHTML = '';
            if (git.changed_files.length === 0) {
                elements.gitChangesList.innerHTML = '<li class="git-status-untracked">No changed files.</li>';
            } else {
                git.changed_files.forEach(f => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${f.file}</span><span class="git-status-modified">[${f.change_type}]</span>`;
                    elements.gitChangesList.appendChild(li);
                });
            }
            
            // Untracked list
            elements.gitUntrackedList.innerHTML = '';
            if (git.untracked_files.length === 0) {
                elements.gitUntrackedList.innerHTML = '<li class="git-status-untracked">No untracked files.</li>';
            } else {
                git.untracked_files.forEach(file => {
                    const li = document.createElement('li');
                    li.innerHTML = `<span>${file}</span><span class="git-status-untracked">[New]</span>`;
                    elements.gitUntrackedList.appendChild(li);
                });
            }
            
            // Timelines
            elements.gitCommitsTimeline.innerHTML = '';
            if (git.recent_commits.length === 0) {
                elements.gitCommitsTimeline.innerHTML = '<p class="git-status-untracked">No commits found.</p>';
            } else {
                git.recent_commits.forEach(commit => {
                    const item = document.createElement('div');
                    item.className = 'timeline-item';
                    const commitDate = new Date(commit.date).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    item.innerHTML = `
                        <div class="commit-meta">
                            <code>${commit.hexsha}</code> &bull; <span class="commit-author">${commit.author}</span> &bull; ${commitDate}
                        </div>
                        <div class="commit-msg">${commit.message}</div>
                    `;
                    elements.gitCommitsTimeline.appendChild(item);
                });
            }
        }
    } catch (err) {
        console.error('Failed to fetch Git status:', err);
    }
}

// Agent Chat handling
async function handleChatSubmit(e) {
    e.preventDefault();
    
    if (!state.apiKey) {
        showToast('Please set your Gemini API Key in Settings first!');
        switchView('settings');
        return;
    }
    
    const query = elements.chatInput.value.trim();
    if (!query) return;
    
    appendMessage(query, 'user');
    elements.chatInput.value = '';
    
    const typingIndicator = appendMessage('<i class="ph-bold ph-spinner spinner"></i> Consulting coordinator...', 'assistant typing');
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Gemini-API-Key': state.apiKey
            },
            body: JSON.stringify({ message: query })
        });
        
        const data = await response.json();
        typingIndicator.remove();
        
        if (data.status === 'success') {
            appendMessage(data.reply, 'assistant');
        } else {
            appendMessage(`Error: ${data.detail || 'Failed to complete agent execution.'}`, 'assistant');
        }
    } catch (err) {
        typingIndicator.remove();
        appendMessage('Error: Failed to connect to the backend agent server. Verify it is online.', 'assistant');
    }
}

function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    if (sender.includes('user')) {
        messageDiv.textContent = text;
    } else {
        let parsedHtml = parseMarkdown(text);
        
        // Parse execution actions: [RECOMMENDED_ACTION:RUN_COMMAND:SHELL_COMMAND]
        const actionPattern = /\[RECOMMENDED_ACTION:RUN_COMMAND:([^\]]+)\]/g;
        
        parsedHtml = parsedHtml.replace(actionPattern, (match, cmd) => {
            const commandEscaped = cmd.replace(/"/g, '&quot;');
            return `
                <div class="recommendation-action-block">
                    <div class="rec-details">
                        <h4><i class="ph-fill ph-warning-circle"></i> VibeOps Shell Command Gate</h4>
                        <p>Approve execution: <code>${cmd}</code></p>
                    </div>
                    <button class="btn-action-execute" onclick="runSystemCommand(this, '${commandEscaped}')">Approve & Run</button>
                </div>
            `;
        });
        
        messageDiv.innerHTML = parsedHtml;
    }
    
    elements.chatMessagesBox.appendChild(messageDiv);
    elements.chatMessagesBox.scrollTop = elements.chatMessagesBox.scrollHeight;
    
    return messageDiv;
}

function parseMarkdown(text) {
    let html = text;
    html = html.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    html = html.replace(/&lt;route&gt;/g, "<route>").replace(/&lt;\/route&gt;/g, "</route>");
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.remove('hidden');
    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 4500);
}

// Binds execution function globally for button clicks
window.runSystemCommand = runSystemCommand;

document.addEventListener('DOMContentLoaded', init);
