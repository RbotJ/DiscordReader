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
import { initializeSocket, subscribeTickers, on, off } from '../services/websocketService';

const Dashboard = () => {
  const [activeTickers, setActiveTickers] = useState([]);
  const [connected, setConnected] = useState(false);
  const eventLogRef = useRef(null);
  
  // Initialize socket and event handlers
  useEffect(() => {
    // Initialize WebSocket connection
    const socket = initializeSocket();
    
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
        const price = data.price ? data.price.toString() : 'unknown';
        eventLogRef.current.addLog('info', `Market data for ${data.ticker}`, `Price: ${price}`);
      }
    };
    
    const handleSignalUpdate = (data) => {
      if (eventLogRef.current) {
        const price = data.price ? data.price.toString() : 'unknown';
        eventLogRef.current.addLog(
          'trade', 
          `Signal triggered for ${data.ticker}`, 
          `${data.category} at ${price}`
        );
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
                activeTickers.map(ticker => (
                  <ChartCard 
                    key={ticker} 
                    ticker={ticker} 
                    onClose={() => handleRemoveTicker(ticker)} 
                  />
                ))
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
            <>
              <i className="bi bi-broadcast me-1"></i> Connected
            </>
          ) : (
            <>
              <i className="bi bi-broadcast me-1"></i> Disconnected
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;