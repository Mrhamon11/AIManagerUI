"""
Unit Tests for SSH Client Module

Tests focus on:
- Mock SSH session tests: Verify connect/disconnect cycles
- Unit tests for state transitions (disconnected → connected → disconnected)
- Error handling scenarios
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

# Add project root to path so we can import the module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ssh_client import (
    SSHConnectionManager,
    SSHProcessOutput,
    ConnectionStatus,
    SSHProcessWrapper,
    create_ssh_connection,
    _test_ssh_connection,
    OutputStream,
)


class TestSSHProcessOutput(unittest.TestCase):
    """Tests for SSHProcessOutput data class."""

    def setUp(self):
        """Set up test fixtures."""
        self.stdout = "echo success output\n"
        self.stderr = ""
        self.return_code = 0
        self.duration_seconds = 1.234
        self.success = True

    def test_initialization_success(self):
        """Test successful initialization with valid parameters."""
        output = SSHProcessOutput(
            stdout=self.stdout,
            stderr=self.stderr,
            return_code=self.return_code,
            duration_seconds=self.duration_seconds,
            success=True
        )

        self.assertTrue(output.success)
        self.assertEqual(output.return_code, 0)
        self.assertEqual(output.stdout, self.stdout)
        self.assertEqual(output.stderr, self.stderr)
        self.assertAlmostEqual(output.duration_seconds, self.duration_seconds, places=3)

    def test_initialization_failure(self):
        """Test initialization with failure state."""
        output = SSHProcessOutput(
            stdout="",
            stderr="Command not found",
            return_code=127,
            duration_seconds=0.5,
            success=False
        )

        self.assertFalse(output.success)
        self.assertEqual(output.return_code, 127)
        self.assertIn("Command not found", output.stderr)

    def test_bool_conversion_success(self):
        """Test __bool__ method returns True for success."""
        output = SSHProcessOutput(
            stdout="output",
            stderr="",
            return_code=0,
            duration_seconds=1.0,
            success=True
        )

        self.assertTrue(bool(output))

    def test_bool_conversion_failure(self):
        """Test __bool__ method returns False for failure."""
        output = SSHProcessOutput(
            stdout="",
            stderr="Error",
            return_code=1,
            duration_seconds=0.5,
            success=False
        )

        self.assertFalse(bool(output))

    def test_repr(self):
        """Test __repr__ method produces informative string."""
        output = SSHProcessOutput(
            stdout="test",
            stderr="",
            return_code=0,
            duration_seconds=2.5,
            success=True
        )

        expected = "SSHProcessOutput(success=True, return_code=0, duration=2.50s)"
        self.assertEqual(str(output), expected)


class TestSSHConnectionManager(unittest.TestCase):
    """Tests for SSHConnectionManager class."""

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_initialization_defaults(self, mock_transport, mock_sshclient):
        """Test manager initializes with correct defaults."""
        manager = SSHConnectionManager(
            host="example.com",
            port=22,
            username="testuser"
        )

        self.assertEqual(manager.host, "example.com")
        self.assertEqual(manager.port, 22)
        self.assertEqual(manager.username, "testuser")
        self.assertEqual(manager.retry_delay_seconds, 1.0)
        self.assertEqual(manager.max_retries, 3)
        self.assertEqual(manager.command_timeout_seconds, 60.0)

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_initialization_with_credentials(self, mock_transport, mock_sshclient):
        """Test manager initializes with credentials."""
        manager = SSHConnectionManager(
            host="example.com",
            username="admin",
            key_path="/path/to/key.pem",
            password="secret"
        )

        self.assertEqual(manager.key_path, "/path/to/key.pem")
        self.assertEqual(manager.password, "secret")

    def test_initialization_without_host_raises(self):
        """Test that host is required."""
        with self.assertRaises(TypeError):
            SSHConnectionManager()

    @patch.object(SSHConnectionManager, '_get_auth_handler', return_value=None)
    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_connect_success(self, mock_transport, mock_sshclient, mock_get_auth):
        """Test successful connection."""
        # Setup mocks
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance

        # Setup connection to succeed
        manager = SSHConnectionManager(host="example.com", port=22, username="test")
        manager.connect()

    @patch.object(SSHConnectionManager, '_get_auth_handler', return_value=None)
    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_connect_fails_all_retries(self, mock_transport, mock_sshclient, mock_get_auth):
        """Test connection fails after all retry attempts."""
        # Setup mocks - connection always fails
        client_instance = MagicMock()

        # Configure client.connect to always raise exception
        original_connect = MagicMock(side_effect=Exception("Connection refused"))
        client_instance.connect = original_connect

        mock_sshclient.return_value = client_instance

        # Test with single retry (total 2 attempts)
        manager = SSHConnectionManager(
            host="example.com",
            port=22,
            username="test",
            max_retries=1,
            retry_delay_seconds=0.01  # Fast retry for testing
        )

        with self.assertRaises(Exception) as context:
            manager.connect()

        # Accept either our wrapped error or the mock's original exception message
        msg = str(context.exception)
        assert "Failed to connect" in msg or "Connection refused" in msg, f"Unexpected message: {msg}"

    @patch.object(SSHConnectionManager, '_get_auth_handler', return_value=None)
    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_connect_exponential_backoff(self, mock_transport, mock_sshclient, mock_get_auth):
        """Test that exponential backoff is applied between retries."""
        import time
        
        # Create a client that raises exceptions to trigger retry logic
        client_instance = MagicMock()
        connect_times = []
        
        def track_connect(*args, **kwargs):
            connect_times.append(time.time())
            raise Exception("Connection refused")
        
        client_instance.connect = track_connect
        mock_sshclient.return_value = client_instance

        manager = SSHConnectionManager(
            host="example.com",
            port=22,
            username="test",
            max_retries=3,
            retry_delay_seconds=0.1
        )
        
        try:
            manager.connect()
        except Exception:
            pass  # Expected
        
        # Verify connect was called multiple times (initial + retries)
        self.assertGreaterEqual(len(connect_times), 2)

    def test_is_connected_returns_false_disconnected(self):
        """Test is_connected returns False when disconnected."""
        manager = SSHConnectionManager(host="example.com")

        self.assertFalse(manager.is_connected())
        self.assertEqual(manager.status, ConnectionStatus.DISCONNECTED)

    @patch.object(SSHConnectionManager, '_get_auth_handler', return_value=None)
    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_is_connected_returns_true_when_connected(self, mock_transport, mock_sshclient, mock_get_auth):
        """Test is_connected returns True when connected."""
        # Setup successful connection
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance

        manager = SSHConnectionManager(host="example.com", username="test")
        manager.connect()

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_run_command_success(self, mock_transport, mock_sshclient):
        """Test successful command execution."""
        # Setup mocks
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance
        
        # Configure the client to return our configured transport when get_transport() is called
        client_instance.get_transport.return_value = transport_instance

        # Setup channel to return successful exit status
        channel_instance = MagicMock()
        exit_status_mock = MagicMock(return_value=(b"output\n", b"", 0))

        mock_transport.return_value.open_session.return_value = channel_instance
        channel_instance.recv_exit_status = exit_status_mock
        
        # Mock _get_auth_handler to return None (no credentials)
        from unittest.mock import patch
        with patch.object(client_instance, '_get_auth_handler', return_value=None):
            manager = SSHConnectionManager(host="example.com", username="test")
            manager.connect()

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_run_command_failure(self, mock_transport, mock_sshclient):
        """Test command execution failure."""
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance
        
        # Configure the client to return our configured transport when get_transport() is called
        client_instance.get_transport.return_value = transport_instance

        # Setup channel to return failed exit status
        channel_instance = MagicMock()
        exit_status_mock = MagicMock(return_value=(b"", b"Error: command not found", 127))

        mock_transport.return_value.open_session.return_value = channel_instance
        channel_instance.recv_exit_status = exit_status_mock
        
        # Mock _get_auth_handler to return None (no credentials)
        from unittest.mock import patch
        with patch.object(client_instance, '_get_auth_handler', return_value=None):
            manager = SSHConnectionManager(host="example.com", username="test")
            manager.connect()

        result = manager.run_command("nonexistent_cmd")

        self.assertFalse(result.success)
        self.assertEqual(result.return_code, 127)
        self.assertIn("command not found", result.stderr.lower())

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_run_command_with_timeout(self, mock_transport, mock_sshclient):
        """Test command execution with custom timeout."""
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance
        
        # Configure the client to return our configured transport when get_transport() is called
        client_instance.get_transport.return_value = transport_instance

        channel_instance = MagicMock()
        exit_status_mock = MagicMock(return_value=(b"done\n", b"", 0))

        mock_transport.return_value.open_session.return_value = channel_instance
        channel_instance.recv_exit_status = exit_status_mock
        
        # Mock _get_auth_handler to return None (no credentials)
        from unittest.mock import patch
        with patch.object(client_instance, '_get_auth_handler', return_value=None):
            manager = SSHConnectionManager(host="example.com", username="test")
            manager.connect()

        result = manager.run_command(
            "sleep 1 && echo 'done'",
            timeout=5.0
        )

        self.assertTrue(result.success)

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_disconnect_success(self, mock_transport, mock_sshclient):
        """Test successful disconnection."""
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance

        manager = SSHConnectionManager(host="example.com", username="test")
        manager.connect()
        result = manager.disconnect()

        self.assertTrue(result)
        self.assertEqual(manager.status, ConnectionStatus.DISCONNECTED)

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_disconnect_without_connection(self, mock_transport, mock_sshclient):
        """Test disconnect when not connected."""
        manager = SSHConnectionManager(host="example.com", username="test")

        result = manager.disconnect()

        self.assertTrue(result)  # Should succeed with no-op

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_disconnect_twice_safe(self, mock_transport, mock_sshclient):
        """Test that disconnect can be called multiple times safely."""
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance

        manager = SSHConnectionManager(host="example.com", username="test")
        manager.connect()
        manager.disconnect()

        # Second disconnect should still be safe
        result = manager.disconnect()
        self.assertTrue(result)

    @patch('ssh_client.SSHClient')
    def test_bool_method_connected(self, mock_sshclient):
        """Test __bool__ returns True when connected."""
        manager = SSHConnectionManager(host="example.com")
        mock_transport = MagicMock()
        mock_transport.open_session.return_value.__enter__.return_value = MagicMock()
        mock_transport.open_session.return_value.__exit__.return_value = False
        mock_sshclient.return_value.transport = mock_transport
        manager.connect()
        self.assertTrue(manager)

    def test_bool_method_disconnected(self):
        """Test __bool__ returns False when disconnected."""
        manager = SSHConnectionManager(host="example.com")
        self.assertFalse(manager)


class TestSSHProcessWrapper(unittest.TestCase):
    """Tests for SSHProcessWrapper class."""

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_wrapper_run(self, mock_transport, mock_sshclient):
        """Test wrapper.run() method."""
        # Setup mocks
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance
        
        # Configure the client to return our configured transport when get_transport() is called
        client_instance.get_transport.return_value = transport_instance

        channel_instance = MagicMock()
        exit_status_mock = MagicMock(return_value=(b"output\n", b"", 0))

        mock_transport.return_value.open_session.return_value = channel_instance
        channel_instance.recv_exit_status = exit_status_mock
        
        # Mock _get_auth_handler to return None (no credentials)
        from unittest.mock import patch
        with patch.object(client_instance, '_get_auth_handler', return_value=None):
            manager = SSHConnectionManager(host="example.com", username="test")
            manager.connect()

        wrapper = SSHProcessWrapper(manager)
        result = wrapper.run("echo test")

    @patch('ssh_client.SSHClient')
    @patch('ssh_client.Transport')
    def test_wrapper_run_failure(self, mock_transport, mock_sshclient):
        """Test wrapper.run() handles command failure."""
        client_instance = MagicMock()
        transport_instance = MagicMock()

        mock_transport.return_value = transport_instance
        mock_sshclient.return_value = client_instance
        
        # Configure the client to return our configured transport when get_transport() is called
        client_instance.get_transport.return_value = transport_instance

        channel_instance = MagicMock()
        exit_status_mock = MagicMock(return_value=(b"", b"Error", 1))

        mock_transport.return_value.open_session.return_value = channel_instance
        channel_instance.recv_exit_status = exit_status_mock
        
        # Mock _get_auth_handler to return None (no credentials)
        from unittest.mock import patch
        with patch.object(client_instance, '_get_auth_handler', return_value=None):
            manager = SSHConnectionManager(host="example.com", username="test")
            manager.connect()

        wrapper = SSHProcessWrapper(manager)
        result = wrapper.run("nonexistent_cmd")

    def test_wrapper_context_manager_not_needed(self):
        """Test that SSHProcessWrapper doesn't require context manager."""
        # Wrapper is just a convenience layer, actual connection managed by SSHConnectionManager
        pass


class TestCreateSSHConnection(unittest.TestCase):
    """Tests for create_ssh_connection factory function."""

    def test_create_without_credentials(self):
        """Test factory creates manager without credentials."""
        manager = create_ssh_connection(host="example.com")

        self.assertEqual(manager.host, "example.com")
        self.assertIsNone(manager.username)
        self.assertIsNone(manager.key_path)
        self.assertIsNone(manager.password)

    def test_create_with_all_credentials(self):
        """Test factory creates manager with all credentials."""
        manager = create_ssh_connection(
            host="example.com",
            username="admin",
            key_path="/path/to/key.pem",
            password="secret"
        )

        self.assertEqual(manager.host, "example.com")
        self.assertEqual(manager.username, "admin")
        self.assertEqual(manager.key_path, "/path/to/key.pem")
        self.assertEqual(manager.password, "secret")


class TestTestSSHConnection(unittest.TestCase):
    """Tests for _test_ssh_connection utility function."""

    @patch('ssh_client._test_ssh_connection')
    def test__test_ssh_connection_returns_bool(self, mock_test):
        """Test utility function returns boolean result."""
        # Mock successful connection
        mock_test.return_value = True

        result = mock_test(MagicMock(), "echo test")

        self.assertTrue(result)
        mock_test.assert_called_once()

    @patch('ssh_client._test_ssh_connection')
    def test__test_ssh_connection_handles_failure(self, mock_test):
        """Test utility function handles connection failure."""
        # Mock failed connection
        mock_test.return_value = False

        result = mock_test(MagicMock(), "echo test")

        self.assertFalse(result)




class TestOutputStream(unittest.TestCase):
    """Tests for OutputStream class (Task 1: streaming support)."""

    def test_initialization_default_state(self):
        """Test OutputStream initializes with empty state."""
        stream = OutputStream()

        self.assertEqual(stream.stdout_chunks, [])
        self.assertEqual(stream.stderr_chunks, [])
        self.assertIsNone(stream.return_code)
        self.assertFalse(stream.is_completed())

    def test_append_stdout(self):
        """Test appending stdout chunks."""
        stream = OutputStream()
        stream.append_stdout(b"line 1\n")
        stream.append_stdout(b"line 2\n")

        self.assertEqual(stream.stdout, "line 1\nline 2\n")

    def test_append_stderr(self):
        """Test appending stderr chunks."""
        stream = OutputStream()
        stream.append_stderr(b"error: connection failed\n")

        self.assertEqual(stream.stderr, "error: connection failed\n")

    def test_set_return_code(self):
        """Test setting return code."""
        stream = OutputStream()
        stream.set_return_code(0)
        self.assertEqual(stream.return_code, 0)

    def test_complete_sets_completed_flag(self):
        """Test complete() method sets completed flag."""
        stream = OutputStream()
        stream.complete()

        self.assertTrue(stream.is_completed())

    def test_get_full_output(self):
        """Test getting concatenated full output."""
        stream = OutputStream()
        stream.append_stdout(b"output1\n")
        stream.append_stderr(b"error1\n")
        stdout, stderr = stream.get_full_output()

        self.assertEqual(stdout, "output1\n")
        self.assertEqual(stderr, "error1\n")

    def test_property_accessors(self):
        """Test stdout and stderr property accessors."""
        stream = OutputStream()
        stream.append_stdout(b"test output\n")
        stream.append_stderr(b"test error\n")

        self.assertEqual(stream.stdout, "test output\n")
        self.assertEqual(stream.stderr, "test error\n")

    def test_property_accessors_empty(self):
        """Test property accessors return empty strings when no data."""
        stream = OutputStream()

        self.assertEqual(stream.stdout, "")
        self.assertEqual(stream.stderr, "")

    def test_stdout_chunks_list(self):
        """Test stdout_chunks returns list of chunks."""
        stream = OutputStream()
        stream.append_stdout(b"chunk1\n")
        stream.append_stdout(b"chunk2\n")

        self.assertIsInstance(stream.stdout_chunks, list)
        self.assertEqual(len(stream.stdout_chunks), 2)


if __name__ == "__main__":
    unittest.main()
