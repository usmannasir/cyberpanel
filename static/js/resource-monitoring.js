// Resource Monitoring
let cpuChart, memoryChart, diskChart;
let cpuData = [], memoryData = [], diskData = [];
const maxDataPoints = 30;
let memoryUsesAbsolute = false;
let diskUsesAbsolute = false;

function formatAbsoluteValue(value) {
    if (value >= 1024) {
        return (value / 1024).toFixed(1) + ' GB';
    }
    return Math.round(value) + ' MB';
}

function buildYAxisOptions(usesAbsolute, peakValue) {
    const options = {
        beginAtZero: true,
        ticks: {
            callback: function(value) {
                return usesAbsolute ? formatAbsoluteValue(value) : value + '%';
            }
        }
    };
    if (usesAbsolute) {
        options.max = Math.max(100, Math.ceil((peakValue || 0) * 1.15));
    } else {
        options.max = 100;
    }
    return options;
}

function applyChartMode(chart, usesAbsolute, label, peakValue) {
    chart.data.datasets[0].label = label;
    chart.options.scales.y = buildYAxisOptions(usesAbsolute, peakValue);
    chart.update('none');
}

function initializeCharts() {
    const cpuOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: buildYAxisOptions(false, 100)
        },
        animation: {
            duration: 750
        }
    };

    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage (%)',
                data: [],
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: cpuOptions
    });

    const memoryCtx = document.getElementById('memoryChart').getContext('2d');
    memoryChart = new Chart(memoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory Usage (%)',
                data: [],
                borderColor: '#00b894',
                backgroundColor: 'rgba(0, 184, 148, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: buildYAxisOptions(false, 100)
            },
            animation: {
                duration: 750
            }
        }
    });

    const diskCtx = document.getElementById('diskChart').getContext('2d');
    diskChart = new Chart(diskCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Disk Usage (%)',
                data: [],
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: buildYAxisOptions(false, 100)
            },
            animation: {
                duration: 750
            }
        }
    });
}

function isUnlimitedMetric(data, limitKey, flagKey) {
    if (data[flagKey] === true || data[flagKey] === 'true' || data[flagKey] === 1) {
        return true;
    }
    const limit = parseFloat(data[limitKey]);
    return !limit || limit <= 0;
}

function getMemoryChartValue(data) {
    if (isUnlimitedMetric(data, 'memory_limit_mb', 'memory_unlimited')) {
        return parseFloat(data.memory_used_mb || data.memory_usage || 0) || 0;
    }
    return parseFloat(data.memory_usage || data.memory_percent || 0) || 0;
}

function getDiskChartValue(data) {
    if (isUnlimitedMetric(data, 'disk_limit_mb', 'disk_unlimited')) {
        return parseFloat(data.disk_used_mb || data.disk_used || 0) || 0;
    }
    return parseFloat(data.disk_percent || 0) || 0;
}

function syncChartModes(data) {
    const nextMemoryAbsolute = isUnlimitedMetric(data, 'memory_limit_mb', 'memory_unlimited');
    const nextDiskAbsolute = isUnlimitedMetric(data, 'disk_limit_mb', 'disk_unlimited');

    if (nextMemoryAbsolute !== memoryUsesAbsolute) {
        memoryUsesAbsolute = nextMemoryAbsolute;
        applyChartMode(
            memoryChart,
            memoryUsesAbsolute,
            memoryUsesAbsolute ? 'Memory Usage (MB)' : 'Memory Usage (%)',
            getMemoryChartValue(data)
        );
    }

    if (nextDiskAbsolute !== diskUsesAbsolute) {
        diskUsesAbsolute = nextDiskAbsolute;
        applyChartMode(
            diskChart,
            diskUsesAbsolute,
            diskUsesAbsolute ? 'Disk Usage (MB)' : 'Disk Usage (%)',
            getDiskChartValue(data)
        );
    }
}

function updateCharts(data) {
    const now = new Date();
    const timeLabel = now.toLocaleTimeString();
    const memoryValue = getMemoryChartValue(data);
    const diskValue = getDiskChartValue(data);

    syncChartModes(data);

    if (memoryUsesAbsolute) {
        const peak = Math.max(memoryValue, ...(memoryData.length ? memoryData : [0]));
        memoryChart.options.scales.y.max = Math.max(100, Math.ceil(peak * 1.15));
    }

    if (diskUsesAbsolute) {
        const peak = Math.max(diskValue, ...(diskData.length ? diskData : [0]));
        diskChart.options.scales.y.max = Math.max(100, Math.ceil(peak * 1.15));
    }

    cpuData.push(data.cpu_usage);
    if (cpuData.length > maxDataPoints) cpuData.shift();
    cpuChart.data.labels.push(timeLabel);
    if (cpuChart.data.labels.length > maxDataPoints) cpuChart.data.labels.shift();
    cpuChart.data.datasets[0].data = cpuData;
    cpuChart.update('none');

    memoryData.push(memoryValue);
    if (memoryData.length > maxDataPoints) memoryData.shift();
    memoryChart.data.labels.push(timeLabel);
    if (memoryChart.data.labels.length > maxDataPoints) memoryChart.data.labels.shift();
    memoryChart.data.datasets[0].data = memoryData;
    memoryChart.update('none');

    diskData.push(diskValue);
    if (diskData.length > maxDataPoints) diskData.shift();
    diskChart.data.labels.push(timeLabel);
    if (diskChart.data.labels.length > maxDataPoints) diskChart.data.labels.shift();
    diskChart.data.datasets[0].data = diskData;
    diskChart.update('none');
}

function fetchResourceUsage() {
    $.ajax({
        url: '/websites/get_website_resources/',
        type: 'POST',
        data: JSON.stringify({
            'domain': $('#domainNamePage').text().trim()
        }),
        contentType: 'application/json',
        dataType: 'json',
        success: function(data) {
            if (data.status === 1) {
                updateCharts(data);
            } else {
                console.error('Error fetching resource data:', data.error_message);
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to fetch resource usage:', error);
        }
    });
}

$(document).ready(function() {
    if (document.getElementById('cpuChart')) {
        initializeCharts();
        setInterval(fetchResourceUsage, 5000);
        fetchResourceUsage();
    }
});
