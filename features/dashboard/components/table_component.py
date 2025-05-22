"""
Table Component

This module provides reusable table components for the dashboard feature.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Callable


def create_data_table(
    data: pd.DataFrame,
    title: Optional[str] = None,
    formatting: Optional[Dict[str, Callable]] = None,
    column_config: Optional[Dict[str, Dict[str, Any]]] = None,
    use_pagination: bool = True,
    page_size: int = 10
) -> None:
    """
    Create and display a data table.
    
    Args:
        data: DataFrame with the data to display
        title: Optional title for the table
        formatting: Optional dictionary mapping column names to formatting functions
        column_config: Optional dictionary of column configuration for st.dataframe
        use_pagination: Whether to use pagination for large tables
        page_size: Number of rows per page when pagination is enabled
    """
    if title:
        st.subheader(title)
    
    if data is None or len(data) == 0:
        st.info("No data available")
        return
    
    # Apply formatting if provided
    if formatting:
        df_display = data.copy()
        for col, format_func in formatting.items():
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(format_func)
    else:
        df_display = data
    
    # Implement pagination for large tables if requested
    if use_pagination and len(df_display) > page_size:
        # Calculate number of pages
        num_pages = (len(df_display) + page_size - 1) // page_size
        
        # Add page selector
        page = st.selectbox(
            "Page",
            options=range(1, num_pages + 1),
            format_func=lambda x: f"Page {x} of {num_pages}"
        )
        
        # Display the current page
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(df_display))
        
        # Show page info
        st.caption(f"Showing rows {start_idx + 1} to {end_idx} of {len(df_display)}")
        
        # Display the data for current page
        if column_config:
            st.dataframe(
                df_display.iloc[start_idx:end_idx],
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.dataframe(
                df_display.iloc[start_idx:end_idx],
                hide_index=True,
                use_container_width=True
            )
    else:
        # Display all data without pagination
        if column_config:
            st.dataframe(
                df_display,
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.dataframe(
                df_display,
                hide_index=True,
                use_container_width=True
            )


def create_metrics_row(metrics: List[Dict[str, Any]]) -> None:
    """
    Create and display a row of metric cards.
    
    Args:
        metrics: List of dictionaries with keys 'label', 'value', and optional 'delta'
    """
    if not metrics:
        return
    
    # Split into columns based on number of metrics
    cols = st.columns(len(metrics))
    
    # Display each metric in its column
    for i, metric in enumerate(metrics):
        if 'delta' in metric:
            cols[i].metric(
                label=metric['label'],
                value=metric['value'],
                delta=metric['delta']
            )
        else:
            cols[i].metric(
                label=metric['label'],
                value=metric['value']
            )


def create_expandable_table(
    data: pd.DataFrame,
    title: str,
    key: str,
    expanded: bool = False,
    formatting: Optional[Dict[str, Callable]] = None
) -> None:
    """
    Create and display an expandable table.
    
    Args:
        data: DataFrame with the data to display
        title: Title for the expandable section
        key: Unique key for the expander
        expanded: Whether the expander should be initially expanded
        formatting: Optional dictionary mapping column names to formatting functions
    """
    with st.expander(title, expanded=expanded):
        if data is None or len(data) == 0:
            st.info("No data available")
            return
        
        # Apply formatting if provided
        if formatting:
            df_display = data.copy()
            for col, format_func in formatting.items():
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(format_func)
        else:
            df_display = data
        
        # Display the data
        st.dataframe(
            df_display,
            hide_index=True,
            use_container_width=True
        )


def create_stats_table(stats: Dict[str, Any], title: Optional[str] = None) -> None:
    """
    Create and display a key-value statistics table.
    
    Args:
        stats: Dictionary of statistics to display
        title: Optional title for the statistics section
    """
    if title:
        st.subheader(title)
    
    if not stats:
        st.info("No statistics available")
        return
    
    # Convert to DataFrame for display
    stats_df = pd.DataFrame([
        {"Statistic": k, "Value": v}
        for k, v in stats.items()
    ])
    
    # Display the statistics
    st.dataframe(
        stats_df,
        hide_index=True,
        use_container_width=True
    )