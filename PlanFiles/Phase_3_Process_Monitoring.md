# Phase 3: Process Monitoring & Script Integration

## Summary
Handle remote script execution and monitoring via SSH. Includes command wrappers, script-specific commands, error handling, and session cleanup logic. Testing is integrated immediately after each task.

**Estimated Duration:** 2 days  
**Target Distribution:** Flatpak

---

## Goals
- Implement SSH command wrapper with output handling
- Define and execute script-specific start/stop commands
- Add robust error handling for remote operations
- Ensure proper session cleanup after operations

---

## Tasks

### 1. SSH command wrapper with output handling
**Goal:** Capture and handle stdout/stderr from SSH sessions reliably.

**Location:** `src/ssh_client.py` (enhancement) or new module

**Features:**
- Capture stdout/stderr from SSH session
- Handle long-running script timeouts (configurable)
- Stream output as it arrives (optional real-time display)
- Proper cleanup on completion or interruption

**Testing Requirements (Unit + Integration):**
- Unit tests: Test command execution, timeout behavior
- Verify output capture works correctly
- Test timeout triggers when commands exceed limit
- Integration tests: Execute long-running commands with timeouts

---

### 2. Implement script-specific commands
**Goal:** Configure and execute start/stop scripts on the remote server.

**Features:**
- Start command: `sh /path/to/start.sh` (configurable via settings)
- Stop command: `sh /path/to/stop.sh` (configurable via settings)
- Handle non-existent scripts gracefully with appropriate error message
- Support alternative script paths per user configuration

**Testing Requirements (Integration):**
- Integration tests: Execute actual start commands on server
- Integration tests: Execute actual stop commands on server
- Test handling of missing/non-existent scripts
- Validate output and exit status capture

---

### 3. Error handling and diagnostics for remote operations
**Goal:** Provide clear feedback when remote operations fail.

**Features:**
- Parse SSH error messages intelligently (distinguish auth, network, script errors)
- Log connection issues to internal log (`~/.local/share/app-name/logs/`)
- Display helpful troubleshooting tips in error popups
- Differentiate between client-side and server-side failures

**Testing Requirements (Integration):**
- Test various failure modes and verify appropriate error messages
- Confirm logs capture detailed diagnostics
- Validate user-facing errors are clear and actionable

---

### 4. Session cleanup logic
**Goal:** Ensure SSH sessions terminate properly after operations.

**Features:**
- Auto-disconnect after successful script completion
- Handle disconnections during active operations gracefully
- Reconnect automatically if needed for subsequent operations
- Clean shutdown on application close

**Testing Requirements:**
- Unit tests: Verify cleanup on exit
- Test reconnection behavior when connection drops mid-operation
- Validate session termination leaves no lingering SSH connections
- Integration tests: Confirm clean state after each operation sequence

---

## Milestones for Phase 3

- [ ] **SSH command wrapper working:** Commands execute, output captured, timeouts enforced
- [ ] **Script commands functional:** Start/stop scripts run successfully on remote host
- [ ] **Error handling robust:** User receives clear messages for various failure modes
- [ ] **Session cleanup verified:** Connections terminate properly after operations
- [ ] **All Phase 3 tests passing:** Both unit and integration tests pass

---

## Deliverables
- Enhanced `/src/ssh_client.py` – With command wrapper and output handling
- Script path configuration integration in settings
- Error diagnostics and logging enhancements
- Session cleanup logic implementation
- `/tests/unit/ssh*` – Enhanced unit tests for SSH operations
- `/tests/integration/ssh*` – Enhanced integration tests with real server

---

## Next Steps (After Phase 3)
Proceed to Phase 4: Security Audit & Comprehensive Testing once script execution and error handling are fully tested.
