import React, { useState, useEffect, useRef } from 'react';

const EventLog = ({ websocketService }) => {
  const [events, setEvents] = useState([]);
  const logEndRef = useRef(null);
  
  useEffect(() => {
    // Subscribe to relevant events
    const unsubscribeMarket = websocketService.subscribe('marketUpdate', 
      data => addEvent('marketUpdate', data));
    
    const unsubscribeSignal = websocketService.subscribe('signalFired', 
      data => addEvent('signalFired', data));
    
    const unsubscribeOrder = websocketService.subscribe('orderUpdate', 
      data => addEvent('orderUpdate', data));
    
    const unsubscribePosition = websocketService.subscribe('positionUpdate', 
      data => addEvent('positionUpdate', data));
    
    const unsubscribeConnect = websocketService.subscribe('connect', 
      () => addEvent('connect', { timestamp: new Date().toISOString() }));
    
    const unsubscribeDisconnect = websocketService.subscribe('disconnect', 
      () => addEvent('disconnect', { timestamp: new Date().toISOString() }));
    
    return () => {
      unsubscribeMarket();
      unsubscribeSignal();
      unsubscribeOrder();
      unsubscribePosition();
      unsubscribeConnect();
      unsubscribeDisconnect();
    };
  }, [websocketService]);
  
  // Auto-scroll to bottom when new events are added
  useEffect(() => {
    scrollToBottom();
  }, [events]);
  
  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const addEvent = (type, data) => {
    const event = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      type,
      data,
      timestamp: data.timestamp || new Date().toISOString()
    };
    
    setEvents(prevEvents => {
      // Keep only the last 100 events
      const newEvents = [...prevEvents, event];
      if (newEvents.length > 100) {
        return newEvents.slice(newEvents.length - 100);
      }
      return newEvents;
    });
  };
  
  const getEventIcon = (type) => {
    switch (type) {
      case 'marketUpdate':
        return <i className="bi bi-graph-up text-info me-2"></i>;
      case 'signalFired':
        return <i className="bi bi-bell-fill text-warning me-2"></i>;
      case 'orderUpdate':
        return <i className="bi bi-currency-dollar text-success me-2"></i>;
      case 'positionUpdate':
        return <i className="bi bi-briefcase-fill text-primary me-2"></i>;
      case 'connect':
        return <i className="bi bi-wifi text-success me-2"></i>;
      case 'disconnect':
        return <i className="bi bi-wifi-off text-danger me-2"></i>;
      default:
        return <i className="bi bi-info-circle text-secondary me-2"></i>;
    }
  };
  
  const getEventDescription = (event) => {
    const { type, data } = event;
    
    switch (type) {
      case 'marketUpdate':
        return `Price update for ${data.symbol}: $${data.price}`;
      case 'signalFired':
        return `Signal triggered for ${data.symbol}: ${data.category} at $${data.price}`;
      case 'orderUpdate':
        return `Order ${data.id} for ${data.symbol} ${data.status} - ${data.side} ${data.qty} @ $${data.price || 'market'}`;
      case 'positionUpdate':
        return `Position update: ${data.symbol} ${data.qty} shares, P/L: $${parseFloat(data.unrealized_pl).toFixed(2)}`;
      case 'connect':
        return 'WebSocket connected';
      case 'disconnect':
        return 'WebSocket disconnected';
      default:
        return JSON.stringify(data);
    }
  };
  
  const formatTimestamp = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString();
  };
  
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="mb-0">Event Log</h5>
      </div>
      <div className="card-body p-0">
        <div 
          className="event-log" 
          style={{ 
            height: '300px', 
            overflowY: 'scroll', 
            padding: '10px',
            fontSize: '0.85rem'
          }}
        >
          {events.length === 0 ? (
            <div className="text-center text-muted py-5">No events yet</div>
          ) : (
            <ul className="list-group list-group-flush">
              {events.map(event => (
                <li key={event.id} className="list-group-item py-1 px-2 border-bottom">
                  <div className="d-flex align-items-center">
                    {getEventIcon(event.type)}
                    <span className="me-2 text-muted">
                      {formatTimestamp(event.timestamp)}
                    </span>
                    <span className="flex-grow-1">
                      {getEventDescription(event)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};

export default EventLog;