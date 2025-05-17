/**
 * EventLog component
 * 
 * Displays a scrollable log of market events, trades, and system messages
 */
import React, { useEffect, useRef, useState, forwardRef, useImperativeHandle } from 'react';

const MAX_LOG_ENTRIES = 100;

const EventLog = forwardRef((props, ref) => {
  const [logs, setLogs] = useState([]);
  const logEndRef = useRef(null);
  
  // Add a new log entry
  const addLogEntry = (entry) => {
    setLogs(prevLogs => {
      // Keep only the most recent entries to prevent memory issues
      const newLogs = [...prevLogs, entry].slice(-MAX_LOG_ENTRIES);
      return newLogs;
    });
  };
  
  // Scroll to bottom when logs change
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);
  
  // Method to add a new log message
  const addLog = (type, message, data = null) => {
    const timestamp = new Date().toISOString();
    
    // Ensure data is a string or null
    let processedData = null;
    if (data !== null) {
      if (typeof data === 'string') {
        processedData = data;
      } else if (typeof data === 'object') {
        try {
          processedData = JSON.stringify(data);
        } catch (e) {
          processedData = String(data);
        }
      } else {
        processedData = String(data);
      }
    }
    
    const entry = {
      id: Date.now() + Math.random().toString(36).substring(2, 8),
      timestamp,
      type,
      message,
      data: processedData
    };
    
    addLogEntry(entry);
  };
  
  // Log entry component
  const LogEntry = ({ entry }) => {
    const { timestamp, type, message, data } = entry;
    
    // Format timestamp
    const formattedTime = new Date(timestamp).toLocaleTimeString();
    
    // Get CSS class based on log type
    const getTypeClass = () => {
      switch (type) {
        case 'error':
          return 'text-danger';
        case 'warning':
          return 'text-warning';
        case 'success':
          return 'text-success';
        case 'info':
          return 'text-info';
        case 'trade':
          return 'text-primary';
        default:
          return '';
      }
    };
    
    return (
      <div className={`log-entry small ${getTypeClass()}`}>
        <span className="log-timestamp text-muted">[{formattedTime}]</span>
        <span className="log-message ms-2">{message}</span>
        {data && (
          <span className="log-data ms-2 text-muted">
            {typeof data === 'string' ? data : (
              typeof data === 'object' ? JSON.stringify(data) : String(data)
            )}
          </span>
        )}
      </div>
    );
  };
  
  // Clear the log
  const clearLog = () => {
    setLogs([]);
    addLog('info', 'Log cleared');
  };
  
  // Expose methods to parent components
  useImperativeHandle(ref, () => ({
    addLog,
    clearLog
  }));
  
  // Add test logs on initial render with guaranteed unique IDs
  useEffect(() => {
    const uniqueId1 = `init_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
    const uniqueId2 = `wait_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
    
    setLogs([
      {
        id: uniqueId1,
        timestamp: new Date().toISOString(),
        type: 'info',
        message: 'Event log initialized',
        data: null
      },
      {
        id: uniqueId2,
        timestamp: new Date().toISOString(),
        type: 'info',
        message: 'Waiting for market data...',
        data: null
      }
    ]);
  }, []);
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Event Log</h5>
        <button 
          className="btn btn-sm btn-outline-secondary"
          onClick={clearLog}
        >
          Clear
        </button>
      </div>
      <div className="card-body p-2">
        <div className="event-log bg-dark p-2 rounded" style={{ height: '200px', overflowY: 'auto' }}>
          {logs.length === 0 ? (
            <div className="text-muted text-center p-3">No events</div>
          ) : (
            logs.map(entry => (
              <LogEntry key={entry.id} entry={entry} />
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
});

export default EventLog;