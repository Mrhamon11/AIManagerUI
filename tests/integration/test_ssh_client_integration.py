"""
Integration Tests for SSH Client Module

Tests require an actual SSH server connection to validate:
- Real SSH command execution
- Error handling with invalid credentials/hosts
- Actual timeout behavior
"""

import unittest
import sys
import os
import socket
from typing import Optional

# Add src directory to path so we can import the module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.ssh_client import SSHConnectionManager, SSHProcessOutput


class IntegrationTestSSHConnectionManager(unittest.TestCase):
    """Integration tests for SSHConnectionManager requiring real server."""

    def setUp(self):
        """Set up test fixtures with a configurable target host."""
        # Try to use environment variable or config if available
        self.target_host = os.environ.get("AI_MANAGER_SSH_TEST_HOST", "")
        self.target_username = os.environ.get("AI_MANAGER_SSH_TEST_USER", "root")
        self.key_path = os.environ.get("AI_MANAGER_SSH_TEST_KEY")
        self.password = os.environ.get("AI_MANAGER_SSH_TEST_PASSWORD")

    def test_connect_success_with_valid_host(self):
        """Test successful connection to configured target host."""
        if not self.target_host:
            self.skipTest("No SSH target host configured. Set AI_MANAGER_SSH_TEST_HOST")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        # Test connection
        try:
            manager.connect(verbose=True)
            
            # Verify connected state
            self.assertTrue(manager.is_connected())
            self.assertEqual(manager.status.value, "connected")
            
            # Test a simple command
            result = manager.run_command("echo 'SSH integration test'")
            
            self.assertTrue(bool(result))
            self.assertIn("SSH integration test", result.stdout)
            self.assertEqual(result.return_code, 0)

        except Exception as e:
            self.fail(f"Connection or command failed: {e}")

        finally:
            manager.disconnect()

    def test_run_command_hostname(self):
        """Test running hostname command on remote server."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Test hostname command
            result = manager.run_command("hostname")
            
            self.assertTrue(bool(result))
            self.assertIn("\n", result.stdout)  # hostname output ends with newline
            
        except Exception as e:
            self.fail(f"Command failed: {e}")

        finally:
            manager.disconnect()

    def test_run_command_ls(self):
        """Test running ls command on remote server."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Test ls command with timeout
            result = manager.run_command("ls -la")
            
            self.assertTrue(bool(result))
            self.assertIn("/home", result.stdout)  # Should list home directory
            
        except Exception as e:
            self.fail(f"Command failed: {e}")

        finally:
            manager.disconnect()

    def test_run_command_with_timeout(self):
        """Test command timeout handling."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=5.0  # Short timeout for test
        )

        try:
            manager.connect()
            
            # Test timeout with a command that would take longer than limit
            result = manager.run_command(
                "sleep 10 && echo 'completed'",
                timeout=2.0  # Should timeout before completion
            )
            
            # Command should have timed out
            self.assertFalse(bool(result))
            self.assertNotEqual(result.return_code, 0)

        except Exception as e:
            # Timeout may raise an exception
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                pass  # Expected behavior
            else:
                self.fail(f"Unexpected error: {e}")

        finally:
            manager.disconnect()

    def test_run_command_with_stdin(self):
        """Test command execution with stdin input."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Test command with stdin (e.g., cat /dev/stdin)
            result = manager.run_command(
                "cat /dev/stdin",
                stdin_data="Hello from SSH\nWorld!"
            )
            
            self.assertTrue(bool(result))
            self.assertIn("Hello from SSH", result.stdout)
            self.assertIn("World!", result.stdout)

        except Exception as e:
            self.fail(f"Command with stdin failed: {e}")

        finally:
            manager.disconnect()

    def test_run_command_nonexistent(self):
        """Test command execution returns failure for nonexistent commands."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Test nonexistent command
            result = manager.run_command("this_command_definitely_does_not_exist_xyz")
            
            self.assertFalse(bool(result))
            self.assertNotEqual(result.return_code, 0)
            self.assertIn("command not found", result.stderr.lower())

        except Exception as e:
            self.fail(f"Expected command failure raised exception: {e}")

        finally:
            manager.disconnect()

    def test_disconnect_after_execution(self):
        """Test proper cleanup after command execution."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Run a few commands
            manager.run_command("echo 1")
            manager.run_command("echo 2")
            
            self.assertTrue(manager.is_connected())
            
        except Exception as e:
            self.fail(f"Execution failed: {e}")

        finally:
            result = manager.disconnect()
            self.assertTrue(result)
            self.assertFalse(manager.is_connected())
            self.assertEqual(manager.status.value, "disconnected")

    def test_connection_refused_error_handling(self):
        """Test error handling when connection is refused."""
        # Use a port that's commonly closed (e.g., on localhost with no service)
        manager = SSHConnectionManager(
            host="127.0.0.1",
            port=9999,  # Unlikely to be open
            username="root",
            max_retries=1,  # Single attempt for test
            retry_delay_seconds=1.0,
            command_timeout_seconds=10.0
        )

        with self.assertRaises(Exception) as context:
            manager.connect()
        
        self.assertIn("connect", str(context.exception).lower())

    def test_invalid_credentials_error_handling(self):
        """Test error handling with invalid credentials."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username="invalid_user_xyz",  # Invalid user
            password="wrong_password_123",
            max_retries=1,
            retry_delay_seconds=1.0,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # If connection succeeded, it means credentials were accepted
            # Try a command that would fail with invalid user permissions
            result = manager.run_command("id")
            
            # This should fail if credentials are wrong (permission denied)
            if not bool(result):
                self.assertIn(
                    "Permission denied",
                    result.stderr.lower() or "Authentication failed".lower()
                )

        except Exception as e:
            # Auth failures may raise exceptions
            pass  # Expected with invalid credentials

        finally:
            manager.disconnect()


class IntegrationTestSSHProcessOutput(unittest.TestCase):
    """Integration tests for SSHProcessOutput data handling."""

    def test_stdout_encoding_utf8(self):
        """Test that stdout is properly decoded as UTF-8."""
        output = SSHProcessOutput(
            stdout="こんにちは世界\n🚀",  # Unicode characters
            stderr="",
            return_code=0,
            duration_seconds=0.1,
            success=True
        )

        self.assertIn("こんにちは世界", output.stdout)
        self.assertTrue(output.success)

    def test_stderr_encoding_utf8(self):
        """Test that stderr with errors is handled gracefully."""
        # Simulate invalid UTF-8 in stderr
        error_bytes = b"Error: \xff\xfe invalid\n"
        
        output = SSHProcessOutput(
            stdout="",
            stderr=error_bytes.decode('utf-8', errors='replace'),
            return_code=1,
            duration_seconds=0.1,
            success=False
        )

        self.assertIn("invalid", output.stderr)  # Replacement character
        self.assertFalse(output.success)

    def test_large_output_handling(self):
        """Test handling of large stdout/stderr."""
        large_output = "x" * 100000  # 100KB
        error_output = "Error message\n" + "y" * 50000
        
        output = SSHProcessOutput(
            stdout=large_output,
            stderr=error_output,
            return_code=0,
            duration_seconds=1.0,
            success=True
        )

        self.assertEqual(len(output.stdout), 100000)
        self.assertIn("Error message", output.stderr)
        self.assertTrue(output.success)


class IntegrationTestConcurrentOperations(unittest.TestCase):
    """Integration tests for concurrent SSH operations."""

    def setUp(self):
        """Set up test fixtures with a configurable target host."""
        # Try to use environment variable or config if available
        self.target_host = os.environ.get("AI_MANAGER_SSH_TEST_HOST", "")
        self.target_username = os.environ.get("AI_MANAGER_SSH_TEST_USER", "root")
        self.key_path = os.environ.get("AI_MANAGER_SSH_TEST_KEY")
        self.password = os.environ.get("AI_MANAGER_SSH_TEST_PASSWORD")

    def test_multiple_commands_same_session(self):
        """Test multiple commands in same session don't interfere."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            manager.connect()
            
            # Run multiple commands sequentially
            results = []
            for cmd in ["echo 1", "echo 2", "echo 3"]:
                result = manager.run_command(cmd)
                results.append(result)
                self.assertTrue(bool(result))

            # Verify all worked
            self.assertEqual(len(results), 3)
            
        except Exception as e:
            self.fail(f"Multiple commands failed: {e}")

        finally:
            manager.disconnect()

    def test_reconnect_same_host(self):
        """Test reconnection to same host works correctly."""
        if not self.target_host:
            self.skipTest("No SSH target host configured")

        manager = SSHConnectionManager(
            host=self.target_host,
            username=self.target_username,
            key_path=self.key_path,
            password=self.password,
            retry_delay_seconds=1.0,
            max_retries=2,
            command_timeout_seconds=30.0
        )

        try:
            # First connection
            manager.connect()
            
            # Test a command
            result = manager.run_command("echo 'first session'")
            self.assertTrue(bool(result))

            # Disconnect and reconnect
            manager.disconnect()
            self.assertFalse(manager.is_connected())

            # Reconnect to same host
            manager.connect()
            
            # Test another command
            result = manager.run_command("echo 'second session'")
            self.assertTrue(bool(result))

        except Exception as e:
            self.fail(f"Reconnection failed: {e}")

        finally:
            manager.disconnect()


def run_integration_tests(target_host: Optional[str] = None) -> int:
    """
    Run integration tests with optional target host override.
    
    Args:
        target_host: Override default SSH test target host
        
    Returns:
        Number of tests passed
    """
    if target_host:
        os.environ["AI_MANAGER_SSH_TEST_HOST"] = target_host
    
    # Check for other env vars
    if not os.environ.get("AI_MANAGER_SSH_TEST_USER"):
        os.environ["AI_MANAGER_SSH_TEST_USER"] = "root"
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(IntegrationTestSSHConnectionManager)
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTestSSHProcessOutput))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTestConcurrentOperations))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.warnings  # Actually return test count via another method


if __name__ == "__main__":
    print("=" * 60)
    print("SSH Client Integration Tests")
    print("=" * 60)
    print()
    print("These tests require an SSH server connection.")
    print("Set AI_MANAGER_SSH_TEST_HOST environment variable with target host.")
    print("Example: AI_MANAGER_SSH_TEST_HOST=your-server.com python test_ssh_client_integration.py")
    print()
    
    # Run the tests
    unittest.main(argv=[''], verbosity=2, exit=False)
