// Setup Notifications - Real-time updates for new trading setups
document.addEventListener('DOMContentLoaded', function() {
    initializeSetupNotifications();
});

// Socket.IO connection
let socket;

function initializeSetupNotifications() {
    // Connect to Socket.IO server
    socket = io();
    
    // Setup Socket.IO event handlers
    setupSocketEvents();
    
    // Set up UI event listeners
    setupEventListeners();
}

function setupSocketEvents() {
    // Connection events
    socket.on('connect', function() {
        console.log('Connected to real-time notification server');
        // Subscribe to setup notifications
        socket.emit('subscribe_setups');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from real-time notification server');
    });
    
    // Setup notification events
    socket.on('new_setup', function(data) {
        console.log('New setup received:', data);
        displaySetupNotification(data);
        // If we're on the recent setups page, refresh the list
        if (document.getElementById('setupsContainer')) {
            refreshSetupsList(data);
        }
    });
    
    socket.on('subscription_response', function(data) {
        console.log('Subscription response:', data);
    });
}

function setupEventListeners() {
    // Add event listener for notification dismiss button
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('notification-dismiss')) {
            const notification = e.target.closest('.setup-notification');
            if (notification) {
                notification.remove();
            }
        }
    });
}

function displaySetupNotification(setupData) {
    // Create notification container if it doesn't exist
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.className = 'notification-container';
        document.body.appendChild(notificationContainer);
        
        // Add CSS for notifications if not already present
        if (!document.getElementById('notification-styles')) {
            const styleElement = document.createElement('style');
            styleElement.id = 'notification-styles';
            styleElement.textContent = `
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    width: 350px;
                    max-width: 90%;
                    z-index: 9999;
                }
                .setup-notification {
                    background-color: #fff;
                    border-left: 4px solid #4caf50;
                    border-radius: 4px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    margin-bottom: 10px;
                    padding: 15px;
                    animation: slide-in 0.3s ease-out forwards;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .notification-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                .notification-title {
                    font-weight: bold;
                    color: #333;
                    margin: 0;
                }
                .notification-dismiss {
                    background: none;
                    border: none;
                    font-size: 16px;
                    cursor: pointer;
                    color: #999;
                }
                .notification-dismiss:hover {
                    color: #555;
                }
                .notification-body {
                    font-size: 14px;
                }
                .ticker-badges {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 5px;
                    margin-bottom: 10px;
                }
                .ticker-badge {
                    background-color: #f0f0f0;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 12px;
                    color: #333;
                    font-weight: bold;
                }
                .notification-footer {
                    margin-top: 10px;
                    text-align: right;
                }
                .view-details-btn {
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 12px;
                    padding: 4px 10px;
                    cursor: pointer;
                }
                .view-details-btn:hover {
                    background-color: #e9ecef;
                }
                @keyframes slide-in {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(styleElement);
        }
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'setup-notification';
    
    // Format date
    const setupDate = new Date(setupData.date);
    const formattedDate = setupDate.toLocaleDateString();
    
    // Create ticker badges HTML
    let tickerBadgesHtml = '';
    if (setupData.ticker_symbols && setupData.ticker_symbols.length > 0) {
        tickerBadgesHtml = '<div class="ticker-badges">';
        setupData.ticker_symbols.forEach(ticker => {
            tickerBadgesHtml += `<span class="ticker-badge">${ticker}</span>`;
        });
        tickerBadgesHtml += '</div>';
    }
    
    // Set notification content
    notification.innerHTML = `
        <div class="notification-header">
            <h5 class="notification-title">New Trading Setup</h5>
            <button class="notification-dismiss">&times;</button>
        </div>
        <div class="notification-body">
            <div class="setup-date">${formattedDate}</div>
            ${tickerBadgesHtml}
            <div class="setup-tickers">
                <small>${setupData.ticker_count} ticker(s) in this setup</small>
            </div>
        </div>
        <div class="notification-footer">
            <a href="/setup-detail/${setupData.id}" class="view-details-btn">View Details</a>
        </div>
    `;
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Remove after 10 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            notification.style.transition = 'all 0.3s ease-out';
            
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }
    }, 10000);
}

function refreshSetupsList(newSetup) {
    // Prepend the new setup to the list without full page refresh
    if (document.getElementById('setupsContainer')) {
        // Get the current list
        const container = document.getElementById('setupsContainer');
        
        // Create new setup card
        const card = document.createElement('div');
        card.className = 'card setup-card mb-4';
        
        // Format date and time
        const setupDate = new Date(newSetup.date);
        const msgDate = setupDate.toLocaleDateString();
        const msgTime = setupDate.toLocaleTimeString();
        
        // Create ticker badges HTML
        let tickerBadges = '';
        if (newSetup.ticker_symbols && newSetup.ticker_symbols.length > 0) {
            newSetup.ticker_symbols.forEach(ticker => {
                tickerBadges += `<span class="badge bg-primary ticker-badge">${ticker}</span> `;
            });
        }
        
        // Set card content
        card.innerHTML = `
            <div class="card-header">
                <div>
                    <h5 class="mb-0">A+ Trade Setup</h5>
                    <small class="setup-date">${msgDate} at ${msgTime}</small>
                </div>
                <span class="badge bg-success source-badge">New</span>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <div class="mt-2">${tickerBadges}</div>
                </div>
                <div class="setup-message mb-3">
                    <strong>${newSetup.ticker_count} ticker(s) in this setup</strong>
                </div>
                <a href="/setup-detail/${newSetup.id}" class="btn btn-outline-primary btn-sm">View Details</a>
            </div>
            <div class="card-footer text-muted">
                <small>Just arrived</small>
            </div>
        `;
        
        // Remove loading indicator if present
        const loadingIndicator = container.querySelector('.loading-container');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        
        // Add new card at the top of the list
        if (container.firstChild) {
            container.insertBefore(card, container.firstChild);
        } else {
            container.appendChild(card);
        }
    }
}