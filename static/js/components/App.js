import React, { useState, useEffect } from 'react';
import Dashboard from './Dashboard';

/**
 * Main App Component
 * 
 * This is the main container component that renders the entire application.
 * It handles global state and routing.
 */
function App() {
  const [appState, setAppState] = useState({
    loading: true,
    account: null,
    error: null
  });
  
  // Load initial account data on mount
  useEffect(() => {
    // Set loading state
    setAppState(prevState => ({ ...prevState, loading: true }));
    
    // Fetch account data
    fetch('/api/account')
      .then(response => {
        if (!response.ok) {
          throw new Error('Error fetching account data');
        }
        return response.json();
      })
      .then(accountData => {
        setAppState({
          loading: false,
          account: accountData,
          error: null
        });
        
        // Hide fallback UI elements if they exist
        const fallback = document.getElementById('dashboard-fallback');
        if (fallback) {
          fallback.style.display = 'none';
        }
      })
      .catch(error => {
        console.error('Failed to load account data:', error);
        setAppState({
          loading: false,
          account: null,
          error: 'Failed to load account data. Please try again.'
        });
      });
  }, []);
  
  return (
    <div className="app-container">
      <Dashboard 
        account={appState.account}
        loading={appState.loading}
        error={appState.error}
      />
    </div>
  );
}

export default App;