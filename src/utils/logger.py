"""
Centralized logging configuration with comprehensive monitoring

Features:
- Colored console output for better readability
- Rotating file handlers (by time and size)
- Structured logging with request tracking
- Performance metrics logging
- Separate error log file
- JSON format for log aggregation tools
"""
import logging
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from contextvars import ContextVar

from src.config import get_settings

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m\033[1m',   # Magenta + Bold
        'RESET': '\033[0m'        # Reset
    }
    
    EMOJI = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }
    
    def format(self, record):
        # Add emoji and request_id
        levelname = record.levelname
        emoji = self.EMOJI.get(levelname, '📝')
        
        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            record.request_id = f" [{request_id[:8]}]"
        else:
            record.request_id = ""
        
        # Add color to level name
        if levelname in self.COLORS:
            record.levelname = f"{emoji} {self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        
        return formatted


class JSONFormatter(logging.Formatter):
    """Formatter for structured JSON logs (for log aggregation tools)"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None,
    log_dir: str = "logs",
    enable_json: bool = False
) -> logging.Logger:
    """
    Setup a comprehensive logger with multiple handlers
    
    Args:
        name: Logger name (usually __name__)
        log_file: Log file name (optional, auto-generated if None)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        enable_json: Enable JSON formatted logs
        
    Returns:
        Configured logger instance
        
    Features:
        - Colored console output with emojis
        - Rotating file logs (daily, keep 30 days)
        - Separate error log file
        - Optional JSON logs for monitoring tools
        - Request ID tracking
        - Performance metrics
    """
    settings = get_settings()
    
    # Get log level
    if level is None:
        level = settings.log_level
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Console handler with colors and emojis
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    console_formatter = ColoredFormatter(
        '%(asctime)s %(levelname)s%(request_id)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 2. Main file handler (rotating daily)
    if log_file is None:
        # Auto-generate log file name based on component
        component = name.split('.')[-1]
        log_file = f"{component}.log"
    
    main_file_handler = TimedRotatingFileHandler(
        filename=log_path / log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    main_file_handler.setLevel(logging.DEBUG)  # File logs everything
    main_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    main_file_handler.setFormatter(main_file_formatter)
    logger.addHandler(main_file_handler)
    
    # 3. Error file handler (only ERROR and above)
    error_file_handler = RotatingFileHandler(
        filename=log_path / 'errors.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d\n'
        '%(message)s\n'
        '%(pathname)s\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_file_handler.setFormatter(error_file_formatter)
    logger.addHandler(error_file_handler)
    
    # 4. JSON file handler (for log aggregation tools like ELK, Splunk)
    if enable_json:
        json_file_handler = TimedRotatingFileHandler(
            filename=log_path / 'app.json.log',
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        json_file_handler.setLevel(logging.INFO)
        json_file_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_file_handler)
    
    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get or create a logger
    
    Args:
        name: Logger name (usually __name__)
        **kwargs: Additional arguments for setup_logger
        
    Returns:
        Logger instance
    """
    return setup_logger(name, **kwargs)


class LoggerContext:
    """Context manager for request tracking and performance logging"""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        
        # Log operation start
        context_str = ', '.join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"🚀 START {self.operation} | {context_str}")
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        
        if exc_type is None:
            # Success
            self.logger.info(f"✅ DONE {self.operation} | took {elapsed:.2f}s")
        else:
            # Error
            self.logger.error(f"❌ FAILED {self.operation} | took {elapsed:.2f}s | {exc_val}")
        
        return False  # Don't suppress exceptions


def log_performance(logger: logging.Logger, operation: str, **kwargs):
    """
    Decorator for logging function performance
    
    Usage:
        @log_performance(logger, "create_kb")
        def create_knowledge_base(kb_name: str):
            ...
    """
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            with LoggerContext(logger, operation, **kwargs):
                return func(*args, **func_kwargs)
        return wrapper
    return decorator


def set_request_id(request_id: str):
    """Set request ID for current context (for tracking requests)"""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_var.get()


def clear_request_id():
    """Clear request ID"""
    request_id_var.set(None)


# Module-level logger
logger = get_logger(__name__)
