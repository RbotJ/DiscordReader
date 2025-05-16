/**
 * AccountInfo component
 * 
 * Displays account information and key metrics
 */
import React, { useEffect, useState } from 'react';
import { fetchAccount } from '../services/apiService';

const AccountInfo = () => {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load account data on component mount
  useEffect(() => {
    loadAccountData();
    
    // Refresh account data every minute
    const refreshInterval = setInterval(loadAccountData, 60000);
    
    return () => clearInterval(refreshInterval);
  }, []);
  
  // Load account data from the API
  const loadAccountData = async () => {
    try {
      setLoading(true);
      const data = await fetchAccount();
      
      if (!data) {
        setError('No account data available');
        return;
      }
      
      setAccount(data);
      setError(null);
    } catch (err) {
      console.error('Error loading account data:', err);
      setError('Failed to load account data');
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
  
  // Handle refresh button click
  const handleRefresh = () => {
    loadAccountData();
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Account Overview</h5>
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
      <div className="card-body">
        {error ? (
          <div className="alert alert-danger">
            {error}
          </div>
        ) : loading ? (
          <div className="d-flex justify-content-center">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : account ? (
          <div className="row g-3">
            <div className="col-md-6 col-lg-3">
              <div className="card bg-dark h-100">
                <div className="card-body">
                  <h6 className="card-subtitle mb-2 text-muted">Portfolio Value</h6>
                  <h4 className="card-title">{formatCurrency(account.portfolio_value)}</h4>
                </div>
              </div>
            </div>
            <div className="col-md-6 col-lg-3">
              <div className="card bg-dark h-100">
                <div className="card-body">
                  <h6 className="card-subtitle mb-2 text-muted">Cash Balance</h6>
                  <h4 className="card-title">{formatCurrency(account.cash)}</h4>
                </div>
              </div>
            </div>
            <div className="col-md-6 col-lg-3">
              <div className="card bg-dark h-100">
                <div className="card-body">
                  <h6 className="card-subtitle mb-2 text-muted">Buying Power</h6>
                  <h4 className="card-title">{formatCurrency(account.buying_power)}</h4>
                </div>
              </div>
            </div>
            <div className="col-md-6 col-lg-3">
              <div className="card bg-dark h-100">
                <div className="card-body">
                  <h6 className="card-subtitle mb-2 text-muted">Account Status</h6>
                  <h4 className="card-title d-flex align-items-center">
                    <span className={account.status === 'ACTIVE' ? 'text-success' : 'text-warning'}>
                      {account.status}
                    </span>
                    {account.status === 'ACTIVE' && (
                      <i className="bi bi-check-circle-fill text-success ms-2"></i>
                    )}
                  </h4>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="alert alert-warning">
            No account information available
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountInfo;