import React, { useEffect, useState } from 'react';
import apiService from '../services/apiService';

/**
 * PositionsTable component
 * Displays current positions in a table format
 */
const PositionsTable = () => {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load positions on component mount
  useEffect(() => {
    loadPositions();
    
    // Set up a refresh interval (every 60 seconds)
    const intervalId = setInterval(loadPositions, 60000);
    
    return () => clearInterval(intervalId);
  }, []);
  
  // Load positions from API
  const loadPositions = async () => {
    try {
      setLoading(true);
      const data = await apiService.getPositions();
      setPositions(data);
      setError(null);
    } catch (err) {
      console.error('Error loading positions:', err);
      setError('Failed to load positions data');
    } finally {
      setLoading(false);
    }
  };
  
  // Handle close position action
  const handleClosePosition = async (positionId) => {
    if (window.confirm('Are you sure you want to close this position?')) {
      try {
        // In a real app, this would call an API to close the position
        console.log('Closing position:', positionId);
        await loadPositions();
      } catch (err) {
        console.error('Error closing position:', err);
      }
    }
  };
  
  // Format profit/loss as a string with color class
  const formatPL = (pl) => {
    const isPositive = pl >= 0;
    const formattedValue = isPositive ? `+$${pl.toFixed(2)}` : `-$${Math.abs(pl).toFixed(2)}`;
    const colorClass = isPositive ? 'text-success' : 'text-danger';
    
    return { value: formattedValue, class: colorClass };
  };
  
  // Format profit/loss percentage as a string with color class
  const formatPLPercent = (plPercent) => {
    const isPositive = plPercent >= 0;
    const formattedValue = isPositive ? `+${plPercent.toFixed(2)}%` : `-${Math.abs(plPercent).toFixed(2)}%`;
    const colorClass = isPositive ? 'text-success' : 'text-danger';
    
    return { value: formattedValue, class: colorClass };
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Current Positions</h5>
        <button 
          className="btn btn-sm btn-outline-secondary" 
          onClick={loadPositions}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              Loading...
            </>
          ) : (
            <>
              <i className="bi bi-arrow-repeat me-1"></i>
              Refresh
            </>
          )}
        </button>
      </div>
      <div className="card-body">
        {error && (
          <div className="alert alert-danger">
            {error}
          </div>
        )}
        
        <div className="table-responsive">
          <table className="table table-hover">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Quantity</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Market Value</th>
                <th>P/L</th>
                <th>P/L %</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-3">
                    {loading ? 'Loading positions...' : 'No positions found'}
                  </td>
                </tr>
              ) : (
                positions.map((position) => {
                  const pl = formatPL(position.unrealized_pl);
                  const plPercent = formatPLPercent(position.unrealized_plpc);
                  
                  return (
                    <tr key={position.symbol}>
                      <td>{position.symbol}</td>
                      <td>{position.qty}</td>
                      <td>${position.avg_entry_price.toFixed(2)}</td>
                      <td>${position.current_price.toFixed(2)}</td>
                      <td>${position.market_value.toFixed(2)}</td>
                      <td className={pl.class}>{pl.value}</td>
                      <td className={plPercent.class}>{plPercent.value}</td>
                      <td>
                        <button 
                          className="btn btn-sm btn-danger"
                          onClick={() => handleClosePosition(position.symbol)}
                        >
                          Close
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PositionsTable;