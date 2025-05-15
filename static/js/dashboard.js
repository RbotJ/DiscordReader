// Initialize Feather icons
document.addEventListener('DOMContentLoaded', function() {
    feather.replace();
    initializeDashboard();
});

// Global refresh intervals
let positionsRefreshInterval;
let signalsRefreshInterval;
let tradeHistoryRefreshInterval;
let performanceRefreshInterval;

function initializeDashboard() {
    // Initialize Chart.js components
    initializeCharts();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initial data loads
    fetchPositions();
    fetchSignals();
    fetchPerformanceData();
    fetchTradeHistory();
    
    // Set up refresh intervals
    positionsRefreshInterval = setInterval(fetchPositions, 15000); // 15 seconds
    signalsRefreshInterval = setInterval(fetchSignals, 30000); // 30 seconds
    tradeHistoryRefreshInterval = setInterval(fetchTradeHistory, 60000); // 1 minute
    performanceRefreshInterval = setInterval(fetchPerformanceData, 60000); // 1 minute
}

function setupEventListeners() {
    // Chart period selection
    const periodButtons = document.querySelectorAll('[data-period]');
    periodButtons.forEach(button => {
        button.addEventListener('click', function() {
            const period = this.getAttribute('data-period');
            // Remove active class from all buttons
            periodButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update chart for selected period
            updateChartForPeriod(period);
        });
    });
    
    // Position close modal
    document.querySelectorAll('.close-position-btn').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            const pl = this.getAttribute('data-pl');
            prepareClosePositionModal(symbol, pl);
        });
    });
    
    // Confirm close position
    document.getElementById('confirmCloseBtn').addEventListener('click', function() {
        const symbol = document.getElementById('positionToClose').value;
        closePosition(symbol);
    });
}

// Initialize charts
function initializeCharts() {
    const ctx = document.getElementById('equityChart').getContext('2d');
    
    // Sample data (will be replaced with real data)
    const labels = Array.from({length: 30}, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (30 - i - 1));
        return d.toLocaleDateString();
    });
    
    const data = {
        labels: labels,
        datasets: [{
            label: 'Equity',
            data: Array.from({length: 30}, (_, i) => 10000 + Math.random() * 2000 - 1000),
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            fill: true,
            tension: 0.4
        }]
    };
    
    const config = {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return '$' + context.raw.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    };
    
    window.equityChart = new Chart(ctx, config);
}

function updateChartForPeriod(period) {
    // This would be updated with real data from the API
    let days;
    switch(period) {
        case '1d':
            days = 1;
            break;
        case '1w':
            days = 7;
            break;
        case '1m':
            days = 30;
            break;
        case 'ytd':
            const now = new Date();
            const startOfYear = new Date(now.getFullYear(), 0, 1);
            days = Math.floor((now - startOfYear) / (24 * 60 * 60 * 1000));
            break;
        default:
            days = 30;
    }
    
    // Update chart data
    // For now, we're using placeholder data
    const labels = Array.from({length: days}, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (days - i - 1));
        return d.toLocaleDateString();
    });
    
    window.equityChart.data.labels = labels;
    window.equityChart.data.datasets[0].data = Array.from({length: days}, (_, i) => 10000 + Math.random() * 2000 - 1000);
    window.equityChart.update();
}

// API functions
function fetchPositions() {
    fetch('/api/execution/positions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayPositions(data.positions);
                updatePositionCount(data.positions.length);
            } else {
                console.error('Error fetching positions:', data.message);
            }
        })
        .catch(error => console.error('Error fetching positions:', error));
}

function displayPositions(positions) {
    const positionsList = document.getElementById('positionsList');
    const noPositionsRow = document.getElementById('noPositionsRow');
    
    // Clear current positions (except for the "no positions" row)
    Array.from(positionsList.children).forEach(child => {
        if (child.id !== 'noPositionsRow') {
            child.remove();
        }
    });
    
    if (!positions || positions.length === 0) {
        noPositionsRow.style.display = 'table-row';
        return;
    }
    
    noPositionsRow.style.display = 'none';
    
    // Display positions
    positions.forEach(position => {
        const isLong = position.side === 'long';
        const profitLoss = parseFloat(position.unrealized_pl);
        const plClass = profitLoss > 0 ? 'positive-value' : (profitLoss < 0 ? 'negative-value' : 'neutral-value');
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><span class="badge ${isLong ? 'bg-success' : 'bg-danger'}">${position.symbol}</span></td>
            <td>${position.quantity}</td>
            <td>$${parseFloat(position.avg_entry_price).toFixed(2)}</td>
            <td>$${parseFloat(position.current_price).toFixed(2)}</td>
            <td class="${plClass}">$${profitLoss.toFixed(2)} (${(parseFloat(position.unrealized_plpc) * 100).toFixed(2)}%)</td>
            <td>
                <button class="btn btn-sm btn-danger close-position-btn" 
                    data-symbol="${position.symbol}" 
                    data-pl="${profitLoss.toFixed(2)}"
                    data-bs-toggle="modal" 
                    data-bs-target="#closePositionModal">
                    <i data-feather="x"></i>
                </button>
            </td>
        `;
        
        positionsList.appendChild(row);
    });
    
    // Re-initialize feather icons
    feather.replace();
    
    // Re-attach event listeners
    document.querySelectorAll('.close-position-btn').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            const pl = this.getAttribute('data-pl');
            prepareClosePositionModal(symbol, pl);
        });
    });
}

function fetchSignals() {
    fetch('/api/strategy/signals')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displaySignals(data.signals);
                updateSignalCount(data.signals);
            } else {
                console.error('Error fetching signals:', data.message);
            }
        })
        .catch(error => console.error('Error fetching signals:', error));
}

function displaySignals(signals) {
    const signalsList = document.getElementById('signalsList');
    const noSignalsMessage = document.getElementById('noSignalsMessage');
    
    // Clear current signals
    signalsList.innerHTML = '';
    
    // Check if we have any signals
    const hasSignals = signals && Object.keys(signals).length > 0;
    
    if (hasSignals) {
        noSignalsMessage.style.display = 'none';
        
        // Flatten the signals object
        let allSignals = [];
        for (const symbol in signals) {
            signals[symbol].forEach(signal => {
                signal.symbol = symbol; // Ensure symbol is included
                allSignals.push(signal);
            });
        }
        
        // Sort by created_at, most recent first
        allSignals.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        // Display signals (limited to first 10)
        allSignals.slice(0, 10).forEach(signal => {
            const signalItem = document.createElement('div');
            signalItem.className = `list-group-item signal-list-item ${signal.status === 'triggered' ? 'signal-triggered' : ''}`;
            
            const createdDate = new Date(signal.created_at);
            const formattedDate = createdDate.toLocaleString();
            
            let statusBadge = '<span class="badge bg-warning">Pending</span>';
            if (signal.status === 'triggered') {
                statusBadge = '<span class="badge bg-success">Triggered</span>';
            }
            
            signalItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-primary">${signal.symbol}</span>
                    <small>${signal.category} ${signal.comparison} $${signal.trigger}</small>
                    ${statusBadge}
                </div>
                <small class="text-muted d-block mt-1">${formattedDate}</small>
            `;
            
            signalsList.appendChild(signalItem);
        });
    } else {
        noSignalsMessage.style.display = 'block';
    }
}

function updateSignalCount(signals) {
    let totalActive = 0;
    
    // Count total active signals
    for (const symbol in signals) {
        totalActive += signals[symbol].length;
    }
    
    // Update UI
    document.getElementById('activeSignalsCount').textContent = totalActive;
}

function updatePositionCount(count) {
    document.getElementById('openPositionsCount').textContent = count;
}

function prepareClosePositionModal(symbol, pl) {
    document.getElementById('closePositionSymbol').textContent = symbol;
    document.getElementById('closePositionPL').textContent = '$' + pl;
    document.getElementById('positionToClose').value = symbol;
}

function closePosition(symbol) {
    fetch(`/api/execution/close/${symbol}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('closePositionModal'));
            modal.hide();
            
            // Refresh positions
            fetchPositions();
            
            // Refresh other data that might be affected
            fetchTradeHistory();
            fetchPerformanceData();
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error closing position:', error);
        alert('Error closing position. Please try again.');
    });
}

function fetchPerformanceData() {
    // This would be replaced with real API call
    // For now, using placeholder data
    const performanceData = {
        total_pl: 2567.89,
        today_pl: 234.56,
        win_rate: 68.5,
        avg_trade: 123.45
    };
    
    // Update UI
    document.getElementById('totalPL').textContent = '$' + performanceData.total_pl.toFixed(2);
    document.getElementById('totalPL').className = performanceData.total_pl >= 0 ? 'positive-value' : 'negative-value';
    
    document.getElementById('todayPL').textContent = '$' + performanceData.today_pl.toFixed(2);
    document.getElementById('todayPL').className = performanceData.today_pl >= 0 ? 'positive-value' : 'negative-value';
    
    document.getElementById('winRate').textContent = performanceData.win_rate.toFixed(1) + '%';
    
    document.getElementById('avgTrade').textContent = '$' + performanceData.avg_trade.toFixed(2);
    document.getElementById('avgTrade').className = performanceData.avg_trade >= 0 ? 'positive-value' : 'negative-value';
}

function fetchTradeHistory() {
    // This would be replaced with real API call
    // For now, using placeholder data
    const tradesList = document.getElementById('recentTradesList');
    const noTradesRow = document.getElementById('noTradesRow');
    
    // Clear current trades (except for the "no trades" row)
    Array.from(tradesList.children).forEach(child => {
        if (child.id !== 'noTradesRow') {
            child.remove();
        }
    });
    
    // Display "No trades" message (for now)
    noTradesRow.style.display = 'table-row';
}