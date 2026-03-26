document.addEventListener('DOMContentLoaded', () => {
    const logList = document.getElementById('logList');
    const contentBody = document.getElementById('contentBody');
    const currentSelection = document.getElementById('currentSelection');
    const searchInput = document.getElementById('searchInput');
    const refreshBtn = document.getElementById('refreshBtn');
    const connStatus = document.getElementById('connStatus');

    let allLogs = [];
    let currentLog = null;

    // Initialize Marked.js options
    marked.setOptions({
        gfm: true,
        breaks: true,
        headerIds: true,
    });

    async function fetchLogList() {
        try {
            logList.innerHTML = '<div class="loading-state">Refreshing...</div>';
            const response = await fetch('/api/logs');
            if (!response.ok) throw new Error('Network response was not ok');
            
            allLogs = await response.json();
            
            connStatus.innerHTML = '● Connected';
            connStatus.style.color = 'var(--success-color)';
            connStatus.style.borderColor = 'rgba(16, 185, 129, 0.2)';
            connStatus.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';

            renderLogList(allLogs);
        } catch (error) {
            console.error('Error fetching logs:', error);
            logList.innerHTML = '<div class="loading-state" style="color: var(--danger-color)">Failed to load logs. Is the server running?</div>';
            
            connStatus.innerHTML = '● Disconnected';
            connStatus.style.color = 'var(--danger-color)';
            connStatus.style.borderColor = 'rgba(244, 63, 94, 0.2)';
            connStatus.style.backgroundColor = 'rgba(244, 63, 94, 0.1)';
        }
    }

    function renderLogList(logs) {
        logList.innerHTML = '';
        
        if (logs.length === 0) {
            logList.innerHTML = '<div class="loading-state">No honeypot sessions found.</div>';
            return;
        }

        logs.forEach(log => {
            const item = document.createElement('div');
            item.className = `log-item ${currentLog === log.filename ? 'active' : ''}`;
            
            // Format time
            const date = new Date(log.mtime * 1000);
            const timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateString = date.toLocaleDateString();

            item.innerHTML = `
                <div class="log-title">${log.filename.replace('report_session_', '').replace('.md', '')}</div>
                <div class="log-meta">
                    <span>${dateString}</span>
                    <span>${timeString}</span>
                </div>
            `;

            item.addEventListener('click', () => loadLogContent(log.filename));
            logList.appendChild(item);
        });
    }

    async function loadLogContent(filename) {
        currentLog = filename;
        renderLogList(allLogs); // Update active state
        
        currentSelection.textContent = `Viewing: ${filename}`;
        contentBody.innerHTML = `
            <div class="placeholder-content">
                <div class="loading-state">Decrypting neural telemetry...</div>
            </div>
        `;

        try {
            const response = await fetch(`/api/logs/${encodeURIComponent(filename)}`);
            if (!response.ok) throw new Error('File not found');
            
            const markdown = await response.text();
            
            // Render markdown to HTML
            const html = marked.parse(markdown);
            
            contentBody.innerHTML = `
                <div class="markdown-body">
                    ${html}
                </div>
            `;
        } catch (error) {
            console.error('Error fetching log content:', error);
            contentBody.innerHTML = `
                <div class="placeholder-content">
                    <div class="placeholder-icon" style="color: var(--danger-color)">⚠</div>
                    <h3 style="color: var(--danger-color)">Failed to load report</h3>
                    <p>The forensic report could not be retrieved from the server.</p>
                </div>
            `;
        }
    }

    // Event Listeners
    refreshBtn.addEventListener('click', fetchLogList);
    
    searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allLogs.filter(log => log.filename.toLowerCase().includes(term));
        renderLogList(filtered);
    });

    // Initial Fetch
    fetchLogList();
    
    // Auto-refresh every 30 seconds
    setInterval(fetchLogList, 30000);
});
