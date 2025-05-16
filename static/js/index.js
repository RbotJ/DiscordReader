/**
 * Main entry point for the React application
 */
import React from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from './components/Dashboard';

// Bootstrap CSS
document.addEventListener('DOMContentLoaded', () => {
  // Find the dashboard container element
  const container = document.getElementById('dashboard-root');
  
  if (container) {
    // Create React root
    const root = createRoot(container);
    
    // Render the dashboard
    root.render(
      <React.StrictMode>
        <Dashboard />
      </React.StrictMode>
    );
    
    console.log('Dashboard initialized');
  } else {
    console.error('Dashboard container not found');
  }
});