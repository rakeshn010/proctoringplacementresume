"""
Log Sanitizer - Automatic PII Redaction
Removes sensitive information from logs to comply with privacy regulations.
"""
import re
import logging
from typing import Any


class LogSanitizer:
    """
    Sanitizes logs by removing Personally Identifiable Information (PII).
    Prevents accidental logging of sensitive data.
    """
    
    # PII patterns to detect and redact
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?91[-.\s]?)?[6-9]\d{9}\b',  # Indian phone numbers
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'password': r'(?i)password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)',
        'token': r'(?i)(?:bearer|token|jwt|api[_-]?key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{20,})',
        'secret': r'(?i)(?:secret|private[_-]?key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{20,})',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'mongodb_id': r'\b[0-9a-fA-F]{24}\b',  # MongoDB ObjectId
    }
    
    @staticmethod
    def sanitize(message: str) -> str:
        """
        Remove PII from log messages.
        
        Args:
            message: Original log message
        
        Returns:
            Sanitized message with PII redacted
        """
        if not isinstance(message, str):
            message = str(message)
        
        sanitized = message
        
        for pii_type, pattern in LogSanitizer.PII_PATTERNS.items():
            # Replace with redacted placeholder
            sanitized = re.sub(
                pattern,
                f'[REDACTED_{pii_type.upper()}]',
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
        
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            # Check if key itself is sensitive
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in ['password', 'token', 'secret', 'key', 'auth']):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = LogSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    LogSanitizer.sanitize_dict(item) if isinstance(item, dict)
                    else LogSanitizer.sanitize(str(item))
                    for item in value
                ]
            elif isinstance(value, str):
                sanitized[key] = LogSanitizer.sanitize(value)
            else:
                sanitized[key] = value
        
        return sanitized


class SanitizedFormatter(logging.Formatter):
    """
    Custom logging formatter that sanitizes PII before logging.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII sanitization."""
        # Sanitize the message
        if isinstance(record.msg, str):
            record.msg = LogSanitizer.sanitize(record.msg)
        
        # Sanitize args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = LogSanitizer.sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    LogSanitizer.sanitize(str(arg)) for arg in record.args
                )
        
        return super().format(record)


def setup_sanitized_logging():
    """
    Setup logging with PII sanitization.
    Call this during application startup.
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Create sanitized formatter
    formatter = SanitizedFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Update all handlers
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    
    logging.info("✅ PII sanitization enabled for all logs")


# Example usage
if __name__ == "__main__":
    # Test sanitization
    test_messages = [
        "User email: john.doe@example.com logged in",
        "Password: MySecret123 was changed",
        "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
        "Credit card: 4532-1234-5678-9010 was charged",
        "Phone: +91-9876543210 verified",
        "IP address 192.168.1.100 blocked"
    ]
    
    print("Testing PII Sanitization:\n")
    for msg in test_messages:
        sanitized = LogSanitizer.sanitize(msg)
        print(f"Original:  {msg}")
        print(f"Sanitized: {sanitized}\n")
