// Main app JavaScript functionality

// Initialize the app when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    // Set up event listeners
    setupEventListeners();
    
    // Fetch initial system status
    fetchSystemStatus();
}

// Set up event listeners for UI interactions
function setupEventListeners() {
    // Add any event listeners needed for the home page
    const dashboardBtn = document.querySelector('a[href*="dashboard"]');
    if (dashboardBtn) {
        dashboardBtn.addEventListener('click', function(e) {
            // Could add analytics tracking or other logic here
            console.log('Dashboard button clicked');
        });
    }
}

// Fetch system status from the API
function fetchSystemStatus() {
    // Check strategy status
    fetch('/api/strategy/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStrategyStatus(data);
            }
        })
        .catch(error => {
            console.error('Error fetching strategy status:', error);
        });
    
    // Check execution status
    fetch('/api/execution/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateExecutionStatus(data);
            }
        })
        .catch(error => {
            console.error('Error fetching execution status:', error);
        });
}

// Update strategy status display
function updateStrategyStatus(data) {
    const isRunning = data.detector?.running || false;
    // You could update UI elements here if needed
    console.log('Strategy service running:', isRunning);
}

// Update execution status display
function updateExecutionStatus(data) {
    const isRunning = data.executor?.running || false;
    // You could update UI elements here if needed
    console.log('Execution service running:', isRunning);
}