/**
 * API Service
 * 
 * This module provides functions to interact with the backend API
 */
import axios from 'axios';

const API_BASE_URL = '/api';

// Define API endpoints
const endpoints = {
  tickers: `${API_BASE_URL}/tickers`,
  account: `${API_BASE_URL}/account`,
  positions: `${API_BASE_URL}/positions`,
  candles: (ticker, timeframe = '1min', limit = 100) => 
    `${API_BASE_URL}/candles/${ticker}?timeframe=${timeframe}&limit=${limit}`,
  signals: (ticker) => `${API_BASE_URL}/signals/${ticker}`,
};

/**
 * Fetch available tickers
 * @returns {Promise<Array>} Array of ticker symbols
 */
export const fetchTickers = async () => {
  try {
    const response = await axios.get(endpoints.tickers);
    return response.data;
  } catch (error) {
    console.error('Error fetching tickers:', error);
    return [];
  }
};

/**
 * Fetch account information
 * @returns {Promise<Object>} Account information
 */
export const fetchAccount = async () => {
  try {
    const response = await axios.get(endpoints.account);
    return response.data;
  } catch (error) {
    console.error('Error fetching account:', error);
    return null;
  }
};

/**
 * Fetch positions
 * @returns {Promise<Array>} Array of positions
 */
export const fetchPositions = async () => {
  try {
    const response = await axios.get(endpoints.positions);
    return response.data;
  } catch (error) {
    console.error('Error fetching positions:', error);
    return [];
  }
};

/**
 * Fetch candle data for a ticker
 * @param {string} ticker - Ticker symbol
 * @param {string} timeframe - Candle timeframe (default: 1min)
 * @param {number} limit - Number of candles to return (default: 100)
 * @returns {Promise<Array>} Array of candles
 */
export const fetchCandles = async (ticker, timeframe = '1min', limit = 100) => {
  try {
    const response = await axios.get(endpoints.candles(ticker, timeframe, limit));
    return response.data;
  } catch (error) {
    console.error(`Error fetching candles for ${ticker}:`, error);
    return [];
  }
};

/**
 * Fetch signals for a ticker
 * @param {string} ticker - Ticker symbol
 * @returns {Promise<Object>} Signal data
 */
export const fetchSignals = async (ticker) => {
  try {
    const response = await axios.get(endpoints.signals(ticker));
    return response.data;
  } catch (error) {
    console.error(`Error fetching signals for ${ticker}:`, error);
    return null;
  }
};