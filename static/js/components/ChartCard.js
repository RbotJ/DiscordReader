import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
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
const ChartCard = ({ ticker, status = 'monitoring', signal = null, onEvent }) => {
  const chartContainerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const triggerLineRef = useRef(null);
  const targetLinesRef = useRef([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [cardStatus, setCardStatus] = useState(status);
  
  // Status colors
  const statusColors = {
    monitoring: {
      headerClass: 'bg-secondary',
      headerText: 'Monitoring',
      borderClass: 'border-secondary'
    },
    inTrade: {
      headerClass: 'bg-primary',
      headerText: 'In Trade',
      borderClass: 'border-primary'
    },
    closed: {
      headerClass: 'bg-success',
      headerText: 'Closed',
      borderClass: 'border-success'
    }
  };
  
  // Update card status when status prop changes
  useEffect(() => {
    setCardStatus(status);
  }, [status]);
  
  // Clean up chart on unmount
  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
      }
    };
  }, []);
  
  // Initialize chart when component mounts or ticker changes
  useEffect(() => {
    if (!ticker) return;
    
    const initializeChart = async () => {
      try {
        setLoading(true);
        
        // Fetch candle data for the ticker
        const candles = await apiService.getCandles(ticker);
        
        // Create chart instance
        if (!chartInstanceRef.current && chartContainerRef.current) {
          // Create chart
          const chart = createChart(chartContainerRef.current, {
            layout: {
              background: { color: '#1e222d' },
              textColor: '#d1d4dc',
            },
            grid: {
              vertLines: { color: '#2e3241' },
              horzLines: { color: '#2e3241' },
            },
            width: chartContainerRef.current.clientWidth,
            height: 300,
            timeScale: {
              timeVisible: true,
              secondsVisible: false,
            },
          });
          
          // Handle chart resizing
          const handleResize = () => {
            if (chartContainerRef.current && chart) {
              chart.applyOptions({
                width: chartContainerRef.current.clientWidth
              });
            }
          };
          
          window.addEventListener('resize', handleResize);
          
          // Create candlestick series
          const candleSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
          });
          
          chartInstanceRef.current = chart;
          candleSeriesRef.current = candleSeries;
          
          // Set up a cleanup function to remove event listener
          return () => {
            window.removeEventListener('resize', handleResize);
          };
        }
        
        // Update candle data
        if (candleSeriesRef.current && candles && candles.length > 0) {
          const formattedCandles = candles.map(candle => ({
            time: candle.time,
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close
          }));
          
          candleSeriesRef.current.setData(formattedCandles);
          
          // Update current price
          if (formattedCandles.length > 0) {
            const latestCandle = formattedCandles[formattedCandles.length - 1];
            setCurrentPrice(latestCandle.close);
          }
        }
        
        // If we have signal data, add trigger and target lines
        if (signal && candleSeriesRef.current) {
          // Add trigger price line
          if (signal.trigger && signal.trigger.price) {
            const triggerPrice = parseFloat(signal.trigger.price);
            
            if (!triggerLineRef.current) {
              const triggerLine = candleSeriesRef.current.createPriceLine({
                price: triggerPrice,
                color: '#ff9800',
                lineWidth: 2,
                lineStyle: 2, // dashed
                axisLabelVisible: true,
                title: 'Trigger',
              });
              
              triggerLineRef.current = triggerLine;
            } else {
              triggerLineRef.current.applyOptions({
                price: triggerPrice
              });
            }
          }
          
          // Add target price lines
          if (signal.targets && Array.isArray(signal.targets) && signal.targets.length > 0) {
            // Remove existing target lines
            targetLinesRef.current.forEach(line => {
              if (line && candleSeriesRef.current) {
                candleSeriesRef.current.removePriceLine(line);
              }
            });
            
            targetLinesRef.current = [];
            
            // Add new target lines
            signal.targets.forEach((target, index) => {
              if (target && target.price) {
                const targetPrice = parseFloat(target.price);
                
                const targetLine = candleSeriesRef.current.createPriceLine({
                  price: targetPrice,
                  color: '#4caf50',
                  lineWidth: 2,
                  lineStyle: 1, // solid
                  axisLabelVisible: true,
                  title: `Target ${index + 1}`,
                });
                
                targetLinesRef.current.push(targetLine);
              }
            });
          }
        }
        
        // Log event
        if (onEvent) {
          onEvent({
            type: 'info',
            message: `Chart for ${ticker} loaded`,
            timestamp: new Date().toISOString(),
          });
        }
        
        setError(null);
      } catch (err) {
        console.error('Error loading chart data:', err);
        setError(`Failed to load chart for ${ticker}`);
        
        // Log error event
        if (onEvent) {
          onEvent({
            type: 'error',
            message: `Failed to load chart for ${ticker}`,
            data: err.message,
            timestamp: new Date().toISOString(),
          });
        }
      } finally {
        setLoading(false);
      }
    };
    
    initializeChart();
  }, [ticker, signal]);
  
  // Handle button actions
  const handleAction = (action) => {
    switch (action) {
      case 'enter':
        setCardStatus('inTrade');
        // Log event
        if (onEvent) {
          onEvent({
            type: 'trade',
            message: `Entered trade for ${ticker}`,
            timestamp: new Date().toISOString(),
          });
        }
        break;
      case 'exit':
        setCardStatus('closed');
        // Log event
        if (onEvent) {
          onEvent({
            type: 'trade',
            message: `Exited trade for ${ticker}`,
            timestamp: new Date().toISOString(),
          });
        }
        break;
      case 'reset':
        setCardStatus('monitoring');
        // Log event
        if (onEvent) {
          onEvent({
            type: 'info',
            message: `Reset status for ${ticker}`,
            timestamp: new Date().toISOString(),
          });
        }
        break;
      default:
        break;
    }
  };
  
  // Get action buttons based on current status
  const getActionButtons = () => {
    switch (cardStatus) {
      case 'monitoring':
        return (
          <button 
            className="btn btn-sm btn-success"
            onClick={() => handleAction('enter')}
          >
            Enter Trade
          </button>
        );
      case 'inTrade':
        return (
          <button 
            className="btn btn-sm btn-warning"
            onClick={() => handleAction('exit')}
          >
            Exit Trade
          </button>
        );
      case 'closed':
        return (
          <button 
            className="btn btn-sm btn-secondary"
            onClick={() => handleAction('reset')}
          >
            Reset
          </button>
        );
      default:
        return null;
    }
  };
  
  return (
    <div className={`card mb-4 ${statusColors[cardStatus]?.borderClass || 'border-secondary'}`}>
      <div className={`card-header ${statusColors[cardStatus]?.headerClass || 'bg-secondary'} text-white d-flex justify-content-between align-items-center`}>
        <div>
          <h5 className="mb-0">{ticker}</h5>
          <span className="badge bg-light text-dark ms-2">
            {statusColors[cardStatus]?.headerText || 'Monitoring'}
          </span>
        </div>
        {!loading && currentPrice && (
          <h5 className="mb-0">${currentPrice.toFixed(2)}</h5>
        )}
      </div>
      <div className="card-body p-0">
        {loading ? (
          <div className="d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : error ? (
          <div className="alert alert-danger m-3">
            {error}
          </div>
        ) : (
          <div 
            ref={chartContainerRef} 
            className="chart-container"
          />
        )}
      </div>
      <div className="card-footer d-flex justify-content-between align-items-center">
        <div>
          {signal && (
            <small className="text-muted">
              {signal.category} {signal.aggressiveness} | Trigger: ${signal.trigger?.price}
            </small>
          )}
        </div>
        <div>
          {getActionButtons()}
        </div>
      </div>
    </div>
  );
};

export default ChartCard;