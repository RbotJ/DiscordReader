import React, { useState, useEffect } from 'react';
import ChartCard from './ChartCard';
import PositionsTable from './PositionsTable';
import EventLog from './EventLog';
import TickerSidebar from './TickerSidebar';
import apiService from '../services/apiService';
import websocketService from '../services/websocketService';

/**
 * Dashboard component
 * Main dashboard component that integrates all UI elements
 */
const Dashboard = () => {
  const [tickers, setTickers] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [signal, setSignal] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Initialize data and WebSocket connection on component mount
  useEffect(() => {
    const initializeData = async () => {
      try {
        setLoading(true);
        
        // Load available tickers
        const tickersData = await apiService.getTickers();
        setTickers(tickersData || []);
        
        // If we have tickers, select the first one
        if (tickersData && tickersData.length > 0) {
          setSelectedTicker(tickersData[0]);
          
          // Load signal for the selected ticker
          const signalData = await apiService.getSignals(tickersData[0]);
          setSignal(signalData);
        }
        
        // Initialize WebSocket connection
        await websocketService.connect();
        
        // Add event handlers for WebSocket events
        websocketService.on('connect', () => {
          addEvent({
            type: 'info',
            message: 'Connected to server',
            timestamp: new Date().toISOString(),
          });
        });
        
        websocketService.on('disconnect', () => {
          addEvent({
            type: 'warning',
            message: 'Disconnected from server',
            timestamp: new Date().toISOString(),
          });
        });
        
        websocketService.on('error', (data) => {
          addEvent({
            type: 'error',
            message: `WebSocket error: ${data.message}`,
            timestamp: new Date().toISOString(),
          });
        });
        
        websocketService.on('price_update', (data) => {
          addEvent({
            type: 'info',
            message: `Price update: ${data.ticker} ${data.price}`,
            timestamp: new Date().toISOString(),
          });
        });
        
        websocketService.on('signal_triggered', (data) => {
          addEvent({
            type: 'signal',
            message: `Signal triggered: ${data.ticker} ${data.category}`,
            data: data,
            timestamp: new Date().toISOString(),
          });
        });
        
        websocketService.on('trade_executed', (data) => {
          addEvent({
            type: 'trade',
            message: `Trade executed: ${data.ticker} ${data.side} ${data.qty} @ ${data.price}`,
            data: data,
            timestamp: new Date().toISOString(),
          });
        });
        
        setError(null);
      } catch (err) {
        console.error('Error initializing dashboard:', err);
        setError('Failed to initialize dashboard data');
        
        addEvent({
          type: 'error',
          message: 'Failed to initialize dashboard data',
          data: err.message,
          timestamp: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    };
    
    initializeData();
    
    // Clean up WebSocket connection on unmount
    return () => {
      websocketService.disconnect();
    };
  }, []);
  
  // Subscribe to ticker updates when selected ticker changes
  useEffect(() => {
    if (!selectedTicker) return;
    
    const loadSignalForTicker = async () => {
      try {
        const signalData = await apiService.getSignals(selectedTicker);
        setSignal(signalData);
        
        addEvent({
          type: 'info',
          message: `Loaded signal data for ${selectedTicker}`,
          timestamp: new Date().toISOString(),
        });
      } catch (err) {
        console.error(`Error loading signal for ${selectedTicker}:`, err);
        
        addEvent({
          type: 'error',
          message: `Failed to load signal for ${selectedTicker}`,
          data: err.message,
          timestamp: new Date().toISOString(),
        });
      }
    };
    
    // Subscribe to the selected ticker updates
    if (websocketService.connected) {
      websocketService.subscribeTickers([selectedTicker]);
      
      addEvent({
        type: 'info',
        message: `Subscribed to ${selectedTicker} updates`,
        timestamp: new Date().toISOString(),
      });
    }
    
    loadSignalForTicker();
    
    // Clean up subscription when selected ticker changes
    return () => {
      if (websocketService.connected) {
        websocketService.unsubscribeTickers([selectedTicker]);
      }
    };
  }, [selectedTicker]);
  
  // Add event to the event log
  const addEvent = (event) => {
    setEvents(prevEvents => [...prevEvents, event]);
  };
  
  // Handle ticker selection
  const handleTickerSelect = (ticker) => {
    setSelectedTicker(ticker);
  };
  
  return (
    <div className="container-fluid mt-4">
      <div className="row">
        <div className="col-md-3">
          <TickerSidebar 
            tickers={tickers}
            selectedTicker={selectedTicker}
            onTickerSelect={handleTickerSelect}
          />
        </div>
        <div className="col-md-9">
          <div className="row mb-4">
            <div className="col-12">
              {loading ? (
                <div className="card">
                  <div className="card-body d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <span className="ms-3">Loading dashboard data...</span>
                  </div>
                </div>
              ) : error ? (
                <div className="alert alert-danger">
                  {error}
                </div>
              ) : selectedTicker ? (
                <ChartCard 
                  ticker={selectedTicker}
                  signal={signal}
                  onEvent={addEvent}
                />
              ) : (
                <div className="alert alert-info">
                  No ticker selected. Please select a ticker from the sidebar.
                </div>
              )}
            </div>
          </div>
          <div className="row">
            <div className="col-12">
              <PositionsTable />
            </div>
          </div>
          <div className="row mt-4">
            <div className="col-12">
              <EventLog 
                events={events}
                maxEvents={100}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;