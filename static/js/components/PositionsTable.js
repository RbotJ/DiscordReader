import React, { useEffect, useState } from 'react';
import { fetchPositions } from '../services/apiService';

const PositionsTable = ({ websocketService }) => {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Initial load
    loadPositions();
    
    // Set up websocket listener for position updates
    const unsubscribe = websocketService.subscribe('positionUpdate', handlePositionUpdate);
    
    return () => {
      unsubscribe();
    };
  }, [websocketService]);
  
  const loadPositions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchPositions();
      setPositions(data);
    } catch (err) {
      console.error('Error loading positions:', err);
      setError('Failed to load positions data');
    } finally {
      setLoading(false);
    }
  };
  
  const handlePositionUpdate = (data) => {
    setPositions(currentPositions => {
      // Find if we already have this position
      const index = currentPositions.findIndex(pos => pos.symbol === data.symbol);
      
      if (index !== -1) {
        // Update existing position
        return [
          ...currentPositions.slice(0, index),
          data,
          ...currentPositions.slice(index + 1)
        ];
      } else {
        // Add new position
        return [...currentPositions, data];
      }
    });
  };
  
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Current Positions</h5>
        </div>
        <div className="card-body">
          <div className="text-center">Loading positions...</div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Current Positions</h5>
        </div>
        <div className="card-body">
          <div className="alert alert-danger">{error}</div>
        </div>
      </div>
    );
  }
  
  if (positions.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Current Positions</h5>
        </div>
        <div className="card-body">
          <div className="text-center text-muted">No open positions</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Current Positions</h5>
      </div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Quantity</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Value</th>
                <th>P/L</th>
                <th>P/L %</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(position => (
                <tr key={position.symbol}>
                  <td>{position.symbol}</td>
                  <td>{position.qty}</td>
                  <td>${parseFloat(position.avg_entry_price).toFixed(2)}</td>
                  <td>${parseFloat(position.current_price).toFixed(2)}</td>
                  <td>${parseFloat(position.market_value).toFixed(2)}</td>
                  <td className={position.unrealized_pl >= 0 ? 'text-success' : 'text-danger'}>
                    ${parseFloat(position.unrealized_pl).toFixed(2)}
                  </td>
                  <td className={position.unrealized_plpc >= 0 ? 'text-success' : 'text-danger'}>
                    {(parseFloat(position.unrealized_plpc) * 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PositionsTable;