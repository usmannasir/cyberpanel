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
                label: 'CPU Usage (%)',
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
                label: 'Memory Usage (%)',
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
                label: 'Disk Usage (%)',
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

function fetchResourceUsage() {
    $.ajax({
        url: '/websites/get_website_resources/',
        type: 'POST',
        data: JSON.stringify({
            'domain': $('#domainNamePage').text().trim()
        }),
        contentType: 'application/json',
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

// Initialize charts when the page loads
$(document).ready(function() {
    if (document.getElementById('cpuChart')) {
        initializeCharts();
        // Fetch resource usage every 5 seconds
        setInterval(fetchResourceUsage, 5000);
        // Initial fetch
        fetchResourceUsage();
    }
}); 