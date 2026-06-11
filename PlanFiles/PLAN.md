# AI Model Server Manager - Complete Development Plan

## Project Overview
A Linux desktop application that allows users to start/stop an AI model server running on a remote home server via SSH, without requiring manual SSH sessions. The app stores connection credentials securely and provides a simple UI with settings.

**Target Distribution:** Flatpak (for easy sandboxed deployment on any Linux distro)

---

## Technology Stack
- **Language:** Python 3 (with PyQt6)
- **SSH Library:** `paramiko`
- **Secure Storage:** `keyring` + Flatpak-specific backends (`libportal`)
- **Build System:** `flatpak-builder` + Meson/CMake for dependencies

---

## Phase Summary Links

| Phase | Focus | Duration | Plan File |
|-------|-------|----------|-----------|
| [Phase 1](./Phase_1_Protocol.md) | Project Setup & Architecture Design | 2 days | `Phase_1_Protocol.md` |
| [Phase 2](./Phase_2_UI_Development.md) | Core Application UI Development | 3 days | `Phase_2_UI_Development.md` |
| [Phase 3](./Phase_3_Process_Monitoring.md) | Process Monitoring & Script Integration | 2 days | `Phase_3_Process_Monitoring.md` |
| [Phase 4](./Phase_4_Security_Audit.md) | Security Audit & Comprehensive Testing | 2 days | `Phase_4_Security_Audit.md` |
| [Phase 5](./Phase_5_Packaging.md) | Flatpak Packaging & Final Release | 2 days | `Phase_5_Packaging.md` |

**Total Estimated Duration:** 11 days (with integrated testing)

---

## Security Considerations

### Password Storage Options (in priority order):

1. **Flatpak Portal Backend** (`org.gnome.keyring/libportal`)
   - Works within Flatpak sandbox
   - System-managed encryption via GNOME Keyring
   - **Best option for target distribution**

2. **System Keyring** (`gnome-keyring`, `kwallet`)
   - When running natively (not in Flatpak)
   - Platform-appropriate storage

3. **Encrypted local file fallback**
   - Use cryptography library with AES-256-GCM
   - Only used if user explicitly enables "Store Locally" option

### For Flatpak Development:
- Develop inside Flatpak sandbox using `flatpak-builder`
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
│   ├── credentials_manager.py   # Secure credential storage
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
- [✅] Toggle action button works (CONNECT green ↔ DISCONNECT red)
- [✅] Settings dialog accepts and saves IP, username
- [✅] "Save Credentials Securely" checkbox stores password in keyring
- [✅] Connectivity test button works (verifies server reachable)
- [✅] Visual feedback during operations (status bar, tooltips)
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
Test modules: SSH connection, credentials storage, configuration, UI components

### Integration Tests (run after Phase 1+2)
Tests requiring actual server connection:
- Start/stop command execution
- Script path validation
- Timeout behavior

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

## References

- Paramiko Documentation: https://docs.paramiko.org/
- Keyring Project: https://pypi.org/project/keyring/
- PyQt6 Documentation: https://riverbankcomputing.com/docstrings/html/pyqt6/index.html
- Flatpak Documentation: https://flatpak.github.io/flatpak-specification/
- libportal Backend: https://pypi.org/project/libportal-py/
