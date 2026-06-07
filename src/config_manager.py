"""
Configuration Manager Module

Provides settings persistence with encrypted sensitive fields (passwords, credentials).
Supports JSON-based storage with default configuration initialization.
"""

import json
import os
from typing import Any, Dict, Optional
from datetime import datetime, timezone

# Simple symmetric encryption using Fernet-like approach with AES-256-CBC
from cryptography.fernet import Fernet


class ConfigManager:
    """Configuration persistence manager with encrypted sensitive fields."""
    
    def __init__(self, config_path: str = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to JSON config file (uses default if not provided)
        """
        self.config_path = config_path or self._get_default_config_path()
        # Load existing config or initialize with defaults
        self._load_or_initialize()
        
        # Generate or load encryption key for Fernet initialization
        self._encryption_key = self._load_or_generate_encryption_key()
        
        # Create Fernet object for encryption (needed for set_encrypted/get_decrypted)
        try:
            self._fernet = Fernet(self._encryption_key)
        except Exception:
            # Invalid key - will be regenerated next time we need it
            self._fernet = None
        
        # Save encryption key to metadata for reuse in future instances
        self._save_encryption_key_to_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration path based on environment."""
        home = os.path.expanduser("~")
        # Check for Flatpak application data
        flatpak_data = os.getenv("XDG_DATA_HOME", os.path.join(home, ".local/share"))
        app_name = "org.ai-managers.AIModelServerManager"
        
        # Try to load from flatpak runtime if available
        runtime = os.getenv("FLATPAK_RUNTIME")
        if runtime:
            return os.path.join(runtime, "share", "applications", f"{app_name}.settings.json")
        
        # Use user data directory for non-flatpak or fallback
        return os.path.join(
            flatpak_data, app_name.replace(".", "/"),
            f"{app_name.replace('.', '-')}.json"
        )
    
    def _load_or_initialize(self) -> Dict[str, Any]:
        """Load existing config or initialize with defaults."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # If corrupted or unreadable, use defaults
                self._config = self.get_defaults()
        else:
            self._config = self.get_defaults()
        
        return self._config
    
    def _load_or_generate_encryption_key(self) -> bytes:
        """Load existing encryption key from config or generate a new one."""
        # Check if metadata already has an encryption key
        existing_key = None
        if "metadata" in self._config and "encryption_key" in self._config["metadata"]:
            existing_key = self._config["metadata"]["encryption_key"]
        
        # Only generate a new key if no existing key was found
        if not existing_key or len(existing_key.strip()) == 0:
            # Generate a new key for fresh installations
            return Fernet.generate_key()
        
        # Load and decode the existing key from metadata
        return existing_key.encode('ascii')
    
    def initialize(self) -> None:
        """Initialize configuration with default values (idempotent)."""
        # This is typically called after creating a fresh ConfigManager
        # to ensure defaults are loaded. Can also be used to reset to defaults.
        if "metadata" not in self._config or "initialized_at" not in self._config["metadata"]:
            self._config = self.get_defaults()
        self.save()
        # Always ensure encryption key is generated and saved (idempotent)
        self._encryption_key = self._load_or_generate_encryption_key()
        self._save_encryption_key_to_config()
    def _save_encryption_key_to_config(self) -> None:
        """Save the current encryption key to config metadata for reuse."""
        # The encryption key is base64-encoded bytes from Fernet.generate_key()
        # Convert to ASCII string for JSON storage (bytes are not JSON-serializable)
        try:
            key_string = self._encryption_key.decode('ascii')
        except Exception:
            # Can't decode - skip saving, will regenerate next time
            return
        
        # Only save if the metadata doesn't exist OR encryption_key is missing/empty
        # For new config files, always include the encryption key in metadata
        metadata = self._config.get("metadata", {})
        existing_key = metadata.get("encryption_key")
        if "encryption_key" not in metadata or not existing_key or len(existing_key.strip()) == 0:
            metadata["encryption_key"] = key_string
            self.save()
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        default_config = {
            # Network settings
            "server": {
                "ip_address": "",  # Will be set by user
                "port": 22,
                "protocol": "ssh",
                "timeout_seconds": 30,
            },
            # Authentication settings
            "auth": {
                "username": "",  # Will be set by user
                "password_file": "",  # Will be set by user for external storage
                "key_path": None,
            },
            # Script paths
            "scripts": {
                "start_script": "/usr/local/bin/start_ai_server.sh",
                "stop_script": "/usr/local/bin/stop_ai_server.sh",
                "restart_script": "/usr/local/bin/restart_ai_server.sh",
            },
            # UI settings
            "ui": {
                "theme": "dark",
                "language": "en_US",
                "window_size": [1200, 800],
                "position": [0, 0],
            },
            # Security settings
            "security": {
                "encrypt_sensitive_fields": True,
                "encryption_key_path": None,
            },
            # Logging settings
            "logging": {
                "level": "INFO",
                "file_path": "/var/log/ai-manager/application.log",
                "rotate_size_mb": 100,
                "backup_count": 5,
            },
            # Metadata (never encrypted)
            "metadata": {
                "version": "0.1.0",
                "initialized_at": None,
                "encryption_key": "",  # Will be populated by _load_or_generate_encryption_key
            },
        }
        
        # Set initialization timestamp if it's a new config
        from datetime import timezone
        if default_config["metadata"]["initialized_at"] is None:
            default_config["metadata"]["initialized_at"] = datetime.now(timezone.utc).isoformat()
        
        return default_config
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """Get a configuration value using dot notation."""
        keys = key.split(".")
        current = self._config
        
        for k in keys:
            if isinstance(current, dict):
                if k in current:
                    current = current[k]
                else:
                    return default
            elif not isinstance(current, dict):
                # Can't navigate deeper than a non-dict value
                return default
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        keys = key.split(".")  # Full path including leaf key
        
        current = self._config
        
        # Navigate to parent dict (all but last key)
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the leaf value
        leaf_key = keys[-1]
        current[leaf_key] = value
        
        self._save()
    
    def set_encrypted(self, key: str, plaintext: Any) -> None:
        """Set a sensitive field with encryption."""
        # Encrypt the plaintext value
        encrypted_bytes = self._fernet.encrypt(str(plaintext).encode('utf-8'))
        
        # Wrap in JSON structure for identification (matches _encrypt format)
        wrapped = {
            "__type": "encrypted",
            "__data": encrypted_bytes.decode('ascii'),
            "__created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.set(key, json.dumps(wrapped))
    
    def get_decrypted(self, key: str) -> Optional[Any]:
        """Get and decrypt a sensitive field."""
        stored = self.get(key)
        if stored is None:
            return None
        
        try:
            decrypted = self._decrypt(stored)
        except ValueError:
            # Decryption failed for corrupted/invalid data
            raise
        except Exception:
            # If decryption fails, return the stored value as-is (may be plaintext or wrong key)
            return stored
        
        return decrypted
    
    def _decrypt(self, encrypted_text: str) -> Any:
        """Decrypt an encrypted value or return plain text if not encrypted."""
        # Try to parse as JSON first (encrypted values are always JSON wrapped)
        try:
            parsed = json.loads(encrypted_text)
        except json.JSONDecodeError:
            # Not valid JSON - could be corrupted data or truly plaintext
            # Treat as potentially corrupted to alert the user
            raise ValueError("Corrupted or invalid encrypted data (not valid JSON)")
        
        # If parsed but not marked as encrypted, return as-is (plain text)
        if parsed.get("__type") != "encrypted":
            return parsed
        
        # This is an encrypted value - decrypt the inner __data field
        try:
            data = parsed["__data"]
            decrypted_bytes = self._fernet.decrypt(data.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Decryption failed - could be wrong key or corrupted data
            raise ValueError(f"Decryption failed: corrupted or invalid encrypted data")
    
    def _encrypt(self, plaintext: Any) -> str:
        """Encrypt a plaintext value and wrap with metadata."""
        # Convert to string
        text = str(plaintext)
        
        # Encrypt the data directly
        encrypted_bytes = self._fernet.encrypt(text.encode('utf-8'))
        encrypted_data = encrypted_bytes.decode('ascii')
        
        # Wrap with metadata for identification (this matches test expectations)
        wrapped = {
            "__type": "encrypted",
            "__data": encrypted_data,
            "__created_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(wrapped)


    
    def save(self) -> None:
        """Save current configuration to file."""
        self._save()
    
    def _save(self) -> None:
        """Internal save method."""
        # Ensure directory exists
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        # Write config (defaults already loaded in __init__)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2, default=str)
    def clear(self) -> None:
        """Clear configuration and reload defaults."""
        self._config = self.get_defaults()
        self.save()
    
    def reset_sensitive_fields(self) -> None:
        """Reset all sensitive fields to empty/unset state."""
        sensitive_keys = [
            "server.ip_address",
            "auth.username", 
            "auth.password_file",
            "auth.key_path",
        ]
        
        for key in sensitive_keys:
            self.set(key, "")
    
    def is_initialized(self) -> bool:
        """Check if configuration has been initialized."""
        return "metadata" in self._config and \
               "initialized_at" in self._config["metadata"]
    
    def get_metadata(self) -> Dict[str, str]:
        """Get configuration metadata (never encrypted)."""
        metadata = self.get("metadata", {})
        if isinstance(metadata, dict):
            return {k: v for k, v in metadata.items() if not k.startswith("__")}
        return {}
    
    def get_sensitive_fields(self) -> Dict[str, str]:
        """Get list of sensitive field names (not values)."""
        return [
            "server.ip_address",
            "auth.username", 
            "auth.password_file",
            "auth.key_path",
        ]
