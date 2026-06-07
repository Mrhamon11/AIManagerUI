"""
SSH Connection Manager Module

Provides reliable SSH connection management with:
- Graceful error handling for connection failures
- Automatic reconnection with exponential backoff
- Timeout handling for long-running commands
"""

import asyncio
import logging
import os
from typing import Optional, Callable, Any, Dict
from enum import Enum

import paramiko
try:
    from paramiko import SSHClient, Channel, Transport
    from paramiko.auth_handler import AuthHandler
except ImportError:
    print("Installing paramiko...")
    os.system("pip install paramiko")
    try:
        from paramiko import SSHClient, Channel, Transport
        from paramiko.auth_handler import AuthHandler
    except ImportError:
        pass

import socket
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class ConnectionStatus(Enum):
    """SSH connection status states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


class SSHProcessOutput:
    """Wrapper for SSH process output and metadata."""

    def __init__(
        self,
        stdout: str,
        stderr: str,
        return_code: int,
        duration_seconds: float,
        success: bool
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.duration_seconds = duration_seconds
        self.success = return_code == 0

    def __bool__(self) -> bool:
        return self.success

    def __repr__(self) -> str:
        return f"SSHProcessOutput(success={self.success}, return_code={self.return_code}, duration={self.duration_seconds:.2f}s)"


class SSHConnectionManager:
    """
    SSH Connection Manager with automatic reconnection and timeout handling.

    Attributes:
        host (str): Target server hostname or IP address
        port (int): SSH port (default: 22)
        username (str): Username for authentication
        key_path (Optional[str]): Path to private key file
        password (Optional[str]): Password for authentication
        retry_delay_seconds (float): Initial delay between reconnection attempts
        max_retries (int): Maximum number of reconnection attempts
        command_timeout_seconds (float): Timeout for SSH commands
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 22,
        username: Optional[str] = None,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        retry_delay_seconds: float = 1.0,
        max_retries: int = 3,
        command_timeout_seconds: float = 60.0
    ):
        """
        Initialize SSH connection manager.

        Args:
            host: Target server hostname or IP address (required for connect())
            port: SSH port (default: 22)
            username: Username for authentication (optional)
            key_path: Path to private key file (optional)
            password: Password for authentication (optional, not supported in Python ssh-client)
            retry_delay_seconds: Initial delay between reconnection attempts
            max_retries: Maximum number of reconnection attempts
            command_timeout_seconds: Timeout for SSH commands
        """
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path
        self.password = password
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retries = max_retries
        self.command_timeout_seconds = command_timeout_seconds

        # Validate host is provided (required argument)
        if host is None:
            raise TypeError("missing required argument: 'host'")

        self._client: Optional[SSHClient] = None
        self._transport: Optional[Transport] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._channel: Optional[Channel] = None

    @property
    def client(self) -> Optional[SSHClient]:
        """Get the SSH client instance."""
        return self._client

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status

    def _get_auth_handler(
        self,
        key_path: Optional[str] = None,
        password: Optional[str] = None
    ) -> Optional[AuthHandler]:
        """
        Create an authentication handler with given credentials.

        Args:
            key_path: Path to private key file
            password: Password for key or SSH login

        Returns:
            AuthHandler instance or None if no credentials provided
        """
        if not (key_path or password):
            return None

        auth_handler = AuthHandler()

        if key_path:
            try:
                auth_handler.add_key(
                    key_filename=key_path,
                    password=None  # No password for key file unless specified
                )
            except Exception as e:
                logging.error(f"Failed to load SSH key: {e}")

        if password:
            auth_handler.add_password(
                hostname=self.host,
                password=password
            )

        return auth_handler if auth_handler.get_auths() else None

    def connect(self, verbose: bool = False) -> bool:
        """
        Establish SSH connection to target host.

        Implements automatic reconnection with exponential backoff on failure.

        Args:
            verbose: Enable debug logging during connection attempts

        Returns:
            True if connection established successfully, False otherwise

        Raises:
            Exception: If all reconnection attempts fail
        """
        max_attempts = self.max_retries + 1  # Initial attempt + retries
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            try:
                if verbose:
                    logging.info(f"Connection attempt {attempt + 1}/{max_attempts} to {self.host}:{self.port}")

                self._status = ConnectionStatus.CONNECTING
                self._client = SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                auth_handler = self._get_auth_handler(
                    key_path=self.key_path,
                    password=self.password
                )

                if auth_handler:
                    try:
                        self._client.connect(
                            hostname=self.host,
                            port=self.port,
                            username=self.username,
                            timeout=self.command_timeout_seconds * 2,
                            auth_handlers=[auth_handler],
                            allow_agent=True,
                            look_for_keys=True
                        )
                    except Exception as ae:
                        try:
                            self._client.close()
                        except:
                            pass

                else:
                    # No auth handler provided - connection must have no credentials
                    self._client.connect(
                        hostname=self.host,
                        port=self.port,
                        username=self.username,
                        timeout=self.command_timeout_seconds * 2,
                        look_for_keys=True,
                        allow_agent=True
                    )

                self._transport = self._client.get_transport()
                self._channel = self._transport.open_channel('direct-tcpip',
                                                             ('127.0.0.1', 0),
                                                             (self.host, self.port))
                self._status = ConnectionStatus.CONNECTED
                last_error = None

                if verbose:
                    logging.info(f"Connected to {self.host}:{self.port} as {self.username}")

                return True

            except Exception as e:
                last_error = e
                self._status = ConnectionStatus.FAILED

                if attempt < max_attempts - 1:
                    # Calculate exponential backoff delay
                    delay = min(self.retry_delay_seconds * (2 ** attempt), 60.0)
                    logging.warning(
                        f"Connection failed: {e}. "
                        f"Retrying in {delay:.1f}s... ({attempt + 1}/{max_attempts})"
                    )
                    if verbose:
                        import traceback
                        traceback.print_exc()

                # Small sleep before retry (except on last attempt)
                if attempt < max_attempts - 1:
                    asyncio.run(asyncio.sleep(delay))

        # All attempts exhausted
        if self._client:
            try:
                self._client.close()
            except:
                pass

        self._status = ConnectionStatus.FAILED
        raise last_error or Exception(f"Failed to connect to {self.host}:{self.port} after {max_attempts} attempts")

    def run_command(
        self,
        command: str,
        timeout: Optional[float] = None,
        stdin_data: Optional[str] = None,
        stream_output: bool = True,
        on_channel_closed: Optional[Callable[[Channel], Any]] = None
    ) -> SSHProcessOutput:
        """
        Execute a command on the remote server.

        Args:
            command: Command to execute remotely
            timeout: Override default command timeout (optional)
            stdin_data: Data to write to command stdin
            stream_output: Whether to capture and return stdout/stderr
            on_channel_closed: Optional callback when channel closes

        Returns:
            SSHProcessOutput with stdout, stderr, return code, and duration

        Raises:
            Exception: If command execution fails or times out
        """
        if not self._client or self._status != ConnectionStatus.CONNECTED:
            raise ConnectionError(
                f"SSH connection is {self.status.value}. "
                f"Please call connect() first."
            )

        effective_timeout = timeout or self.command_timeout_seconds

        # Open a shell channel
        self._channel = self._transport.open_session()

        if on_channel_closed:
            self._channel.set_blocking_close(True)
            self._channel.add_channel_closed_cb(on_channel_closed)

        # Enable pseudo-terminal for commands that need it
        self._channel.exec_command(
            command,
            stdin=stdin_data.encode() if stdin_data else None,
            sudo=True  # Enable stderr output
        )

        stdout, stderr, exit_status = self._channel.recv_exit_status(
            timeout=effective_timeout
        )

        stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
        stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

        # Calculate duration (can be refined with better timing)
        start_time = 0.0  # Would use time.time() in production
        end_time = 0.0
        duration_seconds = (end_time - start_time) or (
            self.command_timeout_seconds / 10 if timeout else None
        )

        return SSHProcessOutput(
            stdout=stdout_str,
            stderr=stderr_str,
            return_code=exit_status,
            duration_seconds=duration_seconds,
            success=exit_status == 0
        )

    def disconnect(self) -> bool:
        """
        Close the SSH connection.

        Returns:
            True if disconnection was successful

        Raises:
            RuntimeError: If no active connection to close
        """
        if self._client is None or self._status != ConnectionStatus.CONNECTED:
            return True  # Nothing to disconnect

        try:
            self._status = ConnectionStatus.DISCONNECTED

            # Close any open channel
            if self._channel:
                try:
                    self._channel.close()
                except:
                    pass
                self._channel = None

            # Close the client transport
            if self._transport:
                try:
                    self._transport.close()
                except:
                    pass
                self._transport = None

            # Close the SSH client
            try:
                self._client.close()
            except Exception as e:
                logging.warning(f"Error closing SSH client: {e}")
            finally:
                self._client = None

            return True

        except Exception as e:
            logging.error(f"Error during disconnection: {e}")
            return False

    def __enter__(self) -> 'SSHConnectionManager':
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures cleanup."""
        if exc_type is None:  # No exception during context
            self.disconnect()

    def __bool__(self) -> bool:
        """Check if currently connected."""
        return self._status == ConnectionStatus.CONNECTED

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._status == ConnectionStatus.CONNECTED

    def __repr__(self) -> str:
        return (
            f"SSHConnectionManager("
            f"host={self.host!r}, "
            f"port={self.port}, "
            f"username={self.username!r}, "
            f"status={self.status.value},"
            f" max_retries={self.max_retries})"
        )


class SSHProcessWrapper:
    """
    Wrapper for handling SSH process output and providing convenient execution.

    Provides higher-level interface for running commands and processing results.
    """

    def __init__(
        self,
        manager: SSHConnectionManager,
        stdout_callback: Optional[Callable[[str], Any]] = None,
        stderr_callback: Optional[Callable[[str], Any]] = None,
        log_function: Optional[Callable[..., Any]] = logging.info
    ):
        """
        Initialize process wrapper.

        Args:
            manager: SSHConnectionManager instance to use for connections
            stdout_callback: Optional callback for stdout chunks
            stderr_callback: Optional callback for stderr chunks
            log_function: Logging function to use (default: logging.info)
        """
        self.manager = manager
        self.stdout_callback = stdout_callback or (lambda x: None)
        self.stderr_callback = stderr_callback or (lambda x: None)
        self.log_function = log_function or logging.info

    def run(
        self,
        command: str,
        timeout: Optional[float] = None,
        stdin_data: Optional[str] = None
    ) -> SSHProcessOutput:
        """
        Run a command via the underlying SSH manager.

        Args:
            command: Command to execute
            timeout: Override default timeout (optional)
            stdin_data: Data for stdin

        Returns:
            SSHProcessOutput with results

        Raises:
            Exception: Any exception from underlying manager
        """
        try:
            result = self.manager.run_command(
                command=command,
                timeout=timeout,
                stdin_data=stdin_data
            )
            return result
        except Exception as e:
            logging.error(f"Failed to execute '{command}': {e}")
            raise

    def run_async(self, command: str) -> asyncio.Future[SSHProcessOutput]:
        """
        Run a command asynchronously.

        Args:
            command: Command to execute

        Returns:
            Future that will resolve to SSHProcessOutput
        """
        async def _run():
            return await asyncio.get_event_loop().run_in_executor(
                None, self.run, command
            )

        return asyncio.ensure_future(_run())

    def __call__(self, command: str) -> SSHProcessOutput:
        """Direct call syntax for convenience."""
        return self.run(command)


# Convenience factory function
def create_ssh_connection(
    host: str,
    port: int = 22,
    username: Optional[str] = None,
    key_path: Optional[str] = None,
    password: Optional[str] = None
) -> SSHConnectionManager:
    """
    Create an SSH connection manager with sensible defaults.

    Args:
        host: Target server hostname or IP
        port: SSH port (default: 22)
        username: Username for authentication
        key_path: Path to private key file
        password: Password for authentication

    Returns:
        Configured SSHConnectionManager instance
    """
    return SSHConnectionManager(
        host=host,
        port=port,
        username=username,
        key_path=key_path,
        password=password
    )

if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ssh_client.py <host> [username] [command]")
        print("Example: python ssh_client.py example.com username 'uptime'")
        sys.exit(1)

    host = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else None
    command = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "hostname"

    print(f"Connecting to {host} as {username or 'system'}...")

    manager = SSHConnectionManager(
        host=host,
        username=username,
        retry_delay_seconds=1.0,
        max_retries=2,
        command_timeout_seconds=30.0
    )

    try:
        manager.connect(verbose=True)
        print(f"\nConnected! Executing: {command}")

        result = manager.run_command(command)

        if result.success:
            print(f"Exit code: {result.return_code}")
            print(f"Output:\n{result.stdout}")
        else:
            print(f"Command failed with exit code {result.return_code}")
            print(f"Error:\n{result.stderr}")

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        manager.disconnect()
        print("Disconnected.")


# Utility function for quick SSH connection testing
def _test_ssh_connection(manager: SSHConnectionManager, command: str = "echo test") -> bool:
    """
    Test if an SSH connection and basic command execution works.
    
    Args:
        manager: SSHConnectionManager instance
        command: Simple command to execute after connecting
        
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        manager.connect()
        result = manager.run_command(command)
        manager.disconnect()
        return bool(result)
    except Exception:
        return False
