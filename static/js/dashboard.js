// Dashboard JavaScript functionality

// Initialize the dashboard when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

// Main initialization function
function initializeDashboard() {
    // Set up event listeners
    setupEventListeners();
    
    // Initialize charts
    initializeCharts();
    
    // Fetch initial data
    fetchPositions();
    fetchSignals();
    fetchSystemStatus();
    fetchPerformanceData();
    
    // Set up refresh interval (every 30 seconds)
    setInterval(function() {
        fetchPositions();
        fetchSignals();
        fetchSystemStatus();
    }, 30000);
}

// Set up event listeners for dashboard interactions
function setupEventListeners() {
    // Chart period buttons
    const chartPeriodButtons = document.querySelectorAll('.chart-period');
    chartPeriodButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            chartPeriodButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update chart for selected period
            updateChartForPeriod(this.dataset.period);
        });
    });
    
    // Close position confirmation
    const confirmCloseBtn = document.getElementById('confirmClosePosition');
    if (confirmCloseBtn) {
        confirmCloseBtn.addEventListener('click', function() {
            const symbol = document.getElementById('closePositionSymbol').textContent;
            closePosition(symbol);
        });
    }
    
    // Close type change handler (full vs partial)
    const closeTypeSelect = document.getElementById('closeType');
    if (closeTypeSelect) {
        closeTypeSelect.addEventListener('change', function() {
            const partialOptions = document.getElementById('partialCloseOptions');
            if (this.value === 'partial') {
                partialOptions.classList.remove('d-none');
            } else {
                partialOptions.classList.add('d-none');
            }
        });
    }
    
    // Update percentage value display when slider changes
    const closePercentage = document.getElementById('closePercentage');
    if (closePercentage) {
        closePercentage.addEventListener('input', function() {
            document.getElementById('percentageValue').textContent = this.value + '%';
        });
    }
    
    // Service control buttons
    document.getElementById('startAllBtn')?.addEventListener('click', startAllServices);
    document.getElementById('stopAllBtn')?.addEventListener('click', stopAllServices);
    document.getElementById('startStrategyBtn')?.addEventListener('click', startStrategyService);
    document.getElementById('stopStrategyBtn')?.addEventListener('click', stopStrategyService);
    document.getElementById('startExecutorBtn')?.addEventListener('click', startExecutionService);
    document.getElementById('stopExecutorBtn')?.addEventListener('click', stopExecutionService);
    document.getElementById('refreshDataBtn')?.addEventListener('click', refreshMarketData);
}

// Initialize performance chart
function initializeCharts() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;
    
    // Sample data - will be replaced by actual data
    const labels = Array.from({length: 7}, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - 6 + i);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    window.performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'P/L',
                data: [0, 0, 0, 0, 0, 0, 0],
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `P/L: $${context.raw.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Update chart based on selected time period
function updateChartForPeriod(period) {
    // Here we would fetch data for the selected period
    // For now, just update chart with sample data
    const dataPoints = {
        '1d': [0, 0.5, -0.3, 0.8, 0.2, -0.5, 0.9],
        '1w': [0, 1.2, 0.8, 1.5, 2.0, 1.7, 2.5],
        '1m': [0, 2.5, 1.8, 3.2, 3.8, 4.5, 5.2],
        '3m': [0, 3.5, 5.2, 4.8, 7.5, 8.2, 10.5],
        '1y': [0, 8.5, 12.2, 15.8, 18.5, 22.2, 25.5]
    };
    
    // Get data for the selected period or use 1d as fallback
    const data = dataPoints[period] || dataPoints['1d'];
    
    // Update chart data
    if (window.performanceChart) {
        window.performanceChart.data.datasets[0].data = data;
        window.performanceChart.update();
    }
    
    // Fetch actual performance data for the selected period
    fetchPerformanceData(period);
}

// Fetch positions from the API
function fetchPositions() {
    fetch('/api/execution/positions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayPositions(data.positions);
                updatePositionCount(data.positions.length);
            }
        })
        .catch(error => {
            console.error('Error fetching positions:', error);
        });
}

// Display positions in the table
function displayPositions(positions) {
    const tableBody = document.getElementById('positionsTableBody');
    if (!tableBody) return;
    
    if (positions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No positions found</td></tr>';
        return;
    }
    
    let html = '';
    positions.forEach(position => {
        const isProfitable = parseFloat(position.unrealized_pl) >= 0;
        const plClass = isProfitable ? 'profit' : 'loss';
        
        html += `
        <tr>
            <td>${position.symbol}</td>
            <td>${position.qty}</td>
            <td>$${parseFloat(position.avg_entry_price).toFixed(2)}</td>
            <td>$${parseFloat(position.current_price).toFixed(2)}</td>
            <td class="${plClass}">$${parseFloat(position.unrealized_pl).toFixed(2)}</td>
            <td class="${plClass}">${(parseFloat(position.unrealized_plpc) * 100).toFixed(2)}%</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="prepareClosePositionModal('${position.symbol}', '${position.unrealized_pl}')">
                    Close
                </button>
            </td>
        </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// Fetch signals from the API
function fetchSignals() {
    fetch('/api/strategy/signals')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displaySignals(data.signals);
                updateSignalCount(data.signals.length);
            }
        })
        .catch(error => {
            console.error('Error fetching signals:', error);
        });
}

// Display signals in the list
function displaySignals(signals) {
    const signalsList = document.getElementById('signalsList');
    if (!signalsList) return;
    
    if (signals.length === 0) {
        signalsList.innerHTML = '<div class="text-center py-3"><span class="text-muted">No active signals</span></div>';
        return;
    }
    
    let html = '';
    signals.forEach(signal => {
        const badgeClass = getBadgeClassForSignal(signal);
        
        html += `
        <div class="signal-item">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">${signal.symbol}</h6>
                <span class="badge ${badgeClass}">${signal.category}</span>
            </div>
            <div class="mb-2">
                <small class="text-muted">Trigger: $${parseFloat(signal.trigger).toFixed(2)}</small>
            </div>
            <div class="d-flex justify-content-between">
                <small>${formatTargets(signal.targets)}</small>
                <button class="btn btn-sm btn-outline-secondary" 
                        onclick="deleteSignal('${signal.id}')">
                    Remove
                </button>
            </div>
        </div>
        `;
    });
    
    signalsList.innerHTML = html;
}

// Helper to get appropriate badge class for signal category
function getBadgeClassForSignal(signal) {
    const categoryMap = {
        'breakout': 'bg-success',
        'breakdown': 'bg-danger',
        'rejection': 'bg-warning',
        'bounce': 'bg-info'
    };
    
    return categoryMap[signal.category] || 'bg-secondary';
}

// Helper to format targets array
function formatTargets(targets) {
    if (!targets || targets.length === 0) return '';
    
    return 'Targets: ' + targets.map(t => '$' + parseFloat(t).toFixed(2)).join(', ');
}

// Update signal count
function updateSignalCount(count) {
    document.getElementById('signalCount')?.textContent = count;
    document.getElementById('signalCountBadge')?.textContent = count;
}

// Update position count
function updatePositionCount(count) {
    document.getElementById('positionCount')?.textContent = count;
}

// Prepare the close position modal
function prepareClosePositionModal(symbol, pl) {
    const modal = new bootstrap.Modal(document.getElementById('closePositionModal'));
    document.getElementById('closePositionSymbol').textContent = symbol;
    
    const plValue = parseFloat(pl);
    const plFormatted = '$' + Math.abs(plValue).toFixed(2);
    const plElement = document.getElementById('closePositionPL');
    plElement.textContent = plFormatted;
    
    if (plValue >= 0) {
        plElement.className = 'fw-bold profit';
        plElement.textContent = '+' + plFormatted;
    } else {
        plElement.className = 'fw-bold loss';
        plElement.textContent = '-' + plFormatted;
    }
    
    // Reset form
    document.getElementById('closeType').value = 'full';
    document.getElementById('partialCloseOptions').classList.add('d-none');
    document.getElementById('closePercentage').value = 50;
    document.getElementById('percentageValue').textContent = '50%';
    
    modal.show();
}

// Close a position
function closePosition(symbol) {
    const closeType = document.getElementById('closeType').value;
    let data = {};
    
    if (closeType === 'partial') {
        const percentage = document.getElementById('closePercentage').value / 100;
        data = { percentage };
    }
    
    fetch(`/api/execution/close/${symbol}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('closePositionModal')).hide();
            
            // Refresh positions
            fetchPositions();
            
            // Show success message
            alert(`Position ${symbol} closed successfully`);
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error closing position:', error);
        alert('Error closing position. See console for details.');
    });
}

// Fetch performance data
function fetchPerformanceData(period = '1d') {
    // This would fetch actual performance data from the API
    // For now, we'll use the sample data from updateChartForPeriod
    
    // Also update the P/L display with sample values
    document.getElementById('todayPL')?.textContent = '$' + (Math.random() * 100 - 50).toFixed(2);
    document.getElementById('totalPL')?.textContent = '$' + (Math.random() * 1000).toFixed(2);
}

// Fetch system status
function fetchSystemStatus() {
    // Fetch strategy status
    fetch('/api/strategy/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStrategyStatus(data.detector.running);
            }
        })
        .catch(error => {
            console.error('Error fetching strategy status:', error);
        });
    
    // Fetch executor status
    fetch('/api/execution/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateExecutorStatus(data.executor.running);
            }
        })
        .catch(error => {
            console.error('Error fetching executor status:', error);
        });
}

// Update strategy status indicators
function updateStrategyStatus(isRunning) {
    const statusElement = document.getElementById('strategyStatus');
    if (!statusElement) return;
    
    statusElement.innerHTML = isRunning 
        ? '<span class="badge bg-success">Running</span>' 
        : '<span class="badge bg-secondary">Not Running</span>';
}

// Update executor status indicators
function updateExecutorStatus(isRunning) {
    const statusElement = document.getElementById('executorStatus');
    if (!statusElement) return;
    
    statusElement.innerHTML = isRunning 
        ? '<span class="badge bg-success">Running</span>' 
        : '<span class="badge bg-secondary">Not Running</span>';
}

// Service control functions
function startAllServices() {
    startStrategyService();
    startExecutionService();
}

function stopAllServices() {
    stopStrategyService();
    stopExecutionService();
}

function startStrategyService() {
    fetch('/api/strategy/start', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStrategyStatus(true);
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error starting strategy service:', error);
        });
}

function stopStrategyService() {
    fetch('/api/strategy/stop', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStrategyStatus(false);
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error stopping strategy service:', error);
        });
}

function startExecutionService() {
    fetch('/api/execution/start', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateExecutorStatus(true);
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error starting execution service:', error);
        });
}

function stopExecutionService() {
    fetch('/api/execution/stop', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateExecutorStatus(false);
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error stopping execution service:', error);
        });
}

function refreshMarketData() {
    fetch('/api/market/prices')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Refresh positions to reflect new prices
                fetchPositions();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error refreshing market data:', error);
        });
}

// Function to delete a signal
function deleteSignal(signalId) {
    if (!confirm('Are you sure you want to delete this signal?')) return;
    
    fetch(`/api/strategy/signals/${signalId}`, { 
        method: 'DELETE' 
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            fetchSignals();
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error deleting signal:', error);
    });
}