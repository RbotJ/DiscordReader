/**
 * Dashboard Module for the Trading Application
 * 
 * This module handles the functionality of the main trading dashboard,
 * including chart display, watchlist management, and position monitoring.
 */

import { formatCurrency, formatPercent, formatDate, formatPrice } from '/static/common/js/utils.js';
import { MarketApiClient, AccountApiClient } from '/static/common/js/api-client.js';
import { createChart, initChartControls } from './charts.js';

// Initialize API clients
const marketApi = new MarketApiClient();
const accountApi = new AccountApiClient();

// Dashboard state
const state = {
  selectedSymbol: 'SPY',
  timeframe: '1Day',
  marketStatus: null,
  watchlist: [],
  positions: [],
  account: null
};

/**
 * Initialize the dashboard
 */
async function initDashboard() {
  try {
    // Initialize chart
    const chartContainer = document.getElementById('chart-plot-area');
    if (chartContainer) {
      createChart(chartContainer, state.selectedSymbol, state.timeframe);
      initChartControls(document.getElementById('chart-controls'));
    }

    // Initialize data
    await Promise.all([
      loadMarketStatus(),
      loadWatchlist(),
      loadAccount(),
      loadPositions()
    ]);

    // Set up event listeners
    setupEventListeners();

    // Set up periodic data refresh
    setupDataRefresh();

    console.log('Dashboard initialized successfully');
  } catch (error) {
    console.error('Error initializing dashboard:', error);
    displayError('Failed to initialize dashboard. Please try refreshing the page.');
  }
}

/**
 * Load current market status
 */
async function loadMarketStatus() {
  try {
    const status = await marketApi.getMarketStatus();
    state.marketStatus = status;
    updateMarketStatusDisplay(status);
  } catch (error) {
    console.error('Error loading market status:', error);
    displayError('Failed to load market status.');
  }
}

/**
 * Update the market status display
 * @param {Object} status - Market status data
 */
function updateMarketStatusDisplay(status) {
  const statusElement = document.getElementById('market-status');
  if (!statusElement) return;

  // Determine status class and text
  let statusClass = 'market-closed';
  let statusText = 'Closed';

  if (status.is_open) {
    statusClass = 'market-open';
    statusText = 'Open';
  } else if (status.is_pre_market) {
    statusClass = 'market-pre';
    statusText = 'Pre-Market';
  } else if (status.is_after_hours) {
    statusClass = 'market-after';
    statusText = 'After-Hours';
  }

  // Update status display
  statusElement.className = `market-status ${statusClass}`;
  statusElement.innerHTML = `
    <span class="market-status-indicator"></span>
    <span>${statusText}</span>
  `;

  // Update next open/close times
  const nextEventElement = document.getElementById('market-next-event');
  if (nextEventElement) {
    if (status.is_open) {
      nextEventElement.textContent = `Closes: ${formatDate(status.next_close, 'short')} ${formatTime(status.next_close)}`;
    } else {
      nextEventElement.textContent = `Opens: ${formatDate(status.next_open, 'short')} ${formatTime(status.next_open)}`;
    }
  }
}

/**
 * Load watchlist data
 */
async function loadWatchlist() {
  try {
    const tickers = await marketApi.getTickers();
    state.watchlist = tickers;
    updateWatchlistDisplay(tickers);
  } catch (error) {
    console.error('Error loading watchlist:', error);
    displayError('Failed to load watchlist data.');
  }
}

/**
 * Update the watchlist display
 * @param {Array} tickers - List of ticker data
 */
function updateWatchlistDisplay(tickers) {
  const watchlistElement = document.getElementById('watchlist-list');
  if (!watchlistElement) return;

  // Clear current list
  watchlistElement.innerHTML = '';

  // Add items
  tickers.forEach(ticker => {
    const item = document.createElement('div');
    item.className = `watchlist-item ${ticker.symbol === state.selectedSymbol ? 'active' : ''}`;
    item.dataset.symbol = ticker.symbol;

    const changeClass = ticker.change_percent >= 0 ? 'positive' : 'negative';
    const changeSign = ticker.change_percent >= 0 ? '+' : '';

    item.innerHTML = `
      <div class="watchlist-ticker">${ticker.symbol}</div>
      <div class="watchlist-price">
        <div class="watchlist-price-current">${formatPrice(ticker.last_price)}</div>
        <div class="watchlist-price-change ${changeClass}">
          ${changeSign}${formatPercent(ticker.change_percent / 100)}
        </div>
      </div>
    `;

    item.addEventListener('click', () => selectSymbol(ticker.symbol));
    watchlistElement.appendChild(item);
  });
}

/**
 * Select a symbol to display
 * @param {string} symbol - Ticker symbol
 */
function selectSymbol(symbol) {
  state.selectedSymbol = symbol;
  
  // Update chart
  const chartContainer = document.getElementById('chart-plot-area');
  if (chartContainer) {
    createChart(chartContainer, symbol, state.timeframe);
  }
  
  // Update watchlist selection
  const watchlistItems = document.querySelectorAll('.watchlist-item');
  watchlistItems.forEach(item => {
    if (item.dataset.symbol === symbol) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
  
  // Update trade form
  const symbolInputs = document.querySelectorAll('.trade-symbol-input');
  symbolInputs.forEach(input => {
    input.value = symbol;
  });
}

/**
 * Load account information
 */
async function loadAccount() {
  try {
    const account = await accountApi.getAccount();
    state.account = account;
    updateAccountDisplay(account);
  } catch (error) {
    console.error('Error loading account:', error);
    displayError('Failed to load account information.');
  }
}

/**
 * Update the account display
 * @param {Object} account - Account data
 */
function updateAccountDisplay(account) {
  const balanceElement = document.getElementById('account-balance');
  if (balanceElement) {
    balanceElement.textContent = formatCurrency(account.equity);
  }
  
  const buyingPowerElement = document.getElementById('buying-power');
  if (buyingPowerElement) {
    buyingPowerElement.textContent = formatCurrency(account.buying_power);
  }
  
  const cashElement = document.getElementById('cash-balance');
  if (cashElement) {
    cashElement.textContent = formatCurrency(account.cash);
  }
}

/**
 * Load position information
 */
async function loadPositions() {
  try {
    const positions = await accountApi.getPositions();
    state.positions = positions;
    updatePositionsDisplay(positions);
  } catch (error) {
    console.error('Error loading positions:', error);
    displayError('Failed to load position information.');
  }
}

/**
 * Update the positions display
 * @param {Array} positions - List of position data
 */
function updatePositionsDisplay(positions) {
  const positionsTable = document.getElementById('positions-table-body');
  if (!positionsTable) return;
  
  // Clear current table
  positionsTable.innerHTML = '';
  
  if (positions.length === 0) {
    // Show no positions message
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="6" class="text-center">No positions found.</td>';
    positionsTable.appendChild(row);
    return;
  }
  
  // Add position rows
  positions.forEach(position => {
    const row = document.createElement('tr');
    
    const plClass = parseFloat(position.unrealized_pl) >= 0 ? 'positive' : 'negative';
    const plSign = parseFloat(position.unrealized_pl) >= 0 ? '+' : '';
    
    row.innerHTML = `
      <td>${position.symbol}</td>
      <td>${position.qty}</td>
      <td class="position-value">${formatPrice(position.avg_entry_price)}</td>
      <td class="position-value">${formatPrice(position.current_price)}</td>
      <td class="position-pl ${plClass}">
        ${plSign}${formatCurrency(position.unrealized_pl)}
        <small>(${plSign}${formatPercent(position.unrealized_plpc)})</small>
      </td>
      <td class="position-actions">
        <button class="position-action-btn" data-action="chart" data-symbol="${position.symbol}">Chart</button>
        <button class="position-action-btn close" data-action="close" data-symbol="${position.symbol}">Close</button>
      </td>
    `;
    
    positionsTable.appendChild(row);
  });
  
  // Add event listeners to position action buttons
  const actionButtons = positionsTable.querySelectorAll('.position-action-btn');
  actionButtons.forEach(button => {
    const action = button.dataset.action;
    const symbol = button.dataset.symbol;
    
    if (action === 'chart') {
      button.addEventListener('click', () => selectSymbol(symbol));
    } else if (action === 'close') {
      button.addEventListener('click', () => closePosition(symbol));
    }
  });
}

/**
 * Close a position
 * @param {string} symbol - Ticker symbol
 */
async function closePosition(symbol) {
  try {
    if (!confirm(`Are you sure you want to close your ${symbol} position?`)) {
      return;
    }
    
    const result = await accountApi.closePosition(symbol);
    
    if (result.status === 'success') {
      displayNotification(`Successfully closed ${symbol} position.`, 'success');
      // Refresh positions
      await loadPositions();
    } else {
      displayError(`Failed to close position: ${result.message}`);
    }
  } catch (error) {
    console.error('Error closing position:', error);
    displayError(`Failed to close position: ${error.message}`);
  }
}

/**
 * Set up event listeners for dashboard controls
 */
function setupEventListeners() {
  // Timeframe selector
  const timeframeOptions = document.querySelectorAll('.chart-timeframe-option');
  timeframeOptions.forEach(option => {
    option.addEventListener('click', () => {
      // Update active class
      timeframeOptions.forEach(opt => opt.classList.remove('active'));
      option.classList.add('active');
      
      // Update chart
      state.timeframe = option.dataset.timeframe;
      const chartContainer = document.getElementById('chart-plot-area');
      if (chartContainer) {
        createChart(chartContainer, state.selectedSymbol, state.timeframe);
      }
    });
  });
  
  // Watchlist search
  const watchlistSearch = document.getElementById('watchlist-search-input');
  if (watchlistSearch) {
    watchlistSearch.addEventListener('input', event => {
      const searchTerm = event.target.value.trim().toUpperCase();
      const watchlistItems = document.querySelectorAll('.watchlist-item');
      
      watchlistItems.forEach(item => {
        const symbol = item.dataset.symbol;
        if (symbol.includes(searchTerm)) {
          item.style.display = '';
        } else {
          item.style.display = 'none';
        }
      });
    });
  }
  
  // Trade form submission
  const tradeForm = document.getElementById('trade-form');
  if (tradeForm) {
    tradeForm.addEventListener('submit', async event => {
      event.preventDefault();
      
      const formData = new FormData(tradeForm);
      const order = {
        symbol: formData.get('symbol'),
        qty: parseFloat(formData.get('quantity')),
        side: formData.get('side'),
        type: formData.get('order-type'),
        time_in_force: formData.get('time-in-force')
      };
      
      // Add limit price if needed
      if (order.type === 'limit' || order.type === 'stop_limit') {
        order.limit_price = parseFloat(formData.get('limit-price'));
      }
      
      // Add stop price if needed
      if (order.type === 'stop' || order.type === 'stop_limit') {
        order.stop_price = parseFloat(formData.get('stop-price'));
      }
      
      try {
        const tradingApi = new TradingApiClient();
        const result = await tradingApi.placeOrder(order);
        
        if (result.status === 'success') {
          displayNotification(`Order placed successfully: ${order.side} ${order.qty} ${order.symbol}`, 'success');
          tradeForm.reset();
          
          // Refresh positions
          await loadPositions();
          await loadAccount();
        } else {
          displayError(`Failed to place order: ${result.message}`);
        }
      } catch (error) {
        console.error('Error placing order:', error);
        displayError(`Failed to place order: ${error.message}`);
      }
    });
  }
}

/**
 * Set up periodic data refresh
 */
function setupDataRefresh() {
  // Refresh market status every minute
  setInterval(loadMarketStatus, 60000);
  
  // Refresh watchlist prices every 10 seconds (when market is open)
  setInterval(() => {
    if (state.marketStatus && (state.marketStatus.is_open || state.marketStatus.is_pre_market || state.marketStatus.is_after_hours)) {
      loadWatchlist();
    }
  }, 10000);
  
  // Refresh account and positions every 30 seconds (when market is open)
  setInterval(() => {
    if (state.marketStatus && (state.marketStatus.is_open || state.marketStatus.is_pre_market || state.marketStatus.is_after_hours)) {
      loadAccount();
      loadPositions();
    }
  }, 30000);
}

/**
 * Display an error message
 * @param {string} message - Error message to display
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
 * Display a notification message
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

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', initDashboard);

// Export functions for external use
export {
  state,
  loadMarketStatus,
  loadWatchlist,
  loadAccount,
  loadPositions,
  selectSymbol
};