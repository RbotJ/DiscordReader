/**
 * ChartCard component
 * 
 * Displays a candlestick chart with price levels and signals for a ticker
 */
import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { fetchCandles, fetchSignals } from '../services/apiService';
import { on, off } from '../services/websocketService';

// Trading states
const STATES = {
  MONITORING: 'monitoring',
  IN_TRADE: 'in_trade',
  CLOSED: 'closed'
};

const ChartCard = ({ ticker, onClose }) => {
  const chartContainerRef = useRef(null);
  const chart = useRef(null);
  const candleSeries = useRef(null);
  const priceLevels = useRef([]);
  
  const [timeframe, setTimeframe] = useState('1min');
  const [chartData, setChartData] = useState([]);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tradeState, setTradeState] = useState(STATES.MONITORING);
  
  // Initialize the chart
  useEffect(() => {
    if (chartContainerRef.current && !chart.current) {
      // Create the chart
      chart.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 400,
        layout: {
          background: { color: '#1e222d' },
          textColor: '#d1d4dc',
        },
        grid: {
          vertLines: { color: '#2b2b43' },
          horzLines: { color: '#363c4e' },
        },
        crosshair: {
          mode: 1
        },
        rightPriceScale: {
          borderColor: '#485c7b',
        },
        timeScale: {
          borderColor: '#485c7b',
        },
      });
      
      // Add candlestick series
      candleSeries.current = chart.current.addCandlestickSeries({
        upColor: '#4bffb5',
        downColor: '#ff4976',
        borderDownColor: '#ff4976',
        borderUpColor: '#4bffb5',
        wickDownColor: '#838ca1',
        wickUpColor: '#838ca1',
      });
      
      // Handle resize
      const handleResize = () => {
        if (chart.current && chartContainerRef.current) {
          chart.current.applyOptions({ 
            width: chartContainerRef.current.clientWidth 
          });
        }
      };
      
      window.addEventListener('resize', handleResize);
      
      // Clean up
      return () => {
        window.removeEventListener('resize', handleResize);
        if (chart.current) {
          chart.current.remove();
          chart.current = null;
          candleSeries.current = null;
        }
      };
    }
  }, []);
  
  // Load chart data when ticker or timeframe changes
  useEffect(() => {
    loadChartData();
    loadSignals();
    
    // Subscribe to real-time updates
    const handleRealTimeUpdate = (data) => {
      if (data.ticker === ticker) {
        updateLatestCandle(data);
      }
    };
    
    const handleSignalUpdate = (data) => {
      if (data.ticker === ticker) {
        updateSignals(data);
      }
    };
    
    on('candle_update', handleRealTimeUpdate);
    on('signal_update', handleSignalUpdate);
    
    // Clean up
    return () => {
      off('candle_update', handleRealTimeUpdate);
      off('signal_update', handleSignalUpdate);
      clearPriceLevels();
    };
  }, [ticker, timeframe]);
  
  // Load chart data from API
  const loadChartData = async () => {
    try {
      setLoading(true);
      const data = await fetchCandles(ticker, timeframe);
      
      if (!data || data.length === 0) {
        setError('No chart data available');
        return;
      }
      
      // Format data for lightweight-charts
      const formattedData = data.map(candle => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: candle.volume
      }));
      
      setChartData(formattedData);
      
      if (candleSeries.current) {
        candleSeries.current.setData(formattedData);
        chart.current.timeScale().fitContent();
      }
      
      setError(null);
    } catch (err) {
      console.error('Error loading chart data:', err);
      setError('Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };
  
  // Load signals from API
  const loadSignals = async () => {
    try {
      const data = await fetchSignals(ticker);
      
      if (!data) {
        console.log('No signals available');
        return;
      }
      
      setSignals(data);
      
      // Add price levels to the chart
      clearPriceLevels();
      
      data.forEach(signal => {
        // Add trigger level
        if (typeof signal.trigger === 'object' && signal.trigger.value) {
          addPriceLevel(signal.trigger.value, '#ff9800');
        } else if (typeof signal.trigger === 'number') {
          addPriceLevel(signal.trigger, '#ff9800');
        }
        
        // Add target levels
        if (Array.isArray(signal.targets)) {
          signal.targets.forEach((target, index) => {
            if (typeof target === 'object' && target.price) {
              addPriceLevel(target.price, '#4caf50');
            } else if (typeof target === 'number') {
              addPriceLevel(target, '#4caf50');
            }
          });
        }
      });
      
    } catch (err) {
      console.error('Error loading signals:', err);
    }
  };
  
  // Add a horizontal price level to the chart
  const addPriceLevel = (price, color) => {
    if (!chart.current || !price) return;
    
    const line = chart.current.addLineSeries({
      color: color,
      lineWidth: 2,
      lineStyle: 1,
      priceLineVisible: true,
      lastValueVisible: true,
    });
    
    line.setData([
      { time: chartData[0]?.time || Math.floor(Date.now() / 1000) - 86400, value: price },
      { time: chartData[chartData.length - 1]?.time || Math.floor(Date.now() / 1000), value: price }
    ]);
    
    priceLevels.current.push(line);
  };
  
  // Clear all price levels
  const clearPriceLevels = () => {
    if (!chart.current) return;
    
    priceLevels.current.forEach(line => {
      chart.current.removeSeries(line);
    });
    
    priceLevels.current = [];
  };
  
  // Update the latest candle with real-time data
  const updateLatestCandle = (data) => {
    if (!candleSeries.current || !chart.current) return;
    
    const lastCandle = {
      time: Math.floor(new Date(data.timestamp).getTime() / 1000),
      open: data.open,
      high: data.high,
      low: data.low,
      close: data.close,
      volume: data.volume
    };
    
    candleSeries.current.update(lastCandle);
  };
  
  // Update signals with real-time data
  const updateSignals = (data) => {
    setSignals(prevSignals => {
      const newSignals = [...prevSignals];
      
      // Find if signal exists
      const existingIndex = newSignals.findIndex(s => s.id === data.id);
      
      if (existingIndex >= 0) {
        // Update existing signal
        newSignals[existingIndex] = { ...data };
      } else {
        // Add new signal
        newSignals.push(data);
      }
      
      return newSignals;
    });
    
    // Update price levels
    clearPriceLevels();
    loadSignals();
  };
  
  // Handle timeframe change
  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };
  
  // Handle state change button click
  const handleStateChange = () => {
    switch (tradeState) {
      case STATES.MONITORING:
        setTradeState(STATES.IN_TRADE);
        break;
      case STATES.IN_TRADE:
        setTradeState(STATES.CLOSED);
        break;
      case STATES.CLOSED:
        setTradeState(STATES.MONITORING);
        break;
    }
  };
  
  // Get styles for the state badge
  const getStateBadgeClass = () => {
    switch (tradeState) {
      case STATES.MONITORING:
        return 'bg-secondary';
      case STATES.IN_TRADE:
        return 'bg-warning';
      case STATES.CLOSED:
        return 'bg-success';
      default:
        return 'bg-secondary';
    }
  };
  
  // Get text for the state button
  const getStateButtonText = () => {
    switch (tradeState) {
      case STATES.MONITORING:
        return 'Enter Trade';
      case STATES.IN_TRADE:
        return 'Close Trade';
      case STATES.CLOSED:
        return 'Reset';
      default:
        return 'Change State';
    }
  };
  
  return (
    <div className="card mb-4">
      <div className="card-header d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center">
          <h5 className="mb-0 me-2">{ticker}</h5>
          <span className={`badge ${getStateBadgeClass()} ms-2`}>
            {tradeState.toUpperCase()}
          </span>
        </div>
        <div className="d-flex">
          <div className="btn-group me-2">
            <button 
              className={`btn btn-sm ${timeframe === '1min' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => handleTimeframeChange('1min')}
            >
              1m
            </button>
            <button 
              className={`btn btn-sm ${timeframe === '5min' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => handleTimeframeChange('5min')}
            >
              5m
            </button>
            <button 
              className={`btn btn-sm ${timeframe === '15min' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => handleTimeframeChange('15min')}
            >
              15m
            </button>
            <button 
              className={`btn btn-sm ${timeframe === '1hour' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => handleTimeframeChange('1hour')}
            >
              1h
            </button>
            <button 
              className={`btn btn-sm ${timeframe === '1day' ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => handleTimeframeChange('1day')}
            >
              1d
            </button>
          </div>
          <button 
            className="btn btn-sm btn-outline-primary me-2"
            onClick={handleStateChange}
          >
            {getStateButtonText()}
          </button>
          <button 
            className="btn btn-sm btn-outline-danger"
            onClick={onClose}
          >
            <i className="bi bi-x"></i>
          </button>
        </div>
      </div>
      <div className="card-body p-0">
        {error ? (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        ) : loading ? (
          <div className="d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : (
          <div ref={chartContainerRef} className="chart-container"></div>
        )}
      </div>
      {signals.length > 0 && (
        <div className="card-footer">
          <div className="small">
            <strong>Signals:</strong> {signals.map(signal => signal.category).join(', ')}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartCard;