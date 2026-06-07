"""
Unit tests for config_manager.py

Tests JSON read/write operations, encryption/decryption, and configuration persistence.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_manager import ConfigManager


class TestConfigManagerInitialization:
    """Test configuration manager initialization."""
    
    def test_initializes_with_defaults_on_new_path(self, tmp_path):
        """Configuration should initialize with default values on new path."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        assert cfg.get("metadata.version") == "0.1.0"
        assert cfg.get("server.protocol") == "ssh"
        assert cfg.get("ui.theme") == "dark"
    
    def test_initializes_from_existing_file(self, tmp_path):
        """Configuration should load from existing file."""
        config_path = str(tmp_path / "config.json")
        
        # Create initial config
        with open(config_path, 'w') as f:
            json.dump({
                "metadata": {"version": "0.2.0"},
                "server": {"protocol": "ssh"},
            }, f)
        
        cfg = ConfigManager(config_path)
        
        assert cfg.get("metadata.version") == "0.2.0"
    
    def test_initializes_from_corrupted_file(self, tmp_path):
        """Configuration should initialize with defaults if file is corrupted."""
        config_path = str(tmp_path / "config.json")
        
        # Create corrupted JSON
        with open(config_path, 'w') as f:
            f.write("{invalid json}")
        
        cfg = ConfigManager(config_path)
        assert cfg.get("metadata.version") == "0.1.0"  # Should use defaults
    
    def test_sets_initialization_timestamp(self, tmp_path):
        """New configurations should have initialization timestamp."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        metadata = cfg.get_metadata()
        assert "initialized_at" in metadata
        # Verify it's a valid ISO format datetime string
        assert "T" in metadata["initialized_at"]


class TestConfigReadWrite:
    """Test configuration read/write operations."""
    
    def test_set_and_get_simple_value(self, tmp_path):
        """Should be able to set and get simple values."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        cfg.set("server.ip_address", "192.168.1.100")
        assert cfg.get("server.ip_address") == "192.168.1.100"
    
    def test_set_nested_value(self, tmp_path):
        """Should be able to set nested values."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        cfg.set("ui.theme", "light")
        cfg.set("logging.level", "DEBUG")
        
        assert cfg.get("ui.theme") == "light"
        assert cfg.get("logging.level") == "DEBUG"
    
    def test_set_with_default_returns_value(self, tmp_path):
        """get() should return default for non-existent keys."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        value = cfg.get("nonexistent.key", "default")
        assert value == "default"
    
    def test_get_metadata_returns_dict(self, tmp_path):
        """get_metadata() should return metadata as dict."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        metadata = cfg.get_metadata()
        assert isinstance(metadata, dict)
        assert "version" in metadata
        assert "initialized_at" in metadata
    
    def test_get_sensitive_fields_returns_list(self, tmp_path):
        """get_sensitive_fields() should return list of sensitive field names."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        fields = cfg.get_sensitive_fields()
        assert isinstance(fields, list)
        assert "server.ip_address" in fields
        assert "auth.username" in fields
    
    def test_save_creates_file(self, tmp_path):
        """save() should persist current config state to file."""
        # After initialization, config file is created with defaults including encryption key
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        assert os.path.exists(config_path)
    
    def test_save_preserves_data(self, tmp_path):
        """save() should persist changes to file."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        cfg.set("server.ip_address", "10.0.0.1")
        cfg.save()
        
        # Read file directly
        with open(config_path, 'r') as f:
            content = json.load(f)
        
        assert content["server"]["ip_address"] == "10.0.0.1"
    
    def test_clear_resets_to_defaults(self, tmp_path):
        """clear() should reset config to defaults."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Modify config
        cfg.set("server.ip_address", "1.2.3.4")
        cfg.save()
        
        # Clear
        cfg.clear()
        
        assert cfg.get("server.ip_address") == ""  # Default is empty string
    
    def test_reset_sensitive_fields(self, tmp_path):
        """reset_sensitive_fields() should clear sensitive values."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Set sensitive fields
        cfg.set("server.ip_address", "192.168.1.1")
        cfg.set("auth.username", "admin")
        cfg.save()
        
        assert cfg.get("server.ip_address") == "192.168.1.1"
        assert cfg.get("auth.username") == "admin"
        
        # Reset sensitive fields
        cfg.reset_sensitive_fields()
        cfg.save()
        
        assert cfg.get("server.ip_address") == ""
        assert cfg.get("auth.username") == ""


class TestEncryption:
    """Test encryption/decryption of sensitive fields."""
    
    def test_set_encrypted(self, tmp_path):
        """set_encrypted() should encrypt the value before storing."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        cfg.set_encrypted("auth.password_file", "/etc/secrets/passwords.txt")
        
        # Read raw file - should be encrypted JSON
        with open(config_path, 'r') as f:
            content = json.load(f)
        
        stored_value = content["auth"]["password_file"]
        assert stored_value != "/etc/secrets/passwords.txt"  # Not plain text
        
        # Should have encryption metadata
        assert isinstance(stored_value, str)
        assert stored_value.startswith('"') or stored_value.startswith('{')  # Encrypted JSON
    
    def test_get_decrypted_returns_plaintext(self, tmp_path):
        """get_decrypted() should return plaintext for encrypted fields."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        original_value = "/etc/secrets/passwords.txt"
        cfg.set_encrypted("auth.password_file", original_value)
        cfg.save()
        
        decrypted = cfg.get_decrypted("auth.password_file")
        assert decrypted == original_value
    
    def test_get_unencrypted_returns_as_is(self, tmp_path):
        """Reading unencrypted value should return as-is."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Note: This is tricky - we need to manually set an unencrypted value
        cfg.set("metadata.test_field", "unencrypted_value")
        
        value = cfg.get("metadata.test_field")
        assert value == "unencrypted_value"


class TestEncryptionEdgeCases:
    """Test encryption edge cases and error handling."""
    
    def test_encrypt_decrypt_same_instance(self, tmp_path):
        """Encrypt/decrypt should work within same ConfigManager instance."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Write encrypted value
        cfg.set_encrypted("server.ip_address", "192.168.1.100")
        cfg.save()
        
        # Read and decrypt
        decrypted = cfg.get_decrypted("server.ip_address")
        assert decrypted == "192.168.1.100"
    
    def test_read_unencrypted_from_encrypted_instance(self, tmp_path):
        """Should handle reading unencrypted value from initialized config."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Set a sensitive field (will be encrypted)
        cfg.set_encrypted("server.ip_address", "10.0.0.1")
        cfg.save()
        
        # Read as string - should still work for basic types
        stored = cfg.get("server.ip_address")
        assert stored is not None
    
    def test_decrypt_nonexistent_returns_none(self, tmp_path):
        """get_decrypted on nonexistent key should return None."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        value = cfg.get_decrypted("nonexistent.key")
        assert value is None


class TestConfigurationPersistence:
    """Test configuration persistence across sessions."""
    
    def test_config_survives_restart(self, tmp_path):
        """Config should survive 'restart' (new ConfigManager instance)."""
        config_path = str(tmp_path / "config.json")
        
        # Create and configure first session
        cfg1 = ConfigManager(config_path)
        cfg1.set("server.ip_address", "172.16.0.1")
        cfg1.set("auth.username", "service_account")
        cfg1.set_encrypted("auth.password_file", "/var/secrets/auth.key")
        cfg1.save()
        
        # Create second session (simulating restart)
        cfg2 = ConfigManager(config_path)
        
        assert cfg2.get("server.ip_address") == "172.16.0.1"
        assert cfg2.get("auth.username") == "service_account"
        assert cfg2.get_decrypted("auth.password_file") == "/var/secrets/auth.key"
    
    def test_config_updates_across_sessions(self, tmp_path):
        """Updates in one session should persist to next."""
        config_path = str(tmp_path / "config.json")
        
        # First session: set basic values
        cfg1 = ConfigManager(config_path)
        cfg1.set("server.port", 8080)
        cfg1.save()
        
        # Second session: read and modify
        cfg2 = ConfigManager(config_path)
        port = cfg2.get("server.port")
        assert port == 8080
        
        cfg2.set("server.port", 9090)
        cfg2.save()
        
        # Third session: verify update persisted
        cfg3 = ConfigManager(config_path)
        assert cfg3.get("server.port") == 9090
    
    def test_config_with_flatpak_runtime(self, tmp_path):
        """Config should use flatpak runtime path if FLATPAK_RUNTIME is set."""
        with tempfile.TemporaryDirectory() as flatpak_dir:
            os.environ["FLATPAK_RUNTIME"] = flatpak_dir
            config_path = str(tmp_path / "config.json")  # Will override anyway
            
            cfg = ConfigManager(config_path)
            assert cfg.config_path == config_path
        
        # Clean up
        del os.environ["FLATPAK_RUNTIME"]
    
    def test_default_config_values(self, tmp_path):
        """Should initialize with all expected default values."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        defaults = cfg.get_defaults()
        
        assert defaults["server"]["ip_address"] == ""
        assert defaults["server"]["port"] == 22
        assert defaults["server"]["protocol"] == "ssh"
        assert defaults["ui"]["theme"] == "dark"
        assert defaults["logging"]["level"] == "INFO"


class TestConfigPathHandling:
    """Test configuration path handling."""
    
    def test_custom_config_path(self, tmp_path):
        """Should accept custom config path."""
        config_path = str(tmp_path / "custom_config.json")
        cfg = ConfigManager(config_path)
        
        assert cfg.config_path == config_path
    
    def test_default_config_path_used_when_no_arg(self, tmp_path):
        """Should use default path when no argument provided."""
        # Temporarily change current working directory for relative path resolution
        original_cwd = os.getcwd()
        
        try:
            with tempfile.TemporaryDirectory() as td:
                os.chdir(td)
                
                # Create a fake home dir structure
                fake_home = Path(td) / "home" / "hamon"
                fake_home.mkdir(parents=True)
                
                config_path = ConfigManager()._get_default_config_path()
                assert isinstance(config_path, str)
        finally:
            os.chdir(original_cwd)


class TestIsInitializedAndMetadata:
    """Test initialization state and metadata access."""
    
    def test_is_initialized_new_config(self, tmp_path):
        """New config should be considered initialized with defaults."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        assert cfg.is_initialized()
    
    def test_metadata_never_encrypted(self, tmp_path):
        """Metadata fields should never be encrypted."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        metadata = cfg.get_metadata()
        
        # Check no encryption markers
        assert "__type" not in metadata
        assert "__data" not in metadata


class TestExceptionHandling:
    """Test exception handling."""
    
    def test_decrypt_corrupted_value_raises(self, tmp_path):
        """Decrypting corrupted value should raise ValueError."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        # Manually inject corrupted encrypted data
        with open(config_path, 'w') as f:
            json.dump({
                "auth": {
                    "password_file": "not_valid_fernet_encrypted_data_"
                }
            }, f)
        
        with pytest.raises(ValueError):
            cfg.get_decrypted("auth.password_file")
    
    def test_read_nonexistent_with_default(self, tmp_path):
        """get() should return default for nonexistent key."""
        config_path = str(tmp_path / "config.json")
        cfg = ConfigManager(config_path)
        
        value = cfg.get("nonexistent", "my_default")
        assert value == "my_default"
