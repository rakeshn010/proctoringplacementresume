"""
Database session management.
Handles MongoDB connection and provides database instance.
"""
from pymongo import MongoClient
from core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Get MongoDB URL from environment with fallback
MONGODB_URL = os.getenv("MONGODB_URL", os.getenv("DATABASE_URL", "mongodb://localhost:27017"))

try:
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    db = client[settings.DB_NAME]
    
    # Test connection
    client.server_info()
    logger.info(f"Connected to MongoDB: {settings.DB_NAME}")
    
except Exception as e:
    logger.warning(f"MongoDB connection failed: {e}")
    logger.warning("App will start but database operations will fail until MongoDB is configured")
    # Create dummy client for now - will fail on actual operations
    client = None
    db = None
