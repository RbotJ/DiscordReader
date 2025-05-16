import React from 'react';
import Dashboard from './components/Dashboard';

const App = () => {
  return (
    <div className="app">
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container-fluid">
          <a className="navbar-brand" href="/">
            <img src="/static/logo.svg" alt="Trading App Logo" height="30" className="me-2" />
            A+ Trading Dashboard
          </a>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav">
              <li className="nav-item">
                <a className="nav-link active" href="/dashboard">Dashboard</a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/setups">Setups</a>
              </li>
            </ul>
          </div>
          <div className="d-flex">
            <span className="badge bg-success me-2">Paper Trading</span>
          </div>
        </div>
      </nav>
      
      <Dashboard />
    </div>
  );
};

export default App;