// PM2 Manager Dashboard JavaScript
// Real-time updates via HTTP polling only (no WebSocket)

const TABLE_COLUMNS = 13;
let apps = [];
let sortKey = 'pm_id';
let sortDir = 'asc';
let monitorInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadApps();
    startRealTimeMonitoring();
    document.getElementById('addAppForm').addEventListener('submit', handleAddApp);
    var tbody = document.getElementById('appsTableBody');
    if (tbody) tbody.addEventListener('click', handleActionClick);
    // Click on column headers only (thead) to sort; each column is a separate clickable header
    var thead = document.querySelector('.apps-table-wrapper thead');
    if (thead) {
        thead.addEventListener('click', function(e) {
            var th = e.target && e.target.closest ? e.target.closest('th.sortable-column') : null;
            if (!th) return;
            e.preventDefault();
            e.stopPropagation();
            var key = th.getAttribute('data-sort-key');
            if (!key) return;
            if (sortKey === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            else { sortKey = key; sortDir = 'asc'; }
            apps = sortApps(apps);
            updateStats(apps);
            renderAppsTable(apps);
            updateSortIcons();
        });
    }
});

// Load PM2 apps list (checks PM2 status and loads active apps)
function loadApps() {
    fetch('/plugins/pm2Manager/api/list/')
        .then(response => response.json())
        .then(data => {
            const pm2Status = data.pm2_status || {};
            updatePm2StatusBadge(pm2Status);
            if (data.success) {
                apps = sortApps(data.apps || []);
                updateStats(apps);
                renderAppsTable(apps, pm2Status);
                updateSortIcons();
            } else {
                renderAppsTable([], pm2Status);
                if (data.error) showError(data.error);
            }
        })
        .catch(error => {
            console.error('Error loading apps:', error);
            updatePm2StatusBadge({ installed: false, running: false, message: error.message });
            renderAppsTable([], { installed: false, running: false });
            showError('Error loading PM2 applications');
        });
}

function updatePm2StatusBadge(pm2Status) {
    const badge = document.getElementById('pm2StatusBadge');
    if (!badge) return;
    if (pm2Status.running) {
        badge.textContent = 'PM2 running';
        badge.className = 'status-badge status-online';
        badge.style.marginLeft = '12px';
        badge.style.fontSize = '11px';
    } else if (pm2Status.installed) {
        badge.textContent = 'PM2 daemon not running';
        badge.className = 'status-badge status-stopped';
        badge.style.marginLeft = '12px';
        badge.style.fontSize = '11px';
    } else {
        badge.textContent = 'PM2 not installed';
        badge.className = 'status-badge status-stopped';
        badge.style.marginLeft = '12px';
        badge.style.fontSize = '11px';
    }
}

// Start real-time monitoring (HTTP polling only; api/monitor/ is not a WebSocket endpoint)
function startRealTimeMonitoring() {
    startPolling();
}

// Start HTTP polling for real-time updates
function startPolling() {
    if (monitorInterval) clearInterval(monitorInterval);
    
    monitorInterval = setInterval(() => {
        fetch('/plugins/pm2Manager/api/monitor/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRealTimeData(data.data);
                }
            })
            .catch(error => console.error('Polling error:', error));
    }, 2000);
}

// Update real-time data (merge all monitor fields so ID, namespace, version, etc. stay populated)
function updateRealTimeData(monitorData) {
    monitorData.forEach(monitor => {
        const app = apps.find(a => a.name === monitor.name);
        if (app) {
            Object.keys(monitor).forEach(function(k) { app[k] = monitor[k]; });
        }
    });
    apps = sortApps(apps);
    updateStats(apps);
    renderAppsTable(apps);
    if (apps.length > 0) updateSortIcons();
}

function sortApps(appsList) {
    if (!appsList || appsList.length === 0) return appsList;
    const key = sortKey;
    const dir = sortDir === 'asc' ? 1 : -1;
    const numericKeys = ['pm_id', 'id', 'cpu', 'memory', 'uptime', 'restarts'];
    const boolKeys = ['watching'];
    return appsList.slice().sort(function(a, b) {
        let va = key === 'pm_id' ? (a.pm_id != null ? a.pm_id : a.id) : a[key];
        let vb = key === 'pm_id' ? (b.pm_id != null ? b.pm_id : b.id) : b[key];
        if (numericKeys.indexOf(key) !== -1) {
            va = Number(va) || 0;
            vb = Number(vb) || 0;
            return dir * (va - vb);
        }
        if (boolKeys.indexOf(key) !== -1) {
            va = va ? 1 : 0;
            vb = vb ? 1 : 0;
            return dir * (va - vb);
        }
        va = (va != null ? String(va) : '');
        vb = (vb != null ? String(vb) : '');
        return dir * (va.localeCompare(vb, undefined, { numeric: true }));
    });
}

function updateSortIcons() {
    document.querySelectorAll('.apps-table-wrapper .apps-table th.sortable-column').forEach(function(th) {
        var key = th.getAttribute('data-sort-key');
        var existing = th.querySelector('.sort-icon');
        if (existing) existing.remove();
        if (key === sortKey) {
            var icon = document.createElement('span');
            icon.className = 'sort-icon';
            icon.setAttribute('aria-hidden', 'true');
            icon.textContent = sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
            icon.style.marginLeft = '4px';
            icon.style.fontWeight = 'bold';
            th.appendChild(icon);
        }
    });
}

// Update statistics
function updateStats(appsList) {
    const total = appsList.length;
    const running = appsList.filter(a => a.status === 'online').length;
    const stopped = appsList.filter(a => a.status === 'stopped').length;
    const avgCpu = appsList.length > 0 
        ? (appsList.reduce((sum, a) => sum + (a.cpu || 0), 0) / appsList.length).toFixed(1)
        : 0;
    
    document.getElementById('totalApps').textContent = total;
    document.getElementById('runningApps').textContent = running;
    document.getElementById('stoppedApps').textContent = stopped;
    document.getElementById('avgCpu').textContent = avgCpu + '%';
}

// Render apps table (appsList + optional pm2Status for empty-state message)
// Build rows with DOM so every row has exactly 13 <td> cells matching thead columns.
function renderAppsTable(appsList, pm2Status) {
    const tbody = document.getElementById('appsTableBody');
    if (!tbody) return;
    pm2Status = pm2Status || {};
    
    if (appsList.length === 0) {
        let emptyMsg = 'No PM2 applications found';
        if (pm2Status.message && !pm2Status.running) {
            emptyMsg = pm2Status.message + (pm2Status.installed ? ' Start the PM2 daemon (e.g. run "pm2 list" in a shell) to see existing apps.' : '');
        } else if (!pm2Status.installed) {
            emptyMsg = 'PM2 is not installed. Install with: npm install -g pm2';
        }
        tbody.innerHTML = '<tr><td colspan="' + TABLE_COLUMNS + '" class="empty-state"><div class="empty-icon"><i class="fas fa-cube"></i></div><div>' + escapeHtml(emptyMsg) + '</div><div style="margin-top:10px;"><button class="action-btn btn-restart" onclick="refreshApps()"><i class="fas fa-sync-alt"></i> Refresh</button></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    appsList.forEach(function(app) {
        var statusClass = app.status === 'online' ? 'status-online' : (app.status === 'stopped' ? 'status-stopped' : 'status-restarting');
        var statusText = app.status === 'online' ? 'Running' : (app.status === 'stopped' ? 'Stopped' : 'Restarting');
        var uptime = formatUptime(app.uptime);
        var cpuPercent = (app.cpu || 0).toFixed(1);
        var memoryMB = ((app.memory || 0) / 1024 / 1024).toFixed(2);
        var watchingText = app.watching ? 'Yes' : 'No';
        var rawId = (app.pm_id != null && app.pm_id !== '') ? app.pm_id : (app.id != null && app.id !== '') ? app.id : null;
        var displayId = (rawId !== null && rawId !== '' && !isNaN(Number(rawId))) ? String(Number(rawId)) : '\u2013';
        var safeName = escapeHtml(app.name || '');
        var pidStr = app.pid != null ? String(app.pid) : 'N/A';
        var memPct = Math.min((app.memory || 0) / 1024 / 1024 / 100, 100);
        var cpuPct = Math.min(parseFloat(cpuPercent), 100);

        var row = tbody.insertRow(-1);
        // Column 0: ID (numeric only)
        var c0 = row.insertCell(0);
        c0.setAttribute('data-col', 'id');
        c0.textContent = displayId;
        // Column 1: App name + PID
        var c1 = row.insertCell(1);
        c1.setAttribute('data-col', 'name');
        c1.innerHTML = '<strong>' + safeName + '</strong><br><small style="color: var(--text-secondary, #64748b);">PID: ' + escapeHtml(pidStr) + '</small>';
        // Column 2: Namespace
        var c2 = row.insertCell(2);
        c2.setAttribute('data-col', 'namespace');
        c2.textContent = app.namespace != null ? String(app.namespace) : 'default';
        // Column 3: Version
        var c3 = row.insertCell(3);
        c3.setAttribute('data-col', 'version');
        c3.textContent = app.version != null ? String(app.version) : '';
        // Column 4: Mode
        var c4 = row.insertCell(4);
        c4.setAttribute('data-col', 'mode');
        c4.textContent = app.mode != null ? String(app.mode) : 'fork';
        // Column 5: Status
        var c5 = row.insertCell(5);
        c5.setAttribute('data-col', 'status');
        c5.innerHTML = '<span class="status-badge ' + statusClass + '">' + statusText + '</span>';
        // Column 6: CPU
        var c6 = row.insertCell(6);
        c6.setAttribute('data-col', 'cpu');
        c6.innerHTML = '<div>' + cpuPercent + '%</div><div class="usage-bar"><div class="usage-fill usage-cpu" style="width:' + cpuPct + '%"></div></div>';
        // Column 7: Memory
        var c7 = row.insertCell(7);
        c7.setAttribute('data-col', 'memory');
        c7.innerHTML = '<div>' + memoryMB + ' MB</div><div class="usage-bar"><div class="usage-fill usage-memory" style="width:' + memPct + '%"></div></div>';
        // Column 8: Uptime
        var c8 = row.insertCell(8);
        c8.setAttribute('data-col', 'uptime');
        c8.textContent = uptime;
        // Column 9: Restarts
        var c9 = row.insertCell(9);
        c9.setAttribute('data-col', 'restarts');
        c9.textContent = app.restarts != null ? String(app.restarts) : '0';
        // Column 10: User
        var c10 = row.insertCell(10);
        c10.setAttribute('data-col', 'user');
        c10.textContent = app.user != null ? String(app.user) : '';
        // Column 11: Watching
        var c11 = row.insertCell(11);
        c11.setAttribute('data-col', 'watching');
        c11.textContent = watchingText;
        // Column 12: Actions
        var c12 = row.insertCell(12);
        c12.setAttribute('data-col', 'actions');
        c12.className = 'actions-cell';
        var actionsDiv = document.createElement('div');
        actionsDiv.className = 'actions-cell';
        var btnStop = app.status === 'online' ? makeActionBtn('stop', 'btn-stop', 'fa-stop', 'Stop', safeName) : makeActionBtn('start', 'btn-start', 'fa-play', 'Start', safeName);
        var btnRestart = app.status === 'online' ? makeActionBtn('restart', 'btn-restart', 'fa-redo', 'Restart', safeName) : null;
        var btnView = makeActionBtn('view', 'btn-view', 'fa-info-circle', 'Details', safeName);
        var btnDelete = makeActionBtn('delete', 'btn-delete', 'fa-trash', 'Delete', safeName);
        actionsDiv.appendChild(btnStop);
        if (btnRestart) actionsDiv.appendChild(btnRestart);
        actionsDiv.appendChild(btnView);
        actionsDiv.appendChild(btnDelete);
        c12.appendChild(actionsDiv);
    });
}

function makeActionBtn(action, btnClass, iconClass, label, safeName) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'action-btn ' + btnClass;
    b.setAttribute('data-action', action);
    b.setAttribute('data-app-name', safeName);
    b.innerHTML = '<i class="fas ' + iconClass + '"></i> ' + label;
    return b;
}

function handleActionClick(e) {
    var btn = e.target && e.target.closest ? e.target.closest('button[data-action][data-app-name]') : null;
    if (!btn) return;
    e.preventDefault();
    var action = btn.getAttribute('data-action');
    var name = btn.getAttribute('data-app-name');
    if (!name) return;
    if (action === 'stop') stopApp(name);
    else if (action === 'restart') restartApp(name);
    else if (action === 'start') startApp(name);
    else if (action === 'view') viewAppDetails(name);
    else if (action === 'delete') deleteApp(name);
}

function cellText(text) {
    var td = document.createElement('td');
    td.textContent = text != null ? String(text) : '';
    return td;
}

function cellHtml(html) {
    var td = document.createElement('td');
    td.innerHTML = html;
    return td;
}

function btn(label, btnClass, iconClass, action, appName) {
    var b = document.createElement('button');
    b.className = 'action-btn ' + btnClass;
    b.setAttribute('data-app-name', appName);
    b.setAttribute('data-action', action);
    b.innerHTML = '<i class="fas ' + iconClass + '"></i> ' + label;
    b.onclick = function() {
        var name = this.getAttribute('data-app-name');
        if (!name) return;
        if (action === 'stop') stopApp(name);
        else if (action === 'restart') restartApp(name);
        else if (action === 'start') startApp(name);
        else if (action === 'view') viewAppDetails(name);
        else if (action === 'delete') deleteApp(name);
    };
    return b;
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
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function startApp(name) {
    if (!confirm(`Start ${name}?`)) return;
    fetch(`/plugins/pm2Manager/api/start/${encodeURIComponent(name)}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App started successfully');
            loadApps();
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
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App stopped successfully');
            loadApps();
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
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App restarted successfully');
            loadApps();
        } else {
            showError(data.error || 'Failed to restart app');
        }
    })
    .catch(error => {
        console.error('Error restarting app:', error);
        showError('Error restarting application');
    });
}

function deleteApp(name) {
    if (!confirm(`Delete ${name}? This action cannot be undone.`)) return;
    fetch(`/plugins/pm2Manager/api/delete/${encodeURIComponent(name)}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message || 'App deleted successfully');
            loadApps();
        } else {
            showError(data.error || 'Failed to delete app');
        }
    })
    .catch(error => {
        console.error('Error deleting app:', error);
        showError('Error deleting application');
    });
}

function viewAppDetails(name) {
    window.location.href = `/plugins/pm2Manager/node/${encodeURIComponent(name)}/`;
}

function refreshApps() {
    loadApps();
}

function showAddAppModal() {
    document.getElementById('addAppModal').style.display = 'flex';
}

function closeAddAppModal() {
    document.getElementById('addAppModal').style.display = 'none';
    document.getElementById('addAppForm').reset();
}

function handleAddApp(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        script_path: formData.get('script_path'),
        args: formData.get('args') || '',
        instances: parseInt(formData.get('instances')) || 1,
        exec_mode: formData.get('exec_mode') || 'fork',
        max_memory_restart: formData.get('max_memory_restart') || '',
        autorestart: formData.get('autorestart') || 'true',
        cwd: formData.get('cwd') || '',
        interpreter: formData.get('interpreter') || ''
    };
    
    fetch('/plugins/pm2Manager/api/add/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showSuccess(result.message || 'App added successfully');
            closeAddAppModal();
            loadApps();
        } else {
            showError(result.error || 'Failed to add app');
        }
    })
    .catch(error => {
        console.error('Error adding app:', error);
        showError('Error adding application');
    });
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
    if (monitorInterval) clearInterval(monitorInterval);
});
