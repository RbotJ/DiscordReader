import React, { useState, useEffect } from 'react';
import apiService from '../services/apiService';

/**
 * TickerSidebar component
 * Sidebar for selecting tickers to display in the dashboard
 * 
 * @param {Object} props Component props
 * @param {Array} props.tickers Array of ticker symbols
 * @param {string} props.selectedTicker Currently selected ticker
 * @param {function} props.onTickerSelect Function to call when a ticker is selected
 */
const TickerSidebar = ({ tickers = [], selectedTicker, onTickerSelect }) => {
  const [availableTickers, setAvailableTickers] = useState(tickers);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Load tickers on component mount if none are provided
  useEffect(() => {
    if (tickers && tickers.length > 0) {
      setAvailableTickers(tickers);
      setLoading(false);
      return;
    }
    
    const loadTickers = async () => {
      try {
        setLoading(true);
        const data = await apiService.getTickers();
        setAvailableTickers(data || []);
        setError(null);
      } catch (err) {
        console.error('Error loading tickers:', err);
        setError('Failed to load tickers');
      } finally {
        setLoading(false);
      }
    };
    
    loadTickers();
  }, [tickers]);
  
  // Filter tickers based on search query
  const filteredTickers = searchQuery.trim() !== '' 
    ? availableTickers.filter(ticker => 
        ticker.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : availableTickers;
  
  return (
    <div className="card mb-4">
      <div className="card-header">
        <h5 className="mb-0">Trading Setups</h5>
      </div>
      <div className="card-body p-0">
        <div className="p-3">
          <input
            type="text"
            className="form-control form-control-sm"
            placeholder="Search tickers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        {loading ? (
          <div className="text-center p-3">
            <div className="spinner-border spinner-border-sm text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <span className="ms-2">Loading tickers...</span>
          </div>
        ) : error ? (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        ) : filteredTickers.length === 0 ? (
          <div className="text-center p-3 text-muted">
            {searchQuery ? 'No matching tickers found' : 'No tickers available'}
          </div>
        ) : (
          <div className="list-group list-group-flush">
            {filteredTickers.map((ticker) => (
              <button
                key={ticker}
                className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${
                  ticker === selectedTicker ? 'active' : ''
                }`}
                onClick={() => onTickerSelect(ticker)}
              >
                <span>{ticker}</span>
                {ticker === selectedTicker && (
                  <i className="bi bi-check2"></i>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TickerSidebar;