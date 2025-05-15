// Global state
let notifications = [];
let systemStatus = "connecting";
let activeSignals = [];
let recentTrades = [];
let optionContracts = [];
let currentOptionSymbol = "";
let optionViewType = "calls"; // 'calls' or 'puts'

// Initialize dashboard when page loads
function initDashboard() {
    // Start periodic updates
    fetchSystemStatus();
    fetchActiveSignals();
    fetchPositions();
    fetchNotifications();
    
    // Initialize charts
    initPerformanceChart();
    
    // Set up notification refresh
    setInterval(fetchNotifications, 30000);
    
    // Set up system status refresh
    setInterval(fetchSystemStatus, 15000);
    
    // Set up notification panel toggle
    document.addEventListener('click', function(e) {
        if (e.target.closest('#system-status-indicator') || e.target.closest('#system-status-text')) {
            toggleNotificationPanel();
        }
    });
    
    // Clear notifications button
    document.getElementById('clearNotifications')?.addEventListener('click', function() {
        clearNotifications();
    });
}

// Initialize setup page functionality
function initSetupPage() {
    // Setup parser form
    initSetupParserForm();
    
    // Manual setup form
    const hasBiasSwitch = document.getElementById('has-bias-switch');
    if (hasBiasSwitch) {
        hasBiasSwitch.addEventListener('change', function() {
            document.getElementById('bias-container').style.display = this.checked ? 'block' : 'none';
        });
    }
    
    const hasFlipSwitch = document.getElementById('has-flip-switch');
    if (hasFlipSwitch) {
        hasFlipSwitch.addEventListener('change', function() {
            document.getElementById('flip-container').style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Add signal button
    const addSignalBtn = document.getElementById('add-signal-btn');
    if (addSignalBtn) {
        addSignalBtn.addEventListener('click', function() {
            const category = document.getElementById('signal-category').value;
            const comparison = document.getElementById('signal-comparison').value;
            const trigger = document.getElementById('signal-trigger').value;
            
            if (!trigger) {
                return alert('Please enter a trigger price');
            }
            
            const signalList = document.getElementById('signal-list');
            const signalItem = document.createElement('div');
            signalItem.className = 'signal-item badge bg-primary me-2 mb-2';
            signalItem.innerHTML = `${category} ${comparison} ${trigger} <button type="button" class="btn-close btn-close-white ms-1" aria-label="Remove"></button>`;
            signalList.appendChild(signalItem);
            
            // Add remove listener
            signalItem.querySelector('.btn-close').addEventListener('click', function() {
                signalItem.remove();
            });
            
            // Clear input
            document.getElementById('signal-trigger').value = '';
        });
    }
    
    // Add target button
    const addTargetBtn = document.getElementById('add-target-btn');
    if (addTargetBtn) {
        addTargetBtn.addEventListener('click', function() {
            const targetPrice = document.getElementById('target-price').value;
            
            if (!targetPrice) {
                return alert('Please enter a target price');
            }
            
            const targetsList = document.getElementById('targets-list');
            const targetItem = document.createElement('span');
            targetItem.className = 'badge bg-success me-2 mb-2';
            targetItem.innerHTML = `${targetPrice} <button type="button" class="btn-close btn-close-white ms-1" aria-label="Remove"></button>`;
            targetsList.appendChild(targetItem);
            
            // Add remove listener
            targetItem.querySelector('.btn-close').addEventListener('click', function() {
                targetItem.remove();
            });
            
            // Clear input
            document.getElementById('target-price').value = '';
        });
    }
    
    // Setup message form
    const setupMessageForm = document.getElementById('setup-message-form');
    if (setupMessageForm) {
        setupMessageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const messageText = document.getElementById('setup-message-input').value;
            
            if (!messageText) {
                return alert('Please enter a setup message');
            }
            
            // Create a loading indicator
            const modal = setupMessageForm.closest('.modal');
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Parsing setup message...</p>';
            setupMessageForm.appendChild(loadingMsg);
            
            // Disable form
            const formElements = setupMessageForm.querySelectorAll('input, textarea, button');
            formElements.forEach(el => el.disabled = true);
            
            // Submit to API
            fetch('/api/setups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    raw_text: messageText
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert(`Setup parsed successfully! Found ${data.data.ticker_count} tickers.`);
                    
                    // Close modal and refresh page
                    bootstrap.Modal.getInstance(modal).hide();
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator and re-enable form
                    loadingMsg.remove();
                    formElements.forEach(el => el.disabled = false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator and re-enable form
                loadingMsg.remove();
                formElements.forEach(el => el.disabled = false);
            });
        });
    }
    
    // Manual setup form
    const manualSetupForm = document.getElementById('manual-setup-form');
    if (manualSetupForm) {
        manualSetupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Collect basic info
            const symbol = document.getElementById('manual-symbol').value;
            
            if (!symbol) {
                return alert('Please enter a symbol');
            }
            
            // Collect signals
            const signalItems = document.querySelectorAll('#signal-list .signal-item');
            if (signalItems.length === 0) {
                return alert('Please add at least one signal');
            }
            
            const signals = [];
            signalItems.forEach(item => {
                const text = item.textContent.trim();
                const parts = text.split(' ');
                
                // Extract category, comparison, and trigger
                const category = parts[0];
                const comparison = parts[1];
                const trigger = parseFloat(parts[2]);
                
                // Collect targets
                const targetItems = document.querySelectorAll('#targets-list .badge');
                const targets = [];
                targetItems.forEach(item => {
                    targets.push(parseFloat(item.textContent.trim()));
                });
                
                signals.push({
                    category: category,
                    comparison: comparison,
                    trigger: trigger,
                    targets: targets.length > 0 ? targets : [trigger * (category === 'breakout' || category === 'bounce' ? 1.05 : 0.95)]
                });
            });
            
            // Collect bias if enabled
            let bias = null;
            if (document.getElementById('has-bias-switch').checked) {
                const direction = document.getElementById('bias-direction').value;
                const condition = document.getElementById('bias-condition').value;
                const price = parseFloat(document.getElementById('bias-price').value);
                
                if (!price) {
                    return alert('Please enter a bias price');
                }
                
                bias = {
                    direction: direction,
                    condition: condition,
                    price: price
                };
                
                // Add flip if enabled
                if (document.getElementById('has-flip-switch').checked) {
                    const flipDirection = document.getElementById('flip-direction').value;
                    const flipCondition = document.getElementById('flip-condition').value;
                    const flipPrice = parseFloat(document.getElementById('flip-price').value);
                    
                    if (!flipPrice) {
                        return alert('Please enter a flip price');
                    }
                    
                    bias.flip = {
                        new_direction: flipDirection,
                        condition: flipCondition,
                        price: flipPrice
                    };
                }
            }
            
            // Create setup data
            const setupData = {
                manual_setup: {
                    symbol: symbol,
                    signals: signals,
                    bias: bias
                }
            };
            
            // Create a loading indicator
            const modal = manualSetupForm.closest('.modal');
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Creating setup...</p>';
            manualSetupForm.appendChild(loadingMsg);
            
            // Disable form
            const formElements = manualSetupForm.querySelectorAll('input, textarea, select, button');
            formElements.forEach(el => el.disabled = true);
            
            // Submit to API
            fetch('/api/setups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(setupData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert('Setup created successfully!');
                    
                    // Close modal and refresh page
                    bootstrap.Modal.getInstance(modal).hide();
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator and re-enable form
                    loadingMsg.remove();
                    formElements.forEach(el => el.disabled = false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator and re-enable form
                loadingMsg.remove();
                formElements.forEach(el => el.disabled = false);
            });
        });
    }
    
    // View setup button
    const viewSetupBtns = document.querySelectorAll('.view-setup-btn');
    viewSetupBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const symbol = this.dataset.setup;
            
            // Get all setups data from the page
            const setupsList = document.querySelectorAll('.setup-ticker-item');
            let setupData = null;
            
            setupsList.forEach(setup => {
                if (setup.querySelector('.ticker-symbol').textContent === symbol) {
                    setupData = {
                        symbol: symbol,
                        signals: [],
                        bias: null
                    };
                    
                    // Extract signals
                    const signalBadges = setup.querySelectorAll('.signal-badge');
                    signalBadges.forEach(badge => {
                        const text = badge.textContent.trim();
                        const parts = text.split(' ');
                        setupData.signals.push({
                            category: parts[0],
                            comparison: parts[1],
                            trigger: parseFloat(parts[2])
                        });
                    });
                    
                    // Extract bias
                    const biasBadge = setup.querySelector('.bias-badge');
                    if (biasBadge) {
                        const text = biasBadge.textContent.trim();
                        const parts = text.split(' ');
                        setupData.bias = {
                            direction: parts[0],
                            condition: parts[1],
                            price: parseFloat(parts[2])
                        };
                    }
                }
            });
            
            if (setupData) {
                // Populate modal
                const detailsContainer = document.getElementById('setup-details-container');
                detailsContainer.innerHTML = `
                    <h3>${setupData.symbol}</h3>
                    <div class="mb-3">
                        <h5>Signals</h5>
                        <div class="signals-list">
                            ${setupData.signals.map(signal => `
                                <div class="signal-detail-item">
                                    <div class="badge signal-badge signal-${signal.category}">${signal.category} ${signal.comparison} ${signal.trigger}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ${setupData.bias ? `
                        <div class="mb-3">
                            <h5>Bias</h5>
                            <div class="bias-detail">
                                <div class="badge bias-badge bias-${setupData.bias.direction}">${setupData.bias.direction} ${setupData.bias.condition} ${setupData.bias.price}</div>
                            </div>
                        </div>
                    ` : ''}
                    <div class="current-price-section mb-3">
                        <h5>Current Price</h5>
                        <div id="current-price-loading">Loading...</div>
                        <div id="current-price-display" style="display: none;"></div>
                    </div>
                `;
                
                // Set up trade button
                document.getElementById('trade-setup-btn').dataset.symbol = setupData.symbol;
                document.getElementById('trade-setup-btn').addEventListener('click', function() {
                    const symbol = this.dataset.symbol;
                    loadOptionContractsAndShowModal(symbol);
                });
                
                // Fetch current price
                fetchCurrentPrice(setupData.symbol);
            }
        });
    });
    
    // Trigger setup button
    const triggerSetupBtns = document.querySelectorAll('.trigger-setup-btn');
    triggerSetupBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const symbol = this.dataset.setup;
            
            // Confirm
            if (confirm(`Are you sure you want to manually trigger a signal for ${symbol}?`)) {
                // Get all setups data from the page
                const setupsList = document.querySelectorAll('.setup-ticker-item');
                let setupData = null;
                
                setupsList.forEach(setup => {
                    if (setup.querySelector('.ticker-symbol').textContent === symbol) {
                        const signalBadges = setup.querySelectorAll('.signal-badge');
                        if (signalBadges.length > 0) {
                            const text = signalBadges[0].textContent.trim();
                            const parts = text.split(' ');
                            setupData = {
                                symbol: symbol,
                                price: parseFloat(parts[2]),
                                signalType: parts[0]
                            };
                        }
                    }
                });
                
                if (setupData) {
                    manuallyTriggerSignal(setupData.symbol, setupData.price, setupData.signalType);
                }
            }
        });
    });
}

// Initialize position page functionality
function initPositionsPage() {
    // Show/hide option symbol field based on switch
    const isOptionSwitch = document.getElementById('is-option-switch');
    if (isOptionSwitch) {
        isOptionSwitch.addEventListener('change', function() {
            document.getElementById('option-container').style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Save position button
    const savePositionBtn = document.getElementById('save-position-btn');
    if (savePositionBtn) {
        savePositionBtn.addEventListener('click', function() {
            const symbol = document.getElementById('manual-symbol').value;
            const quantity = parseFloat(document.getElementById('position-quantity').value);
            const side = document.getElementById('position-side').value;
            const entryPrice = parseFloat(document.getElementById('entry-price').value);
            const currentPrice = parseFloat(document.getElementById('current-price').value);
            const isOption = document.getElementById('is-option-switch').checked;
            const optionSymbol = isOption ? document.getElementById('option-symbol').value : null;
            const strategy = document.getElementById('strategy-name').value || null;
            
            // Validate
            if (!symbol || isNaN(quantity) || !side || isNaN(entryPrice) || isNaN(currentPrice)) {
                return alert('Please fill all required fields');
            }
            
            if (isOption && !optionSymbol) {
                return alert('Please enter an option symbol');
            }
            
            // Create position data
            const positionData = {
                symbol: symbol,
                quantity: quantity,
                side: side,
                average_price: entryPrice,
                current_price: currentPrice,
                option_symbol: optionSymbol,
                strategy: strategy
            };
            
            // Create a loading indicator
            const form = document.getElementById('manual-position-form');
            const modal = form.closest('.modal');
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Adding position...</p>';
            form.appendChild(loadingMsg);
            
            // Submit to API
            fetch('/api/positions/manual', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(positionData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert('Position added successfully!');
                    
                    // Close modal and refresh page
                    bootstrap.Modal.getInstance(modal).hide();
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator
                    loadingMsg.remove();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator
                loadingMsg.remove();
            });
        });
    }
    
    // Close position buttons
    const closePositionBtns = document.querySelectorAll('.close-position-btn');
    closePositionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const row = this.closest('.position-row');
            const symbol = row.dataset.symbol;
            const optionSymbol = row.dataset.optionSymbol;
            const side = row.dataset.side;
            
            // Show close position modal
            const modal = new bootstrap.Modal(document.getElementById('closePositionModal'));
            
            // Populate modal
            document.getElementById('close-symbol').value = symbol;
            document.getElementById('close-option-symbol').value = optionSymbol || '';
            document.getElementById('close-display').value = `${symbol}${optionSymbol ? ' (Option)' : ''} - ${side.toUpperCase()}`;
            
            // Set up current price as default
            const currentPriceCell = row.querySelector('td:nth-child(6)');
            if (currentPriceCell) {
                const priceText = currentPriceCell.textContent.trim();
                const price = parseFloat(priceText.replace('$', ''));
                document.getElementById('close-price').value = price;
            }
            
            modal.show();
        });
    });
    
    // Confirm close position button
    const confirmCloseBtn = document.getElementById('confirm-close-position-btn');
    if (confirmCloseBtn) {
        confirmCloseBtn.addEventListener('click', function() {
            const symbol = document.getElementById('close-symbol').value;
            const optionSymbol = document.getElementById('close-option-symbol').value || null;
            const exitPrice = parseFloat(document.getElementById('close-price').value);
            const exitReason = document.getElementById('close-reason').value;
            
            // Validate
            if (!symbol || isNaN(exitPrice) || !exitReason) {
                return alert('Please fill all required fields');
            }
            
            // Create close data
            const closeData = {
                symbol: symbol,
                exit_price: exitPrice,
                exit_reason: exitReason,
                option_symbol: optionSymbol
            };
            
            // Create a loading indicator
            const form = document.getElementById('close-position-form');
            const modal = document.getElementById('closePositionModal');
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Closing position...</p>';
            form.appendChild(loadingMsg);
            
            // Disable button
            this.disabled = true;
            
            // Submit to API
            fetch('/api/positions/close', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(closeData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert('Position closed successfully!');
                    
                    // Close modal and refresh page
                    bootstrap.Modal.getInstance(modal).hide();
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator and re-enable button
                    loadingMsg.remove();
                    this.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator and re-enable button
                loadingMsg.remove();
                this.disabled = false;
            });
        });
    }
    
    // Exit rules form
    const exitRulesForm = document.getElementById('exit-rules-form');
    if (exitRulesForm) {
        exitRulesForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const symbol = document.getElementById('exit-symbol').value;
            const targetPrice = document.getElementById('target-price').value ? parseFloat(document.getElementById('target-price').value) : null;
            const stopPrice = document.getElementById('stop-price').value ? parseFloat(document.getElementById('stop-price').value) : null;
            
            // Validate
            if (!symbol) {
                return alert('Please select a position');
            }
            
            if (!targetPrice && !stopPrice) {
                return alert('Please enter at least one exit rule (target or stop)');
            }
            
            // Get option symbol if present
            const optionSymbol = document.getElementById('exit-symbol').selectedOptions[0].dataset.option || null;
            
            // Create exit rule data
            const exitRuleData = {
                symbol: symbol,
                option_symbol: optionSymbol,
                target_price: targetPrice,
                stop_price: stopPrice
            };
            
            // Create a loading indicator
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Adding exit rules...</p>';
            exitRulesForm.appendChild(loadingMsg);
            
            // Disable form
            const formElements = exitRulesForm.querySelectorAll('input, select, button');
            formElements.forEach(el => el.disabled = true);
            
            // Submit to API
            fetch('/api/positions/exit-rules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(exitRuleData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert('Exit rules added successfully!');
                    
                    // Refresh the page to show updated rules
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator and re-enable form
                    loadingMsg.remove();
                    formElements.forEach(el => el.disabled = false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator and re-enable form
                loadingMsg.remove();
                formElements.forEach(el => el.disabled = false);
            });
        });
    }
    
    // Initialize exposure chart
    initExposureChart();
}

// Initialize setup parser form
function initSetupParserForm() {
    const form = document.getElementById('setup-parser-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const messageText = document.getElementById('setup-message').value;
            
            if (!messageText) {
                return alert('Please enter a setup message');
            }
            
            // Create a loading indicator
            const resultContainer = document.getElementById('parser-result');
            resultContainer.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Parsing setup message...</p></div>';
            
            // Disable form
            const formElements = form.querySelectorAll('input, textarea, button');
            formElements.forEach(el => el.disabled = true);
            
            // Submit to API
            fetch('/api/setups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    raw_text: messageText
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message with details
                    resultContainer.innerHTML = `
                        <div class="alert alert-success">
                            <h5>Setup Parsed Successfully!</h5>
                            <p>Found ${data.data.ticker_count} ticker${data.data.ticker_count !== 1 ? 's' : ''}:</p>
                            <p>${data.data.tickers.join(', ')}</p>
                            <button class="btn btn-sm btn-primary refresh-btn">Refresh Page to View</button>
                        </div>
                    `;
                    
                    // Add refresh button listener
                    resultContainer.querySelector('.refresh-btn').addEventListener('click', function() {
                        location.reload();
                    });
                } else {
                    // Show error
                    resultContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <h5>Error</h5>
                            <p>${data.message}</p>
                        </div>
                    `;
                }
                
                // Re-enable form
                formElements.forEach(el => el.disabled = false);
            })
            .catch(error => {
                console.error('Error:', error);
                resultContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <h5>Error</h5>
                        <p>An unexpected error occurred. Please try again.</p>
                    </div>
                `;
                
                // Re-enable form
                formElements.forEach(el => el.disabled = false);
            });
        });
    }
}

// Initialize manual signal form
function initManualSignalForm() {
    const form = document.getElementById('manual-signal-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const symbol = document.getElementById('manual-symbol').value;
            const price = parseFloat(document.getElementById('manual-price').value);
            const signalType = document.getElementById('manual-signal-type').value;
            
            if (!symbol || isNaN(price)) {
                return alert('Please fill all required fields');
            }
            
            // Create a loading indicator
            const resultContainer = form.querySelector('button[type="submit"]').parentNode;
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Creating signal...</p>';
            resultContainer.appendChild(loadingMsg);
            
            // Disable form
            const formElements = form.querySelectorAll('input, select, button');
            formElements.forEach(el => el.disabled = true);
            
            // Call function to trigger signal
            manuallyTriggerSignal(symbol, price, signalType)
                .then(success => {
                    if (success) {
                        // Show success message
                        alert(`Manual signal for ${symbol} created successfully!`);
                        
                        // Clear form
                        form.reset();
                    } else {
                        alert('Failed to create signal. Please try again.');
                    }
                    
                    // Remove loading indicator and re-enable form
                    loadingMsg.remove();
                    formElements.forEach(el => el.disabled = false);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An unexpected error occurred. Please try again.');
                    
                    // Remove loading indicator and re-enable form
                    loadingMsg.remove();
                    formElements.forEach(el => el.disabled = false);
                });
        });
    }
}

// Initialize options modals
function initOptionsModals() {
    // Order type change handler
    const orderTypeSelect = document.getElementById('order-type');
    if (orderTypeSelect) {
        orderTypeSelect.addEventListener('change', function() {
            const limitPriceContainer = document.getElementById('limit-price-container');
            limitPriceContainer.style.display = this.value === 'limit' ? 'block' : 'none';
        });
    }
    
    // Submit order button
    const submitOrderBtn = document.getElementById('submit-order-btn');
    if (submitOrderBtn) {
        submitOrderBtn.addEventListener('click', function() {
            const symbol = document.getElementById('order-symbol').value;
            const optionSymbol = document.getElementById('order-option-symbol').value;
            const side = document.getElementById('order-side').value;
            const quantity = parseInt(document.getElementById('order-quantity').value);
            const orderType = document.getElementById('order-type').value;
            const timeInForce = document.getElementById('order-time-in-force').value;
            const limitPrice = orderType === 'limit' ? parseFloat(document.getElementById('order-limit-price').value) : null;
            
            // Validate
            if (!symbol || !side || isNaN(quantity) || quantity <= 0) {
                return alert('Please fill all required fields');
            }
            
            if (orderType === 'limit' && (isNaN(limitPrice) || limitPrice <= 0)) {
                return alert('Please enter a valid limit price');
            }
            
            // Create order data
            const orderData = {
                symbol: symbol,
                option_symbol: optionSymbol || null,
                side: side,
                quantity: quantity,
                order_type: orderType,
                time_in_force: timeInForce,
                limit_price: limitPrice
            };
            
            // Create a loading indicator
            const modal = document.getElementById('executeOrderModal');
            const modalBody = modal.querySelector('.modal-body');
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-center mt-3';
            loadingMsg.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Submitting order...</p>';
            modalBody.appendChild(loadingMsg);
            
            // Disable buttons
            const modalButtons = modal.querySelectorAll('.modal-footer button');
            modalButtons.forEach(btn => btn.disabled = true);
            
            // Submit to API
            fetch('/api/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(orderData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert('Order submitted successfully!');
                    
                    // Close modal and refresh page
                    bootstrap.Modal.getInstance(modal).hide();
                    location.reload();
                } else {
                    // Show error
                    alert(`Error: ${data.message}`);
                    
                    // Remove loading indicator and re-enable buttons
                    loadingMsg.remove();
                    modalButtons.forEach(btn => btn.disabled = false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred. Please try again.');
                
                // Remove loading indicator and re-enable buttons
                loadingMsg.remove();
                modalButtons.forEach(btn => btn.disabled = false);
            });
        });
    }
    
    // Options view toggle buttons
    const viewCallsBtn = document.getElementById('view-calls');
    const viewPutsBtn = document.getElementById('view-puts');
    
    if (viewCallsBtn && viewPutsBtn) {
        viewCallsBtn.addEventListener('click', function() {
            optionViewType = 'calls';
            viewCallsBtn.classList.add('active');
            viewPutsBtn.classList.remove('active');
            renderOptionsTable();
        });
        
        viewPutsBtn.addEventListener('click', function() {
            optionViewType = 'puts';
            viewPutsBtn.classList.add('active');
            viewCallsBtn.classList.remove('active');
            renderOptionsTable();
        });
    }
}

// Load option contracts and show the selection modal
function loadOptionContractsAndShowModal(symbol) {
    currentOptionSymbol = symbol;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('optionSelectorModal'));
    modal.show();
    
    // Update title
    document.getElementById('option-symbol-title').innerText = `Loading options for ${symbol}...`;
    
    // Clear options list
    document.getElementById('options-list').innerHTML = `
        <tr>
            <td colspan="7" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Loading option contracts...</p>
            </td>
        </tr>
    `;
    
    // Fetch options
    fetch(`/api/options/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                optionContracts = data.data;
                
                // Update title
                document.getElementById('option-symbol-title').innerText = `Options for ${symbol}`;
                
                // Render options table
                renderOptionsTable();
            } else {
                document.getElementById('options-list').innerHTML = `
                    <tr>
                        <td colspan="7" class="text-center">
                            <div class="alert alert-danger">
                                Failed to load options: ${data.message}
                            </div>
                        </td>
                    </tr>
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching options:', error);
            document.getElementById('options-list').innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">
                        <div class="alert alert-danger">
                            An error occurred while loading options. Please try again.
                        </div>
                    </td>
                </tr>
            `;
        });
}

// Render the options table
function renderOptionsTable() {
    const optionsList = document.getElementById('options-list');
    
    if (!optionContracts || optionContracts.length === 0) {
        optionsList.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">No option contracts available.</td>
            </tr>
        `;
        return;
    }
    
    // Filter contracts by type
    const filteredContracts = optionContracts.filter(contract => 
        contract.option_type.toLowerCase() === (optionViewType === 'calls' ? 'call' : 'put')
    );
    
    if (filteredContracts.length === 0) {
        optionsList.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">No ${optionViewType} available.</td>
            </tr>
        `;
        return;
    }
    
    // Sort contracts by strike
    filteredContracts.sort((a, b) => a.strike - b.strike);
    
    // Group contracts by expiration
    const contractsByExpiry = {};
    filteredContracts.forEach(contract => {
        if (!contractsByExpiry[contract.expiration]) {
            contractsByExpiry[contract.expiration] = [];
        }
        contractsByExpiry[contract.expiration].push(contract);
    });
    
    // Get unique expiry dates, sorted
    const expiryDates = Object.keys(contractsByExpiry).sort();
    
    // Get nearest expiry
    const nearestExpiry = expiryDates[0];
    
    // Get contracts for nearest expiry
    const contracts = contractsByExpiry[nearestExpiry];
    
    // Render the table
    optionsList.innerHTML = contracts.map(contract => `
        <tr>
            <td>${contract.strike.toFixed(2)}</td>
            <td>${contract.expiration}</td>
            <td>${contract.bid.toFixed(2)}</td>
            <td>${contract.ask.toFixed(2)}</td>
            <td>${contract.delta.toFixed(2)}</td>
            <td>${(contract.implied_volatility * 100).toFixed(1)}%</td>
            <td>
                <button class="btn btn-sm btn-primary trade-option-btn" 
                        data-symbol="${currentOptionSymbol}" 
                        data-option-symbol="${contract.symbol}">
                    Trade
                </button>
            </td>
        </tr>
    `).join('');
    
    // Add event listeners to trade buttons
    const tradeButtons = document.querySelectorAll('.trade-option-btn');
    tradeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const symbol = this.dataset.symbol;
            const optionSymbol = this.dataset.optionSymbol;
            
            // Close the options modal
            bootstrap.Modal.getInstance(document.getElementById('optionSelectorModal')).hide();
            
            // Show the order execution modal
            const executeModal = new bootstrap.Modal(document.getElementById('executeOrderModal'));
            
            // Populate the form
            document.getElementById('order-symbol').value = symbol;
            document.getElementById('order-option-symbol').value = optionSymbol;
            document.getElementById('order-contract-display').value = optionSymbol;
            
            executeModal.show();
        });
    });
}

// Manually trigger a signal
async function manuallyTriggerSignal(symbol, price, signalType) {
    try {
        const response = await fetch('/api/strategy/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                price: price,
                signal_type: signalType
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Add to notifications
            addNotification({
                message: `Manual signal triggered for ${symbol} (${signalType}) at ${price}`,
                level: 'info',
                timestamp: new Date().toISOString()
            });
            
            return true;
        } else {
            console.error('Error triggering signal:', data.message);
            return false;
        }
    } catch (error) {
        console.error('Error triggering signal:', error);
        return false;
    }
}

// Fetch current price for a symbol
function fetchCurrentPrice(symbol) {
    fetch(`/api/market/price/${symbol}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const priceContainer = document.getElementById('current-price-display');
                const loadingContainer = document.getElementById('current-price-loading');
                
                if (priceContainer && loadingContainer) {
                    priceContainer.innerHTML = `<h3>$${data.data.price.toFixed(2)}</h3>`;
                    priceContainer.style.display = 'block';
                    loadingContainer.style.display = 'none';
                }
            } else {
                console.error('Error fetching price:', data.message);
            }
        })
        .catch(error => {
            console.error('Error fetching price:', error);
        });
}

// Fetch system status
function fetchSystemStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Update system status indicator
            systemStatus = data.execution;
            
            const indicator = document.getElementById('system-status-indicator');
            const statusText = document.getElementById('system-status-text');
            
            if (indicator && statusText) {
                indicator.className = 'status-indicator status-' + systemStatus;
                statusText.innerText = 'System: ' + systemStatus.charAt(0).toUpperCase() + systemStatus.slice(1);
            }
        })
        .catch(error => {
            console.error('Error fetching system status:', error);
            
            // Update indicator to error state
            const indicator = document.getElementById('system-status-indicator');
            const statusText = document.getElementById('system-status-text');
            
            if (indicator && statusText) {
                indicator.className = 'status-indicator status-error';
                statusText.innerText = 'System: Error';
            }
        });
}

// Fetch active signals
function fetchActiveSignals() {
    fetch('/api/strategy/signals')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                activeSignals = data.data;
                
                // Update active signals display
                const signalsCount = document.getElementById('active-signals-count');
                const signalsTable = document.getElementById('active-signals-table');
                
                if (signalsCount) {
                    signalsCount.innerText = activeSignals.length;
                }
                
                if (signalsTable) {
                    if (activeSignals.length === 0) {
                        signalsTable.innerHTML = `
                            <tr>
                                <td colspan="4" class="text-center">No active signals</td>
                            </tr>
                        `;
                    } else {
                        signalsTable.innerHTML = activeSignals.map(signal => `
                            <tr>
                                <td>${signal.symbol}</td>
                                <td><span class="badge signal-badge signal-${signal.category.toLowerCase()}">${signal.category}</span></td>
                                <td>$${signal.price.toFixed(2)}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick="loadOptionContractsAndShowModal('${signal.symbol}')">
                                        <i class="fas fa-exchange-alt"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error fetching active signals:', error);
        });
}

// Fetch positions
function fetchPositions() {
    fetch('/api/positions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const positions = data.data;
                
                // Update positions count
                const positionsCount = document.getElementById('open-positions-count');
                const tradesTable = document.getElementById('recent-trades-table');
                
                if (positionsCount) {
                    positionsCount.innerText = positions.length;
                }
                
                if (tradesTable) {
                    if (positions.length === 0) {
                        tradesTable.innerHTML = `
                            <tr>
                                <td colspan="4" class="text-center">No recent trades</td>
                            </tr>
                        `;
                    } else {
                        // Sort by entry time, newest first
                        positions.sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));
                        
                        // Take the 5 most recent
                        const recentPositions = positions.slice(0, 5);
                        
                        tradesTable.innerHTML = recentPositions.map(position => {
                            const entryTime = new Date(position.entry_time);
                            return `
                                <tr>
                                    <td>${position.symbol}</td>
                                    <td>${position.side.toUpperCase()}</td>
                                    <td>$${position.average_price.toFixed(2)}</td>
                                    <td>${entryTime.toLocaleTimeString()}</td>
                                </tr>
                            `;
                        }).join('');
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error fetching positions:', error);
        });
}

// Fetch notifications
function fetchNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                notifications = data.data;
                
                // Update notifications display
                renderNotifications();
            }
        })
        .catch(error => {
            console.error('Error fetching notifications:', error);
        });
}

// Add a notification
function addNotification(notification) {
    notifications.unshift(notification);
    
    // Limit to 50 notifications
    if (notifications.length > 50) {
        notifications.pop();
    }
    
    // Update notifications display
    renderNotifications();
}

// Render notifications
function renderNotifications() {
    const dashboardNotifications = document.getElementById('dashboard-notifications');
    const notificationBody = document.getElementById('notificationBody');
    
    if (dashboardNotifications) {
        if (notifications.length === 0) {
            dashboardNotifications.innerHTML = `
                <div class="text-center p-3">No notifications</div>
            `;
        } else {
            // Take the 5 most recent for dashboard
            const recentNotifications = notifications.slice(0, 5);
            
            dashboardNotifications.innerHTML = recentNotifications.map(notification => {
                const date = new Date(notification.timestamp);
                return `
                    <div class="notification-item level-${notification.level}">
                        <div class="notification-content">${notification.message}</div>
                        <div class="notification-time">${date.toLocaleTimeString()}</div>
                    </div>
                `;
            }).join('');
        }
    }
    
    if (notificationBody) {
        if (notifications.length === 0) {
            notificationBody.innerHTML = `
                <div class="text-center p-3">No notifications</div>
            `;
        } else {
            notificationBody.innerHTML = notifications.map(notification => {
                const date = new Date(notification.timestamp);
                return `
                    <div class="notification-item level-${notification.level}">
                        <div class="notification-content">${notification.message}</div>
                        <div class="notification-time">${date.toLocaleTimeString()}</div>
                    </div>
                `;
            }).join('');
        }
    }
}

// Toggle notification panel
function toggleNotificationPanel() {
    const panel = document.getElementById('notificationPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

// Clear notifications
function clearNotifications() {
    notifications = [];
    renderNotifications();
}

// Initialize performance chart
function initPerformanceChart() {
    const ctx = document.getElementById('performance-chart');
    if (!ctx) return;
    
    // Sample data - would be replaced with real data in production
    const labels = [];
    const data = [];
    
    // Create labels for the last 7 days
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString());
        
        // Dummy data (would be replaced with real cumulative P/L in production)
        data.push(0);
    }
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative P/L',
                data: data,
                fill: false,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// Initialize exposure chart
function initExposureChart() {
    const ctx = document.getElementById('exposure-chart');
    if (!ctx) return;
    
    // Extract data from positions
    const positions = document.querySelectorAll('.position-row');
    const symbolsMap = {};
    
    positions.forEach(position => {
        const symbol = position.dataset.symbol;
        const currentPriceCell = position.querySelector('td:nth-child(6)');
        const quantityCell = position.querySelector('td:nth-child(4)');
        
        if (currentPriceCell && quantityCell) {
            const price = parseFloat(currentPriceCell.textContent.replace('$', ''));
            const quantity = parseFloat(quantityCell.textContent);
            const value = price * Math.abs(quantity);
            
            if (symbolsMap[symbol]) {
                symbolsMap[symbol] += value;
            } else {
                symbolsMap[symbol] = value;
            }
        }
    });
    
    const labels = Object.keys(symbolsMap);
    const data = Object.values(symbolsMap);
    
    // Generate background colors
    const backgroundColors = labels.map((_, i) => {
        const hue = (i * 137.5) % 360;
        return `hsl(${hue}, 70%, 60%)`;
    });
    
    if (labels.length === 0) {
        // No data case
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['No Positions'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(200, 200, 200, 0.2)'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    } else {
        // Create the chart
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }
}
