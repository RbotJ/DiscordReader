/**
 * TickerSidebar component
 * 
 * Displays a sidebar with available tickers and allows the user to add them to the dashboard
 */
import React, { useEffect, useState } from 'react';
import { fetchTickers } from '../services/apiService';

const TickerSidebar = ({ onAddTicker }) => {
  const [tickers, setTickers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  
  // Load tickers on component mount
  useEffect(() => {
    loadTickers();
  }, []);
  
  // Load tickers from the API
  const loadTickers = async () => {
    try {
      setLoading(true);
      const data = await fetchTickers();
      setTickers(data || []);
      setError(null);
    } catch (err) {
      console.error('Error loading tickers:', err);
      setError('Failed to load tickers');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle search input change
  const handleSearchChange = (e) => {
    setSearch(e.target.value);
  };
  
  // Filter tickers based on search query
  const filteredTickers = tickers.filter(ticker => 
    ticker.includes(search.toUpperCase())
  );
  
  // Handle ticker click
  const handleTickerClick = (ticker) => {
    if (onAddTicker) {
      onAddTicker(ticker);
    }
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header">
        <h5 className="mb-0">Tickers</h5>
      </div>
      <div className="card-body">
        <div className="input-group mb-3">
          <input
            type="text"
            className="form-control"
            placeholder="Search tickers..."
            value={search}
            onChange={handleSearchChange}
          />
          <button
            className="btn btn-outline-secondary"
            type="button"
            onClick={loadTickers}
            disabled={loading}
          >
            {loading ? (
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            ) : (
              <i className="bi bi-arrow-clockwise"></i>
            )}
          </button>
        </div>
        
        {error && (
          <div className="alert alert-danger">
            {error}
          </div>
        )}
        
        <div className="list-group" style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {loading ? (
            <div className="d-flex justify-content-center p-3">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : filteredTickers.length === 0 ? (
            <div className="text-center p-3 text-muted">
              {search ? 'No matching tickers found' : 'No tickers available'}
            </div>
          ) : (
            filteredTickers.map(ticker => (
              <button
                key={ticker}
                className="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                onClick={() => handleTickerClick(ticker)}
              >
                {ticker}
                <i className="bi bi-plus-circle text-primary"></i>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default TickerSidebar;