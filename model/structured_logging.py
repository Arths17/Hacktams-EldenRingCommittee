"""
Structured JSON logging for HealthOS API.
Provides request tracing, performance tracking, and audit logging.
"""

import os
import json
import time
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Structured JSON logger with request context."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.request_context: Dict[str, Any] = {}
    
    def set_request_context(self, request_id: str, username: Optional[str] = None, 
                           endpoint: Optional[str] = None, method: Optional[str] = None):
        """Set request context for tracing.
        
        Args:
            request_id: Unique request identifier
            username: Authenticated username (if applicable)
            endpoint: API endpoint being called
            method: HTTP method
        """
        self.request_context = {
            "request_id": request_id,
            "username": username,
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def clear_context(self):
        """Clear request context."""
        self.request_context = {}
    
    def log(self, level: str, message: str, **kwargs):
        """Log message with structured context.
        
        Args:
            level: Log level ('debug', 'info', 'warning', 'error', 'critical')
            message: Log message
            **kwargs: Additional fields to include in JSON
        """
        log_data = {
            "message": message,
            **self.request_context,
            **kwargs,
        }
        
        getattr(self.logger, level)(json.dumps(log_data))
    
    def debug(self, message: str, **kwargs):
        self.log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log("warning", message, **kwargs)
    
    def error(self, message: str, exc_info: Optional[str] = None, **kwargs):
        self.log("error", message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log("critical", message, **kwargs)
    
    def log_request(self, method: str, endpoint: str, username: Optional[str] = None):
        """Log incoming request."""
        request_id = str(uuid.uuid4())
        self.set_request_context(request_id, username, endpoint, method)
        self.info(f"{method} {endpoint} received", request_id=request_id)
        return request_id
    
    def log_response(self, status_code: int, response_time_ms: float, error: Optional[str] = None):
        """Log outgoing response."""
        log_data = {
            "status_code": status_code,
            "response_time_ms": round(response_time_ms, 2),
        }
        
        if error:
            log_data["error"] = error
            self.error(f"Request failed with status {status_code}", **log_data)
        else:
            self.info(f"Request completed with status {status_code}", **log_data)
    
    def log_database_query(self, table: str, operation: str, rows_affected: int, 
                          query_time_ms: float, error: Optional[str] = None):
        """Log database operation."""
        log_data = {
            "table": table,
            "operation": operation,
            "rows_affected": rows_affected,
            "query_time_ms": round(query_time_ms, 2),
        }
        
        if error:
            log_data["error"] = error
            self.error(f"Database error: {operation} on {table}", **log_data)
        else:
            self.debug(f"Database {operation} on {table}", **log_data)
    
    def log_auth_attempt(self, username: str, success: bool, ip_address: Optional[str] = None):
        """Log authentication attempt."""
        self.info(
            f"Auth attempt for {username}: {'success' if success else 'failed'}",
            username=username,
            success=success,
            ip_address=ip_address,
        )
    
    def log_rate_limit_exceeded(self, endpoint: str, username: Optional[str] = None):
        """Log rate limit exceeded event."""
        self.warning(
            f"Rate limit exceeded on {endpoint}",
            endpoint=endpoint,
            username=username,
        )
    
    def log_feedback_processed(self, username: str, feedback_type: str, confidence: float):
        """Log feedback processing."""
        self.info(
            f"Feedback processed: {feedback_type}",
            username=username,
            feedback_type=feedback_type,
            confidence=round(confidence, 3),
        )


def setup_json_logging(log_file: Optional[str] = None):
    """Setup JSON logging to file and console.
    
    Args:
        log_file: Optional file path for JSON logs
    """
    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # JSON formatter
    json_formatter = jsonlogger.JsonFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"JSON logging initialized to {log_file}")


# Global structured logger instance
logger = StructuredLogger("healthos")
