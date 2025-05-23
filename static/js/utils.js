/**
 * A+ Trading Platform - Shared JavaScript Utilities
 * Centralized functions to eliminate duplication across templates
 */

// Alert and notification utilities
function showSuccess(message, duration = 3000) {
    const alert = createAlert(message, 'success');
    document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
    if (duration > 0) {
        setTimeout(() => alert.remove(), duration);
    }
}

function showError(message, duration = 0) {
    const alert = createAlert(message, 'danger');
    document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
    if (duration > 0) {
        setTimeout(() => alert.remove(), duration);
    }
}

function showWarning(message, duration = 5000) {
    const alert = createAlert(message, 'warning');
    document.querySelector('.container').insertBefore(alert, document.querySelector('.container').firstChild);
    if (duration > 0) {
        setTimeout(() => alert.remove(), duration);
    }
}

function createAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    return alert;
}

// Loading state utilities
function showSpinner(container, message = 'Loading...') {
    const spinner = document.createElement('div');
    spinner.className = 'text-center py-4';
    spinner.innerHTML = `
        <div class="spinner-border" role="status">
            <span class="visually-hidden">${message}</span>
        </div>
        <div class="mt-2 text-muted">${message}</div>
    `;
    container.innerHTML = '';
    container.appendChild(spinner);
}

function hideSpinner(container) {
    const spinner = container.querySelector('.spinner-border');
    if (spinner) {
        spinner.closest('.text-center').remove();
    }
}

// API utilities with consistent error handling
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        if (data.status && data.status !== 'success') {
            throw new Error(data.message || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Configuration update utilities for Discord admin
async function updateChannelConfig(channelId, type, enabled) {
    try {
        const data = await apiCall('/admin/discord/api/channels/config', {
            method: 'POST',
            body: JSON.stringify({
                channel_id: channelId,
                type: type,
                enabled: enabled
            })
        });
        
        showSuccess(`Channel ${type} setting updated successfully`);
        return data;
    } catch (error) {
        showError(`Failed to update channel: ${error.message}`);
        throw error;
    }
}

// Modal utilities
function showModal(modalId, title, body, confirmAction = null, confirmText = 'Confirm') {
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Modal with ID ${modalId} not found`);
        return;
    }
    
    // Update modal content
    const titleElement = modal.querySelector('.modal-title');
    const bodyElement = modal.querySelector('.modal-body');
    const confirmButton = modal.querySelector('.btn-primary');
    
    if (titleElement) titleElement.textContent = title;
    if (bodyElement) bodyElement.innerHTML = body;
    
    if (confirmButton && confirmAction) {
        confirmButton.textContent = confirmText;
        confirmButton.onclick = confirmAction;
        confirmButton.style.display = 'inline-block';
    } else if (confirmButton) {
        confirmButton.style.display = 'none';
    }
    
    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Table utilities
function createTableRow(data, actions = []) {
    const row = document.createElement('tr');
    
    // Add data cells
    data.forEach(cellData => {
        const cell = document.createElement('td');
        
        if (typeof cellData === 'object' && cellData.type) {
            switch (cellData.type) {
                case 'badge':
                    cell.innerHTML = `<span class="badge bg-${cellData.color || 'secondary'}">${cellData.value}</span>`;
                    break;
                case 'link':
                    cell.innerHTML = `<a href="${cellData.url}" class="text-decoration-none">${cellData.value}</a>`;
                    break;
                case 'currency':
                    cell.innerHTML = `<span class="font-monospace">$${Number(cellData.value).toFixed(2)}</span>`;
                    break;
                case 'datetime':
                    const date = new Date(cellData.value);
                    cell.innerHTML = `<span class="text-muted">${date.toLocaleString()}</span>`;
                    break;
                default:
                    cell.textContent = cellData.value;
            }
        } else {
            cell.textContent = cellData;
        }
        
        row.appendChild(cell);
    });
    
    // Add actions cell if provided
    if (actions.length > 0) {
        const actionsCell = document.createElement('td');
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = `btn btn-sm ${action.class || 'btn-outline-primary'} me-1`;
            button.innerHTML = action.icon ? `<i class="${action.icon}"></i>` : action.text;
            button.onclick = action.onclick;
            actionsCell.appendChild(button);
        });
        row.appendChild(actionsCell);
    }
    
    return row;
}

// Form utilities
function setupFormToggles() {
    document.querySelectorAll('[data-form-toggle]').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const targetId = this.dataset.formToggle;
            const enabled = this.checked;
            
            if (this.dataset.apiEndpoint) {
                // Make API call if endpoint is specified
                const endpoint = this.dataset.apiEndpoint;
                updateChannelConfig(targetId, this.dataset.toggleType || 'toggle', enabled)
                    .catch(() => {
                        // Revert toggle on error
                        this.checked = !enabled;
                    });
            }
        });
    });
}

// Auto-refresh utilities
function setupAutoRefresh(refreshFunction, interval = 30000) {
    let refreshTimer;
    
    function startRefresh() {
        refreshTimer = setInterval(refreshFunction, interval);
    }
    
    function stopRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
    }
    
    // Start auto-refresh
    startRefresh();
    
    // Stop refresh when page is hidden, restart when visible
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopRefresh();
        } else {
            startRefresh();
        }
    });
    
    return { start: startRefresh, stop: stopRefresh };
}

// Initialize common functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Setup form toggles
    setupFormToggles();
    
    // Setup tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Export utilities for modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showSuccess,
        showError,
        showWarning,
        showSpinner,
        hideSpinner,
        apiCall,
        updateChannelConfig,
        showModal,
        createTableRow,
        setupAutoRefresh
    };
}