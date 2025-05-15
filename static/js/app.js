// Initialize Feather icons
document.addEventListener('DOMContentLoaded', function() {
    feather.replace();
    initializeApp();
});

// Global refresh intervals
let statusRefreshInterval;
let setupsRefreshInterval;
let signalsRefreshInterval;
let positionsRefreshInterval;
let ordersRefreshInterval;

function initializeApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Initial data loads
    fetchSystemStatus();
    fetchSetups();
    fetchSignals();
    fetchPositionsAndOrders();
    
    // Set up refresh intervals
    statusRefreshInterval = setInterval(fetchSystemStatus, 10000); // 10 seconds
    setupsRefreshInterval = setInterval(fetchSetups, 30000); // 30 seconds
    signalsRefreshInterval = setInterval(fetchSignals, 15000); // 15 seconds
    positionsRefreshInterval = setInterval(fetchPositions, 20000); // 20 seconds
    ordersRefreshInterval = setInterval(fetchOrders, 20000); // 20 seconds
}

function setupEventListeners() {
    // Start/Stop buttons
    document.getElementById('startAllBtn').addEventListener('click', startAllServices);
    document.getElementById('stopAllBtn').addEventListener('click', stopAllServices);
    
    // Setup form submission
    document.getElementById('submitSetupBtn').addEventListener('click', submitSetup);
    
    // Trade form submission
    document.getElementById('submitTradeBtn').addEventListener('click', submitTrade);
    
    // Tab changes for refreshing data
    document.getElementById('positions-tab').addEventListener('click', fetchPositions);
    document.getElementById('orders-tab').addEventListener('click', fetchOrders);
}

// System Status Functions
function fetchSystemStatus() {
    // Fetch strategy status
    fetch('/api/strategy/status')
        .then(response => response.json())
        .then(data => {
            updateStrategyStatus(data);
        })
        .catch(error => console.error('Error fetching strategy status:', error));
    
    // Fetch execution status
    fetch('/api/execution/status')
        .then(response => response.json())
        .then(data => {
            updateExecutionStatus(data);
        })
        .catch(error => console.error('Error fetching execution status:', error));
}

function updateStrategyStatus(data) {
    const strategyStatus = document.getElementById('strategyStatus');
    const strategyStatusBadge = document.getElementById('strategyStatusBadge');
    
    if (data.status === 'success' && data.detector && data.detector.running) {
        strategyStatus.classList.remove('status-inactive');
        strategyStatus.classList.add('status-active');
        strategyStatusBadge.textContent = 'Active';
        strategyStatusBadge.classList.remove('bg-danger');
        strategyStatusBadge.classList.add('bg-success');
        
        // Update signal counts
        document.getElementById('activeSignalsCount').textContent = data.detector.active_signals || 0;
    } else {
        strategyStatus.classList.remove('status-active');
        strategyStatus.classList.add('status-inactive');
        strategyStatusBadge.textContent = 'Inactive';
        strategyStatusBadge.classList.remove('bg-success');
        strategyStatusBadge.classList.add('bg-danger');
    }
}

function updateExecutionStatus(data) {
    const executionStatus = document.getElementById('executionStatus');
    const executionStatusBadge = document.getElementById('executionStatusBadge');
    
    if (data.status === 'success' && data.executor && data.executor.running) {
        executionStatus.classList.remove('status-inactive');
        executionStatus.classList.add('status-active');
        executionStatusBadge.textContent = 'Active';
        executionStatusBadge.classList.remove('bg-danger');
        executionStatusBadge.classList.add('bg-success');
    } else {
        executionStatus.classList.remove('status-active');
        executionStatus.classList.add('status-inactive');
        executionStatusBadge.textContent = 'Inactive';
        executionStatusBadge.classList.remove('bg-success');
        executionStatusBadge.classList.add('bg-danger');
    }
}

// Setups Functions
function fetchSetups() {
    fetch('/api/setups/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displaySetups(data.setups);
            } else {
                console.error('Error fetching setups:', data.message);
            }
        })
        .catch(error => console.error('Error fetching setups:', error));
}

function displaySetups(setups) {
    const setupsList = document.getElementById('setupsList');
    
    // Clear current content except for empty state
    setupsList.innerHTML = '';
    
    if (!setups || setups.length === 0) {
        setupsList.innerHTML = `
            <div class="text-center py-4 text-muted">
                <i data-feather="inbox" style="width: 48px; height: 48px;"></i>
                <p class="mt-2">No setups available</p>
            </div>
        `;
        feather.replace();
        return;
    }
    
    // Display the first 5 most recent setups
    const recentSetups = setups.slice(0, 5);
    
    recentSetups.forEach(setup => {
        const createdDate = new Date(setup.created_at);
        const formattedDate = createdDate.toLocaleString();
        
        const setupTickers = setup.setups.map(s => s.symbol).join(', ');
        
        const setupItem = document.createElement('div');
        setupItem.className = 'card setup-card mb-3';
        
        setupItem.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <span class="badge bg-secondary">${setup.source}</span>
                        <small class="text-muted ms-2">${formattedDate}</small>
                    </div>
                    <div>
                        <span class="badge bg-primary ticker-badge">${setupTickers}</span>
                    </div>
                </div>
                <p class="setup-text">${setup.raw_text}</p>
            </div>
        `;
        
        setupsList.appendChild(setupItem);
    });
}

function submitSetup() {
    const setupText = document.getElementById('setupText').value.trim();
    
    if (!setupText) {
        alert('Please enter setup text');
        return;
    }
    
    // Send to API
    fetch('/api/setups/manual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            raw_text: setupText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal and refresh setups
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualSetupModal'));
            modal.hide();
            
            // Clear form
            document.getElementById('setupText').value = '';
            
            // Refresh setups
            fetchSetups();
            
            // Refresh signals after a delay to allow processing
            setTimeout(fetchSignals, 1000);
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error submitting setup:', error);
        alert('Error submitting setup. Please try again.');
    });
}

// Signals Functions
function fetchSignals() {
    fetch('/api/strategy/signals')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displaySignals(data.signals);
                updateSignalCounts(data.signals);
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
        
        // Display signals
        allSignals.forEach(signal => {
            const signalItem = document.createElement('div');
            signalItem.className = `list-group-item signal-${signal.status}`;
            
            const createdDate = new Date(signal.created_at);
            const formattedDate = createdDate.toLocaleString();
            
            let statusBadge = '<span class="badge bg-warning">Pending</span>';
            if (signal.status === 'triggered') {
                statusBadge = '<span class="badge bg-success">Triggered</span>';
                
                // Add triggered date if available
                if (signal.triggered_at) {
                    const triggeredDate = new Date(signal.triggered_at);
                    const formattedTriggeredDate = triggeredDate.toLocaleString();
                    formattedDate += ` ➜ ${formattedTriggeredDate}`;
                }
            }
            
            signalItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5 class="mb-1">
                        <span class="badge bg-primary">${signal.symbol}</span>
                        ${signal.category} ${signal.comparison} $${signal.trigger}
                    </h5>
                    ${statusBadge}
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">Created: ${formattedDate}</small>
                    <small class="text-muted">Aggressiveness: ${signal.aggressiveness}</small>
                </div>
                ${signal.targets && signal.targets.length > 0 ? 
                    `<div class="mt-2">
                        <small>Targets: ${signal.targets.map(t => '$' + t).join(', ')}</small>
                    </div>` : ''}
            `;
            
            signalsList.appendChild(signalItem);
        });
    } else {
        noSignalsMessage.style.display = 'block';
    }
}

function updateSignalCounts(signals) {
    let totalActive = 0;
    let pending = 0;
    let triggered = 0;
    
    // Count signals by status
    for (const symbol in signals) {
        signals[symbol].forEach(signal => {
            totalActive++;
            if (signal.status === 'pending') {
                pending++;
            } else if (signal.status === 'triggered') {
                triggered++;
            }
        });
    }
    
    // Update UI
    document.getElementById('activeSignalsCount').textContent = totalActive;
    document.getElementById('pendingSignalsCount').textContent = pending;
    document.getElementById('triggeredSignalsCount').textContent = triggered;
}

// Positions and Orders Functions
function fetchPositionsAndOrders() {
    fetchPositions();
    fetchOrders();
}

function fetchPositions() {
    fetch('/api/execution/positions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayPositions(data.positions);
                document.getElementById('openPositionsCount').textContent = data.positions.length;
            } else {
                console.error('Error fetching positions:', data.message);
            }
        })
        .catch(error => console.error('Error fetching positions:', error));
}

function displayPositions(positions) {
    const positionsList = document.getElementById('positionsList');
    const noPositionsMessage = document.getElementById('noPositionsMessage');
    
    // Clear current positions
    positionsList.innerHTML = '';
    
    if (!positions || positions.length === 0) {
        noPositionsMessage.style.display = 'block';
        return;
    }
    
    noPositionsMessage.style.display = 'none';
    
    // Display positions
    positions.forEach(position => {
        const isLong = position.side === 'long';
        const profitLoss = parseFloat(position.unrealized_pl);
        const plClass = profitLoss > 0 ? 'text-success' : (profitLoss < 0 ? 'text-danger' : '');
        
        const positionRow = document.createElement('div');
        positionRow.className = 'card mb-2';
        
        positionRow.innerHTML = `
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="mb-0">
                            <span class="badge ${isLong ? 'bg-success' : 'bg-danger'}">${position.symbol}</span>
                            <span class="ms-2">${isLong ? 'LONG' : 'SHORT'} ${position.quantity}</span>
                        </h5>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-danger position-close-btn" data-symbol="${position.symbol}">
                            <i data-feather="x"></i> Close
                        </button>
                    </div>
                </div>
                <div class="d-flex justify-content-between mt-2">
                    <div>Entry: $${parseFloat(position.avg_entry_price).toFixed(2)}</div>
                    <div>Current: $${parseFloat(position.current_price).toFixed(2)}</div>
                    <div class="${plClass}">P&L: $${profitLoss.toFixed(2)} (${(parseFloat(position.unrealized_plpc) * 100).toFixed(2)}%)</div>
                </div>
            </div>
        `;
        
        positionsList.appendChild(positionRow);
        
        // Add event listener to close button
        const closeBtn = positionRow.querySelector('.position-close-btn');
        closeBtn.addEventListener('click', () => {
            closePosition(position.symbol, profitLoss.toFixed(2));
        });
    });
    
    // Re-initialize feather icons
    feather.replace();
}

function closePosition(symbol, profitLoss) {
    if (confirm(`Are you sure you want to close your position in ${symbol}? Current P&L: $${profitLoss}`)) {
        fetch(`/api/execution/close/${symbol}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Refresh positions
                fetchPositions();
                
                // Refresh orders after a delay
                setTimeout(fetchOrders, 1000);
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error closing position:', error);
            alert('Error closing position. Please try again.');
        });
    }
}

function fetchOrders() {
    fetch('/api/execution/orders')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayOrders(data.orders);
                
                // Count pending orders
                const pendingOrders = data.orders.filter(order => 
                    order.status === 'new' || order.status === 'accepted' || order.status === 'pending_new'
                );
                
                document.getElementById('pendingOrdersCount').textContent = pendingOrders.length;
            } else {
                console.error('Error fetching orders:', data.message);
            }
        })
        .catch(error => console.error('Error fetching orders:', error));
}

function displayOrders(orders) {
    const ordersList = document.getElementById('ordersList');
    const noOrdersMessage = document.getElementById('noOrdersMessage');
    
    // Clear current orders
    ordersList.innerHTML = '';
    
    if (!orders || orders.length === 0) {
        noOrdersMessage.style.display = 'block';
        return;
    }
    
    noOrdersMessage.style.display = 'none';
    
    // Sort orders by created_at, most recent first
    orders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // Display only the 10 most recent orders
    const recentOrders = orders.slice(0, 10);
    
    // Display orders
    recentOrders.forEach(order => {
        let statusBadge;
        switch (order.status) {
            case 'filled':
                statusBadge = '<span class="badge bg-success">Filled</span>';
                break;
            case 'canceled':
            case 'rejected':
                statusBadge = '<span class="badge bg-danger">' + order.status.charAt(0).toUpperCase() + order.status.slice(1) + '</span>';
                break;
            case 'new':
            case 'accepted':
            case 'pending_new':
                statusBadge = '<span class="badge bg-warning">Pending</span>';
                break;
            default:
                statusBadge = '<span class="badge bg-secondary">' + order.status.charAt(0).toUpperCase() + order.status.slice(1) + '</span>';
        }
        
        const orderDate = new Date(order.created_at);
        const formattedDate = orderDate.toLocaleString();
        
        const orderRow = document.createElement('div');
        orderRow.className = 'card mb-2';
        
        orderRow.innerHTML = `
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="mb-0">
                            <span class="badge bg-primary">${order.symbol}</span>
                            <span class="ms-2 ${order.side === 'buy' ? 'text-success' : 'text-danger'}">${order.side.toUpperCase()} ${order.quantity}</span>
                        </h5>
                    </div>
                    <div>
                        ${statusBadge}
                    </div>
                </div>
                <div class="d-flex justify-content-between mt-2">
                    <div>Type: ${order.type.charAt(0).toUpperCase() + order.type.slice(1)}</div>
                    <div>Created: ${formattedDate}</div>
                    ${order.filled_price ? `<div>Fill Price: $${parseFloat(order.filled_price).toFixed(2)}</div>` : ''}
                </div>
            </div>
        `;
        
        ordersList.appendChild(orderRow);
    });
}

function submitTrade() {
    const symbol = document.getElementById('tradeSymbol').value.trim().toUpperCase();
    const direction = document.querySelector('input[name="direction"]:checked').value;
    const quantity = parseInt(document.getElementById('tradeQuantity').value);
    
    if (!symbol) {
        alert('Please enter a symbol');
        return;
    }
    
    if (isNaN(quantity) || quantity <= 0) {
        alert('Please enter a valid quantity');
        return;
    }
    
    // Send to API
    fetch('/api/execution/trade', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            symbol: symbol,
            direction: direction,
            quantity: quantity,
            order_type: 'market'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close modal and refresh positions/orders
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualTradeModal'));
            modal.hide();
            
            // Clear form
            document.getElementById('tradeSymbol').value = '';
            document.getElementById('tradeQuantity').value = '1';
            
            // Refresh data
            setTimeout(() => {
                fetchPositions();
                fetchOrders();
            }, 1000);
            
            alert('Trade submitted successfully!');
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error submitting trade:', error);
        alert('Error submitting trade. Please try again.');
    });
}

// Service control functions
function startAllServices() {
    startStrategyService()
        .then(() => startExecutionService())
        .then(() => {
            alert('All services started');
            fetchSystemStatus();
        })
        .catch(error => {
            console.error('Error starting services:', error);
            alert('Error starting services. Check console for details.');
        });
}

function stopAllServices() {
    stopStrategyService()
        .then(() => stopExecutionService())
        .then(() => {
            alert('All services stopped');
            fetchSystemStatus();
        })
        .catch(error => {
            console.error('Error stopping services:', error);
            alert('Error stopping services. Check console for details.');
        });
}

function startStrategyService() {
    return fetch('/api/strategy/start', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to start strategy service');
        }
        return data;
    });
}

function stopStrategyService() {
    return fetch('/api/strategy/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to stop strategy service');
        }
        return data;
    });
}

function startExecutionService() {
    return fetch('/api/execution/start', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to start execution service');
        }
        return data;
    });
}

function stopExecutionService() {
    return fetch('/api/execution/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to stop execution service');
        }
        return data;
    });
}
