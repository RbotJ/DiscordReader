import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import apiService from '../services/apiService';

/**
 * ChartCard component
 * Displays a ticker chart with trigger and target lines
 * 
 * @param {Object} props Component props
 * @param {string} props.ticker Ticker symbol
 * @param {string} props.status Card status (monitoring, inTrade, closed)
 * @param {Object} props.signal Signal data containing trigger and target prices
 */
const ChartCard = ({ ticker, status = 'monitoring', signal = null }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeries = useRef(null);
  const triggerLineRef = useRef(null);
  const targetLineRef = useRef(null);
  
  const [timeframe, setTimeframe] = useState('5min');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Card classes based on status
  const cardClasses = {
    monitoring: 'border-primary',
    inTrade: 'border-warning',
    closed: 'border-success'
  };
  
  // Card titles based on status
  const cardTitles = {
    monitoring: 'Monitoring',
    inTrade: 'In Trade',
    closed: 'Closed'
  };
  
  // Load chart data when component mounts or ticker/timeframe changes
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Create chart instance if it doesn't exist
    if (!chartRef.current) {
      // Create the chart
      chartRef.current = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 300,
        layout: {
          backgroundColor: '#131722',
          textColor: '#d1d4dc',
        },
        grid: {
          vertLines: {
            color: 'rgba(42, 46, 57, 0.5)',
          },
          horzLines: {
            color: 'rgba(42, 46, 57, 0.5)',
          },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
        },
        priceScale: {
          borderColor: 'rgba(197, 203, 206, 0.8)',
        },
        timeScale: {
          borderColor: 'rgba(197, 203, 206, 0.8)',
          timeVisible: true,
        },
      });
      
      // Create the candlestick series
      candleSeries.current = chartRef.current.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
      
      // Handle window resize
      const handleResize = () => {
        if (chartRef.current) {
          chartRef.current.applyOptions({ 
            width: chartContainerRef.current.clientWidth 
          });
        }
      };
      
      window.addEventListener('resize', handleResize);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }
      };
    }
    
    // Load candle data
    const loadCandleData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch candle data from API
        const candles = await apiService.getCandles(ticker, timeframe);
        
        if (candles && candles.length > 0) {
          // Format candles for the chart
          const formattedCandles = candles.map(candle => ({
            time: candle.time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close
          }));
          
          // Update chart data
          candleSeries.current.setData(formattedCandles);
          
          // Add trigger and target lines if signal is provided
          updateSignalLines();
          
          // Fit content to view
          chartRef.current.timeScale().fitContent();
        } else {
          setError('No candle data available');
        }
      } catch (err) {
        console.error('Error loading candle data:', err);
        setError('Failed to load chart data');
      } finally {
        setLoading(false);
      }
    };
    
    loadCandleData();
  }, [ticker, timeframe]);
  
  // Update signal lines when signal changes
  useEffect(() => {
    updateSignalLines();
  }, [signal]);
  
  // Update trigger and target lines
  const updateSignalLines = () => {
    if (!chartRef.current || !candleSeries.current || !signal) return;
    
    // Remove existing lines
    if (triggerLineRef.current) {
      chartRef.current.removePriceLine(triggerLineRef.current);
      triggerLineRef.current = null;
    }
    
    if (targetLineRef.current) {
      chartRef.current.removePriceLine(targetLineRef.current);
      targetLineRef.current = null;
    }
    
    // Add trigger line
    if (signal.trigger) {
      triggerLineRef.current = candleSeries.current.createPriceLine({
        price: signal.trigger.price,
        color: '#ff9800',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: 'Trigger',
      });
    }
    
    // Add target line
    if (signal.target) {
      targetLineRef.current = candleSeries.current.createPriceLine({
        price: signal.target.price,
        color: '#4caf50',
        lineWidth: 2,
        lineStyle: 0, // Solid
        axisLabelVisible: true,
        title: 'Target',
      });
    }
  };
  
  // Handle timeframe change
  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };
  
  return (
    <div className={`card ${cardClasses[status] || 'border-primary'} mb-3`}>
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h5 className="mb-0">{ticker}</h5>
          <span className="badge bg-secondary">{cardTitles[status] || 'Monitoring'}</span>
        </div>
        <div className="btn-group">
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
            className={`btn btn-sm ${timeframe === '1day' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => handleTimeframeChange('1day')}
          >
            1d
          </button>
        </div>
      </div>
      <div className="card-body">
        {loading && (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        )}
        
        {error && (
          <div className="alert alert-danger">
            {error}
          </div>
        )}
        
        <div 
          className="chart-container" 
          ref={chartContainerRef}
          style={{ height: '300px', visibility: loading ? 'hidden' : 'visible' }}
        ></div>
        
        {signal && (
          <div className="mt-3">
            <div className="row">
              {signal.category && (
                <div className="col-md-3 mb-2">
                  <div className="text-muted small">Type</div>
                  <div className="fw-bold">
                    {signal.category === 'breakout' && (
                      <span className="badge bg-primary">Breakout</span>
                    )}
                    {signal.category === 'breakdown' && (
                      <span className="badge bg-danger">Breakdown</span>
                    )}
                    {signal.category === 'rejection' && (
                      <span className="badge bg-warning">Rejection</span>
                    )}
                    {signal.category === 'bounce' && (
                      <span className="badge bg-success">Bounce</span>
                    )}
                  </div>
                </div>
              )}
              
              {signal.trigger && (
                <div className="col-md-3 mb-2">
                  <div className="text-muted small">Trigger</div>
                  <div className="fw-bold">${signal.trigger.price.toFixed(2)}</div>
                </div>
              )}
              
              {signal.target && (
                <div className="col-md-3 mb-2">
                  <div className="text-muted small">Target</div>
                  <div className="fw-bold">${signal.target.price.toFixed(2)}</div>
                </div>
              )}
              
              {signal.aggressiveness && (
                <div className="col-md-3 mb-2">
                  <div className="text-muted small">Aggressiveness</div>
                  <div className="fw-bold">
                    {signal.aggressiveness === 'low' && (
                      <span className="badge bg-info">Low</span>
                    )}
                    {signal.aggressiveness === 'medium' && (
                      <span className="badge bg-warning">Medium</span>
                    )}
                    {signal.aggressiveness === 'high' && (
                      <span className="badge bg-danger">High</span>
                    )}
                    {signal.aggressiveness === 'aggressive' && (
                      <span className="badge bg-danger">Aggressive</span>
                    )}
                    {signal.aggressiveness === 'conservative' && (
                      <span className="badge bg-info">Conservative</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <div className="card-footer d-flex justify-content-between">
        {status === 'monitoring' && (
          <button className="btn btn-success">
            <i className="bi bi-play-fill"></i> Trade
          </button>
        )}
        
        {status === 'inTrade' && (
          <button className="btn btn-danger">
            <i className="bi bi-x-lg"></i> Close Trade
          </button>
        )}
        
        {status === 'closed' && (
          <button className="btn btn-primary">
            <i className="bi bi-arrow-repeat"></i> Reactivate
          </button>
        )}
        
        <button className="btn btn-outline-secondary">
          <i className="bi bi-gear-fill"></i>
        </button>
      </div>
    </div>
  );
};

export default ChartCard;