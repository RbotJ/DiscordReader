/**
 * WebSocket Service
 * Handles WebSocket connections for real-time data
 */
class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.callbacks = {
      onConnect: null,
      onDisconnect: null,
      onMarketData: null,
      onSignalUpdate: null,
      onPositionUpdate: null,
      onAccountUpdate: null,
      onError: null
    };
  }

  /**
   * Initialize the WebSocket connection
   */
  initialize() {
    try {
      // Get the protocol (ws or wss) based on the current page protocol
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const socketUrl = `${protocol}//${host}/socket.io/?EIO=4&transport=websocket`;

      // Create a new WebSocket connection
      this.socket = io();

      // Set up event listeners
      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.connected = true;
        if (this.callbacks.onConnect) {
          this.callbacks.onConnect();
        }
      });

      this.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        this.connected = false;
        if (this.callbacks.onDisconnect) {
          this.callbacks.onDisconnect();
        }
      });

      this.socket.on('market_data', (data) => {
        if (this.callbacks.onMarketData) {
          this.callbacks.onMarketData(data);
        }
      });

      this.socket.on('signal_update', (data) => {
        if (this.callbacks.onSignalUpdate) {
          this.callbacks.onSignalUpdate(data);
        }
      });

      this.socket.on('position_update', (data) => {
        if (this.callbacks.onPositionUpdate) {
          this.callbacks.onPositionUpdate(data);
        }
      });

      this.socket.on('account_update', (data) => {
        if (this.callbacks.onAccountUpdate) {
          this.callbacks.onAccountUpdate(data);
        }
      });
      
      this.socket.on('error', (error) => {
        console.error('WebSocket error:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError(error);
        }
      });

      return true;
    } catch (error) {
      console.error('Error initializing WebSocket:', error);
      return false;
    }
  }

  /**
   * Register callback functions for WebSocket events
   * @param {Object} callbacks - Object containing callback functions
   */
  registerCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Subscribe to market data for specific tickers
   * @param {Array} tickers - Array of ticker symbols to subscribe to
   */
  subscribeTickers(tickers) {
    if (!this.connected || !tickers || !tickers.length) {
      return false;
    }

    this.socket.emit('subscribe_tickers', { tickers });
    return true;
  }

  /**
   * Send a message to the server
   * @param {string} eventName - Name of the event
   * @param {Object} data - Data to send with the event
   */
  send(eventName, data) {
    if (!this.connected) {
      return false;
    }

    this.socket.emit(eventName, data);
    return true;
  }

  /**
   * Disconnect the WebSocket connection
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }
}

// Create and export a singleton instance
const websocketService = new WebSocketService();
export default websocketService;