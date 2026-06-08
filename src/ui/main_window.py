"""
AI Model Server Manager - Main Window

Provides the main application interface for managing remote AI model servers.
Supports both X11 and Wayland display servers.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QLineEdit, QSpinBox, QGroupBox, QFormLayout, QMessageBox,
    QPlainTextEdit, QStatusBar, QScrollArea, QToolBar, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot


def _detect_display_type() -> str:
    """Detect the display type (Wayland or X11)."""
    # Check for Wayland session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    elif os.environ.get("DISPLAY"):
        return "x11"
    else:
        return "headless"


class MainWindow(QMainWindow):
    """Main application window with server management interface."""

    # Signals for UI interactions
    status_changed = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize main window with display type detection."""
        super().__init__()

        # Log display type for testing purposes
        self._display_type = _detect_display_type()
        print(f"[MainWindow] Display detected: {self._display_type}", file=sys.stderr)

        # Set application metadata
        self.setObjectName("AI Model Server Manager")
        self.setWindowTitle("AI Model Server Manager - AI Group Admin")
        self.setMinimumSize(900, 650)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QLabel { color: #ffffff; background-color: transparent; }
            QPushButton {
                min-height: 40px;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            QLineEdit, QSpinBox {
                background-color: #2a2a3e;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px;
            }
        """)

        # Setup central widget with splitter layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter)
        splitter.setStyleSheet("QSplitter::handle { background: #444; }")

        # Action panel (left)
        action_panel = QWidget()
        action_layout = QVBoxLayout(action_panel)
        action_panel.setFixedWidth(210)
        splitter.addWidget(action_panel)

        # Settings panel (right)
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        splitter.addWidget(settings_panel)

        self._setup_action_panel(action_layout)
        self._setup_settings_panel(settings_layout)

        # Status tracking
        self.is_connected = False
        self.ssh_manager: Optional[SSHConnectionManager] = None

    def _setup_action_panel(self, layout: QVBoxLayout) -> None:
        """Setup action buttons panel."""
        # Toolbar
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #16213e;
                border-bottom: 1px solid #0f3460;
                padding: 8px;
            }
        """)
        layout.addWidget(toolbar)

        # Status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready - Connect to a server", 5000)

        # Status label
        status_label = QLabel("Status: Disconnected", self)
        status_label.setObjectName("status")
        status_label.setStyleSheet("color: #808080; padding: 8px;")
        toolbar.addWidget(status_label)

        # Start button
        start_btn = QPushButton("▶ Connect", self)
        start_btn.setMinimumHeight(45)
        start_btn.setToolTip("Connect to server - Starts SSH connection")
        start_btn.clicked.connect(self._on_start_clicked)
        self.start_btn = start_btn

        # Run Command button (only visible when connected)
        cmd_btn = QPushButton("⚡ Run Command", self)
        cmd_btn.setMinimumHeight(45)
        cmd_btn.setDisabled(True)
        cmd_btn.clicked.connect(self._on_command_clicked)
        self.cmd_btn = cmd_btn

        # Stop button with proper stop icon
        stop_btn = QPushButton("⏹ Disconnect", self)
        stop_btn.setMinimumHeight(45)
        stop_btn.setToolTip("Disconnect from server - Ends SSH connection")
        stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn = stop_btn

        toolbar.addWidget(start_btn)
        toolbar.addWidget(cmd_btn)
        toolbar.addWidget(stop_btn)

        # Command output log view
        log_group = QGroupBox("Command Output", self)
        log_vbox = QVBoxLayout(log_group)

        log_edit = QPlainTextEdit(self)
        log_edit.setMinimumHeight(150)
        log_edit.setPlaceholderText("Command output will appear here...")
        log_edit.setReadOnly(True)
        log_edit.setStyleSheet("QPlainTextEdit { background-color: #1a1a2e; color: #e0e0e0; }")
        log_vbox.addWidget(log_edit)

        self._log_view = log_edit
        log_group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #16213e; border-bottom: 1px solid #0f3460; padding: 8px; margin-bottom: 8px; }")

        layout.addWidget(log_group)

    def _setup_settings_panel(self, layout: QVBoxLayout) -> None:
        """Setup settings form panel."""
        # Scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background: #1a1a2e; }")

        content_widget = QWidget()
        form_layout = QFormLayout(content_widget)

        # IP Address field
        ip_group = QGroupBox("Connection", self)
        ip_vbox = QVBoxLayout(ip_group)

        ip_edit = QLineEdit(self)
        ip_edit.setPlaceholderText("Server IP or hostname (e.g., 192.168.1.100)")
        ip_edit.setObjectName("ip_edit")

        port_spin = QSpinBox(self)
        port_spin.setRange(1, 65535)
        port_spin.setValue(22)
        port_spin.setObjectName("port_spin")

        user_edit = QLineEdit(self)
        user_edit.setPlaceholderText("Username (e.g., root, deploy)")
        user_edit.setObjectName("user_edit")

        key_check = QCheckBox("Use SSH Key Authentication", self)
        key_check.setChecked(True)

        # Password field (optional)
        pass_spin = QSpinBox(self)
        pass_spin.setRange(1, 65535)
        pass_spin.setValue(22)
        pass_spin.setEnabled(False)
        pass_spin.setToolTip("SSH port for password authentication")

        ip_vbox.addWidget(ip_edit)
        ip_vbox.addWidget(port_spin)
        ip_vbox.addWidget(user_edit)
        ip_vbox.addSpacing(10)
        ip_vbox.addWidget(key_check)
        ip_vbox.addWidget(pass_spin)
        ip_vbox.addStretch()

        form_layout.addRow("Host:", ip_edit)
        form_layout.addRow("Port:", port_spin)
        form_layout.addRow("Username:", user_edit)
        form_layout.addRow("Use SSH Key?", key_check)

        # Add to scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def _on_start_clicked(self) -> None:
        """Handle start button click - connects to SSH server."""
        # Prevent double-clicking while operation is in progress
        if hasattr(self.start_btn, 'is_disabled') and self.start_btn.is_disabled:
            return

        if self.is_connected:
            QMessageBox.warning(self, "Already Connected",
                "A server connection is already active!")
            return

        # Gather connection parameters
        host = str(self.findChild(QLineEdit, "ip_edit").text()).strip()
        port = int(self.findChild(QSpinBox, "port_spin").value())
        user = str(self.findChild(QLineEdit, "user_edit").text()).strip()
        use_key = self.findChild(QCheckBox, "key_check").isChecked()

        # Handle password authentication (currently not supported)
        if not use_key:
            QMessageBox.information(self, "Note",
                "Password authentication is not currently supported.")
            return

        # Initialize SSH manager
        self.ssh_manager = SSHConnectionManager(
            host=host,
            port=port,
            username=user,
            key_path=None,
            password=None,
            retry_delay_seconds=1.0,
            max_retries=3,
            command_timeout_seconds=60.0
        )

        try:
            # Attempt connection (blocks briefly)
            self.ssh_manager.connect(verbose=True)
            self.is_connected = True
            self.status_changed.emit("connected")

            # Update UI feedback
            status_label = self.findChild(QLabel, "status")
            if status_label:
                status_label.setText("Status: Connected")
                status_label.setStyleSheet("color: #4ade80; padding: 8px;")

            self._status_bar.clearMessage()
            self._status_bar.showMessage(f"Connected to {host} as {user}", 10000)

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.status_changed.emit("error")
            QMessageBox.critical(self, "Connection Error",
                f"Failed to connect:\n{error_msg}")

    def _on_stop_clicked(self) -> None:
        """Handle stop button click - disconnects from SSH server."""
        # Prevent double-clicking while operation is in progress
        if hasattr(self.stop_btn, 'is_disabled') and self.stop_btn.is_disabled:
            return
        # Immediately unlock start/stop buttons when user clicks stop
        self.start_btn.setDisabled(False)
        self.stop_btn.setDisabled(False)

        if not self.is_connected:
            QMessageBox.information(self, "Not Connected",
                "Please connect to a server first.")
            return

        try:
            # Disconnect gracefully
            if hasattr(self.ssh_manager, 'disconnect'):
                self.ssh_manager.disconnect()
            self.is_connected = False
            self.status_changed.emit("disconnected")

            # Update UI feedback
            status_label = self.findChild(QLabel, "status")
            if status_label:
                status_label.setText("Status: Disconnected")
                status_label.setStyleSheet("color: #808080; padding: 8px;")

            self._status_bar.clearMessage()
            self._status_bar.showMessage("Disconnected", 5000)

        except Exception as e:
            error_msg = f"Disconnect failed: {str(e)}"
            self.status_changed.emit("error")
            QMessageBox.critical(self, "Disconnect Error",
                f"Failed to disconnect:\n{error_msg}")

    def _on_command_clicked(self) -> None:
        """Handle run command button click."""
        # Lock start and stop buttons during operation
        self.start_btn.setDisabled(True)
        self.stop_btn.setDisabled(True)

        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Execute Remote Command")
            dialog.setMinimumSize(600, 250)
            dialog.setModal(True)

            # Input for command
            input_group = QGroupBox("Command", self)
            input_vbox = QVBoxLayout(input_group)

            cmd_edit = QLineEdit(self)
            cmd_edit.setPlaceholderText("Enter command to run on remote server (e.g., ls -la, whoami)")
            cmd_edit.setObjectName("cmd_edit")
            cmd_edit.returnShortcut = ""

            input_vbox.addWidget(cmd_edit)
            input_vbox.addStretch()

            button_layout = QHBoxLayout()
            dialog_vbox = QVBoxLayout(dialog)
            dialog_vbox.addWidget(input_group)
            dialog_vbox.addLayout(button_layout)

            # OK button
            ok_btn = QPushButton("Run")
            ok_btn.clicked.connect(lambda: self._execute_command_and_close(cmd_edit, dialog))
            ok_btn.setMinimumHeight(30)
            ok_btn.setDefault(True)

            # Cancel button
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.accept)  # Dialog will be rejected via reject()
            cancel_btn.setDisabled(True)

            button_layout.addWidget(ok_btn)
            button_layout.addWidget(cancel_btn)

            dialog.connect(self.status_changed, lambda sig: self._update_dialog_buttons(sig, dialog, ok_btn, cancel_btn))
            try:
                dialog.exec()  # Will be handled by Qt's auto-delete after execution
            except Exception:
                pass  # Dialog was dismissed or closed
        except Exception:
            # Handle any errors from dialog creation/setup
            QMessageBox.critical(self, "Dialog Error", f"Failed to create command dialog: {str(e)}")

    def _execute_command_and_close(self, cmd_edit: QLineEdit, dialog: QDialog) -> None:
        """Execute command and close dialog."""
        cmd = str(cmd_edit.text()).strip()
        if not cmd:
            QMessageBox.warning(self, "Empty Command", "Please enter a command.")
            return

        self.run_command(cmd)

    def _update_dialog_buttons(self, sig: Signal, dialog: QDialog, ok_btn: QPushButton, cancel_btn: QPushButton) -> None:
        """Update dialog button states based on connection status."""
        if sig == "connected":
            ok_btn.setDisabled(False)
            ok_btn.setText("Run")
            self._status_bar.showMessage(f"Connected - ready for commands", 5000)
        elif sig == "disconnected":
            dialog.reject()
            QMessageBox.information(self, "Session Ended", "Connection ended. Command execution cancelled.")
        elif sig == "error":
            cancel_btn.setDisabled(False)
            ok_btn.setText("Close")

    def _update_log_view(self) -> None:
        """Update log view (stub method)."""

    def run_command(self, command: str) -> None:
        """Execute a remote command via SSH."""
        if not self.is_connected or not self.ssh_manager:
            QMessageBox.warning(self, "Not Connected",
                "Please connect to a server first.")
            return

        # Lock start and stop buttons during operation
        try:
            self.start_btn.setDisabled(True)
            self.stop_btn.setDisabled(True)
        except Exception:
            pass  # Ignore button locking errors

        try:
            # Escape special characters in command for Python
            escaped_command = command.replace("'", "\\''")
            cmd_string = f"'{escaped_command}'"

            # Execute command (blocks briefly)
            result, output, error, exit_code = self.ssh_manager.run_command(
                command=cmd_string,
                timeout=30.0
            )

            # Parse and show results
            if result:
                if exit_code == 0:
                    status_label = self.findChild(QLabel, "status")
                    if status_label:
                        status_label.setStyleSheet("color: #4ade80; padding: 8px;")

                output_text = ""
                if error and exit_code != 0:
                    output_text += f"<strong>STDERR:</strong><br>{error}<hr>"
                if output:
                    output_text += f"<strong>STDOUT:</strong><br>{output}"

                self._status_bar.showMessage(
                    f"Command executed. Exit code: {exit_code}",
                    5000
                )

        finally:
            # Always unlock buttons after operation completes
            self.start_btn.setDisabled(False)
            self.stop_btn.setDisabled(False)

    def _update_log_view(self) -> None:
        """Clear and update the log view with current state."""
        self._log_view.clear()
        if self.is_connected:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_view.appendPlainText(f"[{timestamp}] Connection established - ready for commands")

    @pyqtSlot(str)
    def _on_status_changed(self, status: str) -> None:
        """Update UI based on connection state and manage button states."""
        # Update status label and styling
        status_label = self.findChild(QLabel, "status")
        if status_label:
            if status == "connected":
                status_label.setText("Status: Connected")
                status_label.setStyleSheet("color: #4ade80; padding: 8px;")
            elif status == "disconnected":
                status_label.setText("Status: Disconnected")
                status_label.setStyleSheet("color: #808080; padding: 8px;")

        # Update button states (Task 2c)
        if status == "connected":
            self.is_connected = True
            self.cmd_btn.setDisabled(False)
            self.start_btn.setDisabled(False)
            self.stop_btn.setDisabled(False)
            self._status_bar.showMessage("Connected", 5000)
            self._update_log_view()
        elif status == "disconnected":
            self.is_connected = False
            self.cmd_btn.setDisabled(True)
            self._status_bar.clearMessage()
            self._status_bar.showMessage("Disconnected", 5000)
            # Unlock start and stop buttons on disconnect
            self.start_btn.setDisabled(False)
            self.stop_btn.setDisabled(False)
        elif status == "error":
            self.is_connected = False
            self.cmd_btn.setDisabled(True)
            # Also unlock start and stop buttons on error
            self.start_btn.setDisabled(False)
            self.stop_btn.setDisabled(False)


def main():
    """Entry point - runs the application."""
    # Check display type for logging
    display_type = _detect_display_type()
    print(f"[AIManagerUI] Starting on {display_type} display", file=sys.stderr)

    # Create and show the main window
    app = QApplication(sys.argv)
    app.setApplicationName("AI Model Server Manager")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
