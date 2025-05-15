"""
Script to convert SVG logo to PNG
"""
import cairosvg

# Convert SVG to PNG
cairosvg.svg2png(url="static/logo.svg", write_to="static/logo.png", output_width=100, output_height=100)
print("Logo converted successfully!")