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

// Clear any orphaned modal backdrops
function clearOrphanedModals() {
  // Remove any leftover backdrops
  document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
  // Restore body scrolling if it was disabled
  document.body.classList.remove('modal-open');
}

// Mount the React application
document.addEventListener('DOMContentLoaded', () => {
  // Clean up any modal issues first
  clearOrphanedModals();
  
  // Try various possible container IDs
  const containerSelectors = ['#react-root', '#dashboard-root', '#app-container', '#root'];
  let container = null;
  
  for (const selector of containerSelectors) {
    container = document.querySelector(selector);
    if (container) {
      console.log(`Found React container with selector: ${selector}`);
      break;
    }
  }
  
  // If no container found, create one
  if (!container) {
    console.log('Creating React root container');
    container = document.createElement('div');
    container.id = 'react-root';
    
    // Get main content area or append to body as fallback
    const mainContent = document.querySelector('.container-fluid') || document.body;
    mainContent.appendChild(container);
  }
  
  // Mount React app to the container
  try {
    const root = createRoot(container);
    root.render(<App />);
    console.log('React application mounted successfully');
  } catch (error) {
    console.error('Error mounting React application:', error);
  }
});