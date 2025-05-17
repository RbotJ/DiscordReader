/**
 * React application entry point
 * 
 * This is the main entry point for our React application
 */
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './components/App';

// Log initialization
console.log('Dashboard initialized');

// Mount the React application
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('react-root');
  
  if (container) {
    const root = createRoot(container);
    root.render(<App />);
  } else {
    console.error('Could not find root element with ID "react-root"');
  }
});