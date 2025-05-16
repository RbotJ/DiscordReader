import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { fetchTickerData } from '../services/apiService';

// Trade state constants
const TRADE_STATE = {
  MONITORING: 'monitoring',
  IN_TRADE: 'inTrade',
  CLOSED: 'closed'
};

const ChartCard = ({ 
  symbol, 
  signal, 
  onRemove,
  onSignalFired,
  onOrderUpdate
}) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeries = useRef(null);
  const [tradeState, setTradeState] = useState(TRADE_STATE.MONITORING);
  const [candleData, setCandleData] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Initialize chart
  useEffect(() => {
    if (chartContainerRef.current && !chartRef.current) {
      // Create chart
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 300,
        layout: {
          background: { color: '#18181B' },
          textColor: '#DDD',
        },
        grid: {
          vertLines: { color: '#242424' },
          horzLines: { color: '#242424' }
        },
        timeScale: {
          borderColor: '#3C3C3C',
          timeVisible: true,
        },
        crosshair: {
          mode: 0
        },
        rightPriceScale: {
          borderColor: '#3C3C3C',
        },
      });
      
      // Create candlestick series
      candleSeries.current = chartRef.current.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350'
      });
      
      // Resize handler
      const handleResize = () => {
        if (chartRef.current) {
          chartRef.current.applyOptions({ 
            width: chartContainerRef.current.clientWidth 
          });
        }
      };
      
      window.addEventListener('resize', handleResize);
      
      // Load data
      loadChartData();
      
      return () => {
        window.removeEventListener('resize', handleResize);
        
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
          candleSeries.current = null;
        }
      };
    }
  }, [chartContainerRef, symbol]);
  
  // Load chart data
  const loadChartData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchTickerData(symbol, '10m', 1);
      
      // Format data for lightweight-charts
      const formattedData = data.map(candle => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }));
      
      setCandleData(formattedData);
      
      if (candleSeries.current) {
        candleSeries.current.setData(formattedData);
      }
      
      // Draw trigger and target lines if we have signal data
      if (signal) {
        drawSignalLines(signal);
      }
      
    } catch (err) {
      console.error(`Error loading chart data for ${symbol}:`, err);
      setError(`Failed to load chart data for ${symbol}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Draw trigger and target lines on the chart
  const drawSignalLines = (signal) => {
    if (!chartRef.current || !candleSeries.current) return;
    
    // Clear previous lines
    chartRef.current.removeSeries();
    
    // Re-add candlestick series
    candleSeries.current = chartRef.current.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350'
    });
    
    // Set data again
    if (candleData.length > 0) {
      candleSeries.current.setData(candleData);
    }
    
    // Add trigger line
    if (signal.trigger) {
      const triggerLine = chartRef.current.addLineSeries({
        color: '#F6C244',
        lineWidth: 2,
        lineStyle: 0,
        title: 'Trigger'
      });
      
      // For time range we need start and end times
      const firstTime = candleData.length > 0 ? candleData[0].time : Math.floor(Date.now() / 1000) - 86400;
      const lastTime = candleData.length > 0 ? candleData[candleData.length - 1].time : Math.floor(Date.now() / 1000);
      
      let triggerValue = signal.trigger;
      // Handle range triggers
      if (Array.isArray(triggerValue)) {
        triggerValue = triggerValue[0]; // Use first value for simplicity
      }
      
      triggerLine.setData([
        { time: firstTime, value: triggerValue },
        { time: lastTime, value: triggerValue }
      ]);
    }
    
    // Add target lines
    if (signal.targets && signal.targets.length > 0) {
      signal.targets.forEach((target, index) => {
        const targetLine = chartRef.current.addLineSeries({
          color: '#4CAF50',
          lineWidth: 1,
          lineStyle: 2,
          title: `Target ${index + 1}`
        });
        
        const firstTime = candleData.length > 0 ? candleData[0].time : Math.floor(Date.now() / 1000) - 86400;
        const lastTime = candleData.length > 0 ? candleData[candleData.length - 1].time : Math.floor(Date.now() / 1000);
        
        targetLine.setData([
          { time: firstTime, value: target },
          { time: lastTime, value: target }
        ]);
      });
    }
  };
  
  // Handle WebSocket updates
  useEffect(() => {
    // This would be set up to listen for websocket events
    
    // Mock signal fired handler (connect this to WebSocket in real implementation)
    const handleSignalFired = (event) => {
      if (event.symbol === symbol) {
        setTradeState(TRADE_STATE.IN_TRADE);
        onSignalFired && onSignalFired(event);
      }
    };
    
    // Mock order update handler (connect this to WebSocket in real implementation)
    const handleOrderUpdate = (event) => {
      if (event.symbol === symbol) {
        if (event.status === 'filled' && event.side === 'sell') {
          setTradeState(TRADE_STATE.CLOSED);
          // Schedule removal after showing close badge
          setTimeout(() => {
            onRemove && onRemove(symbol);
          }, 5000);
        }
        onOrderUpdate && onOrderUpdate(event);
      }
    };
    
    // Set up listeners here
    
    return () => {
      // Clean up listeners here
    };
  }, [symbol, onRemove, onSignalFired, onOrderUpdate]);
  
  // Get card class based on trade state
  const getCardClass = () => {
    switch (tradeState) {
      case TRADE_STATE.MONITORING:
        return 'card border-primary';
      case TRADE_STATE.IN_TRADE:
        return 'card border-warning';
      case TRADE_STATE.CLOSED:
        return 'card border-success';
      default:
        return 'card';
    }
  };
  
  // Get badge based on trade state
  const getBadge = () => {
    switch (tradeState) {
      case TRADE_STATE.MONITORING:
        return <span className="badge bg-primary">Monitoring</span>;
      case TRADE_STATE.IN_TRADE:
        return <span className="badge bg-warning">In Trade</span>;
      case TRADE_STATE.CLOSED:
        return <span className="badge bg-success">✅ Closed</span>;
      default:
        return null;
    }
  };
  
  return (
    <div className={getCardClass()}>
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="mb-0">{symbol}</h5>
        <div>
          {getBadge()}
          <button 
            className="btn btn-sm btn-close ms-2" 
            onClick={() => onRemove(symbol)} 
            aria-label="Close"
          />
        </div>
      </div>
      <div className="card-body">
        {loading && <div className="text-center">Loading chart data...</div>}
        {error && <div className="alert alert-danger">{error}</div>}
        <div 
          ref={chartContainerRef} 
          className="chart-container" 
          style={{ height: '300px' }}
        />
        
        {signal && (
          <div className="mt-3">
            <h6>Signal</h6>
            <div className="small">
              <div><strong>Category:</strong> {signal.category}</div>
              <div><strong>Trigger:</strong> {Array.isArray(signal.trigger) 
                ? `${signal.trigger[0]} - ${signal.trigger[1]}` 
                : signal.trigger}
              </div>
              <div>
                <strong>Targets:</strong> {signal.targets.join(', ')}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChartCard;