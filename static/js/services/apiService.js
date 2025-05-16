import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

export const fetchActiveTickers = async () => {
  try {
    const response = await apiClient.get('/tickers/active');
    return response.data;
  } catch (error) {
    console.error('Error fetching active tickers:', error);
    throw error;
  }
};

export const fetchTickerData = async (symbol, timeframe = '10m', days = 1) => {
  try {
    const response = await apiClient.get(`/market/candles/${symbol}`, {
      params: { timeframe, days }
    });
    return response.data;
  } catch (error) {
    console.error(`Error fetching ticker data for ${symbol}:`, error);
    throw error;
  }
};

export const fetchSignals = async (symbol) => {
  try {
    const response = await apiClient.get(`/strategy/signals/${symbol}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching signals for ${symbol}:`, error);
    throw error;
  }
};

export const fetchPositions = async () => {
  try {
    const response = await apiClient.get('/execution/positions');
    return response.data;
  } catch (error) {
    console.error('Error fetching positions:', error);
    throw error;
  }
};

export const fetchOrders = async (status = 'all') => {
  try {
    const response = await apiClient.get('/execution/orders', {
      params: { status }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching orders:', error);
    throw error;
  }
};

export default {
  fetchActiveTickers,
  fetchTickerData,
  fetchSignals,
  fetchPositions,
  fetchOrders
};