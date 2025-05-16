import React from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from './components/Dashboard';

// Render the application
const container = document.getElementById('app');
if (container) {
  const root = createRoot(container);
  root.render(
    <React.StrictMode>
      <Dashboard />
    </React.StrictMode>
  );
}

// Add event listener for errors
window.addEventListener('error', (event) => {
  console.error('Global error caught:', event.error);
});