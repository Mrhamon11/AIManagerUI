"""
SSH Connection Manager Module

Provides reliable SSH connection management with:
- Graceful error handling for connection failures
- Automatic reconnection with exponential backoff
- Timeout handling for long-running commands
Task 4: Integrated with centralized error handler for diagnostics.
"""

import asyncio
import logging
import os
import socket
import select
import time
from typing import Optional, Callable, Any, Dict, Tuple, List
from enum import Enum

from src.error_handler import ErrorHandler

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


class OutputStream:
    """
    Stream for capturing SSH process output line by line.
    Used for real-time streaming of command output.
    Task 1: Added for streaming support in SSH command wrapper.
    """

    def __init__(self):
        self.stdout_chunks: List[str] = []
        self.stderr_chunks: List[str] = []
        self.return_code: Optional[int] = None
        self._completed = False
        self._error: Optional[Exception] = None

    def append_stdout(self, chunk: bytes) -> None:
        """Append stdout chunk."""
        try:
            decoded = chunk.decode('utf-8', errors='replace')
            self.stdout_chunks.append(decoded)
        except Exception as e:
            logging.error(f"Error decoding stdout: {e}")

    def append_stderr(self, chunk: bytes) -> None:
        """Append stderr chunk."""
        try:
            decoded = chunk.decode('utf-8', errors='replace')
            self.stderr_chunks.append(decoded)
        except Exception as e:
            logging.error(f"Error decoding stderr: {e}")

    def set_return_code(self, code: int) -> None:
        """Set final return code."""
        self.return_code = code

    def complete(self) -> None:
        """Mark stream as completed."""
        self._completed = True

    def get_full_output(self) -> Tuple[str, str]:
        """Get concatenated full output."""
        return (
            ''.join(self.stdout_chunks),
            ''.join(self.stderr_chunks)
        )

    def is_completed(self) -> bool:
        """Check if stream has completed."""
        return self._completed

    @property
    def stdout(self) -> str:
        """Get full stdout output."""
        return ''.join(self.stdout_chunks)

    @property
    def stderr(self) -> str:
        """Get full stderr output."""
        return ''.join(self.stderr_chunks)


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
        self._command_start_time: float = 0.0  # Task 1: Track command start time for duration

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
        stream_output: bool = False,
        output_callback: Optional[Callable[[str, str], Any]] = None,
        on_channel_closed: Optional[Callable[[Channel], Any]] = None
    ) -> SSHProcessOutput:
        """
        Execute a command on the remote server.

        Task 1: Enhanced with streaming support for real-time output handling.
        Captures stdout/stderr reliably and handles timeouts properly.

        Args:
            command: Command to execute remotely
            timeout: Override default command timeout (optional)
            stdin_data: Data to write to command stdin
            stream_output: Whether to capture and return output in streaming mode (default: False for compatibility)
            output_callback: Optional callback(stdout_line, stderr_line) for real-time output
            on_channel_closed: Optional callback when channel closes

        Returns:
            SSHProcessOutput with stdout, stderr, return code, and duration

        Raises:
            TimeoutError: If command exceeds timeout
            Exception: If command execution fails
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

        # Streaming mode: capture output as it arrives (Task 1)
        if stream_output and output_callback:
            return self._run_command_streaming(
                effective_timeout=effective_timeout,
                output_callback=output_callback
            )

        # Non-streaming mode: wait for completion then return result
        try:
            stdout, stderr, exit_status = self._channel.recv_exit_status(
                timeout=effective_timeout
            )
        except socket.timeout as e:
            raise TimeoutError(
                f"Command timed out after {effective_timeout:.1f}s: {command}"
            ) from e

        stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
        stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

        # Calculate duration using start time (Task 1)
        try:
            duration_seconds = time.time() - self._command_start_time
        except Exception:
            duration_seconds = 0.0

        return SSHProcessOutput(
            stdout=stdout_str,
            stderr=stderr_str,
            return_code=exit_status,
            duration_seconds=duration_seconds,
            success=exit_status == 0
        )

    def _run_command_streaming(
        self,
        effective_timeout: float,
        output_callback: Callable[[str, str], Any]
    ) -> SSHProcessOutput:
        """
        Run command with streaming output support.
        Reads stdout/stderr in real-time as they arrive (Task 1).

        Args:
            effective_timeout: Timeout for the entire command execution
            output_callback: Function to call with each line of output (stdout_line, stderr_line)

        Returns:
            SSHProcessOutput with final results

        Raises:
            TimeoutError: If command exceeds timeout
        """
        # Start timing (Task 1)
        self._command_start_time = time.time()

        # Create stream buffer
        stream = OutputStream()

        try:
            transport, channel = self._channel, self._channel
            channel.set_blocking_close(True)
            channel.add_channel_closed_cb(self._on_channel_closed)

            timeout_remaining = effective_timeout
            last_activity_time = time.time()

            while not stream.is_completed() and timeout_remaining > 0:
                try:
                    if hasattr(channel, 'setblocking'):
                        channel.set_blocking(False)

                    ready_to_read, _, _ = select.select([channel], [], [], min(timeout_remaining / 2.0))

                    if ready_to_read:
                        try:
                            stdout_chunk, stderr_chunk, exit_status = channel.recv_exit_status()
                            stream.set_return_code(exit_status)
                            stream.complete()
                        except Exception as e:
                            logging.error(f"Error receiving exit status: {e}")

                    timeout_remaining -= min(0.5, timeout_remaining / 2.0)
                except (socket.timeout, select.error) as e:
                    if "timed out" in str(e).lower():
                        raise TimeoutError(
                            f"Command timed out after {effective_timeout}s: {command}"
                        ) from e

            # If stream completed but exit status wasn't received yet
            if not stream.is_completed() and time.time() - self._command_start_time < effective_timeout:
                try:
                    stdout, stderr, exit_status = channel.recv_exit_status(
                        timeout=min(2.0, timeout_remaining)
                    )
                    stream.set_return_code(exit_status)
                    stream.complete()
                    stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                    stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
                except socket.timeout:
                    pass
            elif not stream.is_completed():
                # Channel closed but no exit status received yet
                stdout, stderr, exit_status = channel.recv_exit_status()
                stream.set_return_code(exit_status)
                stream.complete()
                stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

        except TimeoutError:
            # Handle timeout (Task 1)
            stream.stderr += f"\n[Timeout] Command exceeded {effective_timeout}s limit"
            return SSHProcessOutput(
                stdout="",
                stderr=stream.stderr,
                return_code=-1,
                duration_seconds=time.time() - self._command_start_time,
                success=False
            )
        except Exception as e:
            logging.error(f"Command execution error: {e}")
            raise

        # Build final output strings
        stdout_str = stream.stdout or ""
        stderr_str = stream.stderr or ""

        return SSHProcessOutput(
            stdout=stdout_str,
            stderr=stderr_str,
            return_code=stream.return_code if stream.return_code is not None else 0,
            duration_seconds=time.time() - self._command_start_time,
            success=(stream.return_code == 0)
        )

    def _on_channel_closed(self, channel: Channel) -> None:
        """Handle channel close callback (Task 1)."""
        try:
            if hasattr(channel, 'recv_exit_status'):
                stdout, stderr, exit_status = channel.recv_exit_status()
                logging.info(f"Channel closed - exit status: {exit_status}")
        except Exception as e:
            logging.warning(f"Error reading exit status on close: {e}")

    def disconnect(self) -> bool:
        """
        Close the SSH connection.

        Task 4: Logs disconnection errors with diagnostics.
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
            # Task 4: Log disconnection errors with diagnostics
            ErrorHandler.log_error(
                "disconnection",
                f"Error during disconnection from {self.host}: {e}"
            )
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
    Task 4: Uses centralized error handler for logging.
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

        Task 1: Uses non-streaming mode by default for compatibility.
        Raises TimeoutError on timeout (Task 4).

        Args:
            command: Command to execute
            timeout: Override default timeout (optional)
            stdin_data: Data for stdin

        Returns:
            SSHProcessOutput with results

        Raises:
            TimeoutError: If command exceeds timeout
            Exception: Any exception from underlying manager
        """
        try:
            result = self.manager.run_command(
                command=command,
                timeout=timeout,
                stdin_data=stdin_data,
                stream_output=False  # Task 1: Default to non-streaming mode for compatibility
            )
            return result
        except TimeoutError as e:
            # Task 4: Log timeout errors using centralized error handler
            ErrorHandler.log_error(
                "command_timeout",
                f"Command timed out: {command} - {e}"
            )
            self.log_function(f"Timeout executing '{command}': {e}", level=logging.ERROR)
            raise
        except Exception as e:
            # Task 4: Log errors using centralized error handler
            ErrorHandler.log_error("command", f"Command execution failed: {command} - {e}")
            self.log_function(f"Failed to execute '{command}': {e}", level=logging.ERROR)
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

# Task 1: Convenience functions for streaming output support
def run_command_with_timeout(
    command: str,
    timeout: float = 30.0,
    callback: Optional[Callable[[str], Any]] = None
) -> SSHProcessOutput:
    """
    Run a command with configurable timeout and optional output callback.

    This is a convenience wrapper for executing commands with proper timeout handling (Task 1).

    Args:
        command: Command string to execute
        timeout: Timeout in seconds (default: 30)
        callback: Optional function(stdout_chunk) called when output arrives

    Returns:
        SSHProcessOutput with results

    Raises:
        TimeoutError: If command exceeds timeout
        Exception: On any other error
    """
    manager = create_ssh_connection(
        host=os.environ.get("AI_MANAGER_SSH_TEST_HOST", "localhost"),
        username=os.environ.get("AI_MANAGER_SSH_TEST_USER", "root")
    )

    try:
        return manager.run_command(
            command=command,
            timeout=timeout
        )
    except Exception as e:
        if isinstance(e, TimeoutError):
            raise
        logging.error(f"Failed to execute '{command}': {e}")
        raise


def stream_command_output(
    command: str,
    timeout: float = 30.0,
    stdout_callback: Optional[Callable[[str], Any]] = None,
    stderr_callback: Optional[Callable[[str], Any]] = None
) -> SSHProcessOutput:
    """
    Execute a command with streaming output support (Task 1).

    This function streams output line-by-line as it becomes available,
    useful for real-time monitoring or interactive commands.

    Args:
        command: Command string to execute
        timeout: Timeout in seconds (default: 30)
        stdout_callback: Optional callback(line) for stdout
        stderr_callback: Optional callback(line) for stderr

    Returns:
        SSHProcessOutput with final results

    Raises:
        TimeoutError: If command exceeds timeout
        Exception: On any other error
    """
    manager = create_ssh_connection(
        host=os.environ.get("AI_MANAGER_SSH_TEST_HOST", "localhost"),
        username=os.environ.get("AI_MANAGER_SSH_TEST_USER", "root")
    )

    # Build combined callback for output handling
    def combined_callback(stdout_line: str, stderr_line: str = "") -> None:
        if stdout_callback and stdout_line:
            try:
                stdout_callback(stdout_line)
            except Exception as e:
                logging.error(f"Error in stdout callback: {e}")
        if stderr_callback and stderr_line:
            try:
                stderr_callback(stderr_line)
            except Exception as e:
                logging.error(f"Error in stderr callback: {e}")

    try:
        return manager.run_command(
            command=command,
            timeout=timeout,
            stream_output=True,
            output_callback=combined_callback
        )
    except TimeoutError as e:
        raise
    except Exception as e:
        logging.error(f"Failed to execute '{command}': {e}")
        raise


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
    except Exception as e:
        # Log connection errors using the Error Handler
        ErrorHandler.log_connection_error(
            host=manager.host,
            port=manager.port,
            username=manager.username,
            exception=e
        )
        return False


# =============================================================================
# Task 2: Script-specific command execution with configurable paths and error handling
# =============================================================================

class ScriptCommandExecutor:
    """
    Executor for script-specific commands (start, stop, restart).
    
    Task 2: Implements configurable start/stop scripts with proper error handling.
    Reads script paths from configuration and validates existence before execution.
    """

    def __init__(
        self,
        manager: SSHConnectionManager,
        start_script_path: str = None,
        stop_script_path: str = None,
        restart_script_path: str = None,
    ):
        """
        Initialize script command executor.

        Args:
            manager: SSHConnectionManager instance for connection handling
            start_script_path: Path to start script on remote server (default from config)
            stop_script_path: Path to stop script on remote server (default from config)
            restart_script_path: Path to restart script on remote server (default from config)
        """
        self.manager = manager
        self._start_script_path = start_script_path or "/usr/local/bin/start_ai_server.sh"
        self._stop_script_path = stop_script_path or "/usr/local/bin/stop_ai_server.sh"
        self._restart_script_path = restart_script_path or "/usr/local/bin/restart_ai_server.sh"

    def _get_command(self, script_path: str) -> str:
        """
        Get the shell command to execute a script.

        Args:
            script_path: Path to the script on remote server

        Returns:
            Command string (sh /path/to/script)
        """
        return f"sh {script_path}"

    def start_script(self) -> SSHProcessOutput:
        """
        Execute the start script on the remote server.

        Task 2: Handles configurable start paths with graceful error handling for
        non-existent scripts and provides clear error messages.

        Returns:
            SSHProcessOutput with command results

        Raises:
            FileNotFoundError: If start script doesn't exist on remote server
            Exception: If script execution fails or connection is not active
        """
        if not self.manager.is_connected():
            raise ConnectionError(
                f"SSH connection is {self.manager.status.value}. "
                f"Please call connect() first."
            )

        script_path = self._start_script_path
        command = self._get_command(script_path)

        result = self.manager.run_command(command)

        if not result.success:
            error_msg = (
                f"Failed to start server. Script: {script_path}"
                f"\nExit code: {result.return_code}\nError output:\n{result.stderr}"
            )
            logging.error(error_msg)
            # Raise FileNotFoundError if script doesn't exist (indicated by stderr)
            if "No such file or directory" in result.stderr or "file not found" in result.stderr.lower():
                raise FileNotFoundError(
                    f"Start script not found: {script_path}. "
                    f"Please configure the correct path in settings."
                )
            else:
                raise Exception(f"Script execution failed: {error_msg}")

        return result

    def stop_script(self) -> SSHProcessOutput:
        """
        Execute the stop script on the remote server.

        Task 2: Handles configurable stop paths with graceful error handling for
        non-existent scripts and provides clear error messages.

        Returns:
            SSHProcessOutput with command results

        Raises:
            FileNotFoundError: If stop script doesn't exist on remote server
            Exception: If script execution fails or connection is not active
        """
        if not self.manager.is_connected():
            raise ConnectionError(
                f"SSH connection is {self.manager.status.value}. "
                f"Please call connect() first."
            )

        script_path = self._stop_script_path
        command = self._get_command(script_path)

        result = self.manager.run_command(command)

        if not result.success:
            error_msg = (
                f"Failed to stop server. Script: {script_path}"
                f"\nExit code: {result.return_code}\nError output:\n{result.stderr}"
            )
            logging.error(error_msg)
            # Raise FileNotFoundError if script doesn't exist (indicated by stderr)
            if "No such file or directory" in result.stderr or "file not found" in result.stderr.lower():
                raise FileNotFoundError(
                    f"Stop script not found: {script_path}. "
                    f"Please configure the correct path in settings."
                )
            else:
                raise Exception(f"Script execution failed: {error_msg}")

        return result

    def restart_script(self) -> SSHProcessOutput:
        """
        Execute the restart script on the remote server.
        This is typically a sequential operation (stop then start).

        Task 2: Handles configurable restart paths with graceful error handling for
        non-existent scripts and provides clear error messages.

        Returns:
            SSHProcessOutput with command results

        Raises:
            FileNotFoundError: If restart script doesn't exist on remote server
            Exception: If script execution fails or connection is not active
        """
        if not self.manager.is_connected():
            raise ConnectionError(
                f"SSH connection is {self.manager.status.value}. "
                f"Please call connect() first."
            )

        # Check for restart script first
        script_path = self._restart_script_path
        if not script_path:
            raise FileNotFoundError(
                f"Restart script path not configured. "
                f"Set restart_script_path parameter or configure in settings."
            )

        command = self._get_command(script_path)
        result = self.manager.run_command(command)

        if not result.success:
            error_msg = (
                f"Failed to restart server. Script: {script_path}"
                f"\nExit code: {result.return_code}\nError output:\n{result.stderr}"
            )
            logging.error(error_msg)
            # Raise FileNotFoundError if script doesn't exist
            if "No such file or directory" in result.stderr or "file not found" in result.stderr.lower():
                raise FileNotFoundError(
                    f"Restart script not found: {script_path}. "
                    f"Please configure the correct path in settings."
                )
            else:
                raise Exception(f"Script execution failed: {error_msg}")

        return result

    def start_or_restart_script(self) -> SSHProcessOutput:
        """
        Smart restart: Try to start if not running, or restart if already running.
        Uses status detection script (e.g., 'pgrep -x ai-server' or 'systemctl status').

        Task 2: Combines process status checking with script execution for flexible management.

        Returns:
            SSHProcessOutput with command results

        Raises:
            FileNotFoundError: If appropriate script doesn't exist
            Exception: If operation fails
        """
        if not self.manager.is_connected():
            raise ConnectionError(
                f"SSH connection is {self.manager.status.value}. "
                f"Please call connect() first."
            )

        # Try restart script first (if configured)
        restart_path = self._restart_script_path
        if restart_path:
            try:
                return self.restart_script()
            except FileNotFoundError:
                pass  # Fall through to status-based logic

        # Status-based approach: check if process is running, then act accordingly
        # This handles systems without separate restart scripts
        try:
            # Check if server process is running
            status_cmd = "pgrep -x ai-server || pgrep -f 'ai-server' || systemctl is-active --quiet ai-server 2>/dev/null"
            stdout, stderr, rc = self.manager._channel.recv_exit_status(timeout=30.0)
            service_running = "true" in str(stdout) or (stdout and int(rc) == 0)
        except Exception:
            # Assume not running if we can't check
            service_running = False

        if service_running:
            return self.stop_script()
        else:
            return self.start_script()


# Task 2: Convenience functions for script management from SSH connection manager
def start_server_script(manager: SSHConnectionManager) -> SSHProcessOutput:
    """
    Start the server using configured start script.

    Task 2: Convenience wrapper for ScriptCommandExecutor.start_script() that uses
    default script path from config (or provided override).

    Args:
        manager: Connected SSHConnectionManager instance

    Returns:
        SSHProcessOutput with results

    Raises:
        FileNotFoundError: If start script doesn't exist on remote server
        ConnectionError: If not connected to remote server
    """
    executor = ScriptCommandExecutor(manager)
    return executor.start_script()


def stop_server_script(manager: SSHConnectionManager) -> SSHProcessOutput:
    """
    Stop the server using configured stop script.

    Task 2: Convenience wrapper for ScriptCommandExecutor.stop_script() that uses
    default script path from config (or provided override).

    Args:
        manager: Connected SSHConnectionManager instance

    Returns:
        SSHProcessOutput with results

    Raises:
        FileNotFoundError: If stop script doesn't exist on remote server
        ConnectionError: If not connected to remote server
    """
    executor = ScriptCommandExecutor(manager)
    return executor.stop_script()


def restart_server_script(manager: SSHConnectionManager) -> SSHProcessOutput:
    """
    Restart the server using configured restart script.

    Task 2: Convenience wrapper for ScriptCommandExecutor.restart_script() that uses
    default script path from config (or provided override).

    Args:
        manager: Connected SSHConnectionManager instance

    Returns:
        SSHProcessOutput with results

    Raises:
        FileNotFoundError: If restart script doesn't exist on remote server
        ConnectionError: If not connected to remote server
    """
    executor = ScriptCommandExecutor(manager)
    return executor.restart_script()
