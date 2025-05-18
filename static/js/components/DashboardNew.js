import React, { useState, useEffect, useCallback, useRef } from 'react';
import io from 'socket.io-client';

/**
 * Chart Error Boundary Component - Catches errors in chart rendering
 */
class ChartErrorBoundary extends React.Component {
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

/**
 * Event Item Component - Renders individual event
 */
const EventItem = ({ event }) => {
  const getBadgeClass = (type) => {
    switch (type) {
      case 'error': return 'bg-danger';
      case 'system': return 'bg-secondary';
      case 'signal': return 'bg-primary';
      case 'market': return 'bg-success';
      default: return 'bg-info';
    }
  };

  return (
    <div className="list-group-item py-2">
      <small className="text-muted me-2">
        {new Date(event.timestamp).toLocaleTimeString()}
      </small>
      <span className={`badge me-2 ${getBadgeClass(event.type)}`}>
        {event.type}
      </span>
      {typeof event.message === 'string' 
        ? event.message 
        : JSON.stringify(event.message)}
    </div>
  );
};

/**
 * Chart Component - Renders an individual chart
 */
const Chart = ({ chart, onRemove }) => {
  return (
    <div className="col-md-6 mb-3">
      <ChartErrorBoundary>
        <div className="card">
          <div className="card-header d-flex justify-content-between align-items-center">
            <h5 className="mb-0">{chart.symbol}</h5>
            <button 
              className="btn btn-sm btn-outline-secondary"
              onClick={() => onRemove(chart.id)}
            >
              <i className="bi bi-x"></i>
            </button>
          </div>
          <div className="card-body p-0">
            <div className="chart-container" id={`chart-${chart.id}`}>
              <div className="d-flex align-items-center justify-content-center h-100">
                <p className="text-muted mb-0">Loading chart...</p>
              </div>
            </div>
          </div>
        </div>
      </ChartErrorBoundary>
    </div>
  );
};

/**
 * Ticker Item Component - Renders individual ticker
 */
const TickerItem = ({ ticker, isSelected, onSelect }) => {
  return (
    <div 
      className={`ticker-item ${isSelected ? 'active' : ''}`}
      onClick={() => onSelect(ticker)}
    >
      <div className="d-flex justify-content-between align-items-center">
        <span className="ticker-symbol">{ticker.symbol}</span>
        <span className={`badge ${ticker.change >= 0 ? 'bg-success' : 'bg-danger'}`}>
          {ticker.change >= 0 ? '+' : ''}{ticker.change.toFixed(2)}%
        </span>
      </div>
      <div className="ticker-price mt-1">
        ${ticker.price.toFixed(2)}
      </div>
    </div>
  );
};

/**
 * Dashboard Component - Main trading interface
 */
function Dashboard({ account, loading, error }) {
  // State hooks
  const [tickers, setTickers] = useState([]);
  const [activeCharts, setActiveCharts] = useState([]);
  const [events, setEvents] = useState([]);
  const [socket, setSocket] = useState(null);
  const [lastEventId, setLastEventId] = useState(0);
  
  // Refs
  const chartsRef = useRef({});
  
  // Connect to WebSocket on component mount
  useEffect(() => {
    const newSocket = io(window.location.origin);
    setSocket(newSocket);
    
    // Log connection
    console.log('Dashboard initialized');
    
    // Add test event
    const initEvent = {
      id: `init-${Date.now()}`, // Ensure unique ID
      type: 'system',
      timestamp: new Date(),
      message: 'Dashboard initialized'
    };
    setEvents([initEvent]);
    
    // Cleanup on unmount
    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, []);
  
  // Setup socket event listeners
  useEffect(() => {
    if (!socket) return;
    
    // Handle ticker updates
    socket.on('ticker_update', (data) => {
      console.log('Ticker update received:', data);
      // Process ticker data from the server with guaranteed unique IDs
      if (Array.isArray(data)) {
        const processedTickers = data.map(ticker => ({
          ...ticker,
          id: `ticker-${ticker.symbol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        }));
        setTickers(processedTickers);
      }
    });
    
    // Handle trading events
    socket.on('event', (data) => {
      console.log('Event received:', data);
      // Always use a guaranteed unique ID
      const newEvent = {
        ...data,
        id: `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      };
      
      setEvents(prev => [newEvent, ...prev].slice(0, 50));
    });
    
    return () => {
      socket.off('ticker_update');
      socket.off('event');
    };
  }, [socket]);
  
  // Handle ticker selection
  const handleTickerSelect = useCallback((ticker) => {
    // Check if already in activeCharts
    const exists = activeCharts.some(chart => chart.symbol === ticker.symbol);
    
    if (!exists) {
      const newChart = {
        ...ticker,
        id: `chart-${ticker.symbol}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      };
      
      setActiveCharts(prev => [...prev, newChart]);
      
      // Subscribe to ticker data
      if (socket) {
        socket.emit('subscribe_ticker', { symbol: ticker.symbol });
      }
    }
  }, [activeCharts, socket]);
  
  // Handle chart removal
  const handleChartRemove = useCallback((chartId) => {
    setActiveCharts(prev => prev.filter(chart => chart.id !== chartId));
  }, []);

  if (loading) {
    return <div className="loading-spinner">Loading...</div>;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <div className="dashboard container-fluid">
      <div className="row mt-4">
        <div className="col-md-3 mb-4">
          <div className="card mb-4">
            <div className="card-header">
              <h5 className="mb-0">Account</h5>
            </div>
            <div className="card-body">
              <div className="d-flex justify-content-between mb-2">
                <span>Balance:</span>
                <span className="fw-bold">${account?.balance?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>Buying Power:</span>
                <span>${account?.buying_power?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span>Open Positions:</span>
                <span>{account?.positions_count || 0}</span>
              </div>
            </div>
          </div>

          <div className="card mb-4">
            <div className="card-header">
              <h5 className="mb-0">Tickers</h5>
            </div>
            <div className="card-body p-0">
              <div className="tickers-list" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {tickers.length > 0 ? (
                  tickers.map(ticker => (
                    <TickerItem
                      key={ticker.id}
                      ticker={ticker}
                      isSelected={activeCharts.some(c => c.symbol === ticker.symbol)}
                      onSelect={handleTickerSelect}
                    />
                  ))
                ) : (
                  <div className="p-3 text-center text-muted">
                    No tickers available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-9 mb-4">
          <div className="row mb-4">
            {activeCharts.length > 0 ? (
              activeCharts.map(chart => (
                <Chart
                  key={chart.id}
                  chart={chart}
                  onRemove={handleChartRemove}
                />
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
            <div className="card-header d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Events</h5>
              <span className="badge bg-secondary">{events.length}</span>
            </div>
            <div className="card-body p-0">
              <div className="list-group list-group-flush event-log" style={{ maxHeight: '250px', overflowY: 'auto' }}>
                {events.length > 0 ? (
                  events.map(event => (
                    <EventItem key={event.id} event={event} />
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