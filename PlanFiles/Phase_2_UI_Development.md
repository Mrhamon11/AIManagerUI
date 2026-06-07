# Phase 2: Core Application UI Development

## Summary
Build functional GUI with all required features for starting/stopping AI model servers. Includes main window, toolbar buttons, settings panel, and error handling. Testing is integrated immediately after each task.

**Estimated Duration:** 3 days  
**Target Distribution:** Flatpak

---

## Goals
- Implement main window structure with responsive layout
- Build Start/Stop button functionality with visual feedback
- Create settings panel for server configuration
- Add comprehensive error handling and diagnostics

---

## Tasks

### 1. Implement main window structure
**Goal:** Create the application skeleton with QMainWindow, toolbar, status bar, and split view.

**Location:** `src/ui/main_window.py` (or `main_window.py`)

**Features:**
- QMainWindow with toolbar containing action buttons
- Split into:
  - **Action area:** Main controls (Start/Stop buttons)
  - **Settings panel:** Configuration inputs
- Responsive layout for different screen sizes
- Flatpak-specific handling: sandbox permissions, desktop integration

**Testing Requirements:**
- Unit tests: Verify widget creation, layout management
- Test responsive behavior at different window sizes
- Validate toolbar and status bar rendering

---

### 2. Build Start/Stop button functionality
**Goal:** Implement primary user actions with proper state management.

**Location:** Toolbar in main window

**Features:**
- Main toolbar button with clear icons:
  - ▶️ Start icon for starting the server script
  - ⏹ Stop icon for stopping the server script
- Button states: enabled/disabled based on connection status
- Progress/status indicator during script execution
- Prevent double-clicking while script is running
- Visual feedback via tooltip, status bar message

**Testing Requirements (Integration):**
- Verify button state changes (enabled ↔ disabled)
- Test visual feedback appears during operations
- Confirm single-button-lock prevents accidental re-execution
- Validate connection-state-dependent enabling/disabling

---

### 3. Create settings panel
**Goal:** Allow users to configure server connection and credentials securely.

**Location:** Settings dialog/panel (`src/ui/settings_dialog.py`)

**Features:**
- Input fields for:
  - Server IP address (IPv4 or hostname)
  - Username
- "Save Credentials Securely" checkbox to store password in keyring
- Connectivity test button with visual result indicator (ping server)
- Connection status indicators (disconnected/connected/connecting)
- Last connection timestamp display

**Testing Requirements:**
- Unit tests: Verify form validation rules
- Test connectivity checks work correctly
- Validate credential storage checkbox behavior
- Verify status indicator updates

---

### 4. Add error handling and diagnostics
**Goal:** Provide helpful feedback when operations fail.

**Location:** Various modules + dialogs

**Features:**
- Log connection issues to internal log (`~/.local/share/app-name/logs/`)
- Error popup with helpful troubleshooting tips
- Clear error messages for common failure modes

**Testing Requirements (Integration):**
- Test various error scenarios and verify appropriate popups
- Confirm logs are written correctly
- Validate error messages are user-friendly and actionable

---

## Milestones for Phase 2

- [ ] **Main window complete:** Window opens with all UI elements visible and responsive
- [ ] **Start/Stop buttons functional:** Buttons respond to clicks, state changes appropriately
- [ ] **Settings panel working:** Users can input server config and test connectivity
- [ ] **Error handling in place:** User sees appropriate feedback on failures
- [ ] **All Phase 2 tests passing:** Both unit and integration tests pass

---

## Deliverables
- `/src/ui/main_window.py` – Main application window implementation
- `/src/ui/settings_dialog.py` – Settings panel dialog
- `/resources/icons/*.svg`, `*.png` – Application icon assets (optional)
- `/logs/` directory structure for app logs
- `/tests/unit/ui*` – Unit tests for UI components
- `/tests/integration/ui*` – Integration tests for UI workflows

---

## Next Steps (After Phase 2)
Proceed to Phase 3: Process Monitoring & Script Integration once the UI is fully functional and tested.
