import React from 'react';
import Dashboard from './components/Dashboard';

/**
 * Main App component
 * Serves as the entry point for our React application
 */
function App() {
  return (
    <>
      {/* Navigation */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div className="container">
          <a className="navbar-brand" href="/">A+ Trading</a>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav ms-auto">
              <li className="nav-item">
                <a className="nav-link" href="/">Home</a>
              </li>
              <li className="nav-item">
                <a className="nav-link active" href="/dashboard">Dashboard</a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/setup">Submit Setup</a>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container-fluid py-3">
        <Dashboard />
      </div>

      {/* Footer */}
      <footer className="bg-dark text-center text-white mt-5 py-4">
        <div className="container">
          <p>© 2025 A+ Trading Platform</p>
        </div>
      </footer>
    </>
  );
}

export default App;