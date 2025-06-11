/**
 * API Client for the Trading Application
 * 
 * This module provides a unified interface for making API calls to the trading
 * application backend. It handles authentication, request formatting, and error handling.
 */

/**
 * Base API client for the trading application
 */
class ApiClient {
  /**
   * Create a new API client instance
   * @param {string} [baseUrl=''] - Base URL for API requests (defaults to current host)
   */
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl || window.location.origin;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
  }

  /**
   * Make a request to the API
   * @param {string} endpoint - API endpoint (e.g., '/api/account')
   * @param {Object} options - Request options
   * @param {string} [options.method='GET'] - HTTP method
   * @param {Object} [options.headers={}] - Additional headers
   * @param {Object} [options.params={}] - URL parameters
   * @param {Object|Array} [options.data=null] - Request body data
   * @returns {Promise<Object>} Response data
   * @throws {Error} If the request fails
   */
  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      params = {},
      data = null
    } = options;

    // Build URL with parameters
    let url = `${this.baseUrl}${endpoint}`;
    if (Object.keys(params).length > 0) {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        queryParams.append(key, value);
      });
      url = `${url}?${queryParams.toString()}`;
    }

    // Build request options
    const requestOptions = {
      method,
      headers: {
        ...this.defaultHeaders,
        ...headers
      }
    };

    // Add request body for non-GET requests
    if (data !== null && method !== 'GET') {
      requestOptions.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, requestOptions);
      
      // Handle HTTP errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new ApiError(
          `API request failed: ${response.status} ${response.statusText}`,
          response.status,
          errorData
        );
      }
      
      // Parse JSON response
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        `API request failed: ${error.message}`,
        0,
        null
      );
    }
  }

  /**
   * Make a GET request
   * @param {string} endpoint - API endpoint
   * @param {Object} [params={}] - URL parameters
   * @param {Object} [headers={}] - Additional headers
   * @returns {Promise<Object>} Response data
   */
  async get(endpoint, params = {}, headers = {}) {
    return this.request(endpoint, {
      method: 'GET',
      params,
      headers
    });
  }

  /**
   * Make a POST request
   * @param {string} endpoint - API endpoint
   * @param {Object|Array} [data=null] - Request body data
   * @param {Object} [params={}] - URL parameters
   * @param {Object} [headers={}] - Additional headers
   * @returns {Promise<Object>} Response data
   */
  async post(endpoint, data = null, params = {}, headers = {}) {
    return this.request(endpoint, {
      method: 'POST',
      data,
      params,
      headers
    });
  }

  /**
   * Make a PUT request
   * @param {string} endpoint - API endpoint
   * @param {Object|Array} [data=null] - Request body data
   * @param {Object} [params={}] - URL parameters
   * @param {Object} [headers={}] - Additional headers
   * @returns {Promise<Object>} Response data
   */
  async put(endpoint, data = null, params = {}, headers = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      data,
      params,
      headers
    });
  }

  /**
   * Make a DELETE request
   * @param {string} endpoint - API endpoint
   * @param {Object} [params={}] - URL parameters
   * @param {Object} [headers={}] - Additional headers
   * @returns {Promise<Object>} Response data
   */
  async delete(endpoint, params = {}, headers = {}) {
    return this.request(endpoint, {
      method: 'DELETE',
      params,
      headers
    });
  }
}

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
  /**
   * Create a new API error
   * @param {string} message - Error message
   * @param {number} status - HTTP status code
   * @param {Object} data - Additional error data
   */
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Create API client instances for specific areas of the application
 */

// Account API client
class AccountApiClient extends ApiClient {
  /**
   * Get account information
   * @returns {Promise<Object>} Account information
   */
  async getAccount() {
    return this.get('/api/account');
  }

  /**
   * Get current positions
   * @returns {Promise<Array>} List of positions
   */
  async getPositions() {
    return this.get('/api/positions');
  }

  /**
   * Close a position
   * @param {string} symbol - The symbol to close
   * @param {number} [percentage=1.0] - Percentage of the position to close (0.0-1.0)
   * @returns {Promise<Object>} Result of the close operation
   */
  async closePosition(symbol, percentage = 1.0) {
    return this.delete(`/api/positions/${symbol}`, { percentage });
  }
}

// Market API client
class MarketApiClient extends ApiClient {
  /**
   * Get market status
   * @returns {Promise<Object>} Market status information
   */
  async getMarketStatus() {
    return this.get('/api/market/status');
  }

  /**
   * Get candle data for a ticker
   * @param {string} ticker - Ticker symbol
   * @param {string} [timeframe='1Day'] - Candle timeframe
   * @param {number} [limit=100] - Number of candles to return
   * @returns {Promise<Array>} Candle data
   */
  async getCandles(ticker, timeframe = '1Day', limit = 100) {
    return this.get(`/api/market/candles/${ticker}`, { timeframe, limit });
  }

  /**
   * Get the latest quote for a ticker
   * @param {string} ticker - Ticker symbol
   * @returns {Promise<Object>} Quote data
   */
  async getQuote(ticker) {
    return this.get(`/api/market/quote/${ticker}`);
  }

  /**
   * Get available tickers with trading setups
   * @returns {Promise<Array>} List of ticker symbols
   */
  async getTickers() {
    return this.get('/api/market/tickers');
  }
}

// Setup API client
class SetupApiClient extends ApiClient {
  /**
   * Get recent trading setups
   * @param {number} [limit=10] - Maximum number of setups to return
   * @param {string} [symbol=null] - Filter by ticker symbol
   * @returns {Promise<Array>} List of setup messages
   */
  async getRecentSetups(limit = 10, symbol = null) {
    const params = { limit };
    if (symbol) {
      params.symbol = symbol;
    }
    return this.get('/api/setups/recent', params);
  }

  /**
   * Get details for a specific setup
   * @param {number} setupId - ID of the setup
   * @returns {Promise<Object>} Setup details
   */
  async getSetupDetail(setupId) {
    return this.get(`/api/setups/${setupId}`);
  }

  /**
   * Sync recent messages from Discord
   * @param {boolean} [refresh=false] - Force refresh of already processed messages
   * @returns {Promise<Object>} Result of the sync operation
   */
  async syncDiscordMessages(refresh = false) {
    return this.post('/api/setups/sync-discord', null, { refresh });
  }
}

// Signal API client
class SignalApiClient extends ApiClient {
  /**
   * Get signals for a ticker
   * @param {string} ticker - Ticker symbol
   * @returns {Promise<Array>} List of signals
   */
  async getSignals(ticker) {
    return this.get(`/api/signals/${ticker}`);
  }

  /**
   * Add a signal (for testing)
   * @param {Object} signal - Signal data
   * @returns {Promise<Object>} Created signal
   */
  async addSignal(signal) {
    return this.post('/api/signals', signal);
  }
}

// Trading API client
class TradingApiClient extends ApiClient {
  /**
   * Place an order
   * @param {Object} order - Order details
   * @param {string} order.symbol - Ticker symbol
   * @param {number} order.qty - Order quantity
   * @param {string} order.side - Order side ('buy' or 'sell')
   * @param {string} [order.type='market'] - Order type ('market', 'limit', 'stop', 'stop_limit')
   * @param {string} [order.time_in_force='day'] - Time in force ('day', 'gtc', 'ioc', 'opg')
   * @param {number} [order.limit_price] - Limit price (required for limit and stop_limit orders)
   * @param {number} [order.stop_price] - Stop price (required for stop and stop_limit orders)
   * @returns {Promise<Object>} Order result
   */
  async placeOrder(order) {
    return this.post('/api/trading/orders', order);
  }
}

// Make API clients globally available
window.ApiClient = ApiClient;
window.ApiError = ApiError;
window.AccountApiClient = AccountApiClient;
window.MarketApiClient = MarketApiClient;
window.SetupApiClient = SetupApiClient;
window.SignalApiClient = SignalApiClient;
window.TradingApiClient = TradingApiClient;