import io from 'socket.io-client';

/**
 * WebSocketService
 * Handles WebSocket connections and events
 */
class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.eventHandlers = {
      'connect': [],
      'disconnect': [],
      'price_update': [],
      'signal_triggered': [],
      'trade_executed': [],
      'error': []
    };
  }
  
  /**
   * Initialize WebSocket connection
   * @returns {Promise} Promise that resolves when connected
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        // If already connected, resolve immediately
        if (this.socket && this.connected) {
          resolve();
          return;
        }
        
        // Create a new socket instance
        this.socket = io();
        
        // Set up connection event handlers
        this.socket.on('connect', () => {
          console.log('WebSocket connected');
          this.connected = true;
          this._notifyHandlers('connect');
          resolve();
        });
        
        this.socket.on('disconnect', () => {
          console.log('WebSocket disconnected');
          this.connected = false;
          this._notifyHandlers('disconnect');
        });
        
        this.socket.on('connect_error', (error) => {
          console.error('WebSocket connection error:', error);
          this._notifyHandlers('error', { message: 'Connection error', error });
          reject(error);
        });
        
        // Set up business event handlers
        this.socket.on('price_update', (data) => {
          this._notifyHandlers('price_update', data);
        });
        
        this.socket.on('signal_triggered', (data) => {
          this._notifyHandlers('signal_triggered', data);
        });
        
        this.socket.on('trade_executed', (data) => {
          this._notifyHandlers('trade_executed', data);
        });
        
      } catch (error) {
        console.error('WebSocket initialization error:', error);
        reject(error);
      }
    });
  }
  
  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
  
  /**
   * Subscribe to ticker updates
   * @param {Array} tickers - Array of ticker symbols to subscribe to
   */
  subscribeTickers(tickers) {
    if (!this.socket || !this.connected) {
      console.error('Cannot subscribe: WebSocket not connected');
      return;
    }
    
    this.socket.emit('subscribe_tickers', { tickers });
    console.log('Subscribed to tickers:', tickers);
  }
  
  /**
   * Unsubscribe from ticker updates
   * @param {Array} tickers - Array of ticker symbols to unsubscribe from
   */
  unsubscribeTickers(tickers) {
    if (!this.socket || !this.connected) {
      console.error('Cannot unsubscribe: WebSocket not connected');
      return;
    }
    
    this.socket.emit('unsubscribe_tickers', { tickers });
    console.log('Unsubscribed from tickers:', tickers);
  }
  
  /**
   * Register event handler
   * @param {string} event - Event name
   * @param {function} handler - Event handler function
   */
  on(event, handler) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    
    this.eventHandlers[event].push(handler);
    return this;
  }
  
  /**
   * Remove event handler
   * @param {string} event - Event name
   * @param {function} handler - Event handler function to remove
   */
  off(event, handler) {
    if (!this.eventHandlers[event]) return this;
    
    this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
    return this;
  }
  
  /**
   * Notify all registered handlers for an event
   * @param {string} event - Event name
   * @param {any} data - Event data
   * @private
   */
  _notifyHandlers(event, data) {
    if (!this.eventHandlers[event]) return;
    
    this.eventHandlers[event].forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error(`Error in ${event} handler:`, error);
      }
    });
  }
}

// Export as singleton
const websocketService = new WebSocketService();
export default websocketService;