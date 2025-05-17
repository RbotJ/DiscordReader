import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';

/**
 * Dashboard Component
 * 
 * Renders the main application dashboard with real-time market data.
 */
function Dashboard({ account, loading, error }) {
  const [dashboardState, setDashboardState] = useState({
    tickers: [],
    positions: [],
    activeCharts: [],
    events: []
  });
  
  const [socket, setSocket] = useState(null);
  
  // Connect to websocket on component mount
  useEffect(() => {
    // Create socket connection
    const newSocket = io({
      path: '/socket.io',
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });
    
    // Set up event handlers
    newSocket.on('connect', () => {
      console.log('Socket connected');
      // Add to events log
      addEvent('system', 'WebSocket connected');
    });
    
    newSocket.on('disconnect', () => {
      console.log('Socket disconnected');
      // Add to events log
      addEvent('system', 'WebSocket disconnected');
    });
    
    newSocket.on('market_update', (data) => {
      // Handle market update data
      console.log('Market update received:', data);
      addEvent('market', `Received update for ${data.symbol}: $${data.price}`);
    });
    
    newSocket.on('signal_update', (data) => {
      // Handle signal updates
      console.log('Signal update received:', data);
      addEvent('signal', `Signal update for ${data.symbol}: ${data.type} at $${data.price}`);
    });
    
    // Save socket to state
    setSocket(newSocket);
    
    // Clean up on unmount
    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, []);
  
  // Fetch tickers on mount
  useEffect(() => {
    fetch('/api/tickers')
      .then(response => response.json())
      .then(data => {
        setDashboardState(prev => ({
          ...prev,
          tickers: data
        }));
      })
      .catch(error => {
        console.error('Error fetching tickers:', error);
        addEvent('error', 'Failed to load tickers');
      });
      
    // Fetch positions
    fetch('/api/positions')
      .then(response => response.json())
      .then(data => {
        setDashboardState(prev => ({
          ...prev,
          positions: data
        }));
      })
      .catch(error => {
        console.error('Error fetching positions:', error);
        addEvent('error', 'Failed to load positions');
      });
  }, []);
  
  // Helper to add events to the event log
  const addEvent = (type, message) => {
    const event = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      type,
      message
    };
    
    setDashboardState(prev => ({
      ...prev,
      events: [event, ...prev.events].slice(0, 100) // Keep last 100 events
    }));
  };
  
  // Handle subscribing to a ticker
  const handleSubscribeTicker = (ticker) => {
    if (socket) {
      socket.emit('subscribe_ticker', { ticker });
      addEvent('user', `Subscribed to ${ticker}`);
      
      // Add to active charts if not already there
      if (!dashboardState.activeCharts.includes(ticker)) {
        setDashboardState(prev => ({
          ...prev,
          activeCharts: [...prev.activeCharts, ticker]
        }));
      }
    }
  };
  
  // Render loading state
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
  
  // Render error state
  if (error) {
    return (
      <div className="container-fluid py-3">
        <div className="alert alert-danger" role="alert">
          <h4 className="alert-heading">Error Loading Dashboard</h4>
          <p>{error}</p>
          <hr />
          <p className="mb-0">Please try refreshing the page or contact support if the problem persists.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container-fluid py-3">
      {/* Account Info Row */}
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
                    <h4>${account ? parseFloat(account.equity).toFixed(2) : '0.00'}</h4>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Buying Power</h6>
                    <h4>${account ? parseFloat(account.buying_power).toFixed(2) : '0.00'}</h4>
                  </div>
                </div>
                <div className="col-md-3">
                  <div className="mb-3">
                    <h6 className="text-muted">Open Positions</h6>
                    <h4>{dashboardState.positions.length}</h4>
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
      
      {/* Main Dashboard Row */}
      <div className="row">
        {/* Sidebar */}
        <div className="col-md-3 mb-4">
          <div className="card h-100">
            <div className="card-header">
              <h5 className="mb-0">Tickers</h5>
            </div>
            <div className="card-body p-0">
              <div className="list-group list-group-flush">
                {dashboardState.tickers.length > 0 ? (
                  dashboardState.tickers.map(ticker => (
                    <button
                      key={ticker}
                      className={`list-group-item list-group-item-action ${dashboardState.activeCharts.includes(ticker) ? 'active' : ''}`}
                      onClick={() => handleSubscribeTicker(ticker)}
                    >
                      {ticker}
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
        
        {/* Main Content */}
        <div className="col-md-9 mb-4">
          {/* Charts Grid */}
          <div className="row mb-4">
            {dashboardState.activeCharts.length > 0 ? (
              dashboardState.activeCharts.map(ticker => (
                <div key={ticker} className="col-md-6 mb-4">
                  <div className="card">
                    <div className="card-header d-flex justify-content-between align-items-center">
                      <h5 className="mb-0">{ticker}</h5>
                      <button 
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => {
                          setDashboardState(prev => ({
                            ...prev,
                            activeCharts: prev.activeCharts.filter(t => t !== ticker)
                          }));
                        }}
                      >
                        <i className="bi bi-x"></i>
                      </button>
                    </div>
                    <div className="card-body">
                      <div className="chart-container" id={`chart-${ticker}`}>
                        <div className="d-flex align-items-center justify-content-center h-100">
                          <p className="text-muted mb-0">Loading chart...</p>
                        </div>
                      </div>
                    </div>
                  </div>
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
          
          {/* Event Log */}
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Event Log</h5>
            </div>
            <div className="card-body p-0">
              <div className="list-group list-group-flush event-log" style={{ maxHeight: '250px', overflowY: 'auto' }}>
                {dashboardState.events.length > 0 ? (
                  dashboardState.events.map(event => (
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