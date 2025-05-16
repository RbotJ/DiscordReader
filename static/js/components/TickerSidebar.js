import React, { useState, useEffect } from 'react';
import { fetchActiveTickers } from '../services/apiService';

const TickerSidebar = ({ onTickerSelect, selectedTickers }) => {
  const [tickers, setTickers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Load active tickers on component mount
    loadTickers();
  }, []);
  
  const loadTickers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchActiveTickers();
      setTickers(data);
    } catch (err) {
      console.error('Error loading active tickers:', err);
      setError('Failed to load active tickers');
    } finally {
      setLoading(false);
    }
  };
  
  const isSelected = (ticker) => {
    return selectedTickers.includes(ticker.symbol);
  };
  
  const handleTickerClick = (ticker) => {
    onTickerSelect(ticker);
  };
  
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Today's Tickers</h5>
        </div>
        <div className="card-body">
          <div className="text-center">Loading tickers...</div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Today's Tickers</h5>
        </div>
        <div className="card-body">
          <div className="alert alert-danger">{error}</div>
          <button 
            className="btn btn-sm btn-outline-primary"
            onClick={loadTickers}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  
  if (tickers.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Today's Tickers</h5>
        </div>
        <div className="card-body">
          <div className="text-center text-muted">No active tickers for today</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Today's Tickers</h5>
        <span className="badge bg-primary">{tickers.length}</span>
      </div>
      <div className="card-body p-0">
        <div className="list-group list-group-flush">
          {tickers.map(ticker => (
            <button
              key={ticker.symbol}
              className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center ${
                isSelected(ticker) ? 'active' : ''
              }`}
              onClick={() => handleTickerClick(ticker)}
            >
              <div>
                <strong>{ticker.symbol}</strong>
                {ticker.signals && ticker.signals.length > 0 && (
                  <span className="badge bg-warning ms-2">
                    {ticker.signals.length} {ticker.signals.length === 1 ? 'signal' : 'signals'}
                  </span>
                )}
              </div>
              <div>
                {isSelected(ticker) ? (
                  <i className="bi bi-check-circle-fill text-success"></i>
                ) : (
                  <i className="bi bi-plus-circle"></i>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TickerSidebar;