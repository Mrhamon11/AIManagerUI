"""
AI Model Server Manager - Error Handler Module

Provides centralized error logging, categorization, and user-friendly diagnostics.
Task 4: Add error handling and diagnostics with helpful troubleshooting tips.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import traceback


class ErrorHandler:
    """
    Centralized error handler for logging and diagnostics.
    
    Features:
    - Logs connection issues to internal log directory
    - Categorizes errors by type with helpful troubleshooting tips
    - Provides user-friendly error messages
    """

    # Default logs directory (can be overridden)
    _logs_dir: Optional[Path] = None
    _logger_name = "AIManagerUI"
    
    @classmethod
    def set_logs_directory(cls, path: str) -> None:
        """Set the logs directory path."""
        cls._logs_dir = Path(path)

    @classmethod
    def get_logs_directory(cls) -> Path:
        """Get the logs directory, creating it if needed."""
        if cls._logs_dir is None:
            # Default to user's local share
            home = Path.home()
            cls._logs_dir = home / ".local" / "share" / "AIManagerUI" / "logs"
        
        # Create directory if it doesn't exist
        cls._logs_dir.mkdir(parents=True, exist_ok=True)
        return cls._logs_dir

    @classmethod
    def log_error(cls, error_type: str, message: str, **kwargs: Any) -> None:
        """
        Log an error with categorization and troubleshooting tips.
        
        Args:
            error_type: Category of error (e.g., "connection", "authentication", "command")
            message: Error message to log
            **kwargs: Additional metadata (host, port, username, etc.)
        """
        logs_dir = cls.get_logs_directory()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Create error-specific log file if not exists
        error_file = logs_dir / f"connection_errors_{timestamp}.log"

        try:
            full_message = message.format(**kwargs) if kwargs else message
            
            with open(error_file, "a") as f:
                f.write("\n=== ERROR LOG ===\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Type: {error_type}\n")
                f.write(f"Message: {full_message}\n")
                
                # Add traceback if available
                if "traceback" in kwargs:
                    tb = kwargs.pop("traceback", "")
                    f.write(f"Traceback:\n{tb}")

            # Also print to stderr for immediate visibility
            print(f"[ERROR[{error_type}]] {full_message}", file=sys.stderr)

        except Exception as e:
            # If logging fails, at least print the error
            print(f"[WARNING] Failed to log error: {e}", file=sys.stderr)

    @classmethod
    def log_connection_error(
        cls,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> str:
        """
        Log a connection error with troubleshooting tips.
        
        Returns:
            User-friendly error message string
        """
        if exception is None:
            exception = Exception("Unknown connection error")
            
        error_str = str(exception)
        error_type = "connection"

        # Categorize the error
        if "timed out" in error_str.lower() or "timeout" in error_str.lower():
            error_type = "timeout"
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• Check your network connection and internet access\n"
                "• Ensure the firewall is not blocking SSH traffic on port 22\n"
                "• Verify DNS resolution if using hostnames\n"
            )
        elif "connection refused" in error_str.lower():
            error_type = "refused"
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• The SSH service may not be running on the target server\n"
                "• Try verifying connectivity with: telnet <host> 22 or nc -zv <host> 22\n"
                "• Check if the correct port is configured in settings\n"
            )
        elif "no such host" in error_str.lower() or "name does not resolve" in error_str.lower():
            error_type = "dns"
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• Verify the hostname or IP address is correct\n"
                "• Check your DNS settings and try pinging the host\n"
                "• Try using an IP address instead of a hostname\n"
            )
        elif "authentication failed" in error_str.lower() or "permission denied" in error_str.lower():
            error_type = "authentication"
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• Verify username is correct\n"
                "• Check SSH key permissions: chmod 600 ~/.ssh/id_*\n"
                "• Ensure the public key is correctly added to server's authorized_keys\n"
                "• If using password auth, verify credentials and that it's not disabled on server\n"
            )
        elif "host key verification failed" in error_str.lower():
            error_type = "hostkey"
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• This is common with first-time connections\n"
                "• The application automatically adds host keys (AutoAddPolicy)\n"
                "• If the connection still fails, verify you're connecting to the correct server\n"
            )
        else:
            troubleshooting = (
                "TROUBLESHOOTING TIPS:\n"
                "• Verify your network connection\n"
                "• Check firewall rules on both local and remote systems\n"
                "• Ensure SSH service is running on the target server\n"
                "• Review logs for more details: ~/.local/share/AIManagerUI/logs/"
            )

        # Log to file
        cls.log_error(
            error_type=error_type,
            message="Connection failed: {error}",
            host=host or "<unknown>",
            port=port or 22,
            username=username or "<unknown>",
            traceback=traceback.format_exc(),
            troubleshooting=troubleshooting
        )

        # Return user-friendly message
        return (
            f"✗ Failed to connect to {host or 'server'}:{port or 22}\n\n"
            f"{error_str}\n\n"
            "TROUBLESHOOTING TIPS:\n"
            "• Verify your network connection\n"
            "• Check if the SSH service is running on the target server\n"
            "• Review detailed logs: ~/.local/share/AIManagerUI/logs/connection_errors_*.log"
        )

    @classmethod
    def log_authentication_error(cls, message: str) -> None:
        """Log authentication-related errors."""
        cls.log_error("authentication", f"Authentication failed: {message}")

    @classmethod
    def log_command_error(cls, command: str, exception: Exception) -> str:
        """
        Log command execution errors.
        
        Returns:
            User-friendly error message with troubleshooting tips
        """
        error_type = "command"
        error_str = str(exception)
        
        troubleshooting = (
            "TROUBLESHOOTING TIPS:\n"
            f"• The remote command failed with exit code: {exception.return_code if hasattr(exception, 'return_code') else 'N/A'}\n"
            f"• Command output:\n{error_str}\n\n"
            "Possible causes:\n"
            "• Command does not exist or is missing dependencies\n"
            "• Permission denied - check file ownership and execute permissions\n"
            "• Path issues - verify the command is available in PATH on remote server\n"
        )
        
        cls.log_error(
            error_type=error_type,
            message=f"Command execution failed: {command}\nError: {error_str}",
            traceback=traceback.format_exc(),
            troubleshooting=troubleshooting
        )

        return (
            f"✗ Command execution failed:\n\n"
            f"{error_str}\n\n"
            "TROUBLESHOOTING TIPS:\n"
            f"• Check if the command exists on the remote server\n"
            f"• Verify file permissions and ownership\n"
            f"• Review detailed logs: ~/.local/share/AIManagerUI/logs/connection_errors_*.log"
        )

    @classmethod
    def log_timeout_error(cls, host: Optional[str] = None, command: Optional[str] = None) -> str:
        """Log timeout-related errors."""
        error_type = "timeout"
        
        cls.log_error(
            error_type=error_type,
            message=f"Operation timed out. Target: {host or 'connection'}, Command: {command or 'N/A'}",
            troubleshooting=(
                "TROUBLESHOOTING TIPS:\n"
                "• Check your internet connection speed and stability\n"
                "• The remote server may be overloaded or responding slowly\n"
                "• Large commands may require longer timeouts\n"
                "• Consider breaking large operations into smaller steps\n"
            )
        )

        return (
            f"⏱ Operation timed out\n\n"
            f"Target: {host or 'connection'}\n"
            f"Command: {command or 'N/A'}\n\n"
            "TROUBLESHOOTING TIPS:\n"
            "• Check your internet connection stability\n"
            "• The remote server may be overloaded\n"
            "• Consider breaking large operations into smaller steps"
        )

    @classmethod
    def log_file_error(cls, filename: str, exception: Exception) -> None:
        """Log file-related errors."""
        cls.log_error("file", f"File operation failed for {filename}: {exception}")


# Configure module-level logging
def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging configuration."""
    logs_dir = ErrorHandler.get_logs_directory()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Create file handler for detailed logs
    file_handler = logging.FileHandler(logs_dir / "debug.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Set up root logger
    root_logger = logging.getLogger("AIManagerUI")
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers if any
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_error_log_path() -> str:
    """Get the path to the current error log file."""
    logs_dir = ErrorHandler.get_logs_directory()
    return str(logs_dir / "connection_errors_*.log")
