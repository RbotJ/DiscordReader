/**
 * PositionsTable component
 * 
 * Displays a table of current positions with key metrics
 */
import React, { useEffect, useState } from 'react';
import { fetchPositions } from '../services/apiService';

const PositionsTable = () => {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load positions on component mount
  useEffect(() => {
    loadPositions();
    
    // Refresh positions every 30 seconds
    const refreshInterval = setInterval(loadPositions, 30000);
    
    return () => clearInterval(refreshInterval);
  }, []);
  
  // Load positions from the API
  const loadPositions = async () => {
    try {
      setLoading(true);
      const data = await fetchPositions();
      setPositions(data || []);
      setError(null);
    } catch (err) {
      console.error('Error loading positions:', err);
      setError('Failed to load positions');
    } finally {
      setLoading(false);
    }
  };
  
  // Format currency values
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2 
    }).format(value);
  };
  
  // Format percentage values
  const formatPercentage = (value) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'percent', 
      minimumFractionDigits: 2,
      maximumFractionDigits: 2 
    }).format(value / 100);
  };
  
  // Get CSS class for P/L values
  const getPLClass = (value) => {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return '';
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Positions</h5>
        <button 
          className="btn btn-sm btn-outline-secondary" 
          onClick={loadPositions}
          disabled={loading}
        >
          {loading ? (
            <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
          ) : (
            <i className="bi bi-arrow-clockwise me-1"></i>
          )}
          Refresh
        </button>
      </div>
      <div className="card-body p-0">
        {error ? (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover table-borderless mb-0">
              <thead className="thead-dark">
                <tr>
                  <th>Symbol</th>
                  <th>Quantity</th>
                  <th>Market Value</th>
                  <th>Average Price</th>
                  <th>Current Price</th>
                  <th>Unrealized P/L</th>
                  <th>P/L %</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="7" className="text-center py-3">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                    </td>
                  </tr>
                ) : positions.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center py-3 text-muted">
                      No open positions
                    </td>
                  </tr>
                ) : (
                  positions.map(position => (
                    <tr key={position.symbol}>
                      <td className="fw-bold">{position.symbol}</td>
                      <td>{position.qty}</td>
                      <td>{formatCurrency(position.market_value)}</td>
                      <td>{formatCurrency(position.avg_entry_price)}</td>
                      <td>{formatCurrency(position.current_price)}</td>
                      <td className={getPLClass(position.unrealized_pl)}>
                        {formatCurrency(position.unrealized_pl)}
                      </td>
                      <td className={getPLClass(position.unrealized_plpc)}>
                        {formatPercentage(position.unrealized_plpc)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PositionsTable;