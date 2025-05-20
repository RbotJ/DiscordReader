/**
 * Setup Viewer Module for the Trading Application
 * 
 * This module handles the viewing and management of trading setups
 * including fetching, displaying, and interacting with setup data.
 */

import { formatDate, formatTime } from '/static/common/js/utils.js';
import { SetupApiClient } from '/static/common/js/api-client.js';

// Initialize API client
const setupApi = new SetupApiClient();

// Setup viewer state
const state = {
  setups: [],
  currentSetup: null,
  filter: '',
  loading: false,
  error: null
};

/**
 * Initialize the setup viewer
 */
async function initSetupViewer() {
  try {
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    await loadSetups();
    
    console.log('Setup viewer initialized successfully');
  } catch (error) {
    console.error('Error initializing setup viewer:', error);
    displayError('Failed to initialize setup viewer. Please try refreshing the page.');
  }
}

/**
 * Load trading setups
 * @param {Object} options - Load options
 * @param {number} [options.limit=20] - Maximum number of setups to load
 * @param {string} [options.symbol=null] - Filter setups by symbol
 * @param {boolean} [options.refresh=false] - Force refresh from source
 */
async function loadSetups(options = {}) {
  const { 
    limit = 20, 
    symbol = null, 
    refresh = false 
  } = options;
  
  try {
    // Update loading state
    state.loading = true;
    updateLoadingIndicator(true);
    
    // Get setup data
    const response = await setupApi.getRecentSetups(limit, symbol);
    
    if (response.status === 'success') {
      state.setups = response.data;
      displaySetups(response.data);
    } else {
      displayError(`Failed to load setups: ${response.message}`);
    }
    
    // If refresh is requested, sync with Discord
    if (refresh) {
      await syncDiscordSetups();
    }
  } catch (error) {
    console.error('Error loading setups:', error);
    displayError(`Failed to load setups: ${error.message}`);
  } finally {
    // Update loading state
    state.loading = false;
    updateLoadingIndicator(false);
  }
}

/**
 * Sync setups from Discord
 * @param {boolean} [forceRefresh=false] - Force refresh of already processed messages
 */
async function syncDiscordSetups(forceRefresh = false) {
  try {
    // Update loading state
    updateLoadingIndicator(true, 'Syncing with Discord...');
    
    // Sync with Discord
    const response = await setupApi.syncDiscordMessages(forceRefresh);
    
    if (response.status === 'success') {
      displayNotification(`Discord messages synced: ${response.processed} new, ${response.skipped} skipped`, 'success');
      
      // Reload setups if new messages were processed
      if (response.processed > 0) {
        await loadSetups();
      }
    } else {
      displayError(`Failed to sync Discord messages: ${response.message}`);
    }
  } catch (error) {
    console.error('Error syncing Discord messages:', error);
    displayError(`Failed to sync Discord messages: ${error.message}`);
  } finally {
    // Update loading state
    updateLoadingIndicator(false);
  }
}

/**
 * Display list of setups
 * @param {Array} setups - List of setup data
 */
function displaySetups(setups) {
  const setupListBody = document.getElementById('setup-list-body');
  if (!setupListBody) return;
  
  // Clear current list
  setupListBody.innerHTML = '';
  
  if (setups.length === 0) {
    // Show empty state
    setupListBody.innerHTML = `
      <tr>
        <td colspan="4">
          <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <h3 class="empty-state-title">No setups found</h3>
            <p class="empty-state-message">
              No trading setups are available. Try syncing with Discord or adjusting your filters.
            </p>
            <button id="empty-sync-button" class="btn btn-primary">
              Sync with Discord
            </button>
          </div>
        </td>
      </tr>
    `;
    
    // Add event listener to sync button
    const syncButton = document.getElementById('empty-sync-button');
    if (syncButton) {
      syncButton.addEventListener('click', () => syncDiscordSetups(true));
    }
    
    return;
  }
  
  // Add setup rows
  setups.forEach(setup => {
    const row = document.createElement('tr');
    row.dataset.setupId = setup.id;
    
    // Format date
    const setupDate = new Date(setup.date);
    const formattedDate = formatDate(setupDate);
    
    // Format source
    const sourceClass = `setup-source-${setup.source.toLowerCase()}`;
    
    // Create ticker tags
    const tickerTags = setup.ticker_symbols.map(symbol => 
      `<span class="setup-ticker-tag">${symbol}</span>`
    ).join('');
    
    row.innerHTML = `
      <td class="setup-date">${formattedDate}</td>
      <td><span class="setup-source ${sourceClass}">${setup.source}</span></td>
      <td class="setup-tickers">${tickerTags}</td>
      <td class="setup-action">
        <button class="btn btn-sm btn-outline-primary view-setup-btn">
          View
        </button>
      </td>
    `;
    
    // Add event listener to view button
    const viewButton = row.querySelector('.view-setup-btn');
    if (viewButton) {
      viewButton.addEventListener('click', (event) => {
        event.stopPropagation();
        loadSetupDetail(setup.id);
      });
    }
    
    // Add event listener to row
    row.addEventListener('click', () => {
      loadSetupDetail(setup.id);
    });
    
    setupListBody.appendChild(row);
  });
}

/**
 * Load setup detail
 * @param {number} setupId - ID of the setup to load
 */
async function loadSetupDetail(setupId) {
  try {
    // Update loading state
    state.loading = true;
    updateLoadingIndicator(true);
    
    // Get setup detail
    const response = await setupApi.getSetupDetail(setupId);
    
    if (response.status === 'success') {
      state.currentSetup = response.data;
      displaySetupDetail(response.data);
    } else {
      displayError(`Failed to load setup detail: ${response.message}`);
    }
  } catch (error) {
    console.error('Error loading setup detail:', error);
    displayError(`Failed to load setup detail: ${error.message}`);
  } finally {
    // Update loading state
    state.loading = false;
    updateLoadingIndicator(false);
  }
}

/**
 * Display setup detail
 * @param {Object} setup - Setup detail data
 */
function displaySetupDetail(setup) {
  // Show detail view, hide list view
  const listContainer = document.getElementById('setup-list-container');
  const detailContainer = document.getElementById('setup-detail-container');
  
  if (listContainer) {
    listContainer.style.display = 'none';
  }
  
  if (!detailContainer) return;
  
  detailContainer.style.display = 'block';
  
  // Format date
  const setupDate = new Date(setup.date);
  const formattedDate = formatDate(setupDate);
  const formattedCreated = setup.created_at ? 
    `${formatDate(new Date(setup.created_at))} ${formatTime(new Date(setup.created_at))}` : 
    'Unknown';
  
  // Format source
  const sourceClass = `setup-source-${setup.source.toLowerCase()}`;
  
  // Update header
  const detailHeader = detailContainer.querySelector('.setup-detail-header');
  if (detailHeader) {
    detailHeader.innerHTML = `
      <div class="setup-detail-back" id="back-to-list">
        <span>&larr;</span> Back to List
      </div>
      <div class="setup-detail-title">
        Setup Detail
      </div>
      <div class="setup-detail-actions">
        <button class="setup-detail-action" id="view-chart-button">
          <span>📊</span> View Chart
        </button>
        <button class="setup-detail-action" id="trade-button">
          <span>💰</span> Trade
        </button>
      </div>
    `;
    
    // Add event listener to back button
    const backButton = detailHeader.querySelector('#back-to-list');
    if (backButton) {
      backButton.addEventListener('click', () => {
        listContainer.style.display = 'block';
        detailContainer.style.display = 'none';
        state.currentSetup = null;
      });
    }
    
    // Add event listeners to action buttons
    const viewChartButton = detailHeader.querySelector('#view-chart-button');
    if (viewChartButton) {
      viewChartButton.addEventListener('click', () => {
        if (setup.ticker_setups.length > 0) {
          const symbol = setup.ticker_setups[0].symbol;
          window.location.href = `/dashboard?symbol=${symbol}`;
        }
      });
    }
    
    const tradeButton = detailHeader.querySelector('#trade-button');
    if (tradeButton) {
      tradeButton.addEventListener('click', () => {
        if (setup.ticker_setups.length > 0) {
          const symbol = setup.ticker_setups[0].symbol;
          window.location.href = `/trading?symbol=${symbol}`;
        }
      });
    }
  }
  
  // Update info section
  const detailInfo = detailContainer.querySelector('.setup-detail-info');
  if (detailInfo) {
    detailInfo.innerHTML = `
      <div class="setup-info-group">
        <div class="setup-info-label">Date</div>
        <div class="setup-info-value">${formattedDate}</div>
      </div>
      <div class="setup-info-group">
        <div class="setup-info-label">Source</div>
        <div class="setup-info-value">
          <span class="setup-source ${sourceClass}">${setup.source}</span>
        </div>
      </div>
      <div class="setup-info-group">
        <div class="setup-info-label">Created</div>
        <div class="setup-info-value">${formattedCreated}</div>
      </div>
      <div class="setup-info-group">
        <div class="setup-info-label">Tickers</div>
        <div class="setup-info-value setup-tickers">
          ${setup.ticker_setups.map(ts => 
            `<span class="setup-ticker-tag">${ts.symbol}</span>`
          ).join('')}
        </div>
      </div>
    `;
  }
  
  // Update raw text
  const rawText = detailContainer.querySelector('.setup-raw-text');
  if (rawText) {
    rawText.textContent = setup.raw_text;
  }
  
  // Update ticker setups
  const tickerSetupsContainer = detailContainer.querySelector('.ticker-setups-container');
  if (tickerSetupsContainer) {
    tickerSetupsContainer.innerHTML = '';
    
    setup.ticker_setups.forEach(tickerSetup => {
      const tickerCard = document.createElement('div');
      tickerCard.className = 'ticker-setup-card';
      
      // Create ticker header
      const tickerHeader = document.createElement('div');
      tickerHeader.className = 'ticker-setup-header';
      tickerHeader.innerHTML = `
        <div class="ticker-setup-symbol">${tickerSetup.symbol}</div>
        <div class="ticker-setup-actions">
          <div class="ticker-setup-action" data-action="chart" data-symbol="${tickerSetup.symbol}">
            📊
          </div>
          <div class="ticker-setup-action" data-action="trade" data-symbol="${tickerSetup.symbol}">
            💰
          </div>
        </div>
      `;
      
      // Create ticker body
      const tickerBody = document.createElement('div');
      tickerBody.className = 'ticker-setup-body';
      
      // Add ticker text if available
      if (tickerSetup.text) {
        const tickerText = document.createElement('div');
        tickerText.className = 'ticker-setup-text';
        tickerText.textContent = tickerSetup.text;
        tickerBody.appendChild(tickerText);
      }
      
      // Add signals if available
      if (tickerSetup.signals && tickerSetup.signals.length > 0) {
        const signalsContainer = document.createElement('div');
        signalsContainer.className = 'signals-container';
        
        const signalsTitle = document.createElement('div');
        signalsTitle.className = 'signals-title';
        signalsTitle.textContent = 'Signals';
        signalsContainer.appendChild(signalsTitle);
        
        const signalList = document.createElement('div');
        signalList.className = 'signal-list';
        
        tickerSetup.signals.forEach(signal => {
          const signalItem = document.createElement('div');
          signalItem.className = `signal-item ${signal.category.toLowerCase()}`;
          
          // Signal header
          const signalHeader = document.createElement('div');
          signalHeader.className = 'signal-header';
          signalHeader.innerHTML = `
            <div class="signal-category">${signal.category}</div>
            <div class="signal-aggressiveness ${signal.aggressiveness.toLowerCase()}">
              ${signal.aggressiveness}
            </div>
          `;
          signalItem.appendChild(signalHeader);
          
          // Signal details
          const signalDetails = document.createElement('div');
          signalDetails.className = 'signal-details';
          
          // Trigger details
          const triggerGroup = document.createElement('div');
          triggerGroup.className = 'signal-detail-group';
          triggerGroup.innerHTML = `
            <div class="signal-detail-label">Trigger</div>
            <div class="signal-detail-value">${formatTrigger(signal.trigger)}</div>
          `;
          signalDetails.appendChild(triggerGroup);
          
          // Comparison details
          const comparisonGroup = document.createElement('div');
          comparisonGroup.className = 'signal-detail-group';
          comparisonGroup.innerHTML = `
            <div class="signal-detail-label">Comparison</div>
            <div class="signal-detail-value">${signal.comparison}</div>
          `;
          signalDetails.appendChild(comparisonGroup);
          
          signalItem.appendChild(signalDetails);
          
          // Signal targets
          if (signal.targets && signal.targets.length > 0) {
            const targetsContainer = document.createElement('div');
            targetsContainer.className = 'signal-targets';
            
            const targetsTitle = document.createElement('div');
            targetsTitle.className = 'signal-targets-title';
            targetsTitle.textContent = 'Targets';
            targetsContainer.appendChild(targetsTitle);
            
            const targetsList = document.createElement('div');
            targetsList.className = 'signal-targets-list';
            
            signal.targets.forEach(target => {
              const targetItem = document.createElement('div');
              targetItem.className = 'signal-target';
              targetItem.innerHTML = `
                <div class="signal-target-price">${formatPrice(target.price)}</div>
                <div class="signal-target-percentage">${formatPercent(target.percentage)}</div>
              `;
              targetsList.appendChild(targetItem);
            });
            
            targetsContainer.appendChild(targetsList);
            signalItem.appendChild(targetsContainer);
          }
          
          signalList.appendChild(signalItem);
        });
        
        signalsContainer.appendChild(signalList);
        tickerBody.appendChild(signalsContainer);
      }
      
      // Add bias if available
      if (tickerSetup.bias) {
        const biasContainer = document.createElement('div');
        biasContainer.className = 'bias-container';
        
        const biasTitle = document.createElement('div');
        biasTitle.className = 'bias-title';
        biasTitle.textContent = 'Market Bias';
        biasContainer.appendChild(biasTitle);
        
        const biasCard = document.createElement('div');
        biasCard.className = `bias-card ${tickerSetup.bias.direction.toLowerCase()}`;
        
        // Bias header
        const biasHeader = document.createElement('div');
        biasHeader.className = 'bias-header';
        biasHeader.innerHTML = `
          <div class="bias-direction ${tickerSetup.bias.direction.toLowerCase()}">
            ${tickerSetup.bias.direction}
          </div>
        `;
        biasCard.appendChild(biasHeader);
        
        // Bias details
        const biasDetails = document.createElement('div');
        biasDetails.className = 'bias-details';
        
        // Price details
        const priceGroup = document.createElement('div');
        priceGroup.className = 'bias-detail-group';
        priceGroup.innerHTML = `
          <div class="bias-detail-label">Price Level</div>
          <div class="bias-detail-value">${formatPrice(tickerSetup.bias.price)}</div>
        `;
        biasDetails.appendChild(priceGroup);
        
        // Condition details
        const conditionGroup = document.createElement('div');
        conditionGroup.className = 'bias-detail-group';
        conditionGroup.innerHTML = `
          <div class="bias-detail-label">Condition</div>
          <div class="bias-detail-value">${tickerSetup.bias.condition}</div>
        `;
        biasDetails.appendChild(conditionGroup);
        
        biasCard.appendChild(biasDetails);
        
        // Add bias flip if available
        if (tickerSetup.bias.flip) {
          const biasFlip = document.createElement('div');
          biasFlip.className = 'bias-flip';
          
          const biasFlipTitle = document.createElement('div');
          biasFlipTitle.className = 'bias-flip-title';
          biasFlipTitle.textContent = 'Bias Flip Condition';
          biasFlip.appendChild(biasFlipTitle);
          
          const biasFlipDetails = document.createElement('div');
          biasFlipDetails.className = 'bias-flip-details';
          
          // Direction details
          const directionGroup = document.createElement('div');
          directionGroup.className = 'bias-detail-group';
          directionGroup.innerHTML = `
            <div class="bias-detail-label">Direction</div>
            <div class="bias-detail-value ${tickerSetup.bias.flip.direction.toLowerCase()}">
              ${tickerSetup.bias.flip.direction}
            </div>
          `;
          biasFlipDetails.appendChild(directionGroup);
          
          // Price level details
          const levelGroup = document.createElement('div');
          levelGroup.className = 'bias-detail-group';
          levelGroup.innerHTML = `
            <div class="bias-detail-label">Price Level</div>
            <div class="bias-detail-value">${formatPrice(tickerSetup.bias.flip.price_level)}</div>
          `;
          biasFlipDetails.appendChild(levelGroup);
          
          biasFlip.appendChild(biasFlipDetails);
          biasCard.appendChild(biasFlip);
        }
        
        biasContainer.appendChild(biasCard);
        tickerBody.appendChild(biasContainer);
      }
      
      tickerCard.appendChild(tickerHeader);
      tickerCard.appendChild(tickerBody);
      
      tickerSetupsContainer.appendChild(tickerCard);
    });
    
    // Add event listeners to ticker actions
    const tickerActions = tickerSetupsContainer.querySelectorAll('.ticker-setup-action');
    tickerActions.forEach(action => {
      action.addEventListener('click', () => {
        const actionType = action.dataset.action;
        const symbol = action.dataset.symbol;
        
        if (actionType === 'chart') {
          window.location.href = `/dashboard?symbol=${symbol}`;
        } else if (actionType === 'trade') {
          window.location.href = `/trading?symbol=${symbol}`;
        }
      });
    });
  }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
  // Setup filter
  const filterInput = document.getElementById('setup-filter');
  if (filterInput) {
    filterInput.addEventListener('input', event => {
      const filterValue = event.target.value.trim().toUpperCase();
      filterSetups(filterValue);
    });
  }
  
  // Refresh button
  const refreshButton = document.getElementById('refresh-setups');
  if (refreshButton) {
    refreshButton.addEventListener('click', () => {
      syncDiscordSetups(true);
    });
  }
}

/**
 * Filter setups by symbol
 * @param {string} filter - Filter value
 */
function filterSetups(filter) {
  state.filter = filter;
  
  const setupRows = document.querySelectorAll('#setup-list-body tr');
  
  setupRows.forEach(row => {
    const tickerTags = row.querySelectorAll('.setup-ticker-tag');
    let match = false;
    
    // If filter is empty, show all
    if (!filter) {
      match = true;
    } else {
      // Check if any ticker matches the filter
      tickerTags.forEach(tag => {
        if (tag.textContent.includes(filter)) {
          match = true;
        }
      });
    }
    
    row.style.display = match ? '' : 'none';
  });
}

/**
 * Update loading indicator
 * @param {boolean} isLoading - Whether loading is in progress
 * @param {string} [message] - Loading message
 */
function updateLoadingIndicator(isLoading, message = 'Loading...') {
  const loadingIndicator = document.getElementById('loading-indicator');
  if (!loadingIndicator) return;
  
  if (isLoading) {
    loadingIndicator.textContent = message;
    loadingIndicator.style.display = 'block';
  } else {
    loadingIndicator.style.display = 'none';
  }
}

/**
 * Format trigger value
 * @param {number|Array} trigger - Trigger value or range
 * @returns {string} Formatted trigger
 */
function formatTrigger(trigger) {
  if (Array.isArray(trigger)) {
    return `${formatPrice(trigger[0])} - ${formatPrice(trigger[1])}`;
  }
  
  return formatPrice(trigger);
}

/**
 * Format price value
 * @param {number} price - Price value
 * @returns {string} Formatted price
 */
function formatPrice(price) {
  return price.toFixed(2);
}

/**
 * Format percentage value
 * @param {number} value - Percentage value (0.25 = 25%)
 * @returns {string} Formatted percentage
 */
function formatPercent(value) {
  return `${(value * 100).toFixed(0)}%`;
}

/**
 * Display error message
 * @param {string} message - Error message
 */
function displayError(message) {
  const errorContainer = document.getElementById('notification-container');
  if (!errorContainer) return;
  
  const notification = document.createElement('div');
  notification.className = 'notification error';
  notification.textContent = message;
  
  // Add close button
  const closeButton = document.createElement('button');
  closeButton.className = 'notification-close';
  closeButton.innerHTML = '&times;';
  closeButton.addEventListener('click', () => {
    notification.remove();
  });
  
  notification.appendChild(closeButton);
  errorContainer.appendChild(notification);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    notification.remove();
  }, 5000);
}

/**
 * Display notification message
 * @param {string} message - Message to display
 * @param {string} type - Notification type ('success', 'warning', 'info')
 */
function displayNotification(message, type = 'info') {
  const notificationContainer = document.getElementById('notification-container');
  if (!notificationContainer) return;
  
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  // Add close button
  const closeButton = document.createElement('button');
  closeButton.className = 'notification-close';
  closeButton.innerHTML = '&times;';
  closeButton.addEventListener('click', () => {
    notification.remove();
  });
  
  notification.appendChild(closeButton);
  notificationContainer.appendChild(notification);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    notification.remove();
  }, 5000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initSetupViewer);

// Export functions for external use
export {
  loadSetups,
  syncDiscordSetups,
  loadSetupDetail
};