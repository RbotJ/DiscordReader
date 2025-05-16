import React, { useEffect, useState } from 'react';
import websocketService from '../services/websocketService';
import { fetchSignals } from '../services/apiService';
import ChartCard from './ChartCard';
import PositionsTable from './PositionsTable';
import EventLog from './EventLog';
import TickerSidebar from './TickerSidebar';

const Dashboard = () => {
  const [activeCharts, setActiveCharts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [selectedTickers, setSelectedTickers] = useState([]);
  
  // Initialize WebSocket connection
  useEffect(() => {
    // Connect to WebSocket
    websocketService.connect();
    
    // Set up connection status listeners
    const connectHandler = () => {
      setConnected(true);
      websocketService.loadTickers();
    };
    
    const disconnectHandler = () => {
      setConnected(false);
    };
    
    // Subscribe to connection events
    const unsubscribeConnect = websocketService.subscribe('connect', connectHandler);
    const unsubscribeDisconnect = websocketService.subscribe('disconnect', disconnectHandler);
    
    // Clean up on unmount
    return () => {
      unsubscribeConnect();
      unsubscribeDisconnect();
      websocketService.disconnect();
    };
  }, []);
  
  // Handle ticker selection from sidebar
  const handleTickerSelect = async (ticker) => {
    // Check if ticker is already selected
    if (selectedTickers.includes(ticker.symbol)) {
      // Remove ticker
      setSelectedTickers(prev => prev.filter(symbol => symbol !== ticker.symbol));
      setActiveCharts(prev => prev.filter(chart => chart.symbol !== ticker.symbol));
      return;
    }
    
    // Add ticker
    setSelectedTickers(prev => [...prev, ticker.symbol]);
    
    // Fetch signals for this ticker
    try {
      const signals = await fetchSignals(ticker.symbol);
      
      // Create chart data
      const chartData = {
        symbol: ticker.symbol,
        signals: signals,
      };
      
      setActiveCharts(prev => [...prev, chartData]);
    } catch (error) {
      console.error(`Error fetching signals for ${ticker.symbol}:`, error);
      // Add ticker without signals
      setActiveCharts(prev => [...prev, { symbol: ticker.symbol, signals: [] }]);
    }
  };
  
  // Handle removing a chart
  const handleRemoveChart = (symbol) => {
    setActiveCharts(prev => prev.filter(chart => chart.symbol !== symbol));
    setSelectedTickers(prev => prev.filter(ticker => ticker !== symbol));
  };
  
  // Handle signal fired event
  const handleSignalFired = (event) => {
    console.log('Signal fired:', event);
  };
  
  // Handle order update event
  const handleOrderUpdate = (event) => {
    console.log('Order update:', event);
  };
  
  return (
    <div className="container-fluid">
      <div className="row mt-3">
        <div className="col-md-3">
          <div className="mb-3">
            <div className={`alert ${connected ? 'alert-success' : 'alert-danger'}`}>
              WebSocket: {connected ? 'Connected' : 'Disconnected'}
              {!connected && (
                <button 
                  className="btn btn-sm btn-outline-light float-end"
                  onClick={() => websocketService.connect()}
                >
                  Reconnect
                </button>
              )}
            </div>
          </div>
          
          <TickerSidebar 
            onTickerSelect={handleTickerSelect}
            selectedTickers={selectedTickers}
          />
        </div>
        
        <div className="col-md-9">
          <div className="row row-cols-1 row-cols-md-2 g-4 mb-4">
            {activeCharts.map(chart => (
              <div className="col" key={chart.symbol}>
                <ChartCard
                  symbol={chart.symbol}
                  signal={chart.signals && chart.signals.length > 0 ? chart.signals[0] : null}
                  onRemove={handleRemoveChart}
                  onSignalFired={handleSignalFired}
                  onOrderUpdate={handleOrderUpdate}
                />
              </div>
            ))}
          </div>
          
          <div className="row">
            <div className="col-md-6 mb-4">
              <PositionsTable websocketService={websocketService} />
            </div>
            <div className="col-md-6 mb-4">
              <EventLog websocketService={websocketService} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;