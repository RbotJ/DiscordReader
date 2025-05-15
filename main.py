import os
import logging
from app import app
from common.utils import setup_redis_connection

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialize Redis connection
    setup_redis_connection()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
