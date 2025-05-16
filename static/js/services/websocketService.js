/**
 * WebSocket Service
 * 
 * Provides methods for real-time communication with the backend
 */
import { io } from 'socket.io-client';

let socket = null;
const eventHandlers = {};

/**
 * Initialize WebSocket connection and set up event handlers
 */
export const initializeSocket = () => {
  if (socket) {
    // Socket already initialized
    return socket;
  }
  
  // Create new socket connection
  socket = io({
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    transports: ['websocket']
  });
  
  // Handle connection events
  socket.on('connect', () => {
    console.log('WebSocket connected');
    triggerHandlers('connect');
  });
  
  socket.on('disconnect', (reason) => {
    console.log(`WebSocket disconnected: ${reason}`);
    triggerHandlers('disconnect', reason);
  });
  
  socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
    triggerHandlers('connect_error', error);
  });
  
  // Handle custom events
  socket.on('market_data', (data) => {
    triggerHandlers('market_data', data);
  });
  
  socket.on('candle_update', (data) => {
    triggerHandlers('candle_update', data);
  });
  
  socket.on('signal_update', (data) => {
    triggerHandlers('signal_update', data);
  });
  
  socket.on('trade_update', (data) => {
    triggerHandlers('trade_update', data);
  });
  
  return socket;
};

/**
 * Register an event handler
 */
export const on = (event, handler) => {
  if (!eventHandlers[event]) {
    eventHandlers[event] = [];
  }
  
  eventHandlers[event].push(handler);
  
  return () => off(event, handler);
};

/**
 * Unregister an event handler
 */
export const off = (event, handler) => {
  if (!eventHandlers[event]) {
    return;
  }
  
  const index = eventHandlers[event].indexOf(handler);
  if (index !== -1) {
    eventHandlers[event].splice(index, 1);
  }
};

/**
 * Trigger event handlers for an event
 */
const triggerHandlers = (event, ...args) => {
  if (!eventHandlers[event]) {
    return;
  }
  
  for (const handler of eventHandlers[event]) {
    try {
      handler(...args);
    } catch (error) {
      console.error(`Error in ${event} handler:`, error);
    }
  }
};

/**
 * Subscribe to tickers for real-time updates
 */
export const subscribeTickers = (tickers) => {
  if (!socket || !socket.connected) {
    console.error('WebSocket not connected, cannot subscribe to tickers');
    return false;
  }
  
  socket.emit('subscribe_tickers', { tickers });
  return true;
};

/**
 * Unsubscribe from ticker updates
 */
export const unsubscribeTickers = (tickers) => {
  if (!socket || !socket.connected) {
    console.error('WebSocket not connected, cannot unsubscribe from tickers');
    return false;
  }
  
  socket.emit('unsubscribe_tickers', { tickers });
  return true;
};

/**
 * Send a message to the server
 */
export const emit = (event, data) => {
  if (!socket || !socket.connected) {
    console.error(`WebSocket not connected, cannot emit ${event}`);
    return false;
  }
  
  socket.emit(event, data);
  return true;
};

/**
 * Disconnect the socket
 */
export const disconnect = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};