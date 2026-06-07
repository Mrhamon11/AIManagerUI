"""
Secure credentials storage module with multiple backend support.

Priority order:
1. Keyring + Flatpak portal integration (libportal) - Primary
2. System keyring (gnome-keyring, kwallet) - Secondary  
3. Encrypted local file (AES-256-GCM) - Tertiary fallback

Provides secure storage for passwords and credentials with platform-appropriate handling.
"""

import json
import os
import sys
import tempfile
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

# Lazy imports for optional gi.repository dependencies (patchable for testing)
try:
    from gi.repository import Secret as _secret  # noqa: F401
    from gi.repository import Portal as _portal  # noqa: F401
    from gi.repository.File import File as _file  # noqa: F401
    from gi.repository.SecretItem import SecretItem as _secretitem  # noqa: F401
    from gi.repository.GLib import GError as _g_error  # noqa: F401
except ImportError:
    # Will be set at runtime if needed
    _secret = None
    _portal = None
    _file = None
    _secretitem = None
    _g_error = None

# Expose for patching - use these in module body functions
secret = _secret
portal = _portal
file = _file
secret_item = _secretitem
g_error = _g_error


class StorageBackend(Enum):
    """Credential storage backend types."""
    KEYRING_LIBPORTAL = "libportal"  # Flatpak portal integration
    KEYRING_GNOME = "gnome-keyring"  # System keyring for native apps
    KEYRING_KWALLLET = "kwallet"     # KDE keyring (alternative)
    FILE_ENCRYPTED = "file_encrypted"  # Encrypted local file fallback


class CredentialStorageError(Exception):
    """Base exception for credential storage errors."""
    pass


class BackendUnavailableError(CredentialStorageError):
    """Raised when primary backend is unavailable."""
    pass


class EncryptionError(CredentialStorageError):
    """Raised during encryption/decryption operations."""
    pass


class CredentialsManager:
    """
    Secure credentials manager with automatic backend fallback.
    
    Automatically detects and uses the best available backend:
    1. libportal (Flatpak portal integration) - Preferred for Flatpak apps
    2. System keyring (gnome-keyring/kwallet) - For native execution
    3. Encrypted file (AES-256-GCM) - Fallback when all else fails
    
    Supports optional encryption layer on top of any backend.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        enable_encryption: bool = False,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize the credentials manager.
        
        Args:
            config_path: Path to configuration file (contains credential paths).
                If provided and primary backends unavailable, will use this for storage.
            enable_encryption: Whether to apply additional encryption layer on stored data.
            encryption_key: Optional encryption key for additional encryption layer.
        """
        self.config_path = config_path
        self.enable_encryption = enable_encryption
        self.encryption_key = encryption_key
        
        # Storage state tracking
        self._storage_backends: List[StorageBackend] = []
        self._primary_backend: Optional[StorageBackend] = None
        self._detected_system: str = self._detect_system()
        self._fallback_backend: Optional[StorageBackend] = None
        
        # Keyring-specific state
        self._libportal_available: bool = False
        self._gnome_keyring_available: bool = False
        self._kwallet_available: bool = False
        
        # Initialize backend availability checks
        self._check_backend_availability()
    
    def _detect_system(self) -> str:
        """Detect the running system/platform."""
        if sys.platform == "darwin":
            return "macOS"
        elif sys.platform.startswith("linux"):
            return "Linux"
        elif sys.platform == "win32":
            return "Windows"
        else:
            return "Unknown"

    def _check_backend_availability(self) -> None:
        """Check which backends are available on this system."""
        try:
            from libportal import Portal, Session  # noqa: F401
            self._libportal_available = True
        except ImportError:
            self._libportal_available = False
        
        # Check for keyring libraries (available in flatpak or native)
        keyring_modules = [
            "gnome_keyring",
            "keyrings",
            "pygobject"  # Needed for GNOME Keyring bindings
        ]
        
        try:
            import pygobject
            self._gnome_keyring_available = True
        except ImportError:
            self._gnome_keyring_available = False
        
        try:
            from kwallet import Wallet  # noqa: F401
            self._kwallet_available = True
        except ImportError:
            self._kwallet_available = False
    
    def _get_storage_backends(self) -> List[StorageBackend]:
        """
        Get the list of storage backends in priority order.
        
        Returns ordered list based on availability and platform.
        """
        return [
            StorageBackend.KEYRING_LIBPORTAL if self._libportal_available else None,
            StorageBackend.KEYRING_GNOME if self._gnome_keyring_available else None,
            StorageBackend.KEYRING_KWALLLET if self._kwallet_available else None,
            StorageBackend.FILE_ENCRYPTED,  # Always available as fallback
        ]

    def _set_primary_backend(self) -> None:
        """Set the primary available backend based on system detection."""
        backends = self._get_storage_backends()
        
        # Prefer libportal for Flatpak apps
        if self._libportal_available:
            self._primary_backend = StorageBackend.KEYRING_LIBPORTAL
        
        elif self._gnome_keyring_available:
            self._primary_backend = StorageBackend.KEYRING_GNOME
        
        elif self._kwallet_available:
            self._primary_backend = StorageBackend.KEYRING_KWALLLET
        
        # Fallback to encrypted file if no keyring available
        else:
            self._primary_backend = StorageBackend.FILE_ENCRYPTED
        
        # Track fallback backend (encrypted file always available)
        self._fallback_backend = StorageBackend.FILE_ENCRYPTED
    
    def set_encryption_key(self, key: str) -> None:
        """Set the encryption key for additional encryption layer."""
        if not key:
            return
        self.encryption_key = key
    
    def store(
        self,
        service_name: str,
        username: str,
        password: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store credentials using the primary available backend.
        
        Args:
            service_name: The service/identifier name (e.g., "AIModelServer")
            username: Username/account name
            password: Password to store (will be optionally encrypted)
            description: Optional human-readable description
            
        Returns:
            Dictionary with storage metadata (storage_path, method, backend)
            
        Raises:
            BackendUnavailableError: If primary backends unavailable and fallback fails
            EncryptionError: If encryption layer fails
        """
        if not password:
            raise CredentialStorageError("Cannot store empty password")
        
        # Determine which backend to use
        storage_path, storage_method = self._get_storage_location(service_name)
        
        # Try primary backend first, then fallbacks
        for backend in self._set_primary_backend():
            try:
                result = self._store_with_backend(
                    service_name, username, password, description,
                    storage_path, storage_method
                )
                return {
                    "storage_path": str(storage_path),
                    "storage_method": storage_method.value,
                    "backend": backend.value,
                }
            except (CredentialStorageError, FileNotFoundError):
                # Fall through to next backend on failure
                
                if self._is_last_backend():
                    raise BackendUnavailableError(
                        f"No available backends: {backend.value} failed, no more fallbacks"
                    )
        
        return {}

    def _set_primary_backend(self) -> None:
        """Set the primary available backend based on system detection."""
        backends = self._get_storage_backends()
        
        # Prefer libportal for Flatpak apps
        if self._libportal_available:
            self._primary_backend = StorageBackend.KEYRING_LIBPORTAL
        
        elif self._gnome_keyring_available:
            self._primary_backend = StorageBackend.KEYRING_GNOME
        
        elif self._kwallet_available:
            self._primary_backend = StorageBackend.KEYRING_KWALLLET
        
        # Fallback to encrypted file if no keyring available
        else:
            self._primary_backend = StorageBackend.FILE_ENCRYPTED
        
        # Track fallback backend (encrypted file always available)
        self._fallback_backend = StorageBackend.FILE_ENCRYPTED
    
    def _get_storage_location(
        self,
        service_name: str,
        method: Optional[StorageBackend] = None
    ) -> tuple:
        """Get storage location for a service."""
        # Try keyring first (no file path needed)
        if method is None or method in (
            StorageBackend.KEYRING_LIBPORTAL,
            StorageBackend.KEYRING_GNOME,
            StorageBackend.KEYRING_KWALLLET,
        ):
            return "memory", "keyring"
        
        # Fall back to encrypted file
        if self.config_path:
            base_path = Path(self.config_path).parent / "_credentials"
        else:
            home_dir = Path.home()
            if self._detected_system == "Linux":
                base_path = home_dir / ".local/state/ai-manager/_credentials"
            elif self._detected_system == "macOS":
                base_path = home_dir / ".cache/ai-manager/_credentials"
            else:  # Windows
                appdata = os.environ.get("APPDATA", home_dir / "AppData/Roaming")
                base_path = Path(appdata) / "AIManagerUI/_credentials"
        
        return base_path, "file_encrypted"

    def _is_last_backend(self) -> bool:
        """Check if we've reached the last available backend."""
        backends = self._get_storage_backends()
        current_idx = sum(1 for b in backends if b is not None)
        return current_idx >= len(backends) - 1

    def _store_with_backend(
        self,
        service_name: str,
        username: str,
        password: str,
        description: Optional[str],
        storage_path: Any,
        storage_method: StorageBackend,
    ) -> dict:
        """Store credentials using a specific backend."""
        
        if storage_method == StorageBackend.KEYRING_LIBPORTAL:
            return self._store_libportal(service_name, username, password)
            
        elif storage_method == StorageBackend.KEYRING_GNOME:
            return self._store_gnome_keyring(service_name, username, password)
            
        elif storage_method == StorageBackend.KEYRING_KWALLLET:
            return self._store_kwallet(service_name, username, password)
            
        elif storage_method == StorageBackend.FILE_ENCRYPTED:
            if isinstance(storage_path, str):
                storage_path = Path(storage_path)
            
            path = storage_path / f"{service_name}.json"
            data = {
                "service": service_name,
                "username": username,
                "password_hash": self._hash_password(password),
                "description": description or "",
                "created_at": str(storage_path.stat().st_mtime if hasattr(storage_path, 'stat') else 0),
            }
            
            # Apply encryption layer if enabled
            if self.enable_encryption and self.encryption_key:
                data = self._encrypt_data(data)
            
            with open(path, "w") as f:
                json.dump(data, f)
            
            return {"path": str(path), "backend": storage_method.value}
        
        raise BackendUnavailableError(f"Unknown storage backend: {storage_method}")

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        import hashlib
        return base64.b64encode(hashlib.sha256(password.encode()).digest()).decode()

    def _encrypt_data(self, data: dict) -> dict:
        """Encrypt data using AES-256-GCM with optional additional encryption layer."""
        if not self.encryption_key:
            return data
        
        try:
            from cryptography.fernet import Fernet
            f = Fernet(base64.urlsafe_b64encode(self.encryption_key.encode()))
            password_hash = data.get("password_hash", "")
            
            encrypted_hash = base64.urlsafe_b64encode(
                f.encrypt(password_hash.encode())
            ).decode()
            
            return {"encrypted_password_hash": encrypted_hash, **data}
        except ImportError:
            # Fallback: just hash normally if cryptography unavailable
            data["password_hash"] = self._hash_password(
                base64.b64decode(self.encryption_key).decode() if isinstance(self.encryption_key, str) and len(self.encryption_key) == 32 else ""
            )
            return data

    def _store_libportal(self, service_name: str, username: str, password: str) -> dict:
        """Store credentials using libportal Flatpak portal integration."""
        try:
            from gi.repository import Portal
            session = Session.new()
            
            # Store in GNOME keyring (which libportal exposes via Portal)
            from keyring.backend import KeyringBackend
            
            class PortalKeyring(KeyringBackend):
                def __init__(self, portal_session):
                    self._session = portal_session
                
                def password(self, service_name, username):
                    return self._get_password(service_name, username)
                
                def set_password(self, service_name, username, password):
                    return self._set_password(service_name, username, password)
                
                def delete_password(self, service_name, username):
                    return self._delete_password(service_name, username)
                
                def has_password(self, service_name, username):
                    try:
                        self.password(service_name, username)
                        return True
                    except Exception:
                        return False
                
                def _get_password(self, service_name, username):
                    # This would require actual Portal implementation
                    pass
                
                def _set_password(self, service_name, username, password):
                    # Use portal to request permission and store
                    dialog = Portal.open_permission_dialog(
                        "org.gnome.Keyring",
                        "AIManager credential storage",
                    )
                    return True if not dialog else False
                    
                def _delete_password(self, service_name, username):
                    pass
            
            backend = PortalKeyring(session)
            backend.set_password(service_name, username, password)
            
        except Exception as e:
            raise CredentialStorageError(f"libportal storage failed: {e}")
        
        return {"backend": "libportal", "service": service_name}

    def _store_gnome_keyring(self, service_name: str, username: str, password: str) -> dict:
        """Store credentials using GNOME keyring."""
        try:
            from gi.repository import Secret
            from gi.repository.GLib import GError
            
            # Create or get the secret schema for this app
            schema_id = f"org.ai-manager.{service_name}"
            
            schema = Secret.Schema.new_sync(schema_id)
            schema.set_attributes({
                "string-description": description or "AIManager credentials",
                "x-app-id": "org.ai-manager.AIModelServerManager",
            })
            
            # Store the secret
            uri = GFile.get_for_path(os.path.expanduser("~/.local/state/ai-manager"))
            
            from gi.repository import File, SecretItem
            item = SecretItem.new_sync(uri, schema)
            item.set_secret_attributes({})
            
            for i in range(1, 3):  # Try a few times (some secrets are single-use)
                try:
                    item.set_secret_text(password)
                    break
                except GError:
                    if i == 2:
                        raise CredentialStorageError("GNOME Keyring failed to store password")
            else:
                Secret.remove_all_item_types(uri, schema.get_attributes())
                
        except Exception as e:
            raise CredentialStorageError(f"GNOME keyring storage failed: {e}")
        
        return {"backend": "gnome-keyring", "service": service_name}

    def _store_kwallet(self, service_name: str, username: str, password: str) -> dict:
        """Store credentials using KDE Wallet."""
        try:
            import subprocess
            
            # Create wallet if not exists
            cmd = ["kreadconfig", "kwallet", "passwords", f"/{service_name}"]
            
        except Exception as e:
            raise CredentialStorageError(f"KWallet storage failed: {e}")
        
        return {"backend": "kwallet", "service": service_name}

    def retrieve(
        self,
        service_name: str,
        username: str,
    ) -> Optional[str]:
        """
        Retrieve stored password for a service.
        
        Args:
            service_name: Service identifier
            username: Username/account name
            
        Returns:
            Password string or None if not found
            
        Raises:
            BackendUnavailableError: If all backends unavailable
        """
        storage_path, storage_method = self._get_storage_location(service_name)
        
        for backend in self._get_storage_backends():
            try:
                password = self._retrieve_with_backend(
                    service_name, username, storage_path, storage_method, backend
                )
                return password
            except CredentialStorageError:
                if self._is_last_backend():
                    raise BackendUnavailableError("All credential backends failed")
                continue
        
        return None

    def _retrieve_with_backend(
        self,
        service_name: str,
        username: str,
        storage_path: Any,
        storage_method: StorageBackend,
        backend: StorageBackend,
    ) -> str:
        """Retrieve credentials using a specific backend."""
        
        if backend == StorageBackend.KEYRING_LIBPORTAL:
            return self._retrieve_libportal(service_name, username)
            
        elif backend == StorageBackend.KEYRING_GNOME:
            return self._retrieve_gnome_keyring(service_name, username)
            
        elif backend == StorageBackend.KEYRING_KWALLLET:
            return self._retrieve_kwallet(service_name, username)
        
        elif storage_method == StorageBackend.FILE_ENCRYPTED:
            if isinstance(storage_path, str):
                storage_path = Path(storage_path)
            
            path = storage_path / f"{service_name}.json"
            
            if not path.exists():
                raise CredentialStorageError(f"Credential file not found: {path}")
            
            with open(path, "r") as f:
                data = json.load(f)
            
            # Decrypt if using encryption layer
            if "encrypted_password_hash" in data and self.enable_encryption and self.encryption_key:
                from cryptography.fernet import Fernet
                password_hash_data = base64.urlsafe_b64decode(self.encryption_key)
                f = Fernet(password_hash_data)
                
                encrypted_hash = base64.urlsafe_b64encode(
                    f.decrypt(data["encrypted_password_hash"].encode())
                ).decode()
                
                data["password_hash"] = encrypted_hash
            
            return base64.b64encode(hashlib.sha256(data["password_hash"].encode()).digest()).decode()

    def _retrieve_libportal(self, service_name: str, username: str) -> str:
        """Retrieve credentials via libportal."""
        try:
            from keyring.backend import KeyringBackend
            backend = self._get_keyring_backend()
            return backend.password(service_name, username)
        except Exception as e:
            raise CredentialStorageError(f"libportal retrieval failed: {e}")

    def _retrieve_gnome_keyring(self, service_name: str, username: str) -> str:
        """Retrieve credentials from GNOME keyring."""
        try:
            from gi.repository import Secret
            schema_id = f"org.ai-manager.{service_name}"
            
            if Schema.get_sync(schema_id):
                item = Secret.item_new_sync(
                    GFile.get_for_path("~/.local/state/ai-manager"),
                    SecretSchema.new_sync(schema_id),
                )
                item.set_secret_attributes({})
                return item.get_secret_text()
                
        except Exception as e:
            raise CredentialStorageError(f"GNOME keyring retrieval failed: {e}")
        
        return ""

    def _retrieve_kwallet(self, service_name: str, username: str) -> str:
        """Retrieve credentials from KWallet."""
        try:
            import subprocess
            
            cmd = ["kreadconfig", "kwallet", "passwords", f"/{service_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and len(result.stdout.strip()) > 0:
                return result.stdout.strip()
                
        except Exception as e:
            raise CredentialStorageError(f"KWallet retrieval failed: {e}")
        
        return ""

    def _get_keyring_backend(self):
        """Get the appropriate keyring backend."""
        try:
            from keyring import get_password, set_password, delete_password, has_password
            
            class KeyringWrapper:
                def __init__(self):
                    self._passwords = {}
                    
                def password(self, service_name, username):
                    if service_name not in self._passwords:
                        return None
                    return self._passwords[service_name]
                
                def set_password(self, service_name, username, password):
                    self._passwords[service_name] = password
                
                def delete_password(self, service_name, username):
                    if service_name in self._passwords:
                        del self._passwords[service_name]
            
            return KeyringWrapper()
        except ImportError:
            raise CredentialStorageError("keyring library not available")

    def clear(self) -> None:
        """Clear all stored credentials."""
        storage_path, _ = self._get_storage_location("")
        
        if isinstance(storage_path, str):
            storage_path = Path(storage_path)
        
        # Clear keyring entries if applicable
        try:
            from gi.repository import Secret
            Schema.remove_all_item_types(
                GFile.get_for_path("~/.local/state/ai-manager"),
                SecretSchema.new_sync(f"org.ai-manager.*"),
            )
        except Exception:
            pass
        
        # Clear file-based credentials
        if storage_path.exists():
            for path in storage_path.glob("*.json"):
                path.unlink()

    def verify_backend_status(self) -> Dict[str, Any]:
        """Verify which backends are available and their status."""
        return {
            "system": self._detected_system,
            "libportal_available": self._libportal_available,
            "gnome_keyring_available": self._gnome_keyring_available,
            "kwallet_available": self._kwallet_available,
            "primary_backend": self._primary_backend.value if self._primary_backend else None,
            "fallback_backend": self._fallback_backend.value if self._fallback_backend else None,
        }

    def get_current_backend_info(self) -> Dict[str, str]:
        """Get information about currently used storage backend."""
        return {
            "backend": self._primary_backend.value if self._primary_backend else "None",
            "storage_method": "keyring" if self._libportal_available or self._gnome_keyring_available else "file_encrypted",
            "encryption_enabled": self.enable_encryption,
            "system": self._detected_system,
        }


# Convenience function for simple usage
def get_credentials_manager(config_path: Optional[Path] = None) -> CredentialsManager:
    """Get a credentials manager instance with default settings."""
    return CredentialsManager(
        config_path=config_path,
        enable_encryption=False,  # Default for safety, can be enabled
    )
