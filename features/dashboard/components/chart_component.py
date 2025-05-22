"""
Chart Component

This module provides reusable charting components for the dashboard feature.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple


def create_candlestick_chart(
    symbol: str, 
    data: pd.DataFrame, 
    signals: Optional[List[Dict[str, Any]]] = None,
    height: int = 400
) -> go.Figure:
    """
    Create a candlestick chart for a given ticker symbol.
    
    Args:
        symbol: Ticker symbol
        data: DataFrame with OHLC price data
        signals: Optional list of signal dictionaries
        height: Chart height in pixels
        
    Returns:
        Plotly figure object
    """
    if data is None or len(data) == 0:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title=f"{symbol} - No Data Available",
            height=height
        )
        return fig
    
    # Create a subplot with 2 rows (price & volume)
    fig = make_subplots(
        rows=2, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2]
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=data['timestamp'] if 'timestamp' in data.columns else data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name=symbol
        ),
        row=1, col=1
    )
    
    # Add volume bar chart
    if 'volume' in data.columns:
        fig.add_trace(
            go.Bar(
                x=data['timestamp'] if 'timestamp' in data.columns else data.index,
                y=data['volume'],
                name='Volume',
                marker=dict(color='rgba(100, 100, 255, 0.5)')
            ),
            row=2, col=1
        )
    
    # Add signals as horizontal lines if provided
    if signals:
        for signal in signals:
            if 'trigger' in signal and 'price' in signal['trigger']:
                fig.add_hline(
                    y=signal['trigger']['price'],
                    line_width=1, 
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"{signal.get('category', 'Signal')} ({signal['trigger']['price']})",
                    row=1, col=1
                )
    
    # Update layout
    fig.update_layout(
        title=f"{symbol} Price Chart",
        xaxis_title='Time',
        yaxis_title='Price ($)',
        xaxis_rangeslider_visible=False,
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    # Style adjustments
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def create_performance_chart(
    data: pd.DataFrame,
    value_column: str = 'return',
    title: str = 'Performance Chart', 
    height: int = 300
) -> go.Figure:
    """
    Create a performance chart.
    
    Args:
        data: DataFrame with performance data
        value_column: Column containing values to plot
        title: Chart title
        height: Chart height in pixels
        
    Returns:
        Plotly figure object
    """
    if data is None or len(data) == 0:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title=f"{title} - No Data Available",
            height=height
        )
        return fig
    
    # Create the figure
    fig = go.Figure()
    
    # Add line trace
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data[value_column],
            mode='lines',
            name=value_column.capitalize(),
            line=dict(color='rgb(49, 130, 189)')
        )
    )
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title=value_column.capitalize(),
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    # Style adjustments
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444')
    )
    
    return fig


def display_chart(
    chart_func, 
    chart_args: Dict[str, Any], 
    key: Optional[str] = None
) -> None:
    """
    Display a chart in the Streamlit app with caching.
    
    Args:
        chart_func: Function to create the chart
        chart_args: Dictionary of arguments to pass to the chart function
        key: Optional key for the st.plotly_chart function
    """
    # Create and display the chart
    fig = chart_func(**chart_args)
    st.plotly_chart(fig, use_container_width=True, key=key)


def create_multi_ticker_chart(
    data_dict: Dict[str, pd.DataFrame],
    chart_title: str = 'Multi-Ticker Comparison',
    height: int = 500
) -> go.Figure:
    """
    Create a chart comparing multiple tickers.
    
    Args:
        data_dict: Dictionary mapping ticker symbols to DataFrames
        chart_title: Chart title
        height: Chart height in pixels
        
    Returns:
        Plotly figure object
    """
    if not data_dict:
        # Create an empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title=f"{chart_title} - No Data Available",
            height=height
        )
        return fig
    
    # Create the figure
    fig = go.Figure()
    
    # Add a line for each ticker
    for ticker, df in data_dict.items():
        if df is None or len(df) == 0:
            continue
            
        # Normalize to percentage change from first value
        if 'close' in df.columns:
            values = df['close'].values
            if len(values) > 0:
                first_value = values[0]
                normalized = [(v / first_value - 1) * 100 for v in values]
                
                fig.add_trace(
                    go.Scatter(
                        x=df['timestamp'] if 'timestamp' in df.columns else df.index,
                        y=normalized,
                        mode='lines',
                        name=ticker
                    )
                )
    
    # Update layout
    fig.update_layout(
        title=chart_title,
        xaxis_title='Time',
        yaxis_title='Percent Change (%)',
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    
    # Style adjustments
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#444'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig