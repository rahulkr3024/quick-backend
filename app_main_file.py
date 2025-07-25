#!/usr/bin/env python3
"""
Main application entry point for Quicky AI Summarizer
This file serves as an alias to quicky_backend.py for easier deployment
"""

from quicky_backend import app, db, create_tables
import os

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        create_tables()
    
    # Get port from environment (for deployment)
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('ENV') == 'development'
    
    # Run the application
    app.run(debug=debug, host='0.0.0.0', port=port)