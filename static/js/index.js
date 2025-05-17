
import './debug-duplicate-keys';

/**
 * React application entry point
 * 
 * This is the main entry point for our React application
 */
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './components/App';
import reportWebVitals from './reportWebVitals';

// Log initialization
console.log('Dashboard initialized');

// Immediately clean up any orphaned Bootstrap modal backdrops
(function clearOrphanedModals() {
  const backdrops = document.querySelectorAll('.modal-backdrop');
  backdrops.forEach(el => el.remove());
  document.body.classList.remove('modal-open');
})();

// Ensure our React root container exists
const ROOT_ID = 'react-root';
let rootContainer = document.getElementById(ROOT_ID);

if (!rootContainer) {
  console.log('React root container not found, creating one');
  rootContainer = document.createElement('div');
  rootContainer.id = ROOT_ID;
  
  // Prefer mounting inside a <main> or fallback to body
  const mainSection = document.querySelector('main') || document.body;
  mainSection.appendChild(rootContainer);
} else {
  console.log('Found existing React root container');
  
  // Clear any fallback content
  const fallback = document.getElementById('dashboard-fallback');
  if (fallback) {
    console.log('Removing fallback dashboard content');
    fallback.style.display = 'none';
  }
}

// Set a flag to indicate React loaded successfully
window.reactLoaded = true;

// Mount the React application under StrictMode for better development experience
try {
  const root = createRoot(rootContainer);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
  console.log('React application mounted successfully');
} catch (error) {
  console.error('Error mounting React application:', error);
  // Keep fallback content visible on error
  const fallback = document.getElementById('dashboard-fallback');
  if (fallback) {
    fallback.style.display = 'block';
  }
}

// Optional: measure performance metrics
reportWebVitals();
