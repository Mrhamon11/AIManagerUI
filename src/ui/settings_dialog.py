"""
AI Model Server Manager - Settings Dialog

Provides configuration interface for server connection and credentials storage.
Implements Task 3: Complete settings panel with connection testing and timestamp tracking.
"""

import socket
import getpass
from typing import Optional, Dict
from datetime import datetime
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QFormLayout,
    QWidget, QScrollArea, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QAction
from src.error_handler import ErrorHandler


class ConnectionTester(QThread):
    """Background thread for testing server connectivity."""

    result_ready = pyqtSignal(str, str)  # status, message

    def __init__(self, host: str, port: int = 22):
        super().__init__()
        self.host = host
        self.port = port
        self._running = False

    def run(self) -> None:
        """Run connection test in background thread."""
        try:
            if not self.host or not self.host.strip():
                self.result_ready.emit("error", "No host specified")
                return

            # Test 1: TCP connection (ping the port)
            socket_error = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    self.result_ready.emit("connected", f"Server reachable on port {self.port}")
                    return
            except socket.error as e:
                socket_error = str(e)

            # Test 2: DNS/hostname resolution test
            try:
                ip_address = socket.gethostbyname(self.host) if self.host else "unknown"
            except socket.gaierror:
                ip_address = "DNS resolution failed"

            # Format result message
            if socket_error:
                msg = f"{socket_error}"
            elif "connected" in str(self.result_ready.emit):
                msg = f"Connection established. Host: {self.host}, Port: {self.port}"
            else:
                msg = f"Host resolves to: {ip_address}. TCP connection failed."

            self.result_ready.emit("error", msg)

        except Exception as e:
            self.result_ready.emit("error", f"Connection test failed: {str(e)}")

    def cancel(self) -> None:
        """Cancel the connection test."""
        self._running = False
        if self.isRunning():
            self.terminate()


class SettingsDialog(QDialog):
    """Settings dialog for configuring server connection and credentials."""

    # Signal emitted when settings are applied to SSH client
    settings_applied = pyqtSignal(object)

    def __init__(
        self,
        ssh_client: Optional[object] = None,
        parent: Optional[QWidget] = None,
        default_host: str = "",
        default_user: str = "",
        default_port: int = 22,
    ) -> None:
        """
        Initialize settings dialog.

        Args:
            ssh_client: SSH connection manager instance (optional)
            parent: Parent widget (main window)
            default_host: Default host IP/hostname
            default_user: Default username
            default_port: Default SSH port
        """
        super().__init__(parent)

        self.ssh_client = ssh_client
        self.connection_thread: Optional[ConnectionTester] = None

        # Set title and properties
        self.setWindowTitle("Settings - AI Model Server Manager")
        self.setMinimumSize(520, 600)
        self.setMinimumHeight(600)

        # Setup UI
        self._setup_ui(default_host, default_user, default_port)

    def _setup_ui(self, default_host: str, default_user: str, default_port: int = 22) -> None:
        """Setup dialog UI with connection settings."""

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Scroll area for scrollable settings panel
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#settings_container {
                background-color: #16213e;
                padding: 10px;
                margin: -10px -10px -10px -10px;
            }
        """)

        # Settings container widget
        settings_container = QWidget()
        settings_container.setObjectName("settings_container")
        form_layout = QFormLayout(settings_container)
        form_layout.setSpacing(12)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )

        # ========================================
        # Server Connection Settings Group
        # ========================================
        connection_group = QGroupBox("Server Connection", self)
        connection_vbox = QVBoxLayout(connection_group)
        connection_vbox.setSpacing(12)

        # IP Address field - Server IP address (IPv4 or hostname)
        ip_label = QLabel("Server IP / Hostname:", self)
        ip_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.ip_edit = QLineEdit(self)
        self.ip_edit.setPlaceholderText(f"e.g., {default_host or '192.168.1.100'}")
        self.ip_edit.setText(default_host if default_host else "")
        self.ip_edit.setMinimumHeight(40)
        self.ip_edit.textChanged.connect(self._validate_ip)

        # Username field
        user_label = QLabel("Username:", self)
        user_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.user_edit = QLineEdit(self)
        self.user_edit.setPlaceholderText(f"e.g., {default_user or 'root'}")
        self.user_edit.setText(default_user if default_user else "")
        self.user_edit.setMinimumHeight(40)
        self.user_edit.textChanged.connect(lambda: self._update_status_indicator())

        # SSH Port field
        port_label = QLabel("SSH Port:", self)
        port_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(default_port)
        self.port_spin.setMinimumHeight(40)

        # ========================================
        # Connection Status Indicators Section (Task 3)
        # ========================================
        status_group = QGroupBox("Connection Status", self)
        status_vbox = QVBoxLayout(status_group)
        status_vbox.setSpacing(8)

        # Status indicator label with state-based styling
        self.status_indicator_label = QLabel("Status: Disconnected", self)
        self.status_indicator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_indicator_label.setStyleSheet("""
            font-size: 14px;
            padding: 12px;
            border-radius: 6px;
            background-color: #3a3a5e;
            color: #ff6b6b;
            font-weight: bold;
        """)
        status_vbox.addWidget(self.status_indicator_label)

        # Connection timestamp display (Task 3 - Last connection timestamp)
        self.timestamp_label = QLabel("Last connected:", self)
        self.timestamp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.timestamp_label.setStyleSheet("color: #a0a0a0; font-size: 12px;")

        self.last_connection_display = QLabel("-", self)
        self.last_connection_display.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.last_connection_display.setStyleSheet("""
            font-size: 14px;
            padding: 10px;
            border-radius: 6px;
            background-color: #2a3a5e;
            color: #4ade80;
            font-weight: bold;
        """)

        status_vbox.addWidget(self.timestamp_label)
        status_vbox.addWidget(self.last_connection_display)

        # ========================================
        # Connection Test Button Group (Task 3)
        # ========================================
        test_group = QGroupBox("Connectivity Test", self)
        test_vbox = QVBoxLayout(test_group)

        # Progress bar for connection test visualization
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(QLabel("Testing connection..."), alignment=Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_bar)

        test_vbox.addLayout(progress_layout)

        # Test connection button with visual result indicator
        self.test_btn = QPushButton("🔌 Test Server Connection", self)
        self.test_btn.setMinimumHeight(45)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #06b6d4;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #67e8f9;
            }
            QPushButton:pressed {
                background-color: #0596cb;
            }
        """)
        self.test_btn.clicked.connect(self._on_test_clicked)

        test_vbox.addWidget(self.test_btn)
        test_vbox.addSpacing(10)

        # ========================================
        # Script Configuration Section (Task 2)
        # ========================================
        script_group = QGroupBox("Script Paths", self)
        script_vbox = QVBoxLayout(script_group)
        script_vbox.setSpacing(10)

        # Start script path field
        start_script_label = QLabel(
            "📂 Start Script Path (remote server):", 
            self
        )
        start_script_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.start_script_edit = QLineEdit(self)
        self.start_script_edit.setPlaceholderText("/usr/local/bin/start_ai_server.sh")
        self.start_script_edit.setMinimumHeight(40)
        self.start_script_edit.setText("/usr/local/bin/start_ai_server.sh")  # Default from config
        self.start_script_edit.textChanged.connect(self._validate_script_paths)

        script_vbox.addWidget(start_script_label)
        script_vbox.addWidget(self.start_script_edit)

        # Stop script path field
        stop_script_label = QLabel(
            "📂 Stop Script Path (remote server):", 
            self
        )
        stop_script_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.stop_script_edit = QLineEdit(self)
        self.stop_script_edit.setPlaceholderText("/usr/local/bin/stop_ai_server.sh")
        self.stop_script_edit.setMinimumHeight(40)
        self.stop_script_edit.setText("/usr/local/bin/stop_ai_server.sh")  # Default from config
        self.stop_script_edit.textChanged.connect(self._validate_script_paths)

        script_vbox.addWidget(stop_script_label)
        script_vbox.addWidget(self.stop_script_edit)

        # Restart script path field (optional - can be omitted for smart restart)
        restart_script_label = QLabel(
            "🔄 Restart Script Path (remote server, optional):", 
            self
        )
        restart_script_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")

        self.restart_script_edit = QLineEdit(self)
        self.restart_script_edit.setPlaceholderText("/usr/local/bin/restart_ai_server.sh")
        self.restart_script_edit.setMinimumHeight(40)
        self.restart_script_edit.setText("")  # Optional field, leave empty for smart restart
        self.restart_script_edit.textChanged.connect(self._validate_script_paths)

        script_vbox.addWidget(restart_script_label)
        script_vbox.addWidget(self.restart_script_edit)

        # Info text about scripts
        info_text = QLabel(
            "ℹ️  These paths are used on the REMOTE SERVER when running start/stop commands.\n"
            "    Scripts will be executed with: <sh /path/to/script>\n"
            "    Leave restart empty to use smart restart (detects if running first)",
            self
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #808080; font-size: 11px;")
        script_vbox.addWidget(info_text, alignment=Qt.AlignmentFlag.AlignLeft)


        # ========================================
        # Credential Storage Settings Group
        # ========================================
        credentials_group = QGroupBox("Credential Storage", self)
        credentials_vbox = QVBoxLayout(credentials_group)

        # Save Credentials Securely checkbox (Task 3 - store password in keyring)
        self.store_credentials_check = QCheckBox(
            "✓ Store password securely in system keyring"
        )
        self.store_credentials_check.setChecked(True)
        self.store_credentials_check.setCheckable(True)
        credentials_vbox.addWidget(self.store_credentials_check)

        # ========================================
        # Additional Connection Settings Group
        # ========================================
        options_group = QGroupBox("Connection Options", self)
        options_vbox = QVBoxLayout(options_group)

        # Auto-reconnect checkbox
        self.auto_reconnect_check = QCheckBox(
            "Auto-reconnect on SSH failure"
        )
        self.auto_reconnect_check.setChecked(True)
        credentials_vbox.addWidget(self.auto_reconnect_check)

        # ========================================
        # Error Messages Display Group
        # ========================================
        errors_group = QGroupBox("Error Messages (Task 3)", self)
        errors_layout = QVBoxLayout(errors_group)

        error_label = QLabel(
            "Connection test failures will be logged to:\n~/.local/share/AIManagerUI/logs/"
        )
        error_label.setWordWrap(True)
        error_label.setStyleSheet("font-size: 11px; color: #a0a0a0;")

        errors_layout.addWidget(error_label)
        connection_vbox.addWidget(errors_group)

        # ========================================
        # Buttons Group
        # ========================================
        buttons_group = QGroupBox("", self)
        buttons_layout = QHBoxLayout(buttons_group)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #9ca3af;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Apply & Connect", self)
        self.apply_btn.setMinimumHeight(45)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #34d399;
            }
        """)
        self.apply_btn.clicked.connect(self._on_apply_clicked)

        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.apply_btn)

        # ========================================
        # Layout assembly
        # ========================================

        # Add all groups to form layout
        form_layout.addRow("Host:", self.ip_edit)
        form_layout.addRow("Username:", self.user_edit)
        form_layout.addRow("Port:", self.port_spin)

        form_layout.addRow(None, None)  # Spacer

        main_layout.addWidget(scroll_area, stretch=2)

        # Add status indicator section
        main_layout.addLayout(status_vbox)

        # Add connection test section
        main_layout.addWidget(test_group)

        # Add credential storage and options groups
        form_layout.addRow(None, None)  # Spacer
        main_layout.addWidget(script_group)
        # Add credential storage and options groups
        form_layout.addRow(None, None)  # Spacer
        main_layout.addWidget(credentials_group)
        main_layout.addWidget(options_group)

        buttons_group.setMinimumHeight(80)
        main_layout.addWidget(buttons_group)

        # Set layout for scroll area widget
        scroll_area.setWidget(settings_container)
        main_layout.addLayout(main_layout, stretch=1)

    def _validate_ip(self, ip: str) -> None:
        """Validate IP address format."""
        if not ip or not ip.strip():
            self.ip_edit.setStyleSheet("")
            return

        import re
        # Check for valid IP or hostname pattern
        ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^([a-zA-Z0-9.-]+)$'
        if not re.match(ip_pattern, ip.strip()):
            self.ip_edit.setStyleSheet("border: 2px solid #ff6b6b;")
            self.test_status_label = QLabel("Warning: Invalid IP format", self)
            self.test_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.test_status_label.setStyleSheet("""
                font-size: 12px;
                padding: 8px;
                background-color: #450a0a;
                color: orange;
                border-radius: 4px;
            """)
            self.ip_edit.addWidget(self.test_status_label)

    def _update_status_indicator(self) -> None:
        """Update status indicator based on username presence."""
        user = str(self.user_edit.text()).strip()
        if not user:
            self.status_indicator_label.setText("Status: Disconnected")
            self.status_indicator_label.setStyleSheet("""
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
                background-color: #3a3a5e;
                color: #ff6b6b;
                font-weight: bold;
            """)
        else:
            self.status_indicator_label.setText("Status: Ready to connect")
            self.status_indicator_label.setStyleSheet("""
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
                background-color: #06b6d420;
                color: #67e8f9;
                font-weight: bold;
            """)
    def _validate_script_paths(self) -> None:
        """Validate that script paths are not empty if provided."""
        start_path = str(self.start_script_edit.text()).strip()
        stop_path = str(self.stop_script_edit.text()).strip()
        restart_path = str(self.restart_script_edit.text()).strip()

        # Only validate non-empty fields (remove error styling)
        if start_path and len(start_path) > 3:
            self.start_script_edit.setStyleSheet("")
        if stop_path and len(stop_path) > 3:
            self.stop_script_edit.setStyleSheet("")
        if restart_path and len(restart_path) > 3:
            self.restart_script_edit.setStyleSheet("")


    def _on_test_clicked(self) -> None:
        """Handle Test Server Connection button click."""
        host = str(self.ip_edit.text()).strip()
        port = int(self.port_spin.value())

        if not host:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a server IP or hostname before testing."
            )
            return

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and run connection tester thread
        self.connection_thread = ConnectionTester(host, port)
        self.connection_thread.result_ready.connect(self._on_test_result)
        self.connection_thread.start()

    def _on_test_result(self, status: str, message: str) -> None:
        """Handle connection test result."""
        if self.progress_bar.isVisible():
            self.progress_bar.setVisible(False)

        # Update status indicator
        if status == "connected":
            self.status_indicator_label.setText("Status: Connected")
            self.status_indicator_label.setStyleSheet("""
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
                background-color: #059669;
                color: white;
                font-weight: bold;
            """)

            self.last_connection_display.setText(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            QMessageBox.information(
                self,
                "Connection Successful",
                f"✓ Server is reachable!\n\nHost: {self.ip_edit.text()}\nPort: {self.port_spin.value()}"
            )
        else:
            self.status_indicator_label.setText("Status: Disconnected")
            self.status_indicator_label.setStyleSheet("""
                font-size: 14px;
                padding: 12px;
                border-radius: 6px;
                background-color: #dc2626;
                color: white;
                font-weight: bold;
            """)

            self.last_connection_display.setText("-")

            # Task 4: Use centralized error handler for logging
            ErrorHandler.log_connection_error(
                host=host,
                port=port,
                username=user_edit.text().strip() if user_edit else None,
                exception=Exception(message)
            )

            QMessageBox.critical(
    self,
    "Connection Failed",
    f"✗ Server connection test failed:\n\n{message}\n\nTROUBLESHOOTING:\n" 
    f"• Verify your network connection\n" 
    f"• Ensure SSH service is running on target server\n" 
    f"• Check firewall rules blocking port 22\n"
    f"Detailed logs: {ErrorHandler.get_error_log_path()}"
)

    

    def _on_apply_clicked(self) -> None:
        """Handle Apply button click."""
        # Validate connection settings
        host = str(self.ip_edit.text()).strip()
        user = str(self.user_edit.text()).strip()
        port = int(self.port_spin.value())
        store_credentials = self.store_credentials_check.isChecked()

        if not host:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a server IP or hostname."
            )
            return

        if not user:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a username."
            )
            return

        # Gather all settings to emit signal
        settings_dict = {
            'ip': host,
            'username': user,
            'port': port,
            'store_credentials': store_credentials,
            'auto_reconnect': self.auto_reconnect_check.isChecked(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Emit signal to apply settings (if ssh_client is available)
        if self.ssh_client:
            self.settings_applied.emit(settings_dict)

        # Show confirmation message
        QMessageBox.information(
            self,
            "Settings Saved",
            f"✓ Connection settings applied:\n"
            f"  • Server: {host}\n"
            f"  • Username: {user}\n"
            f"  • Port: {port}\n\n"
            f"{'Password saved securely' if store_credentials else 'No password stored'}"
        )

        self.accept()


def main():
    """Test script for SettingsDialog (Task 3 testing)."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    dialog = SettingsDialog(
        parent=None,
        default_host="192.168.1.100",
        default_user="root",
        default_port=22
    )

    # Set window flags to make it behave like a regular dialog
    dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint)
    dialog.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
