// Initialize Feather icons
document.addEventListener('DOMContentLoaded', function() {
    feather.replace();
    initializeApp();
});

// Global refresh intervals
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
    setupsRefreshInterval = setInterval(fetchSetups, 30000); // 30 seconds
    signalsRefreshInterval = setInterval(fetchSignals, 15000); // 15 seconds
    positionsRefreshInterval = setInterval(fetchPositions, 15000); // 15 seconds
    ordersRefreshInterval = setInterval(fetchOrders, 15000); // 15 seconds
}

function setupEventListeners() {
    // Tab handling
    const tradingTab = document.getElementById('tradingTab');
    if (tradingTab) {
        tradingTab.addEventListener('click', function(event) {
            if (event.target.getAttribute('data-bs-toggle') === 'tab') {
                const tabId = event.target.getAttribute('data-bs-target');
                localStorage.setItem('lastActiveTab', tabId);
            }
        });
        
        // Restore last active tab
        const lastActiveTab = localStorage.getItem('lastActiveTab');
        if (lastActiveTab) {
            const tab = new bootstrap.Tab(document.querySelector(`[data-bs-target="${lastActiveTab}"]`));
            tab.show();
        }
    }
    
    // Refresh buttons
    const refreshStatusBtn = document.getElementById('refreshStatusBtn');
    if (refreshStatusBtn) {
        refreshStatusBtn.addEventListener('click', fetchSystemStatus);
    }
    
    const refreshSignalsBtn = document.getElementById('refreshSignalsBtn');
    if (refreshSignalsBtn) {
        refreshSignalsBtn.addEventListener('click', fetchSignals);
    }
    
    const refreshPositionsBtn = document.getElementById('refreshPositionsBtn');
    if (refreshPositionsBtn) {
        refreshPositionsBtn.addEventListener('click', fetchPositions);
    }
    
    const refreshOrdersBtn = document.getElementById('refreshOrdersBtn');
    if (refreshOrdersBtn) {
        refreshOrdersBtn.addEventListener('click', fetchOrders);
    }
    
    // Form submissions
    const setupForm = document.getElementById('setupForm');
    if (setupForm) {
        setupForm.addEventListener('submit', function(event) {
            event.preventDefault();
            submitSetup();
        });
    }
    
    const tradeForm = document.getElementById('tradeForm');
    if (tradeForm) {
        tradeForm.addEventListener('submit', function(event) {
            event.preventDefault();
            submitTrade();
        });
        
        // Order type change handler for showing/hiding price fields
        const tradeType = document.getElementById('tradeType');
        if (tradeType) {
            tradeType.addEventListener('change', function() {
                const limitPriceRow = document.getElementById('limitPriceRow');
                const stopPriceRow = document.getElementById('stopPriceRow');
                
                switch (this.value) {
                    case 'limit':
                        limitPriceRow.style.display = 'flex';
                        stopPriceRow.style.display = 'none';
                        break;
                    case 'stop':
                        limitPriceRow.style.display = 'none';
                        stopPriceRow.style.display = 'flex';
                        break;
                    case 'stop_limit':
                        limitPriceRow.style.display = 'flex';
                        stopPriceRow.style.display = 'flex';
                        break;
                    default:
                        limitPriceRow.style.display = 'none';
                        stopPriceRow.style.display = 'none';
                        break;
                }
            });
        }
    }
    
    // Cancel order confirmation
    const confirmCancelBtn = document.getElementById('confirmCancelBtn');
    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', function() {
            const orderId = document.getElementById('orderToCancel').value;
            cancelOrder(orderId);
        });
    }
    
    // System control buttons
    const startAllBtn = document.getElementById('startAllBtn');
    if (startAllBtn) {
        startAllBtn.addEventListener('click', startAllServices);
    }
    
    const stopAllBtn = document.getElementById('stopAllBtn');
    if (stopAllBtn) {
        stopAllBtn.addEventListener('click', stopAllServices);
    }
    
    const startStrategyBtn = document.getElementById('startStrategyBtn');
    if (startStrategyBtn) {
        startStrategyBtn.addEventListener('click', startStrategyService);
    }
    
    const stopStrategyBtn = document.getElementById('stopStrategyBtn');
    if (stopStrategyBtn) {
        stopStrategyBtn.addEventListener('click', stopStrategyService);
    }
    
    const startExecutionBtn = document.getElementById('startExecutionBtn');
    if (startExecutionBtn) {
        startExecutionBtn.addEventListener('click', startExecutionService);
    }
    
    const stopExecutionBtn = document.getElementById('stopExecutionBtn');
    if (stopExecutionBtn) {
        stopExecutionBtn.addEventListener('click', stopExecutionService);
    }
}

// API functions
function fetchSystemStatus() {
    // Fetch strategy service status
    fetch('/api/strategy/status')
        .then(response => response.json())
        .then(data => {
            updateStrategyStatus(data);
        })
        .catch(error => {
            console.error('Error fetching strategy status:', error);
            document.getElementById('strategyStatus').textContent = 'Error';
            document.getElementById('strategyStatus').className = 'badge bg-danger float-end';
        });
    
    // Fetch execution service status
    fetch('/api/execution/status')
        .then(response => response.json())
        .then(data => {
            updateExecutionStatus(data);
        })
        .catch(error => {
            console.error('Error fetching execution status:', error);
            document.getElementById('executionStatus').textContent = 'Error';
            document.getElementById('executionStatus').className = 'badge bg-danger float-end';
        });
}

function updateStrategyStatus(data) {
    const statusElement = document.getElementById('strategyStatus');
    if (!statusElement) return;
    
    if (data.status === 'success') {
        if (data.running) {
            statusElement.textContent = 'Running';
            statusElement.className = 'badge bg-success float-end';
        } else {
            statusElement.textContent = 'Stopped';
            statusElement.className = 'badge bg-secondary float-end';
        }
    } else {
        statusElement.textContent = 'Error';
        statusElement.className = 'badge bg-danger float-end';
    }
}

function updateExecutionStatus(data) {
    const statusElement = document.getElementById('executionStatus');
    if (!statusElement) return;
    
    if (data.status === 'success') {
        if (data.running) {
            statusElement.textContent = 'Running';
            statusElement.className = 'badge bg-success float-end';
        } else {
            statusElement.textContent = 'Stopped';
            statusElement.className = 'badge bg-secondary float-end';
        }
    } else {
        statusElement.textContent = 'Error';
        statusElement.className = 'badge bg-danger float-end';
    }
}

function fetchSetups() {
    fetch('/api/setups')
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
    const noSetups = document.getElementById('noSetups');
    
    if (!setupsList || !noSetups) return;
    
    // Clear current setups
    setupsList.innerHTML = '';
    
    if (!setups || setups.length === 0) {
        noSetups.style.display = 'block';
        return;
    }
    
    noSetups.style.display = 'none';
    
    // Sort by date, newest first
    setups.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Display setups (limited to first 5)
    setups.slice(0, 5).forEach(setup => {
        const setupItem = document.createElement('div');
        setupItem.className = 'list-group-item';
        
        const date = new Date(setup.date);
        const formattedDate = date.toLocaleDateString();
        
        let tickerBadges = '';
        setup.setups.forEach(ticker => {
            tickerBadges += `<span class="badge bg-primary me-1">${ticker.symbol}</span>`;
        });
        
        setupItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <small class="text-muted">${formattedDate} - ${setup.source}</small>
                    <div class="mt-1">${tickerBadges}</div>
                </div>
                <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#setup${setup.id}">
                    <i data-feather="chevron-down"></i>
                </button>
            </div>
            <div class="collapse mt-2" id="setup${setup.id}">
                <div class="setup-text p-2 border rounded bg-dark">
                    ${setup.raw_text.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
        
        setupsList.appendChild(setupItem);
    });
    
    // Re-initialize feather icons
    feather.replace();
}

function submitSetup() {
    const date = document.getElementById('setupDate').value;
    const rawText = document.getElementById('setupText').value;
    const source = document.getElementById('setupSource').value;
    
    if (!date || !rawText) {
        alert('Please fill in all required fields.');
        return;
    }
    
    const setupData = {
        date: date,
        raw_text: rawText,
        source: source
    };
    
    fetch('/api/setups/manual', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(setupData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Clear form
            document.getElementById('setupText').value = '';
            
            // Refresh setups
            fetchSetups();
            
            alert('Setup submitted successfully!');
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error submitting setup:', error);
        alert('Error submitting setup. Please try again.');
    });
}

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
    
    if (!signalsList || !noSignalsMessage) return;
    
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

function updateSignalCounts(signals) {
    const signalCountElement = document.getElementById('signalCount');
    if (!signalCountElement) return;
    
    let totalActive = 0;
    
    // Count total active signals
    for (const symbol in signals) {
        totalActive += signals[symbol].length;
    }
    
    signalCountElement.textContent = totalActive;
}

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
                
                // Update position count
                const positionCountElement = document.getElementById('positionCount');
                if (positionCountElement) {
                    positionCountElement.textContent = data.positions.length;
                }
            } else {
                console.error('Error fetching positions:', data.message);
            }
        })
        .catch(error => console.error('Error fetching positions:', error));
}

function displayPositions(positions) {
    const positionsList = document.getElementById('positionsList');
    const noPositionsRow = document.getElementById('noPositionsRow');
    
    if (!positionsList || !noPositionsRow) return;
    
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
            
            document.getElementById('closePositionSymbol').textContent = symbol;
            document.getElementById('closePositionPL').textContent = '$' + pl;
            document.getElementById('positionToClose').value = symbol;
        });
    });
}

function closePosition(symbol, profitLoss) {
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
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error closing position:', error);
        alert('Error closing position. Please try again.');
    });
}

function fetchOrders() {
    fetch('/api/execution/orders')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayOrders(data.orders);
                
                // Update order count
                const orderCountElement = document.getElementById('orderCount');
                if (orderCountElement) {
                    orderCountElement.textContent = data.orders.length;
                }
            } else {
                console.error('Error fetching orders:', data.message);
            }
        })
        .catch(error => console.error('Error fetching orders:', error));
}

function displayOrders(orders) {
    const ordersList = document.getElementById('ordersList');
    const noOrdersRow = document.getElementById('noOrdersRow');
    
    if (!ordersList || !noOrdersRow) return;
    
    // Clear current orders (except for the "no orders" row)
    Array.from(ordersList.children).forEach(child => {
        if (child.id !== 'noOrdersRow') {
            child.remove();
        }
    });
    
    if (!orders || orders.length === 0) {
        noOrdersRow.style.display = 'table-row';
        return;
    }
    
    noOrdersRow.style.display = 'none';
    
    // Display orders
    orders.forEach(order => {
        const row = document.createElement('tr');
        
        const createdDate = new Date(order.created_at);
        const formattedDate = createdDate.toLocaleString();
        
        const isBuy = order.side === 'buy';
        
        row.innerHTML = `
            <td>${order.symbol}</td>
            <td>${order.type}</td>
            <td><span class="badge ${isBuy ? 'bg-success' : 'bg-danger'}">${order.side}</span></td>
            <td>${order.quantity}</td>
            <td>${order.limit_price ? '$' + parseFloat(order.limit_price).toFixed(2) : 'Market'}</td>
            <td><span class="badge bg-info">${order.status}</span></td>
            <td>${formattedDate}</td>
            <td>
                <button class="btn btn-sm btn-danger cancel-order-btn" 
                    data-order-id="${order.id}" 
                    data-bs-toggle="modal" 
                    data-bs-target="#cancelOrderModal">
                    <i data-feather="x"></i>
                </button>
            </td>
        `;
        
        ordersList.appendChild(row);
    });
    
    // Re-initialize feather icons
    feather.replace();
    
    // Re-attach event listeners
    document.querySelectorAll('.cancel-order-btn').forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            document.getElementById('orderToCancel').value = orderId;
        });
    });
}

function submitTrade() {
    const symbol = document.getElementById('tradeSymbol').value;
    const side = document.getElementById('tradeSide').value;
    const quantity = document.getElementById('tradeQuantity').value;
    const type = document.getElementById('tradeType').value;
    const limitPrice = document.getElementById('limitPrice')?.value;
    const stopPrice = document.getElementById('stopPrice')?.value;
    const extendedHours = document.getElementById('extendedHours')?.checked;
    
    if (!symbol || !quantity || quantity <= 0) {
        alert('Please fill in all required fields.');
        return;
    }
    
    const orderData = {
        symbol: symbol,
        side: side,
        quantity: parseInt(quantity),
        type: type,
        time_in_force: 'day',
        extended_hours: extendedHours || false
    };
    
    if (type === 'limit' || type === 'stop_limit') {
        if (!limitPrice || limitPrice <= 0) {
            alert('Please enter a valid limit price.');
            return;
        }
        orderData.limit_price = parseFloat(limitPrice);
    }
    
    if (type === 'stop' || type === 'stop_limit') {
        if (!stopPrice || stopPrice <= 0) {
            alert('Please enter a valid stop price.');
            return;
        }
        orderData.stop_price = parseFloat(stopPrice);
    }
    
    fetch('/api/execution/trade', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Clear form
            document.getElementById('tradeSymbol').value = '';
            document.getElementById('tradeQuantity').value = '1';
            
            if (document.getElementById('limitPrice')) {
                document.getElementById('limitPrice').value = '';
            }
            
            if (document.getElementById('stopPrice')) {
                document.getElementById('stopPrice').value = '';
            }
            
            // Refresh orders
            fetchOrders();
            
            alert('Order placed successfully!');
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error placing order:', error);
        alert('Error placing order. Please try again.');
    });
}

function cancelOrder(orderId) {
    fetch(`/api/execution/cancel/${orderId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('cancelOrderModal'));
            modal.hide();
            
            // Refresh orders
            fetchOrders();
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error canceling order:', error);
        alert('Error canceling order. Please try again.');
    });
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
    fetch('/api/strategy/start', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStrategyStatus({ status: 'success', running: true });
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error starting strategy service:', error);
        alert('Error starting strategy service. Please try again.');
    });
}

function stopStrategyService() {
    fetch('/api/strategy/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStrategyStatus({ status: 'success', running: false });
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error stopping strategy service:', error);
        alert('Error stopping strategy service. Please try again.');
    });
}

function startExecutionService() {
    fetch('/api/execution/start', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateExecutionStatus({ status: 'success', running: true });
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error starting execution service:', error);
        alert('Error starting execution service. Please try again.');
    });
}

function stopExecutionService() {
    fetch('/api/execution/stop', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateExecutionStatus({ status: 'success', running: false });
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error stopping execution service:', error);
        alert('Error stopping execution service. Please try again.');
    });
}