import sqlite3
import os
from datetime import datetime
from constants import Const


class Logger:
    """General-purpose logger with SQLite database storage and console output."""
    
    def __init__(self, db_name="logs.db"):
        """Initialize the logger.
        
        Args:
            db_name: Name of the SQLite database file (default: logs.db)
        """
        # Ensure config directory exists
        if not os.path.exists(Const.CONFIG_DIR):
            os.makedirs(Const.CONFIG_DIR, exist_ok=True)
        
        self.db_path = os.path.join(Const.CONFIG_DIR, db_name)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database and create logs table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tag TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_timestamp(self):
        """Get formatted timestamp string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def log(self, tag, message):
        """Main logging method.
        
        Args:
            tag: Log tag (e.g., 'SERVER', 'SERVICE', 'REGISTER')
            message: Log message
        """
        timestamp = self._get_timestamp()
        
        # Console output
        console_output = f"<{timestamp}> [{tag}] {message}"
        print(console_output)
        
        # Database storage
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO logs (timestamp, tag, message)
            VALUES (?, ?, ?)
        ''', (timestamp, tag, message))
        
        conn.commit()
        conn.close()
    
    def info(self, message):
        """Log an info message.
        
        Args:
            message: Log message
        """
        self.log("INFO", message)
    
    def error(self, message):
        """Log an error message.
        
        Args:
            message: Log message
        """
        self.log("ERROR", message)
    
    def debug(self, message):
        """Log a debug message.
        
        Args:
            message: Log message
        """
        if Const.DEBUG:
            self.log("DEBUG", message)

