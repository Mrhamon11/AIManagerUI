# AI Model Server Manager - Development Plan

## Project Overview
A Linux desktop application that allows users to start/stop an AI model server running on a remote home server via SSH, without requiring manual SSH sessions. The app will store connection credentials securely and provide a simple UI with settings.

**Target Distribution:** Flatpak (for easy sandboxed deployment on any Linux distro)

---

## Technology Stack Decision
**Language:** Python 3 (with PyQt6)
- **Why:** Cross-platform support, mature libraries, active community, easy to prototype
- **Alternatives considered:** C++/Qt (more complex), Electron (overkill)

**SSH Library:** `paramiko`
- Reliable SSH2 implementation for Python
- Works on all major Linux distributions including Fedora
- Compatible with Flatpak sandboxed environment

**Secure Storage:** `keyring` + Flatpak-specific backends
- **Primary:** `keyrings.backends.keyring` with flatpak portal integration (`libportal`)
- **Secondary:** System keyring fallback (gnome-keyring, kwallet) when running natively
- **Tertiary:** Encrypted local file as last resort

**Build System:** `flatpak-builder` + `Meson`/`CMake` for dependencies
- Use `pyproject.toml` with flatpak metadata
- Bundle Python app in Flatpak sandbox
- Handle Flatpak-specific environment variables (e.g., `$FLATPAK_SESSION_ID`)

---

## Development Phases

### Phase 1: Project Setup & Architecture Design [TESTED]
**Estimated Duration:** 2 days
**Goals:** Establish foundation, project structure, initial dependencies, verify SSH connectivity

**Testing Integration:** All tests run immediately after each task. Tests are written and verified before moving forward.

**Tasks:**
1. **Initialize Python project & Flatpak build infrastructure**
   - Create project directory structure (`src/`, `tests/`)
   - Set up virtual environment for development
   - Create requirements.txt with all dependencies
   - Create flatpak manifest files (flatpak-builder.yml, org.ai-manager.desktop.yaml)
   - Test flatpak build on Fedora

2. **Design and implement SSH connection module [TESTED]**
   - Module: `ssh_client.py`
   - Classes: `SSHConnectionManager`, `SSHProcessWrapper`
   - Methods: connect(), run_command(), disconnect(), is_connected()
   - Handle connection errors gracefully
   - Implement automatic reconnection on failures (exponential backoff)
   - **Write unit tests:** Mock SSH session, test connect/disconnect cycles
   - **Write integration tests:** Test with actual server (verify commands execute)

3. **Design secure credentials storage [TESTED]**
   - Module: `credentials_manager.py`
   - Support multiple backends (keyring + flatpak portal, encrypted file fallback)
   - Implement encryption for passwords before storage (optional, additional layer)
   - Handle Flatpak-specific keyring access via libportal backend
   - Test with different scenarios (GNOME desktop, non-GNOME, flatpak sandbox)
   - **Write unit tests:** Mock keyring interface, verify read/write operations

4. **Create configuration module [TESTED]**
   - Module: `config_manager.py`
   - Load/save settings from JSON (with encrypted sensitive fields)
   - Default values for IP, username, password file path
   - Settings persistence across app sessions and Flatpak updates
   - **Write unit tests:** Verify JSON read/write, encryption/decryption

---

### Phase 2: Core Application UI Development [TESTED]
**Estimated Duration:** 3 days
**Goals:** Build functional GUI with all required features

**Testing Integration:** All tests run immediately after each task.

**Tasks:**
1. **Implement main window structure [TESTED]**
   - Create QMainWindow with toolbar and status bar
   - Split into action area and settings panel
   - Implement responsive layout for different screen sizes
   - Flatpak-specific: Handle sandbox permissions and desktop integration
   - **Write unit tests:** Verify widget creation, layout management

2. **Build Start/Stop button functionality [TESTED]**
   - Main toolbar button with clear icons (▶️ start, ⏹ stop)
   - Button states: enabled/disabled based on connection status
   - Progress/status indicator during script execution
   - Prevent double-clicking while script is running
   - Visual feedback (tooltip, status bar message)
   - **Write integration tests:** Verify button state changes, visual feedback

3. **Create settings panel [TESTED]**
   - Input fields for: Server IP, Username
   - "Save Credentials Securely" checkbox to store password in keyring
   - Connectivity test button with visual result indicator (ping server)
   - Connection status indicators (disconnected/connected/connecting)
   - Last connection timestamp
   - **Write unit tests:** Verify form validation, connectivity checks

4. **Add error handling and diagnostics [TESTED]**
   - Log connection issues to internal log (`~/.local/share/app-name/logs/`)
   - Error popup with helpful troubleshooting tips
   - **Write integration tests:** Test various error scenarios

---

### Phase 3: Process Monitoring & Script Integration [TESTED]
**Estimated Duration:** 2 days
**Goals:** Handle remote script execution and monitoring

**Testing Integration:** All tests run immediately after each task.

**Tasks:**
1. **SSH command wrapper with output handling [TESTED]**
   - Capture stdout/stderr from SSH session
   - Handle long-running script timeouts (configurable)
   - **Write unit tests:** Test command execution, timeout behavior

2. **Implement script-specific commands [TESTED]**
   - Start command: `sh /path/to/start.sh` (configurable via settings)
   - Stop command: `sh /path/to/stop.sh` (configurable via settings)
   - Handle non-existent scripts gracefully
   - **Write integration tests:** Execute actual start/stop commands on server

3. **Error handling and diagnostics [TESTED]**
   - Parse SSH error messages intelligently
   - Log connection issues to internal log
   - Error popup with helpful troubleshooting tips
   - **Write integration tests:** Test various failure modes

4. **Session cleanup logic [TESTED]**
   - Auto-disconnect after successful script completion
   - Handle disconnections during active operations gracefully
   - Reconnect automatically if needed for second operation
   - **Write unit tests:** Verify cleanup on exit, reconnection behavior

---

### Phase 4: Security Audit & Comprehensive Testing [TESTED]
**Estimated Duration:** 2 days
**Goals:** Ensure robustness and user-friendly error messages

**Testing Integration:** This phase focuses on security and edge cases. All tests run immediately after each task.

**Tasks:**
1. **Comprehensive SSH testing [TESTED]**
   - Test with various server versions (OpenSSH)
   - Test SSH key-based auth vs password authentication
   - Test various IP formats (IPv4, hostname)
   - Test connection timeouts and retries
   - **Document findings**

2. **Edge case testing [TESTED]**
   - Empty fields in settings
   - Invalid server credentials
   - Server not responding to commands
   - Script execution failures on remote host
   - Rapid clicking of start/stop buttons
   - Flatpak permission sandboxing
   - **Document findings**

3. **Security audit [TESTED]**
   - Verify passwords are encrypted in storage (when enabled)
   - Check no plaintext credentials in process memory after operations
   - Test credential file permissions (if using local storage)
   - Review for potential injection vulnerabilities
   - Verify Flatpak sandbox works correctly with keyring access
   - **Document findings**

4. **User documentation [TESTED]**
   - Create README.md with setup instructions
   - Document secure storage recommendations (keyring vs encrypted file)
   - List troubleshooting steps for common issues
   - Include Flatpak-specific installation instructions

---

### Phase 5: Flatpak Packaging & Final Release [TESTED]
**Estimated Duration:** 2 days
**Goals:** Create production-ready Flatpak package

**Testing Integration:** All tests run immediately after each task.

**Tasks:**
1. **Optimize Flatpak manifest [TESTED]**
   - Define required runtime dependencies (Python, paramiko, PyQt6)
   - Set sandbox permissions correctly for keyring access
   - Bundle application icons and metadata
   - Test on Fedora 39/40, Ubuntu 24.04, Arch Linux

2. **Create AppStream metadata [TESTED]**
   - Generate appstream.xml for Software Center integration
   - Include category tags (System Tools, Utilities), screenshots
   - Set correct package versioning scheme

3. **Final integration testing [TESTED]**
   - Install Flatpak from local build and verify functionality
   - Test upgrade path from development version
   - Verify sandbox isolation and keyring access works correctly

4. **Release documentation [TESTED]**
   - Update README with installation instructions for all distros
   - Create release notes
   - Prepare for potential upload to FlatHub (optional)

---

## Security Considerations

### Password Storage Options (in priority order):

1. **Flatpak Portal Backend (org.gnome.keyring/libportal)**
   - Works within Flatpak sandbox
   - System-managed encryption via GNOME Keyring
   - Secure across all Fedora/Ubuntu environments with GNOME/KDE
   - **Best option for target distribution**

2. **System Keyring (gnome-keyring, kwallet)**
   - When running natively (not in Flatpak)
   - Platform-appropriate storage

3. **Encrypted local file fallback**
   - Use cryptography library with AES-256-GCM
   - Only used if user explicitly enables "Store Locally" option
   - Encrypted key stored separately (or derived from password prompt)

### For Flatpak Development:
- Develop inside Flatpak sandbox using `flatpak-builder`
- This ensures the app works within its own permissions
- Test with both flatpak and non-flatpak execution paths

### Do NOT:
- Store passwords in plain JSON files (even in config directory)
- Use /etc/ssh/ for storing credentials (wrong purpose)
- Log full SSH command with passwords
- Keep plaintext credentials in memory longer than necessary

---

## Project Directory Structure
```
AIModelServerManager/
├── main.py                      # Application entry point
├── src/
│   ├── __init__.py
│   ├── ssh_client.py            # SSH connection manager
│   ├── credentials_manager.py   # Secure credential storage (keyring + flatpak support)
│   ├── config_manager.py        # Settings persistence
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py       # Main application window
│       └── settings_dialog.py   # Settings panel
├── resources/
│   ├── icons/                   # Application icons (SVG + PNG)
│   └── scripts/                 # Sample script locations (config only)
├── config/
│   ├── sample_config.json       # Default settings template
│   └── credentials.encrypted    # Example encrypted credential format (optional)
├── flatpak/
│   ├── org.ai-managers.AIModelServerManager.yml      # Flatpak manifest
│   ├── org.ai-managers.AIModelServerManager.desktop  # Desktop file
│   └── com.github.ai-managers.AIModelServerBuilder.json  # Build config
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests for each module
│   ├── integration/             # Integration tests requiring server connection
│   └── fixtures/                # Test fixtures and mock data
├── requirements.txt
├── setup.py                     # Or pyproject.toml
├── README.md
├── PLAN.md                      # This file
└── NEWS.md                      # Release notes / changelog
```

---

## Milestones & Review Points (Testing-Integrated)

### Milestone 1: SSH Connection MVP [TESTED]
- [ ] SSHConnectionManager works with real server
- [ ] Commands execute successfully via SSH
- [ ] Error handling tested for various failure modes
- **Review:** Can we trigger actual start/stop? Is connection stable under different network conditions?

### Milestone 2: UI & Settings Panel [TESTED]
- [ ] Settings dialog accepts and saves IP, username
- [ ] "Save Credentials Securely" checkbox stores password in keyring
- [ ] Connectivity test button works (verifies server reachable)
- [ ] Start/Stop buttons respond to user input
- [ ] Visual feedback during operations (status bar, tooltips)
- **Review:** Does the UI feel responsive? Are error messages helpful?

### Milestone 3: Script Execution & Error Handling [TESTED]
- [ ] Start button executes script on remote server
- [ ] Stop button executes cleanup script
- [ ] Timeout handling prevents hanging operations
- [ ] Reconnection works after disconnect
- [ ] Errors displayed clearly to user
- **Review:** End-to-end workflow functions correctly.

### Milestone 4: Flatpak Packaging & Testing [TESTED]
- [ ] Flatpak builds without errors
- [ ] App runs inside Flatpak sandbox
- [ ] Keyring access works via flatpak portal
- [ ] Tested on Fedora and at least one other distro (Ubuntu/Arch)
- [ ] Upgrade path from development version works
- **Review:** Distribution is ready for user installation.

---

## Testing Strategy

### Unit Tests (run automatically after Phase 1 & 2)
```python
# examples of what we test:
def test_ssh_connect_disconnect():
    manager = SSHConnectionManager()
    assert manager.is_connected() == False
    # connect logic tested here
    
def test_credentials_store_retrieve():
    manager = CredentialsManager()
    manager.set_username("test", "user")
    username = manager.get_username()
    assert username == "user"
```

### Integration Tests (run after Phase 1+2)
```python
# tests that require actual server connection
def test_start_command_executes():
    with SSHConnectionManager(server_config) as ssh:
        result = ssh.run_command("/path/to/start.sh")
        assert result.exit_status == 0
        
def test_stop_command_executes():
    with SSHConnectionManager(server_config) as ssh:
        result = ssh.run_command("/path/to/stop.sh")
        assert result.exit_status == 0
```

### Flatpak Compatibility Tests
- Build in Fedora sandbox environment
- Test keyring access from within flatpak-builder container
- Verify app works on Arch (which doesn't use gnome-keyring by default)
- Test with KDE desktop environments (different keyring implementations)

---

## Potential Issues and Mitigations

| Issue | Mitigation | Phase |
|-------|------------|-------|
| SSH library not available in flatpak runtime | Add paramiko to build dependencies | 1 |
| No keyring service on target system | Implement encrypted file fallback | 1 |
| Script paths differ per user | Allow user to specify paths in settings | 3 |
| Connection timeouts | Implement exponential backoff reconnection | 3 |
| GUI freezes during long scripts | Run SSH commands asynchronously (QTimer) | 2 |
| Flatpak permission issues for keyring | Use libportal backend for sandbox access | 1 |

---

## Next Steps (First 48 Hours)

1. [ ] Create project directory structure with flatpak build files
2. [ ] Verify Fedora Python environment and available packages
3. [ ] Set up virtual environment for development inside Flatpak container
4. [ ] Create minimal SSHConnectionManager with unit tests
5. [ ] Test SSH connection to actual server
6. [ ] Implement credentials manager with keyring support
7. [ ] Write integration tests for SSH commands

---

## References

- Paramiko Documentation: https://docs.paramiko.org/
- Keyring Project: https://pypi.org/project/keyring/
- PyQt6 Documentation: https://riverbankcomputing.com/docstrings/html/pyqt6/index.html
- Flatpak Documentation: https://flatpak.github.io/flatpak-specification/
- Flatpak Builder Guide: https://docs.flatpak.org/en/latest/build-a-flatpak-from-scratch.html
- libportal Backend: https://pypi.org/project/libportal-py/
