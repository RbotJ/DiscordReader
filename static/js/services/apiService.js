/**
 * API Service
 * 
 * Provides methods for interacting with the backend API
 */

const API_BASE_URL = '/api';

/**
 * Handle API response and extract data
 */
const handleResponse = async (response) => {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} - ${errorText}`);
  }
  
  const data = await response.json();
  return data;
};

/**
 * Make an API request
 */
const apiRequest = async (endpoint, options = {}) => {
  try {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    return await handleResponse(response);
  } catch (error) {
    console.error(`API request failed: ${error.message}`);
    throw error;
  }
};

/**
 * Fetch available tickers
 */
export const fetchTickers = async () => {
  return apiRequest('/tickers');
};

/**
 * Fetch account information
 */
export const fetchAccount = async () => {
  return apiRequest('/account');
};

/**
 * Fetch open positions
 */
export const fetchPositions = async () => {
  return apiRequest('/positions');
};

/**
 * Fetch candle data for a ticker
 */
export const fetchCandles = async (ticker, timeframe = '1min', limit = 100) => {
  return apiRequest(`/candles/${ticker}?timeframe=${timeframe}&limit=${limit}`);
};

/**
 * Fetch signals for a ticker
 */
export const fetchSignals = async (ticker) => {
  return apiRequest(`/signals/${ticker}`);
};

/**
 * Place a trade order
 */
export const placeOrder = async (orderData) => {
  return apiRequest('/orders', {
    method: 'POST',
    body: JSON.stringify(orderData)
  });
};

/**
 * Cancel a trade order
 */
export const cancelOrder = async (orderId) => {
  return apiRequest(`/orders/${orderId}`, {
    method: 'DELETE'
  });
};

/**
 * Get all orders (open by default)
 */
export const fetchOrders = async (status = 'open') => {
  return apiRequest(`/orders?status=${status}`);
};