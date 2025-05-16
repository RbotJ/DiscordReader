/**
 * WebSocket Service
 * 
 * This module provides functions to interact with the WebSocket server
 */
import { io } from 'socket.io-client';

// Store event listeners and socket instance
let socket = null;
let eventHandlers = {};
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Initialize the WebSocket connection
 * @returns {Object} socket instance
 */
export const initializeSocket = () => {
  if (socket) {
    console.log('Socket already initialized');
    return socket;
  }

  console.log('Initializing WebSocket connection...');
  
  // Create socket instance with auto-reconnect
  socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
  });

  // Handle socket connection events
  socket.on('connect', () => {
    console.log('WebSocket connected');
    reconnectAttempts = 0;
    
    // Trigger any registered connection handlers
    triggerEvent('connect');
  });

  socket.on('disconnect', (reason) => {
    console.log(`WebSocket disconnected: ${reason}`);
    triggerEvent('disconnect', reason);
  });

  socket.on('connection_response', (data) => {
    console.log('Socket connection response:', data);
    triggerEvent('connection_response', data);
  });

  socket.on('subscription_response', (data) => {
    console.log('Subscription response:', data);
    triggerEvent('subscription_response', data);
  });

  socket.on('market_data', (data) => {
    // Only log every 10th message to avoid console flooding
    if (Math.random() < 0.1) {
      console.log('Market data received:', data);
    }
    triggerEvent('market_data', data);
  });

  socket.on('signal_update', (data) => {
    console.log('Signal update received:', data);
    triggerEvent('signal_update', data);
  });

  socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error);
    reconnectAttempts++;
    triggerEvent('connect_error', error);
    
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error('Maximum reconnect attempts reached. Please refresh the page.');
      triggerEvent('max_reconnect_attempts');
    }
  });

  return socket;
};

/**
 * Subscribe to ticker updates
 * @param {Array} tickers - Array of ticker symbols to subscribe to
 */
export const subscribeTickers = (tickers) => {
  if (!socket) {
    console.error('Socket not initialized. Call initializeSocket() first.');
    return;
  }

  console.log('Subscribing to tickers:', tickers);
  socket.emit('subscribe_tickers', { tickers });
};

/**
 * Register an event handler
 * @param {string} event - Event name
 * @param {Function} handler - Event handler function
 */
export const on = (event, handler) => {
  if (!eventHandlers[event]) {
    eventHandlers[event] = [];
  }
  eventHandlers[event].push(handler);
};

/**
 * Remove an event handler
 * @param {string} event - Event name
 * @param {Function} handler - Event handler function
 */
export const off = (event, handler) => {
  if (!eventHandlers[event]) return;
  
  if (handler) {
    eventHandlers[event] = eventHandlers[event].filter(h => h !== handler);
  } else {
    // If no handler provided, remove all handlers for this event
    eventHandlers[event] = [];
  }
};

/**
 * Trigger an event
 * @param {string} event - Event name
 * @param {*} data - Event data
 */
const triggerEvent = (event, data) => {
  if (!eventHandlers[event]) return;
  
  eventHandlers[event].forEach(handler => {
    try {
      handler(data);
    } catch (error) {
      console.error(`Error in ${event} handler:`, error);
    }
  });
};

/**
 * Disconnect the WebSocket
 */
export const disconnect = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
    eventHandlers = {};
  }
};