/**
 * Ticker Charts Module
 * 
 * This module provides functions to create and update candlestick charts
 * with price level annotations for trading setups.
 */

// Create a candlestick chart with price levels for a ticker
function createTickerChart(containerId, tickerData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Extract ticker data
    const ticker = tickerData.symbol;
    const priceLevels = tickerData.price_levels;
    
    // Create a placeholder until we get real market data
    container.innerHTML = `
        <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">${ticker} Price Chart</h5>
                <div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="refreshChart('${ticker}')">
                        <i class="bi bi-arrow-clockwise"></i>
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div id="chart-${ticker}" style="height: 400px;">
                    <div class="d-flex justify-content-center align-items-center h-100">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading chart data...</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-footer">
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-muted">Rejection: ${formatPrice(priceLevels.rejection)}</small>
                    </div>
                    <div class="col-md-6 text-end">
                        <small class="text-muted">Bounce: ${formatPrice(priceLevels.bounce)}</small>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Fetch market data for the ticker
    fetchMarketData(ticker)
        .then(data => {
            if (data && data.candles && data.candles.length > 0) {
                renderCandlestickChart(ticker, data.candles, priceLevels);
            } else {
                document.getElementById(`chart-${ticker}`).innerHTML = `
                    <div class="alert alert-warning h-100 d-flex align-items-center justify-content-center">
                        <div class="text-center">
                            <p><i class="bi bi-exclamation-triangle fs-3"></i></p>
                            <p>No market data available for ${ticker}.</p>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error(`Error fetching market data for ${ticker}:`, error);
            document.getElementById(`chart-${ticker}`).innerHTML = `
                <div class="alert alert-danger h-100 d-flex align-items-center justify-content-center">
                    <div class="text-center">
                        <p><i class="bi bi-x-circle fs-3"></i></p>
                        <p>Error loading market data for ${ticker}.</p>
                        <button class="btn btn-sm btn-outline-danger" onclick="refreshChart('${ticker}')">
                            Try Again
                        </button>
                    </div>
                </div>
            `;
        });
}

// Fetch market data from the API
async function fetchMarketData(ticker) {
    try {
        const response = await fetch(`/api/candles/${ticker}?timeframe=5Min&limit=78`); // Last ~6.5 hours (trading day)
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching market data:", error);
        throw error;
    }
}

// Render the candlestick chart with price levels
function renderCandlestickChart(ticker, candles, priceLevels) {
    const chartElement = document.getElementById(`chart-${ticker}`);
    if (!chartElement) return;
    
    // Prepare data for the candlestick chart
    const data = [];
    
    // Add candlestick trace
    const times = candles.map(candle => new Date(candle.t));
    const opens = candles.map(candle => candle.o);
    const highs = candles.map(candle => candle.h);
    const lows = candles.map(candle => candle.l);
    const closes = candles.map(candle => candle.c);
    
    data.push({
        x: times,
        open: opens,
        high: highs,
        low: lows,
        close: closes,
        type: 'candlestick',
        name: ticker,
        increasing: {line: {color: '#26a69a'}, fillcolor: '#26a69a'},
        decreasing: {line: {color: '#ef5350'}, fillcolor: '#ef5350'}
    });
    
    // Add price level lines
    addPriceLevelLine(data, times, priceLevels.rejection, 'Rejection', '#ff9800');
    addPriceLevelLine(data, times, priceLevels.aggressive_breakdown, 'Aggressive Breakdown', '#e53935');
    addPriceLevelLine(data, times, priceLevels.conservative_breakdown, 'Conservative Breakdown', '#c62828');
    addPriceLevelLine(data, times, priceLevels.aggressive_breakout, 'Aggressive Breakout', '#43a047');
    addPriceLevelLine(data, times, priceLevels.conservative_breakout, 'Conservative Breakout', '#2e7d32');
    addPriceLevelLine(data, times, priceLevels.bounce, 'Bounce', '#29b6f6');
    
    // Layout configuration
    const layout = {
        title: `${ticker} - 5-Minute Candles`,
        height: 400,
        margin: {l: 50, r: 20, t: 40, b: 40},
        xaxis: {
            rangeslider: {visible: false},
            type: 'date',
            title: 'Time'
        },
        yaxis: {
            title: 'Price ($)',
            autorange: true,
            side: 'right'
        },
        legend: {
            orientation: 'h',
            y: -0.2
        },
        template: 'plotly_dark',
        dragmode: 'zoom',
        showlegend: true
    };
    
    // Config options
    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        modeBarButtonsToAdd: [
            {
                name: 'Toggle Price Levels',
                icon: Plotly.Icons.drawrect,
                click: function(gd) {
                    const newVisibility = !gd._fullLayout.showlegend;
                    Plotly.relayout(gd, {'showlegend': newVisibility});
                }
            }
        ]
    };
    
    // Create the chart
    Plotly.newPlot(`chart-${ticker}`, data, layout, config);
    
    // Add mouseover events to show precise price values
    chartElement.on('plotly_hover', function(data) {
        const pointIndex = data.points[0].pointNumber;
        const xValue = data.points[0].x;
        const close = data.points[0].close;
        
        // Format time
        const time = new Date(xValue).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Show tooltip
        document.getElementById(`${ticker}-tooltip`).innerHTML = `
            Time: ${time} | Price: $${close.toFixed(2)}
        `;
    });
}

// Helper function to add price level lines
function addPriceLevelLine(data, times, price, name, color) {
    if (price !== null && price !== undefined) {
        data.push({
            x: times,
            y: Array(times.length).fill(price),
            type: 'scatter',
            mode: 'lines',
            name: name,
            line: {
                color: color,
                width: 2,
                dash: 'dash'
            }
        });
    }
}

// Format price for display
function formatPrice(price) {
    return price !== null && price !== undefined ? `$${price.toFixed(2)}` : 'N/A';
}

// Refresh chart data
function refreshChart(ticker) {
    document.getElementById(`chart-${ticker}`).innerHTML = `
        <div class="d-flex justify-content-center align-items-center h-100">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Refreshing chart data...</span>
            </div>
        </div>
    `;
    
    // Re-fetch market data
    fetchMarketData(ticker)
        .then(data => {
            if (data && data.candles && data.candles.length > 0) {
                // Get the price levels from the page data
                const priceLevelElements = document.querySelectorAll(`[data-ticker="${ticker}"]`);
                const priceLevels = {};
                
                priceLevelElements.forEach(element => {
                    const levelType = element.dataset.levelType;
                    const price = parseFloat(element.dataset.price);
                    priceLevels[levelType] = price;
                });
                
                renderCandlestickChart(ticker, data.candles, priceLevels);
            } else {
                document.getElementById(`chart-${ticker}`).innerHTML = `
                    <div class="alert alert-warning h-100 d-flex align-items-center justify-content-center">
                        <div class="text-center">
                            <p><i class="bi bi-exclamation-triangle fs-3"></i></p>
                            <p>No market data available for ${ticker}.</p>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error(`Error refreshing market data for ${ticker}:`, error);
            document.getElementById(`chart-${ticker}`).innerHTML = `
                <div class="alert alert-danger h-100 d-flex align-items-center justify-content-center">
                    <div class="text-center">
                        <p><i class="bi bi-x-circle fs-3"></i></p>
                        <p>Error refreshing market data for ${ticker}.</p>
                        <button class="btn btn-sm btn-outline-danger" onclick="refreshChart('${ticker}')">
                            Try Again
                        </button>
                    </div>
                </div>
            `;
        });
}