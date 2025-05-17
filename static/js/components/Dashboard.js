/**
 * Dashboard component
 * 
 * Main dashboard component that integrates all UI elements
 */
import React, { useEffect, useState, useRef } from 'react';
import ChartCard from './ChartCard';
import PositionsTable from './PositionsTable';
import EventLog from './EventLog';
import TickerSidebar from './TickerSidebar';
import AccountInfo from './AccountInfo';
import { subscribeTickers, on, off } from '../services/websocketService';

const Dashboard = ({ systemStatus }) => {
  const [activeTickers, setActiveTickers] = useState([]);
  const [connected, setConnected] = useState(false);
  const eventLogRef = useRef(null);
  
  // Initialize socket event handlers
  useEffect(() => {
    // Set up event handlers
    const handleConnect = () => {
      setConnected(true);
      if (eventLogRef.current) {
        eventLogRef.current.addLog('success', 'Connected to server');
      }
      
      // Subscribe to tickers if any are active
      if (activeTickers.length > 0) {
        subscribeTickers(activeTickers);
      }
    };
    
    const handleDisconnect = (reason) => {
      setConnected(false);
      if (eventLogRef.current) {
        eventLogRef.current.addLog('error', `Disconnected from server: ${reason}`);
      }
    };
    
    const handleMarketData = (data) => {
      if (eventLogRef.current && Math.random() < 0.1) { // Log only 10% of market data to avoid flooding
        try {
          const price = typeof data.price === 'number' 
            ? data.price.toFixed(2) 
            : (data.price 
                ? String(data.price) 
                : 'unknown');
                
          eventLogRef.current.addLog('info', `Market data for ${data.ticker}`, `Price: ${price}`);
        } catch (err) {
          console.error('Error in market data handler:', err);
        }
      }
    };
    
    const handleSignalUpdate = (data) => {
      if (eventLogRef.current) {
        try {
          const category = data.category ? String(data.category) : 'unknown';
          const price = typeof data.price === 'number' 
            ? data.price.toFixed(2) 
            : (data.price 
                ? String(data.price) 
                : 'unknown');
                
          eventLogRef.current.addLog(
            'trade', 
            `Signal triggered for ${data.ticker}`, 
            `${category} at ${price}`
          );
        } catch (err) {
          console.error('Error in signal update handler:', err);
        }
      }
    };
    
    // Register event handlers
    on('connect', handleConnect);
    on('disconnect', handleDisconnect);
    on('market_data', handleMarketData);
    on('signal_update', handleSignalUpdate);
    
    // Clean up on unmount
    return () => {
      off('connect', handleConnect);
      off('disconnect', handleDisconnect);
      off('market_data', handleMarketData);
      off('signal_update', handleSignalUpdate);
    };
  }, [activeTickers]);
  
  // Add a ticker to the dashboard
  const handleAddTicker = (ticker) => {
    if (!activeTickers.includes(ticker)) {
      const newTickers = [...activeTickers, ticker];
      setActiveTickers(newTickers);
      
      // Subscribe to the new ticker
      if (connected) {
        subscribeTickers([ticker]);
      }
      
      // Log ticker addition
      if (eventLogRef.current) {
        eventLogRef.current.addLog('info', `Added ${ticker} to dashboard`);
      }
    }
  };
  
  // Remove a ticker from the dashboard
  const handleRemoveTicker = (ticker) => {
    const newTickers = activeTickers.filter(t => t !== ticker);
    setActiveTickers(newTickers);
    
    // Log ticker removal
    if (eventLogRef.current) {
      eventLogRef.current.addLog('info', `Removed ${ticker} from dashboard`);
    }
  };
  
  return (
    <div className="container-fluid py-4">
      <div className="row mb-4">
        <div className="col-12">
          <AccountInfo />
        </div>
      </div>
      
      {/* System Status Section */}
      {systemStatus && (
        <div className="row mb-4">
          <div className="col-12">
            <div className="card">
              <div className="card-header">
                <h5 className="mb-0">System Status</h5>
              </div>
              <div className="card-body">
                <div className="row">
                  <div className="col-md-6">
                    <div className="d-flex align-items-center mb-2">
                      <span className={`badge ${systemStatus.strategyRunning ? 'bg-success' : 'bg-danger'} me-2`}>
                        {systemStatus.strategyRunning ? 'Running' : 'Stopped'}
                      </span>
                      <span>Strategy Detector</span>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="d-flex align-items-center mb-2">
                      <span className={`badge ${systemStatus.executionRunning ? 'bg-success' : 'bg-danger'} me-2`}>
                        {systemStatus.executionRunning ? 'Running' : 'Stopped'}
                      </span>
                      <span>Options Execution</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div className="row">
        <div className="col-md-3">
          <TickerSidebar onAddTicker={handleAddTicker} />
        </div>
        
        <div className="col-md-9">
          <div className="row mb-4">
            <div className="col-12">
              {activeTickers.length === 0 ? (
                <div className="alert alert-info">
                  <i className="bi bi-info-circle me-2"></i>
                  Select tickers from the sidebar to display charts
                </div>
              ) : (
                <div className="card-deck">
                  {activeTickers.map((ticker, index) => (
                    <ChartCard 
                      key={`chart-${ticker}-${index}`}
                      ticker={ticker} 
                      onClose={() => handleRemoveTicker(ticker)} 
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
          
          <div className="row">
            <div className="col-12">
              <PositionsTable />
            </div>
          </div>
          
          <div className="row">
            <div className="col-12">
              <EventLog ref={eventLogRef} />
            </div>
          </div>
        </div>
      </div>
      
      <div className="position-fixed bottom-0 end-0 p-3" style={{ zIndex: 5 }}>
        <div className={`badge ${connected ? 'bg-success' : 'bg-danger'} p-2`}>
          {connected ? (
            <span>
              <i className="bi bi-broadcast me-1"></i> Connected
            </span>
          ) : (
            <span>
              <i className="bi bi-broadcast me-1"></i> Disconnected
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;