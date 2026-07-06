const BACKEND_URL = 'http://localhost:8000';
let pollInterval = null;
let gitPollInterval = null;

// State management
const state = {
    apiKey: localStorage.getItem('vibeops_gemini_key') || '',
    activeView: 'dashboard',
    system: {
        cpu: 0,
        ram: 0,
        ramUsed: 0,
        ramTotal: 0,
        disk: 0
    }
};

// DOM Elements
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
    
    // System Dials & Meta
    cpuRing: document.getElementById('cpu-ring'),
    cpuVal: document.getElementById('cpu-val'),
    ramRing: document.getElementById('ram-ring'),
    ramVal: document.getElementById('ram-val'),
    ramUsed: document.getElementById('ram-used'),
    ramTotal: document.getElementById('ram-total'),
    diskPercent: document.getElementById('disk-percent'),
    
    // Lists & Tables
    processSummaryBody: document.getElementById('process-summary-body'),
    processesTableBody: document.getElementById('processes-table-body'),
    btnRefreshProcesses: document.getElementById('btn-refresh-processes'),
    
    // Git Panel
    gitSummaryContent: document.getElementById('git-summary-content'),
    gitPath: document.getElementById('git-path'),
    gitBranch: document.getElementById('git-branch'),
    gitDirtyStatus: document.getElementById('git-dirty-status'),
    gitChangesList: document.getElementById('git-changes-list'),
    gitUntrackedList: document.getElementById('git-untracked-list'),
    gitCommitsTimeline: document.getElementById('git-commits-timeline'),
    
    // Chat Agent
    chatForm: document.getElementById('chat-form'),
    chatInput: document.getElementById('chat-input'),
    chatMessagesBox: document.getElementById('chat-messages-box'),
    suggestBtns: document.querySelectorAll('.suggest-btn'),
    
    // Notification
    toast: document.getElementById('toast')
};

// Initialization
function init() {
    setupEventListeners();
    checkApiKey();
    checkBackendHealth();
    
    // Start polling system metrics
    updateSystemMetrics();
    pollInterval = setInterval(updateSystemMetrics, 3000);
    
    // Start polling Git repo status
    updateGitStatus();
    gitPollInterval = setInterval(updateGitStatus, 10000);
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

    // Process refresh button
    elements.btnRefreshProcesses.addEventListener('click', () => {
        showToast('Refreshing process metrics...');
        updateSystemMetrics();
    });
}

// Router
function switchView(viewName) {
    state.activeView = viewName;
    
    // Update active nav class
    elements.navLinks.forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) {
            item.classList.add('active');
        }
    });

    // Toggle views
    elements.views.forEach(section => {
        section.classList.remove('active');
        if (section.id === `view-${viewName}`) {
            section.classList.add('active');
        }
    });
    
    // Context-specific actions
    if (viewName === 'processes') {
        updateSystemMetrics();
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

// Backend service connectivity check
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
        elements.backendStatus.textContent = 'Backend Offline (Run start-vibeops.bat)';
    }
}

// Poll OS metrics
async function updateSystemMetrics() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/system-stats`);
        const data = await response.json();
        if (data.status === 'success') {
            const h = data.health;
            
            // Update dials
            setRingProgress(elements.cpuRing, h.cpu_percent);
            elements.cpuVal.textContent = `${Math.round(h.cpu_percent)}%`;
            
            setRingProgress(elements.ramRing, h.ram_percent);
            elements.ramVal.textContent = `${Math.round(h.ram_percent)}%`;
            
            // Update labels
            elements.ramUsed.textContent = h.ram_used_gb.toFixed(2);
            elements.ramTotal.textContent = h.ram_total_gb.toFixed(2);
            elements.diskPercent.textContent = `${h.disk_percent}%`;
            
            // Update process displays
            renderProcesses(data.processes);
        }
    } catch (err) {
        console.error('Failed to fetch system stats:', err);
    }
}

// Update SVG ring dashes
function setRingProgress(circle, percent) {
    const radius = circle.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    circle.style.strokeDasharray = `${circumference} ${circumference}`;
    const offset = circumference - (percent / 100 * circumference);
    circle.style.strokeDashoffset = offset;
}

// Render process tables
function renderProcesses(processes) {
    // 1. Dashboard top 5 processes
    elements.processSummaryBody.innerHTML = '';
    processes.slice(0, 5).forEach(proc => {
        const tr = document.createElement('tr');
        let classTag = 'tag-cyan';
        if (proc.category === 'Development') classTag = 'tag-violet';
        if (proc.category === 'General') classTag = '';
        
        tr.innerHTML = `
            <td><strong>${proc.name}</strong></td>
            <td>${proc.memory_mb.toFixed(1)} MB</td>
            <td><span class="tag ${classTag}">${proc.category}</span></td>
            <td><button class="btn-terminate" onclick="requestProcessKill(${proc.pid}, '${proc.name}')">Kill</button></td>
        `;
        elements.processSummaryBody.appendChild(tr);
    });

    // 2. Full table process manager view
    elements.processesTableBody.innerHTML = '';
    processes.forEach(proc => {
        const tr = document.createElement('tr');
        let classTag = 'tag-cyan';
        if (proc.category === 'Development') classTag = 'tag-violet';
        if (proc.category === 'General') classTag = '';
        
        tr.innerHTML = `
            <td><code>${proc.pid}</code></td>
            <td><strong>${proc.name}</strong></td>
            <td><code>${proc.memory_mb.toFixed(1)} MB</code></td>
            <td><code>${proc.cpu_percent.toFixed(1)}%</code></td>
            <td><span class="tag ${classTag}">${proc.category}</span></td>
            <td><button class="btn-terminate" onclick="requestProcessKill(${proc.pid}, '${proc.name}')"><i class="ph ph-trash"></i> Terminate</button></td>
        `;
        elements.processesTableBody.appendChild(tr);
    });
}

// Action executor trigger (Safety Gate approval)
async function requestProcessKill(pid, name) {
    const confirmKill = confirm(`[Security Gate] Are you sure you want to terminate process "${name}" (PID: ${pid})?`);
    if (confirmKill) {
        await executeKill(pid);
    }
}

async function executeKill(pid) {
    try {
        const response = await fetch(`${BACKEND_URL}/api/execute-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pid })
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast(data.message);
            updateSystemMetrics();
        } else {
            showToast(`Error: ${data.message}`);
        }
    } catch (err) {
        showToast('Failed to connect to backend execution gate.');
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
            
            // Dashboard Summary Card
            const dirtyLabel = git.is_dirty ? '<span class="git-status-modified">Uncommitted Changes</span>' : '<span class="tag-green">Clean</span>';
            elements.gitSummaryContent.innerHTML = `
                <div class="git-meta-details" style="margin-bottom:0; padding-bottom:0; border:none;">
                    <div class="meta-item"><span>Branch:</span><span class="branch-tag"><i class="ph ph-git-branch"></i> ${git.current_branch}</span></div>
                    <div class="meta-item"><span>Status:</span><span>${dirtyLabel}</span></div>
                    <div class="meta-item"><span>Modified Files:</span><span>${git.changed_files.length} files</span></div>
                </div>
            `;
            
            // Full Git Status page
            elements.gitPath.textContent = git.repo_root;
            elements.gitBranch.textContent = git.current_branch;
            elements.gitDirtyStatus.innerHTML = git.is_dirty ? '<span class="git-status-modified">Modified Workspace (Dirty)</span>' : '<span class="tag-green" style="padding:0.25rem 0.5rem; border-radius:4px;">Workspace Clean</span>';
            
            // Changed Files List
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
            
            // Untracked Files List
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
            
            // Timeline Commits
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
    
    // Add user message to UI
    appendMessage(query, 'user');
    elements.chatInput.value = '';
    
    // Add typing indicator
    const typingIndicator = appendMessage('<i class="ph-bold ph-spinner spinner"></i> Thinking...', 'assistant typing');
    
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
        
        // Remove typing indicator
        typingIndicator.remove();
        
        if (data.status === 'success') {
            appendMessage(data.reply, 'assistant');
        } else {
            appendMessage(`Error: ${data.detail || 'Failed to generate agent response.'}`, 'assistant');
        }
    } catch (err) {
        typingIndicator.remove();
        appendMessage('Error: Failed to connect to the backend agent server. Verify it is running.', 'assistant');
    }
}

function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    if (sender.includes('user')) {
        messageDiv.textContent = text;
    } else {
        // Parse basic markdown formatting and custom action tags
        let parsedHtml = parseMarkdown(text);
        
        // Parse recommendation actions: [RECOMMENDED_ACTION:TERMINATE:PID:NAME]
        const actionPattern = /\[RECOMMENDED_ACTION:TERMINATE:(\d+):([^\]]+)\]/g;
        
        parsedHtml = parsedHtml.replace(actionPattern, (match, pid, name) => {
            return `
                <div class="recommendation-action-block">
                    <div class="rec-details">
                        <h4><i class="ph-fill ph-warning-circle"></i> Clean memory leak: ${name}</h4>
                        <p>Terminate Process PID ${pid} to optimize memory.</p>
                    </div>
                    <button class="btn-action-execute" onclick="executeKill(${pid})">Approve Action</button>
                </div>
            `;
        });
        
        messageDiv.innerHTML = parsedHtml;
    }
    
    elements.chatMessagesBox.appendChild(messageDiv);
    
    // Scroll chat window to bottom
    elements.chatMessagesBox.scrollTop = elements.chatMessagesBox.scrollHeight;
    
    return messageDiv;
}

// Simple markdown parsing helper
function parseMarkdown(text) {
    let html = text;
    
    // Escape HTML tags to prevent cross-site scripting/injection
    html = html.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    
    // Restore routing tags or recommendation tags that we want to keep
    html = html.replace(/&lt;route&gt;/g, "<route>").replace(/&lt;\/route&gt;/g, "</route>");
    
    // Parse bold code
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Parse italic code
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Parse inline code blocks
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Parse line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// Toast Notification
function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.remove('hidden');
    
    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 4000);
}

// Global scope bindings for inline event triggers
window.requestProcessKill = requestProcessKill;
window.executeKill = executeKill;

// Run
document.addEventListener('DOMContentLoaded', init);
