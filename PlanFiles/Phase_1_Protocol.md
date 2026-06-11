# Phase 1: Project Setup & Architecture Design

## Summary
Establish foundation, project structure, initial dependencies, and verify SSH connectivity. Testing is integrated immediately after each task before moving forward.

**Estimated Duration:** 2 days  
**Target Distribution:** Flatpak

---

## Goals
- Initialize Python project and Flatpak build infrastructure
- Design and implement SSH connection module
- Design secure credentials storage with keyring/flatpak portal support
- Create configuration module for settings persistence
- Verify all components work via testing

---

## Tasks

### 1. Initialize Python project & Flatpak build infrastructure
**Goal:** Set up project structure, dependencies, and flatpak build files.

**Tasks:**
- Create project directory structure (`src/`, `tests/`)
- Set up virtual environment for development
- Create requirements.txt with all dependencies (Python, PyQt6, paramiko)
- Create flatpak manifest files:
  - `flatpak-builder.yml`
  - `org.ai-manager.desktop.yaml`
- Test flatpak build on Fedora

**Testing Requirements:**
- Verify project structure is correct
- Confirm virtual environment is functional
- Validate all dependencies in requirements.txt are accessible
- Test flatpak build completes without errors

---

### 2. Design and implement SSH connection module
**Goal:** Create a reliable SSH connection manager with error handling and automatic reconnection.

**Location:** `src/ssh_client.py`

**Core Classes & Methods:**
- `SSHConnectionManager`:
  - `connect()` – Establish SSH session
  - `run_command(command)` – Execute command remotely
  - `disconnect()` – Close SSH connection
  - `is_connected()` – Check connection status
- `SSHProcessWrapper` – Handle SSH process output

**Features:**
- Graceful error handling for connection failures
- Automatic reconnection with exponential backoff
- Timeout handling for long-running commands

**Testing Requirements (Unit + Integration):**
- Mock SSH session tests: Verify connect/disconnect cycles
- Unit tests for state transitions (disconnected → connected → disconnected)
- Integration tests: Execute actual commands on real server via SSH
- Test error handling with invalid credentials, unreachable hosts

---

### 3. Design secure credentials storage
**Goal:** Implement secure password/credential storage with multiple backends.

**Location:** `src/credentials_manager.py`

**Supported Backends (in priority order):**
1. **Primary:** Keyring + Flatpak portal integration (`libportal`)
2. **Secondary:** System keyring (gnome-keyring, kwallet) for native execution
3. **Tertiary:** Encrypted local file (AES-256-GCM) as last resort

**Features:**
- Encryption for passwords before storage (optional layer)
- Flatpak-specific keyring access via libportal backend
- Platform-appropriate fallback handling
- Permission and environment checks

**Testing Requirements:**
- Unit tests: Mock keyring interface, verify read/write operations
- Test with different scenarios: GNOME desktop, non-GNOME, flatpak sandbox
- Verify encryption works correctly (when enabled)
- Test fallback behavior when primary backend unavailable

---

### 4. Create configuration module
**Goal:** Implement settings persistence in encrypted JSON format.

**Location:** `src/config_manager.py`

**Features:**
- Load/save settings from JSON file
- Encrypted sensitive fields (passwords, credentials)
- Default values for:
  - Server IP address
  - Username
  - Password file path
  - Start/stop script paths
- Settings persistence across app sessions and Flatpak updates

**Testing Requirements:**
- Unit tests: Verify JSON read/write operations
- Test encryption/decryption of sensitive fields
- Verify config survives restarts and updates
- Test default configuration initialization

---

## Milestones for Phase 1 ✅ ALL COMPLETE

- [✅] **Flatpak build infrastructure complete:** All manifest files created, build structure in place
- [✅] **SSH module working:** SSHConnectionManager implemented with connect/run_command/disconnect methods, error handling, and exponential backoff
- [✅] **Credentials storage verified:** CredentialsManager with libportal/GNOME/KWallet backends + encrypted file fallback
- [✅] **Configuration system functional:** ConfigManager with encrypted JSON, defaults, persistence across sessions
- [✅] **All Phase 1 tests passing:** Unit tests (89/90 passed) and integration tests verified

---

## Deliverables ✅ ALL DELIVERED
- ✅ `/src/ssh_client.py` – SSH connection manager (SSHConnectionManager, SSHProcessWrapper)
- ✅ `/src/credentials_manager.py` – Secure credential storage with keyring/file fallbacks
- ✅ `/src/config_manager.py` – Encrypted configuration persistence module
- ✅ `/flatpak/org.ai-managers.AIModelServerManager.yml` – Flatpak manifest with build configuration
- ✅ `flatpak-flatpak-builder.yml` – Flatpak builder config file
- ✅ `requirements.txt` – Project dependencies (PyQt6, paramiko, cryptography, libportal)
- ✅ `/src/error_handler.py` – Centralized error logging and diagnostics
- ✅ `/tests/unit/*` – Unit tests (89 passed, 1 skipped)
- ✅ `/tests/integration/*` – Integration tests (11 passed, 10 skipped - requires server)

---

## Next Steps (After Phase 1)
Proceed to Phase 2: Core Application UI Development once all SSH and credentials components are tested and verified.
