import React, { useState, useEffect, useCallback, useRef, Component } from 'react';
import io from 'socket.io-client';

/** 
 * Generate a truly unique ID, using crypto.randomUUID when available.
 */
// Simple counter-based ID generation to ensure uniqueness
let idCounter = 0;
function generateId(prefix = 'id') {
  return `${prefix}-${++idCounter}`;
}

/**
 * A simple error boundary so one chart error doesn't kill the whole dashboard.
 */
class ChartErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="alert alert-danger p-3">
          <strong>Chart failed to load.</strong>
        </div>
      );
    }
    return this.props.children;
  }
}

function Dashboard({ account, loading, error }) {
  const [dashboardState, setDashboardState] = useState({
    tickers: [],
    positions: [],
    activeCharts: [],
    events: []
  });
  const [socket, setSocket] = useState(null);
  // used to dedupe exact same messages and to hand out truly unique IDs
  const seenEventSignatures = useRef(new Set());
  const eventCounter = useRef(0);

  useEffect(() => {
    setDashboardState({
      tickers: [],
      positions: [],
      activeCharts: [],
      events: []
    });
    seenEventSignatures.current.clear();
  }, []);

  useEffect(() => {
    const newSocket = io({
      path: '/socket.io',
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    const logEvent = (type, raw) => addEvent(type, raw);

    newSocket.on('connect', () => logEvent('system', 'WebSocket connected'));
    newSocket.on('disconnect', () => logEvent('system', 'WebSocket disconnected'));
    newSocket.on('error', (e) => logEvent('error', e));
    newSocket.on('market_update', (data) => {
      if (data && data.symbol && data.price != null) {
        logEvent('market', `Update for ${data.symbol}: $${data.price}`);
      } else {
        logEvent('market', 'Invalid market update payload');
      }
    });
    newSocket.on('signal_update', (data) => {
      if (data && data.symbol) {
        const price = data.price != null ? `$${data.price}` : '';
        logEvent('signal', `Signal for ${data.symbol}: ${data.type || 'unknown'} ${price}`.trim());
      } else {
        logEvent('signal', 'Invalid signal update payload');
      }
    });

    setSocket(newSocket);
    return () => newSocket.disconnect();
  }, []);

  useEffect(() => {
    fetch('/api/tickers')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          // Transform tickers into objects with stable IDs to avoid key collisions
          const tickersWithIds = Array.from(new Set(data)).map(ticker => ({
            id: generateId('ticker'),
            symbol: ticker
          }));
          setDashboardState(s => ({ ...s, tickers: tickersWithIds }));
        } else {
          addEvent('error', 'Tickers API returned bad format');
        }
      })
      .catch(() => addEvent('error', 'Failed to load tickers'));
  }, []);

  useEffect(() => {
    fetch('/api/positions')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setDashboardState(s => ({ ...s, positions: data }));
        else addEvent('error', 'Positions API returned bad format');
      })
      .catch(() => addEvent('error', 'Failed to load positions'));
  }, []);

  const addEvent = useCallback((type, rawMessage) => {
    // Convert any message to a safe string representation
    let message;
    if (rawMessage == null) {
      message = String(rawMessage);
    } else if (typeof rawMessage === 'object') {
      try {
        message = JSON.stringify(rawMessage);
      } catch {
        message = '[Object]'; // Fallback for circular references
      }
    } else {
      message = String(rawMessage);
    }

    // Build a signature to detect identical events
    const signature = `${type}:${message}`;
    if (seenEventSignatures.current.has(signature)) {
      return; // Skip duplicate events
    }
    seenEventSignatures.current.add(signature);

    // Use simple incremental IDs to ensure uniqueness
    const event = {
      id: `evt-${++eventCounter.current}`,
      timestamp: new Date().toISOString(),
      type,
      message
    };

    setDashboardState(s => ({
      ...s,
      events: [event, ...s.events].slice(0, 100) // Keep last 100 events
    }));
  }, []);

  const handleSubscribeTicker = (ticker) => {
    if (!socket) return;
    socket.emit('subscribe_ticker', { ticker });
    addEvent('user', `Subscribed to ${ticker}`);
    
    setDashboardState(s => {
      // Check if this ticker is already active
      if (s.activeCharts.some(chart => chart.symbol === ticker)) {
        return s; // Already subscribed
      }
      
      // Add as new chart with unique ID
      const newChart = {
        id: generateId('chart'),
        symbol: ticker
      };
      
      return {
        ...s,
        activeCharts: [...s.activeCharts, newChart]
      };
    });
  };

  if (loading) {
    return (
      <div className="container-fluid py-3">
        <div className="text-center my-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-3">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const errMsg = typeof error === 'string'
      ? error
      : (error.message || JSON.stringify(error));
    return (
      <div className="container-fluid py-3">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Error Loading Dashboard</h4>
          <p>{errMsg}</p>
          <hr />
          <p className="mb-0">Please try refreshing the page or contact support if the problem persists.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid py-3">
      <div className="row mb-4">
        <div className="col-12">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Trading Account</h5>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Account Value</h6>
                    <h4>${account && account.equity ? parseFloat(account.equity).toFixed(2) : '0.00'}</h4>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Buying Power</h6>
                    <h4>${account && account.buying_power ? parseFloat(account.buying_power).toFixed(2) : '0.00'}</h4>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Open Positions</h6>
                    <h4>{Array.isArray(dashboardState.positions) ? dashboardState.positions.length : 0}</h4>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Market Status</h6>
                    <h4 className={account && account.market_open ? 'text-success' : 'text-danger'}>
                      {account && account.market_open ? 'Open' : 'Closed'}
                    </h4>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-md-3 mb-4">
          <div className="card h-100">
            <div className="card-header">
              <h5 className="mb-0">Tickers</h5>
            </div>
            <div className="card-body p-0">
              <div className="list-group list-group-flush">
                {dashboardState.tickers.length > 0 ? (
                  dashboardState.tickers.map((ticker) => (
                    <button
                      key={ticker.id}
                      className={`list-group-item list-group-item-action ${dashboardState.activeCharts.some(chart => chart.symbol === ticker.symbol) ? 'active' : ''}`}
                      onClick={() => handleSubscribeTicker(ticker.symbol)}
                    >
                      {ticker.symbol}
                    </button>
                  ))
                ) : (
                  <div className="list-group-item text-center text-muted py-3">
                    No tickers available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-9 mb-4">
          <div className="row mb-4">
            {dashboardState.activeCharts.length > 0 ? (
              dashboardState.activeCharts.map((chart) => (
                <div key={chart.id} className="col-md-6 mb-3">
                  <ChartErrorBoundary>
                    <div className="card">
                      <div className="card-header d-flex justify-content-between align-items-center">
                        <h5 className="mb-0">{chart.symbol}</h5>
                        <button 
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => {
                            setDashboardState(prev => ({
                              ...prev,
                              activeCharts: prev.activeCharts.filter(t => t.id !== chart.id)
                            }));
                          }}
                        >
                          <i className="bi bi-x"></i>
                        </button>
                      </div>
                      <div className="card-body p-0">
                        <div className="chart-container" id={`chart-${ticker}`}>
                          <div className="d-flex align-items-center justify-content-center h-100">
                            <p className="text-muted mb-0">Loading chart...</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </ChartErrorBoundary>
                </div>
              ))
            ) : (
              <div className="col-12">
                <div className="alert alert-info">
                  <i className="bi bi-info-circle me-2"></i>
                  Select tickers from the sidebar to display charts
                </div>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Event Log</h5>
            </div>
            <div className="card-body p-0">
              <div className="list-group list-group-flush event-log" style={{ maxHeight: '250px', overflowY: 'auto' }}>
                {dashboardState.events.length > 0 ? (
                  dashboardState.events.map((event) => (
                    <div key={event.id} className="list-group-item py-2">
                      <small className="text-muted me-2">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </small>
                      <span className={`badge me-2 ${
                        event.type === 'error' ? 'bg-danger' :
                        event.type === 'system' ? 'bg-secondary' :
                        event.type === 'signal' ? 'bg-primary' :
                        event.type === 'market' ? 'bg-success' : 'bg-info'
                      }`}>
                        {event.type}
                      </span>
                      {event.message}
                    </div>
                  ))
                ) : (
                  <div className="list-group-item text-center text-muted py-3">
                    No events yet
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;