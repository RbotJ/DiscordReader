import React, { useState, useEffect, useCallback, useRef, Component } from 'react';
import io from 'socket.io-client';

/**
 * Dashboard component - Trading application main interface
 * 
 * This component displays real-time trading information including:
 * - Account information and balances
 * - Available tickers for trading
 * - Active charts for selected symbols
 * - Real-time event notifications
 * 
 * Key features:
 * - WebSocket connections for real-time data
 * - Unique ID generation for React elements 
 * - Error boundaries to prevent component crashes
 */

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
  
  // Used to dedupe exact same messages
  const seenEventSignatures = useRef(new Set());
  
  // Global counter for each ID namespace to guarantee uniqueness
  // These will be used to ensure truly unique IDs
  const counters = useRef({
    ticker: 0,
    chart: 0,
    event: 0
  });
  
  /**
   * Guaranteed unique ID generation that uses a combination of:
   * - prefix: namespace for the ID
   * - timestamp: makes IDs unique across time
   * - random: makes IDs unique even when created at the exact same millisecond
   * - counter: absolute guarantee of uniqueness by adding a monotonically increasing number
   */
  // Reference removed - using counters only now
  
  // Generate guaranteed unique IDs across renders
  const generateStableId = useCallback((prefix) => {
    // Initialize counter for this namespace if needed
    if (!counters.current[prefix]) {
      counters.current[prefix] = 0;
    }
    
    // Increment the namespace-specific counter
    counters.current[prefix]++;
    
    // Use a UUID-like approach to ensure uniqueness
    // Counter is enough to guarantee uniqueness even if two are created in the same millisecond
    const staticPart = `${prefix}-${counters.current[prefix]}`;
    
    // Add additional randomness to make collisions astronomically unlikely
    const randomPart = Math.random().toString(36).substring(2, 10);
    
    return `${staticPart}-${randomPart}`;
  }, []);

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
  }, [addEvent]);

  useEffect(() => {
    fetch('/api/tickers')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
            // Make sure tickers are unique first
            const uniqueTickers = Array.from(new Set(data));
            
            // Add stable IDs to each ticker - with index as additional uniqueness guarantee
            const tickersWithIds = uniqueTickers.map((ticker, index) => ({
              id: `ticker-${index}-${generateStableId('ticker')}`, // Extra uniqueness with index and stable ID
              symbol: ticker
            }));
            
            setDashboardState(s => ({ ...s, tickers: tickersWithIds }));
        } else {
          addEvent('error', 'Tickers API returned bad format');
        }
      })
      .catch(() => addEvent('error', 'Failed to load tickers'));
  }, [addEvent, generateStableId]);

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
    // Generate a unique counter-based ID first to guarantee uniqueness
    const uniqueCounter = counters.current.event = (counters.current.event || 0) + 1;
    
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

    // Create a truly guaranteed unique ID that doesn't depend on timestamp 
    // This prevents collisions when multiple events are created in the same millisecond
    const uniqueId = `event-${uniqueCounter}-${Math.random().toString(36).substring(2, 10)}`;
    
    // Generate a new event with the guaranteed unique ID
    const event = {
      id: uniqueId,
      timestamp: new Date().toISOString(),
      type,
      // Make doubly sure message is always a string
      message: typeof message === 'string' ? message : String(message)
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

      // Create a genuinely unique ID for the chart with multiple sources of uniqueness
      const chartId = `chart-${ticker}-${s.activeCharts.length}-${generateStableId('chart')}`;
      
      // Add as new chart with guaranteed unique ID 
      const newChart = {
        id: chartId,
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
                  dashboardState.tickers.map((ticker, i) => {
                    const key = ticker.id;
                    console.log('Ticker render:', ticker.symbol, '→ key=', key);
                    return (
                      <button
                        key={key}
                        className={`list-group-item list-group-item-action ${dashboardState.activeCharts.some(chart => chart.symbol === ticker.symbol) ? 'active' : ''}`}
                        onClick={() => handleSubscribeTicker(ticker.symbol)}
                      >
                        {ticker.symbol}
                      </button>
                    );
                  })
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
              dashboardState.activeCharts.map((chart, i) => {
                const key = chart.id;
                console.log('Chart render:', chart.symbol, '→ key=', key);
                return (
                  <div key={key} className="col-md-6 mb-3">
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
                        <div className="chart-container" id={`container-${chart.id}`}>
                          <div className="d-flex align-items-center justify-content-center h-100">
                            <p className="text-muted mb-0">Loading chart...</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </ChartErrorBoundary>
                </div>
              );
            }) 
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
                  dashboardState.events.map((event, i) => {
                    const key = event.id;
                    console.log('Event render:', event.type, event.message, '→ key=', key);
                    return (
                      <div key={key} className="list-group-item py-2">
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
                        {typeof event.message === 'string' 
                          ? event.message 
                          : JSON.stringify(event.message)}
                      </div>
                    );
                  })
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