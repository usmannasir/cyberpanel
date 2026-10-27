(function () {
// Resource Monitoring
let cpuChart, memoryChart, diskChart;
let cpuData = [], memoryData = [], diskData = [];
const maxDataPoints = 30;

function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    callback: function(value) {
                        return value + '%';
                    }
                }
            }
        },
        animation: {
            duration: 750
        }
    };

    // CPU Chart
    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Account CPU (% of server)' ,
                data: [],
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Memory Chart
    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Account RAM (% of server)' ,
                data: [],
                borderColor: '#00b894',
                backgroundColor: 'rgba(0, 184, 148, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Disk Chart
    const diskCtx = document.getElementById('diskChart').getContext('2d');
    diskChart = new Chart(diskCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Document root (% of filesystem)' ,
                data: [],
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });
}

function updateCharts(data) {
    const now = new Date();
    const timeLabel = now.toLocaleTimeString();

    // Update CPU Chart
    cpuData.push(data.cpu_usage);
    if (cpuData.length > maxDataPoints) cpuData.shift();
    cpuChart.data.labels.push(timeLabel);
    if (cpuChart.data.labels.length > maxDataPoints) cpuChart.data.labels.shift();
    cpuChart.data.datasets[0].data = cpuData;
    cpuChart.update('none'); // Use 'none' mode for better performance

    // Update Memory Chart
    memoryData.push(data.memory_usage);
    if (memoryData.length > maxDataPoints) memoryData.shift();
    memoryChart.data.labels.push(timeLabel);
    if (memoryChart.data.labels.length > maxDataPoints) memoryChart.data.labels.shift();
    memoryChart.data.datasets[0].data = memoryData;
    memoryChart.update('none');

    // Update Disk Chart
    diskData.push(data.disk_percent);
    if (diskData.length > maxDataPoints) diskData.shift();
    diskChart.data.labels.push(timeLabel);
    if (diskChart.data.labels.length > maxDataPoints) diskChart.data.labels.shift();
    diskChart.data.datasets[0].data = diskData;
    diskChart.update('none');
}

let resourceRequestPending = false;
let resourceTimer = null;
let resourceStopped = false;
function showResourceStatus(message) {
    const status = document.getElementById('resource-usage-status');
    if (status) status.textContent = message;
}
function scheduleResourceUsage() {
    if (!resourceStopped) resourceTimer = setTimeout(fetchResourceUsage, 5000);
}
function fetchResourceUsage() {
    if (resourceStopped || resourceRequestPending) return;
    if (document.hidden) { scheduleResourceUsage(); return; }
    resourceRequestPending = true;
    $.ajax({
        url: '/websites/get_website_resources/', type: 'POST', timeout: 12000,
        data: JSON.stringify({'domain': $('#domainNamePage').text().trim()}),
        contentType: 'application/json',
        success: function(data) {
            if (data.status === 1 && [data.cpu_usage, data.memory_usage, data.disk_percent].every(Number.isFinite)) {
                updateCharts(data);
                showResourceStatus('Updated ' + new Date().toLocaleTimeString() + '. Document root: ' + data.disk_used + ' MiB.');
            } else {
                showResourceStatus('Resource usage unavailable. Previous chart points are historical.');
            }
        },
        error: function() {
            showResourceStatus('Resource usage unavailable. Retrying after this request finishes.');
        },
        complete: function() {
            resourceRequestPending = false;
            scheduleResourceUsage();
        }
    });
}
$(document).ready(function() {
    if (document.getElementById('cpuChart')) {
        initializeCharts();
        fetchResourceUsage();
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden && !resourceRequestPending) {
                clearTimeout(resourceTimer);
                fetchResourceUsage();
            }
        });
        window.addEventListener('pageshow', function() {
            if (resourceStopped) {
                resourceStopped = false;
                fetchResourceUsage();
            }
        });
        window.addEventListener('pagehide', function() {
            resourceStopped = true;
            clearTimeout(resourceTimer);
        });
    }
});

})();
