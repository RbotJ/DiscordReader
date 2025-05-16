/**
 * API Service
 * Handles HTTP requests to the server API
 */
class ApiService {
  /**
   * Make a GET request to the server
   * @param {string} endpoint - API endpoint to fetch from
   * @returns {Promise} Promise resolving to the response data
   */
  async get(endpoint) {
    try {
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching ${endpoint}:`, error);
      throw error;
    }
  }
  
  /**
   * Make a POST request to the server
   * @param {string} endpoint - API endpoint to post to
   * @param {Object} data - Data to send in the request body
   * @returns {Promise} Promise resolving to the response data
   */
  async post(endpoint, data) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error posting to ${endpoint}:`, error);
      throw error;
    }
  }
  
  /**
   * Get available tickers with trading setups
   * @returns {Promise<Array>} Promise resolving to an array of tickers
   */
  async getTickers() {
    return this.get('/api/tickers');
  }
  
  /**
   * Get account information
   * @returns {Promise<Object>} Promise resolving to account information
   */
  async getAccount() {
    return this.get('/api/account');
  }
  
  /**
   * Get positions
   * @returns {Promise<Array>} Promise resolving to an array of positions
   */
  async getPositions() {
    return this.get('/api/positions');
  }
  
  /**
   * Get historical candle data for a ticker
   * @param {string} ticker - Ticker symbol
   * @param {string} timeframe - Timeframe (e.g., '1min', '5min', '1day')
   * @param {number} limit - Number of candles to fetch
   * @returns {Promise<Array>} Promise resolving to an array of candles
   */
  async getCandles(ticker, timeframe = '1min', limit = 100) {
    return this.get(`/api/candles/${ticker}?timeframe=${timeframe}&limit=${limit}`);
  }
  
  /**
   * Get trading signals for a ticker
   * @param {string} ticker - Ticker symbol
   * @returns {Promise<Array>} Promise resolving to an array of signals
   */
  async getSignals(ticker) {
    return this.get(`/api/signals/${ticker}`);
  }
  
  /**
   * Execute a trade
   * @param {Object} tradeData - Trade data
   * @returns {Promise<Object>} Promise resolving to trade result
   */
  async executeTrade(tradeData) {
    return this.post('/api/trade', tradeData);
  }
  
  /**
   * Close a position
   * @param {string} ticker - Ticker symbol
   * @returns {Promise<Object>} Promise resolving to close result
   */
  async closePosition(ticker) {
    return this.post('/api/close', { ticker });
  }
  
  /**
   * Submit a new setup
   * @param {Object} setupData - Setup data
   * @returns {Promise<Object>} Promise resolving to submission result
   */
  async submitSetup(setupData) {
    return this.post('/api/setup', setupData);
  }
}

// Export as singleton
const apiService = new ApiService();
export default apiService;