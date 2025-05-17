/**
 * App component
 * 
 * Main React application container component
 */
import React, { useState, useEffect } from 'react';
import Dashboard from './Dashboard';
import { initializeSocket } from '../services/websocketService';

const App = () => {
  const [systemStatus, setSystemStatus] = useState({
    strategyRunning: false,
    executionRunning: false,
    loading: true,
    error: null
  });

  // On component mount
  useEffect(() => {
    // Initialize socket connection
    initializeSocket();
    
    // Fetch system status
    fetchSystemStatus();
    
    // Set up interval to refresh system status
    const statusInterval = setInterval(fetchSystemStatus, 60000); // Every minute
    
    // Clean up on unmount
    return () => {
      clearInterval(statusInterval);
    };
  }, []);
  
  // Fetch system status from API
  const fetchSystemStatus = async () => {
    try {
      // Fetch strategy status
      const strategyResponse = await fetch('/api/strategy/status');
      const strategyData = await strategyResponse.json();
      
      // Fetch execution status
      const executionResponse = await fetch('/api/execution/status');
      const executionData = await executionResponse.json();
      
      setSystemStatus({
        strategyRunning: strategyData.detector?.running || false,
        executionRunning: executionData.executor?.running || false,
        loading: false,
        error: null
      });
    } catch (error) {
      console.error('Error fetching system status:', error);
      setSystemStatus(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to load system status'
      }));
    }
  };
  
  return (
    <div className="app-container">
      {/* Pass system status to Dashboard */}
      <Dashboard systemStatus={systemStatus} />
    </div>
  );
};

export default App;