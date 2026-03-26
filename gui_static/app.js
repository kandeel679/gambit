document.addEventListener('DOMContentLoaded', () => {
    // Nav Elements
    const navItems = document.querySelectorAll('.nav-item');
    const dashboardView = document.getElementById('dashboardView');
    const analyticsView = document.getElementById('analyticsView');
    const analyticsSidebar = document.getElementById('analyticsSidebar');

    // Form Elements
    const configForm = document.getElementById('configForm');
    const llmProvider = document.getElementById('llmProvider');
    const ollamaFields = document.getElementById('ollamaFields');
    const launchBtn = document.getElementById('launchBtn');

    // Status Elements
    const statusSection = document.getElementById('statusSection');
    const statusConsole = document.getElementById('statusConsole');
    const progressBar = document.getElementById('progressBar');

    // Live Logs Elements
    const liveLogsSection = document.getElementById('liveLogsSection');
    const liveLogsConsole = document.getElementById('liveLogsConsole');

    // Log Elements
    const logList = document.getElementById('logList');
    const contentBody = document.getElementById('analyticsView'); // Re-using analyticsView for logs
    const currentSelection = document.getElementById('currentSelection');
    const searchInput = document.getElementById('searchInput');
    const refreshBtn = document.getElementById('refreshBtn');
    const connStatus = document.getElementById('connStatus');

    let allLogs = [];
    let currentLog = null;
    let isDeploying = false;
    let liveLogsSince = 0;
    let liveLogsPolling = false;

    // View Switching Logic
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const view = item.getAttribute('data-view');
            
            // Update Nav UI
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            // Toggle Views
            if (view === 'dashboard') {
                dashboardView.classList.remove('hidden');
                analyticsView.classList.add('hidden');
                analyticsSidebar.classList.add('hidden');
                currentSelection.textContent = "Honeypot Orchestration Dashboard";
            } else {
                dashboardView.classList.add('hidden');
                analyticsView.classList.remove('hidden');
                analyticsSidebar.classList.remove('hidden');
                currentSelection.textContent = "Select a session to view analysis";
                fetchLogList();
            }
        });
    });

    // LLM Provider Toggle
    llmProvider.addEventListener('change', () => {
        if (llmProvider.value === 'ollama') {
            ollamaFields.classList.remove('hidden');
        } else {
            ollamaFields.classList.add('hidden');
        }
    });

    // Fetch Current Config
    async function loadConfig() {
        try {
            const res = await fetch('/api/config');
            if (res.ok) {
                const config = await res.json();
                for (const [key, value] of Object.entries(config)) {
                    const input = configForm.querySelector(`[name="${key}"]`);
                    if (input) input.value = value;
                }
                // Trigger LLM change UI
                llmProvider.dispatchEvent(new Event('change'));
            }
        } catch (e) { console.error("Failed to load config", e); }
    }

    // Launch Deployment
    configForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (isDeploying) return;

        const formData = new FormData(configForm);
        const data = Object.fromEntries(formData.entries());

        isDeploying = true;
        launchBtn.disabled = true;
        launchBtn.innerHTML = '<span class="loading-spinner"></span> Deploying...';
        statusSection.classList.remove('hidden');
        liveLogsSection.classList.remove('hidden');
        statusConsole.innerHTML = '<div class="console-line system">Initializing Orbit...</div>';
        liveLogsConsole.innerHTML = '<div class="console-line system">Connecting to live log stream...</div>';
        liveLogsSince = 0;
        progressBar.style.width = '5%';

        try {
            const response = await fetch('/api/launch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('Launch failed');
            
            // Start polling for status and live logs
            pollStatus();
            startLiveLogPolling();
        } catch (error) {
            addConsoleLine("Launch failed: " + error.message, "error");
            isDeploying = false;
            launchBtn.disabled = false;
            launchBtn.textContent = '🚀 Launch Gambit Orchestrator';
        }
    });

    function addConsoleLine(text, type = "info") {
        const line = document.createElement('div');
        line.className = `console-line ${type}`;
        line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
        statusConsole.appendChild(line);
        statusConsole.scrollTop = statusConsole.scrollHeight;
    }

    // --- LIVE SYSTEM LOGS ---
    function startLiveLogPolling() {
        if (liveLogsPolling) return;
        liveLogsPolling = true;
        pollLiveLogs();
    }

    async function pollLiveLogs() {
        if (!liveLogsPolling) return;
        try {
            const res = await fetch(`/api/live-logs?since=${liveLogsSince}`);
            const data = await res.json();

            if (data.logs.length > 0) {
                // Clear placeholder on first real data
                if (liveLogsSince === 0) {
                    liveLogsConsole.innerHTML = '';
                }
                data.logs.forEach(log => {
                    const line = document.createElement('div');
                    line.className = `console-line ${log.type}`;
                    line.textContent = log.message;
                    liveLogsConsole.appendChild(line);
                });
                liveLogsConsole.scrollTop = liveLogsConsole.scrollHeight;
                liveLogsSince = data.total;
            }
        } catch (e) {
            console.error("Live logs fetch failed", e);
        }
        setTimeout(pollLiveLogs, 1000);
    }

    async function pollStatus() {
        if (!isDeploying) return;

        try {
            const res = await fetch('/api/status');
            const status = await res.json();

            // Clear console and re-render to avoid duplicates if backend returns total log
            statusConsole.innerHTML = '';
            status.logs.forEach(log => {
                const line = document.createElement('div');
                line.className = `console-line ${log.type}`;
                line.textContent = log.message;
                statusConsole.appendChild(line);
            });
            statusConsole.scrollTop = statusConsole.scrollHeight;

            progressBar.style.width = `${status.progress}%`;

            if (status.complete) {
                isDeploying = false;
                launchBtn.disabled = false;
                launchBtn.innerHTML = '✅ Honeypot Live';
                progressBar.style.width = '100%';
                addConsoleLine("Gambit System is fully operational on port 2222.", "success");
            } else if (status.error) {
                isDeploying = false;
                launchBtn.disabled = false;
                launchBtn.innerHTML = '❌ Deployment Failed';
                addConsoleLine("Error: " + status.error, "error");
                // Reset button after 3 seconds so user can retry
                setTimeout(() => {
                    launchBtn.innerHTML = '🚀 Launch Gambit Orchestrator';
                    launchBtn.disabled = false;
                }, 3000);
            } else {
                setTimeout(pollStatus, 1000);
            }
        } catch (e) {
            console.error("Status check failed", e);
            setTimeout(pollStatus, 2000);
        }
    }

    // --- LOG LOGIC ---
    marked.use({ gfm: true, breaks: true });

    async function fetchLogList() {
        try {
            logList.innerHTML = '<div class="loading-state">Refreshing...</div>';
            const response = await fetch('/api/logs');
            if (!response.ok) throw new Error('Network response was not ok');
            
            allLogs = await response.json();
            connStatus.innerHTML = '● Connected';
            renderLogList(allLogs);
        } catch (error) {
            logList.innerHTML = '<div class="loading-state" style="color: var(--danger-color)">Failed to load logs.</div>';
            connStatus.innerHTML = '● Disconnected';
        }
    }

    function renderLogList(logs) {
        logList.innerHTML = '';
        if (logs.length === 0) {
            logList.innerHTML = '<div class="loading-state">No sessions found.</div>';
            return;
        }

        logs.forEach(log => {
            const item = document.createElement('div');
            item.className = `log-item ${currentLog === log.filename ? 'active' : ''}`;
            const date = new Date(log.mtime * 1000);
            item.innerHTML = `
                <div class="log-title">${log.filename.replace('report_session_', '').replace('.md', '')}</div>
                <div class="log-meta"><span>${date.toLocaleDateString()}</span><span>${date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span></div>
            `;
            item.addEventListener('click', () => loadLogContent(log.filename));
            logList.appendChild(item);
        });
    }

    async function loadLogContent(filename) {
        currentLog = filename;
        renderLogList(allLogs);
        currentSelection.textContent = `Viewing: ${filename}`;
        analyticsView.innerHTML = '<div class="loading-state">Loading...</div>';

        try {
            const response = await fetch(`/api/logs/${encodeURIComponent(filename)}`);
            const markdown = await response.text();
            analyticsView.innerHTML = `<div class="markdown-body">${marked.parse(markdown)}</div>`;
        } catch (e) {
            analyticsView.innerHTML = '<div class="placeholder-content"><h3>Load Error</h3></div>';
        }
    }

    refreshBtn.addEventListener('click', fetchLogList);
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        renderLogList(allLogs.filter(log => log.filename.toLowerCase().includes(term)));
    });

    // Init
    loadConfig();
    fetchLogList();
    setInterval(() => { if (!analyticsSidebar.classList.contains('hidden')) fetchLogList(); }, 30000);
});
