"""
Application configuration and settings management.
Loads environment variables and provides centralized config access.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Cricket Auction Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_URL: str = "mongodb://localhost:27017"  # Fallback
    DB_NAME: str = "cricket_auction"
    
    # JWT - Strict expiration for maximum security
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short expiration - 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1  # 1 day only
    
    # Admin
    ADMIN_EMAILS: str = "admin@example.com"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # Auction
    BID_INCREMENT: int = 50
    AUCTION_TIMER_SECONDS: int = 30
    MAX_CONCURRENT_CONNECTIONS: int = 1000
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 5242880  # 5MB
    UPLOAD_DIR: str = "./uploads"
    
    # Cloudinary (Image Storage)
    CLOUDINARY_CLOUD_NAME: str = "your_cloud_name"
    CLOUDINARY_API_KEY: str = "your_api_key"
    CLOUDINARY_API_SECRET: str = "your_api_secret"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Security Enhancements
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_CSRF_PROTECTION: bool = False  # Disable for API-only, enable for web forms
    ENABLE_IP_WHITELIST: bool = False
    ADMIN_IP_WHITELIST: str = ""  # Comma-separated IPs
    
    # WebSocket Settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_MESSAGE_COMPRESSION: bool = True
    WS_MAX_CONNECTIONS: int = 1000
    
    # Performance
    ENABLE_RESPONSE_COMPRESSION: bool = True
    CACHE_TTL: int = 300  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def admin_email_list(self) -> List[str]:
        """Parse admin emails into a list."""
        return [email.strip().lower() for email in self.ADMIN_EMAILS.split(",") if email.strip()]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @property
    def admin_ip_whitelist_list(self) -> List[str]:
        """Parse admin IP whitelist into a list."""
        if not self.ADMIN_IP_WHITELIST:
            return []
        return [ip.strip() for ip in self.ADMIN_IP_WHITELIST.split(",") if ip.strip()]


# Global settings instance
settings = Settings()
