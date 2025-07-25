#!/usr/bin/env python3
"""
WSGI entry point for Quicky AI Summarizer
"""

import os
from quicky_backend import app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)