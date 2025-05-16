/**
 * ChartCard Component
 * 
 * This component displays a candlestick chart using lightweight-charts
 * It shows price data, triggers, and targets for a given ticker
 */
import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { fetchCandles, fetchSignals } from '../services/apiService';

// Card states
const CARD_STATES = {
  MONITORING: 'monitoring',
  IN_TRADE: 'inTrade',
  CLOSED: 'closed'
};

const ChartCard = ({ ticker, onClose }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);
  const triggerLineRef = useRef(null);
  const targetLinesRef = useRef([]);
  const [state, setState] = useState(CARD_STATES.MONITORING);
  const [timeframe, setTimeframe] = useState('1min');
  const [signal, setSignal] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [error, setError] = useState(null);
  
  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Create chart instance
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { color: '#1e1e2e' },
        textColor: '#d9d9d9',
      },
      grid: {
        vertLines: { color: '#2e2e3e' },
        horzLines: { color: '#2e2e3e' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: '#4f8bff',
          style: 0,
        },
        horzLine: {
          width: 1,
          color: '#4f8bff',
          style: 0,
        },
      },
      rightPriceScale: {
        borderColor: '#2e2e3e',
      },
      timeScale: {
        borderColor: '#2e2e3e',
        timeVisible: true,
      },
    });
    
    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    
    // Save refs
    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    
    // Handle resize
    const handleResize = () => {
      if (chartRef.current) {
        chartRef.current.applyOptions({ 
          width: chartContainerRef.current.clientWidth 
        });
      }
    };
    
    window.addEventListener('resize', handleResize);
    
    // Load initial data
    loadChartData();
    
    // Load signal data
    loadSignalData();
    
    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [ticker]);
  
  // Effect for timeframe changes
  useEffect(() => {
    loadChartData();
  }, [timeframe]);
  
  // Load chart data
  const loadChartData = async () => {
    try {
      const candleData = await fetchCandles(ticker, timeframe);
      
      if (!candleData || candleData.length === 0) {
        setError('No candle data available');
        return;
      }
      
      setError(null);
      
      // Format data for lightweight-charts
      const formattedData = candleData.map(candle => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }));
      
      if (candlestickSeriesRef.current) {
        candlestickSeriesRef.current.setData(formattedData);
      }
      
      // Update last price
      if (formattedData.length > 0) {
        setLastPrice(formattedData[formattedData.length - 1].close);
      }
    } catch (err) {
      console.error('Error loading chart data:', err);
      setError('Failed to load chart data');
    }
  };
  
  // Load signal data
  const loadSignalData = async () => {
    try {
      const signalData = await fetchSignals(ticker);
      
      if (!signalData) {
        // No signals available, stay in monitoring state
        setState(CARD_STATES.MONITORING);
        return;
      }
      
      setSignal(signalData);
      
      // Add trigger line
      if (chartRef.current && signalData.trigger) {
        const triggerPrice = signalData.trigger.price;
        
        // Remove existing trigger line
        if (triggerLineRef.current) {
          chartRef.current.removePriceLine(triggerLineRef.current);
        }
        
        // Add new trigger line
        const triggerLine = candlestickSeriesRef.current.createPriceLine({
          price: triggerPrice,
          color: '#f5a623',
          lineWidth: 2,
          lineStyle: 1, // Dashed
          axisLabelVisible: true,
          title: `Trigger: ${signalData.category}`
        });
        
        triggerLineRef.current = triggerLine;
        
        // Add target lines
        if (signalData.targets && Array.isArray(signalData.targets)) {
          // Remove existing target lines
          targetLinesRef.current.forEach(line => {
            chartRef.current.removePriceLine(line);
          });
          
          targetLinesRef.current = [];
          
          // Add new target lines
          signalData.targets.forEach((target, index) => {
            const targetLine = candlestickSeriesRef.current.createPriceLine({
              price: target.price,
              color: '#4caf50',
              lineWidth: 1,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `Target ${index + 1}`
            });
            
            targetLinesRef.current.push(targetLine);
          });
        }
        
        // Update card state based on price
        updateCardState(lastPrice, triggerPrice, signalData);
      }
    } catch (err) {
      console.error('Error loading signal data:', err);
    }
  };
  
  // Update card state based on price
  const updateCardState = (price, triggerPrice, signalData) => {
    if (!price || !triggerPrice) return;
    
    // Determine if the trigger has been hit
    const category = signalData.category.toLowerCase();
    const comparison = signalData.comparison.toLowerCase();
    
    let triggerHit = false;
    
    if (category === 'breakout' && comparison === 'above' && price > triggerPrice) {
      triggerHit = true;
    } else if (category === 'breakdown' && comparison === 'below' && price < triggerPrice) {
      triggerHit = true;
    } else if (category === 'rejection' && ((comparison === 'above' && price > triggerPrice) || 
              (comparison === 'below' && price < triggerPrice))) {
      triggerHit = true;
    } else if (category === 'bounce' && ((comparison === 'above' && price > triggerPrice) || 
              (comparison === 'below' && price < triggerPrice))) {
      triggerHit = true;
    }
    
    // Update state
    if (triggerHit) {
      setState(CARD_STATES.IN_TRADE);
    } else {
      setState(CARD_STATES.MONITORING);
    }
  };
  
  // Handle market data update
  const handleMarketUpdate = (data) => {
    if (data.ticker !== ticker) return;
    
    setLastPrice(data.price);
    
    // Update card state if we have a signal
    if (signal && signal.trigger) {
      updateCardState(data.price, signal.trigger.price, signal);
    }
  };
  
  // Get class based on state
  const getCardClass = () => {
    switch (state) {
      case CARD_STATES.MONITORING:
        return 'border-secondary';
      case CARD_STATES.IN_TRADE:
        return 'border-primary';
      case CARD_STATES.CLOSED:
        return 'border-success';
      default:
        return 'border-secondary';
    }
  };
  
  // Handle timeframe change
  const handleTimeframeChange = (e) => {
    setTimeframe(e.target.value);
  };
  
  // Get badge text and class for state
  const getStateBadge = () => {
    switch (state) {
      case CARD_STATES.MONITORING:
        return { text: 'Monitoring', className: 'bg-secondary' };
      case CARD_STATES.IN_TRADE:
        return { text: 'In Trade', className: 'bg-primary' };
      case CARD_STATES.CLOSED:
        return { text: 'Closed', className: 'bg-success' };
      default:
        return { text: 'Unknown', className: 'bg-secondary' };
    }
  };
  
  const badge = getStateBadge();
  
  return (
    <div className={`card mb-4 ${getCardClass()}`}>
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-0 d-inline">{ticker}</h5>
          <span className={`badge ms-2 ${badge.className}`}>{badge.text}</span>
          {lastPrice && (
            <span className="ms-2">${parseFloat(lastPrice).toFixed(2)}</span>
          )}
        </div>
        <div className="d-flex">
          <select 
            className="form-select form-select-sm me-2" 
            value={timeframe} 
            onChange={handleTimeframeChange}
          >
            <option value="1min">1 Min</option>
            <option value="5min">5 Min</option>
            <option value="15min">15 Min</option>
            <option value="1hour">1 Hour</option>
            <option value="1day">Daily</option>
          </select>
          <button 
            className="btn btn-sm btn-outline-danger" 
            onClick={onClose}
          >
            <i className="bi bi-x-lg"></i>
          </button>
        </div>
      </div>
      <div className="card-body p-0">
        {error ? (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        ) : (
          <div 
            ref={chartContainerRef} 
            className="chart-container"
          ></div>
        )}
      </div>
      {signal && (
        <div className="card-footer">
          <div className="d-flex justify-content-between small">
            <span>
              <strong>Signal:</strong> {signal.category} {signal.comparison}
            </span>
            <span>
              <strong>Trigger:</strong> ${signal.trigger?.price?.toFixed(2)}
            </span>
            <span>
              <strong>Targets:</strong> 
              {signal.targets?.map((target, i) => 
                <span key={i} className="ms-1">${target.price.toFixed(2)}{i < signal.targets.length - 1 ? ',' : ''}</span>
              )}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartCard;