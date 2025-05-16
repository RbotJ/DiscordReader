"""
Database Module

This module provides a centralized SQLAlchemy database instance for the entire application.
"""
from flask_sqlalchemy import SQLAlchemy

# Create a single SQLAlchemy instance to be used across the application
db = SQLAlchemy()