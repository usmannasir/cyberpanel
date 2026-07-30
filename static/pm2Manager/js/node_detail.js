// PM2 Node Detail JavaScript

let refreshInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    loadAppInfo();
    loadLogs();
    startAutoRefresh();
});

function loadAppInfo() {
    fetch(`/plugins/pm2Manager/api/info/${encodeURIComponent(appName)}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                renderAppInfo(data.info);
                updateActionButtons(data.info);
            } else {
                showError(data.error || 'Failed to load app information');
            }
        })
        .catch(error => {
            console.error('Error loading app info:', error);
            showError('Error loading application information');
        });
}

function renderAppInfo(info) {
    var pmId = (info.pm_id != null && info.pm_id !== '') ? info.pm_id : (info.id != null && info.id !== '') ? info.id : 'N/A';
    var labels = {
        status: 'Status',
        pid: 'PID',
        pmId: 'PM ID',
        scriptPath: 'Script Path',
        mode: 'Mode',
        instances: 'Instances',
        restarts: 'Restarts',
        namespace: 'Namespace',
        version: 'Version',
        user: 'User',
        watching: 'Watching',
        cpuUsage: 'CPU Usage',
        memoryUsage: 'Memory Usage',
        uptime: 'Uptime'
    };
    var appInfoHtml = [
        '<div class="info-row"><span class="info-label">' + labels.status + '</span><span class="info-value" id="appStatus">' + getStatusBadge(info.status || 'unknown') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.pid + '</span><span class="info-value">' + (info.pid != null ? info.pid : 'N/A') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.pmId + '</span><span class="info-value">' + pmId + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.scriptPath + '</span><span class="info-value" style="font-size: 12px; word-break: break-all;">' + escapeHtml(info.script_path || 'N/A') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.mode + '</span><span class="info-value">' + escapeHtml(info.mode || 'fork') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.instances + '</span><span class="info-value">' + (info.instances != null ? info.instances : 1) + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.restarts + '</span><span class="info-value">' + (info.restarts != null ? info.restarts : 0) + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.namespace + '</span><span class="info-value">' + escapeHtml(info.namespace != null ? String(info.namespace) : 'default') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.version + '</span><span class="info-value">' + escapeHtml(info.version != null ? String(info.version) : '') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.user + '</span><span class="info-value">' + escapeHtml(info.user != null ? String(info.user) : '') + '</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.watching + '</span><span class="info-value">' + (info.watching ? 'Yes' : 'No') + '</span></div>'
    ].join('');
    document.getElementById('appInfo').innerHTML = appInfoHtml;

    var cpu = (info.cpu || 0).toFixed(1);
    var memory = ((info.memory || 0) / 1024 / 1024).toFixed(2);
    var uptime = formatUptime(info.uptime);
    var resourceHtml = [
        '<div class="info-row"><span class="info-label">' + labels.cpuUsage + '</span><span class="info-value">' + cpu + '%</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.memoryUsage + '</span><span class="info-value">' + memory + ' MB</span></div>',
        '<div class="info-row"><span class="info-label">' + labels.uptime + '</span><span class="info-value">' + uptime + '</span></div>'
    ].join('');
    document.getElementById('resourceUsage').innerHTML = resourceHtml;
}

function updateActionButtons(info) {
    const status = info.status || 'unknown';
    const btnStart = document.getElementById('btnStart');
    const btnStop = document.getElementById('btnStop');
    const btnRestart = document.getElementById('btnRestart');
    
    if (status === 'online') {
        btnStart.style.display = 'none';
        btnStop.style.display = 'inline-block';
        btnRestart.style.display = 'inline-block';
    } else {
        btnStart.style.display = 'inline-block';
        btnStop.style.display = 'none';
        btnRestart.style.display = 'none';
    }
}

function loadLogs() {
    fetch(`/plugins/pm2Manager/api/logs/${encodeURIComponent(appName)}/?lines=200`)
        .then(response => response.json().then(data => ({ ok: response.ok, data: data })))
        .then(({ ok, data }) => {
            if (data.success) {
                renderLogs(data.logs);
            } else {
                document.getElementById('logsContainer').innerHTML = 
                    '<div class="log-line" style="color: #ef4444;">Error: ' + escapeHtml(data.error || 'Failed to load logs') + '</div>';
            }
        })
        .catch(error => {
            console.error('Error loading logs:', error);
            document.getElementById('logsContainer').innerHTML = 
                '<div class="log-line" style="color: #ef4444;">Error loading logs</div>';
        });
}

function renderLogs(logs) {
    const container = document.getElementById('logsContainer');
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="log-line">No logs available</div>';
        return;
    }
    
    container.innerHTML = logs.map(log => {
        const logText = escapeHtml(log);
        let color = '#d4d4d4';
        if (logText.includes('ERROR') || logText.includes('error')) {
            color = '#f48771';
        } else if (logText.includes('WARN') || logText.includes('warning')) {
            color = '#dcdcaa';
        }
        
        return `<div class="log-line" style="color: ${color};">${logText}</div>`;
    }).join('');
    
    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function refreshLogs() {
    loadLogs();
}

function copyAllLogs() {
    const container = document.getElementById('logsContainer');
    if (!container) return;
    const text = (container.innerText || container.textContent || '').trim();
    const btn = document.getElementById('btnCopyLogs');
    if (!text) {
        if (btn) { btn.innerHTML = '<i class="fas fa-copy"></i> Nothing to copy'; setTimeout(function() { if (btn) btn.innerHTML = '<i class="fas fa-copy"></i> Copy all'; }, 1500); }
        return;
    }
    navigator.clipboard.writeText(text).then(function() {
        if (btn) {
            var orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            setTimeout(function() { btn.innerHTML = orig; }, 2000);
        }
    }).catch(function() {
        if (btn) { btn.innerHTML = '<i class="fas fa-copy"></i> Copy failed'; setTimeout(function() { btn.innerHTML = '<i class="fas fa-copy"></i> Copy all'; }, 1500); }
    });
}
window.copyAllLogs = copyAllLogs;

function startAutoRefresh() {
    // Refresh info and logs every 3 seconds
    refreshInterval = setInterval(() => {
        loadAppInfo();
        loadLogs();
    }, 3000);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function startApp(name) {
    if (!confirm(`Start ${name}?`)) return;
    
    fetch(`/plugins/pm2Manager/api/start/${encodeURIComponent(name)}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App started successfully');
            loadAppInfo();
        } else {
            showError(data.error || 'Failed to start app');
        }
    })
    .catch(error => {
        console.error('Error starting app:', error);
        showError('Error starting application');
    });
}

function stopApp(name) {
    if (!confirm(`Stop ${name}?`)) return;
    
    fetch(`/plugins/pm2Manager/api/stop/${encodeURIComponent(name)}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App stopped successfully');
            loadAppInfo();
        } else {
            showError(data.error || 'Failed to stop app');
        }
    })
    .catch(error => {
        console.error('Error stopping app:', error);
        showError('Error stopping application');
    });
}

function restartApp(name) {
    if (!confirm(`Restart ${name}?`)) return;
    
    fetch(`/plugins/pm2Manager/api/restart/${encodeURIComponent(name)}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App restarted successfully');
            loadAppInfo();
        } else {
            showError(data.error || 'Failed to restart app');
        }
    })
    .catch(error => {
        console.error('Error restarting app:', error);
        showError('Error restarting application');
    });
}

function getStatusBadge(status) {
    const badges = {
        'online': '<span class="status-badge status-online">Running</span>',
        'stopped': '<span class="status-badge status-stopped">Stopped</span>',
        'restarting': '<span class="status-badge status-restarting">Restarting</span>'
    };
    return badges[status] || `<span class="status-badge">${status}</span>`;
}

function formatUptime(seconds) {
    if (!seconds || seconds < 0) return '0s';
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert('Error: ' + message);
}

window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});
