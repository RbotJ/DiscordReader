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

  useEffect(() => {
    loadPositions();

    // Refresh positions every 60 seconds
    const refreshInterval = setInterval(loadPositions, 60000);

    return () => clearInterval(refreshInterval);
  }, []);

  const loadPositions = async () => {
    try {
      setLoading(true);
      const data = await fetchPositions();
      setPositions(data || []);
      setError(null);
    } catch (err) {
      console.error('Error loading positions:', err);
      setError('Failed to load positions data');
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
  const formatPercent = (value) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'percent', 
      minimumFractionDigits: 2,
      maximumFractionDigits: 2 
    }).format(value / 100);
  };

  // Get style for profit/loss values
  const getProfitLossClass = (value) => {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return '';
  };

  const handleRefresh = () => {
    loadPositions();
  };

  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Open Positions</h5>
        <button 
          className="btn btn-sm btn-outline-secondary" 
          onClick={handleRefresh}
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
        {error && (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        )}
        {positions.length === 0 && !loading && !error ? (
          <div className="p-4 text-center text-muted">
            <p>No open positions</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover table-striped mb-0">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Quantity</th>
                  <th>Avg Entry</th>
                  <th>Current</th>
                  <th>Market Value</th>
                  <th>P/L</th>
                  <th>P/L %</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr key={position.symbol}>
                    <td>{position.symbol}</td>
                    <td>{parseFloat(position.qty).toFixed(2)}</td>
                    <td>{formatCurrency(position.avg_entry_price)}</td>
                    <td>{formatCurrency(position.current_price)}</td>
                    <td>{formatCurrency(position.market_value)}</td>
                    <td className={getProfitLossClass(position.unrealized_pl)}>
                      {formatCurrency(position.unrealized_pl)}
                    </td>
                    <td className={getProfitLossClass(position.unrealized_plpc)}>
                      {formatPercent(position.unrealized_plpc)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default PositionsTable;