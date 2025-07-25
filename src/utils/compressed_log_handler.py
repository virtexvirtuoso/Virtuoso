"""
Compressed rotating log handler with intelligent filtering
"""
import gzip
import os
import logging
import time
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from datetime import datetime, timedelta


class IntelligentFilter(logging.Filter):
    """Filter to reduce repetitive log messages"""
    
    def __init__(self):
        super().__init__()
        self.message_counts = defaultdict(int)
        self.last_seen = defaultdict(float)
        self.suppressed_count = defaultdict(int)
        
        # Patterns to suppress after first occurrence
        self.suppress_patterns = [
            "WebSocket connection established",
            "Cache hit for",
            "Fetching data for symbol",
            "Order book updated",
            "Ticker data received",
            "Rate limit check",
            "Heartbeat sent",
        ]
        
    def filter(self, record):
        current_time = time.time()
        message = record.getMessage()
        
        # Check for patterns to suppress
        for pattern in self.suppress_patterns:
            if pattern in message:
                key = f"{record.name}:{pattern}"
                
                # Allow first occurrence, then limit to once per minute
                if key not in self.last_seen:
                    self.last_seen[key] = current_time
                    return True
                elif current_time - self.last_seen[key] > 60:  # 1 minute
                    suppressed = self.suppressed_count[key]
                    if suppressed > 0:
                        record.msg = f"{message} (suppressed {suppressed} similar messages)"
                        self.suppressed_count[key] = 0
                    self.last_seen[key] = current_time
                    return True
                else:
                    self.suppressed_count[key] += 1
                    return False
        
        return True


class CompressedRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that compresses rotated files"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add intelligent filter
        self.addFilter(IntelligentFilter())
    
    def doRollover(self):
        """Do a rollover and compress the old file"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            
            # Compress the current file
            dfn = self.rotation_filename(self.baseFilename + ".1.gz")
            if os.path.exists(dfn):
                os.remove(dfn)
            
            # Compress the current log file
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(dfn, 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(self.baseFilename)
        
        if not self.delay:
            self.stream = self._open()


def setup_optimized_logging():
    """Setup optimized logging with compression and filtering"""
    import logging.config
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'compressed_file': {
                '()': 'src.utils.compressed_log_handler.CompressedRotatingFileHandler',
                'filename': 'logs/app_compressed.log',
                'maxBytes': 5242880,  # 5MB
                'backupCount': 10,
                'formatter': 'detailed',
                'level': 'DEBUG'
            }
        },
        'loggers': {
            'src': {
                'handlers': ['compressed_file'],
                'level': 'DEBUG',
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(config)