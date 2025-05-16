import React, { useState, useEffect, useRef } from 'react';

/**
 * EventLog component
 * Displays real-time event logs
 * 
 * @param {Object} props Component props
 * @param {Array} props.events Array of event objects
 * @param {number} props.maxEvents Maximum number of events to display
 */
const EventLog = ({ events = [], maxEvents = 50 }) => {
  const [visibleEvents, setVisibleEvents] = useState([]);
  const logContainerRef = useRef(null);
  
  // Update visible events when events prop changes
  useEffect(() => {
    if (events.length === 0) return;
    
    // Keep only the most recent events, up to maxEvents
    const updatedEvents = [...visibleEvents, ...events];
    const trimmedEvents = updatedEvents.slice(-maxEvents);
    
    setVisibleEvents(trimmedEvents);
  }, [events, maxEvents]);
  
  // Auto-scroll to the bottom when new events are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [visibleEvents]);
  
  // Clear all events
  const handleClear = () => {
    setVisibleEvents([]);
  };
  
  // Get the appropriate badge class based on event type
  const getEventBadgeClass = (type) => {
    switch (type.toLowerCase()) {
      case 'error':
        return 'bg-danger';
      case 'warning':
        return 'bg-warning';
      case 'success':
        return 'bg-success';
      case 'info':
        return 'bg-info';
      case 'trade':
        return 'bg-primary';
      case 'signal':
        return 'bg-secondary';
      default:
        return 'bg-secondary';
    }
  };
  
  // Format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">Event Log</h5>
        <button 
          className="btn btn-sm btn-outline-secondary"
          onClick={handleClear}
        >
          Clear
        </button>
      </div>
      <div 
        className="card-body p-0 event-log" 
        ref={logContainerRef}
        style={{ maxHeight: '300px', overflowY: 'auto' }}
      >
        {visibleEvents.length === 0 ? (
          <div className="text-center p-3 text-muted">
            No events to display
          </div>
        ) : (
          <ul className="list-group list-group-flush">
            {visibleEvents.map((event, index) => (
              <li key={index} className="list-group-item py-1 px-3 border-bottom">
                <span className="text-muted small me-2">
                  {formatTimestamp(event.timestamp)}
                </span>
                <span className={`badge ${getEventBadgeClass(event.type)} me-2`}>
                  {event.type}
                </span>
                <span>{event.message}</span>
                {event.data && (
                  <span className="text-muted small ms-2">
                    {typeof event.data === 'object' 
                      ? JSON.stringify(event.data) 
                      : event.data.toString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default EventLog;