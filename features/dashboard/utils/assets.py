"""
Asset Management Utilities

This module provides functions for managing assets like images and SVGs.
"""
import os
import logging
import cairosvg

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_svg_to_png(svg_path, png_path, width=100, height=100):
    """
    Convert SVG file to PNG format.
    
    Args:
        svg_path: Path to the SVG file
        png_path: Path where the PNG should be saved
        width: Output width in pixels
        height: Output height in pixels
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cairosvg.svg2png(
            url=svg_path, 
            write_to=png_path, 
            output_width=width, 
            output_height=height
        )
        logger.info(f"Successfully converted {svg_path} to {png_path}")
        return True
    except Exception as e:
        logger.error(f"Error converting SVG to PNG: {e}")
        return False

def convert_logo():
    """Convert the application logo from SVG to PNG."""
    return convert_svg_to_png("static/logo.svg", "static/logo.png")

if __name__ == "__main__":
    # Convert logo when script is run directly
    if convert_logo():
        print("Logo converted successfully!")
    else:
        print("Failed to convert logo.")