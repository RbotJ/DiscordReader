import { io } from 'socket.io-client';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = {
      marketUpdate: [],
      signalFired: [],
      orderUpdate: [],
      positionUpdate: [],
      connect: [],
      disconnect: []
    };
  }

  connect() {
    // Connect to the server's WebSocket
    this.socket = io(window.location.origin, {
      path: '/ws',
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10
    });

    // Register socket event handlers
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this._notifyListeners('connect');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this._notifyListeners('disconnect');
    });

    this.socket.on('market_update', (data) => {
      this._notifyListeners('marketUpdate', data);
    });

    this.socket.on('signal_fired', (data) => {
      this._notifyListeners('signalFired', data);
    });

    this.socket.on('order_update', (data) => {
      this._notifyListeners('orderUpdate', data);
    });

    this.socket.on('position_update', (data) => {
      this._notifyListeners('positionUpdate', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  subscribe(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return () => this.unsubscribe(event, callback);
  }

  unsubscribe(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  _notifyListeners(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  loadTickers() {
    // Request today's active tickers on connect
    if (this.socket && this.socket.connected) {
      this.socket.emit('load_tickers');
    }
  }
}

// Create a singleton instance
const websocketService = new WebSocketService();
export default websocketService;