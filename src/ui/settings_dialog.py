"""
AI Model Server Manager - Settings Dialog

Provides configuration interface for server connection and credentials storage.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QFormLayout,
    QWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction


class SettingsDialog(QDialog):
    """Settings dialog for configuring server connection."""

    # Signal emitted when settings are applied to SSH client
    settings_applied = pyqtSignal(object)

    def __init__(
        self, 
        ssh_client: Optional[object] = None, 
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize settings dialog.

        Args:
            ssh_client: SSH connection manager instance (optional)
            parent: Parent widget (main window)
        """
        super().__init__(parent)
        self.ssh_client = ssh_client
        
        # Set title and properties
        self.setWindowTitle("Settings - AI Model Server Manager")
        self.setMinimumSize(450, 500)
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup dialog UI with connection settings."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Scroll area for scrollable form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Settings container widget
        settings_container = QWidget()
        form_layout = QFormLayout(settings_container)
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        
        # ========================================
        # Server Connection Settings Group
        # ========================================
        connection_group = QGroupBox("Server Connection", self)
        connection_layout = QVBoxLayout(connection_group)
        
        # Server IP Address field
        ip_label = QLabel("Server IP / Hostname:", self)
        ip_label.setStyleSheet("font-weight: bold;")
        
        self.ip_edit = QLineEdit(self)
        self.ip_edit.setPlaceholderText("e.g., 192.168.1.100 or server.example.com")
        self.ip_edit.setMinimumHeight(35)
        self.ip_edit.textChanged.connect(self._validate_ip)
        
        # Username field
        user_label = QLabel("Username:", self)
        user_label.setStyleSheet("font-weight: bold;")
        
        self.user_edit = QLineEdit(self)
        self.user_edit.setPlaceholderText("e.g., admin, root, ubuntu")
        self.user_edit.setMinimumHeight(35)
        
        # SSH Port field
        port_label = QLabel("SSH Port:", self)
        port_label.setStyleSheet("font-weight: bold;")
        
        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        self.port_spin.setMinimumHeight(35)
        
        # Save credentials checkbox
        self.store_credentials_check = QCheckBox(self)
        self.store_credentials_check.setChecked(True)
        self.store_credentials_check.setText("✓ Store password in secure keyring")
        
        # Auto-reconnect checkbox
        self.auto_reconnect_check = QCheckBox(self)
        self.auto_reconnect_check.setChecked(True)
        self.auto_reconnect_check.setText("Auto-reconnect on SSH failure")
        
        # ========================================
        # Script Paths Configuration Group
        # ========================================
        scripts_group = QGroupBox("Script Paths (Optional)", self)
        scripts_layout = QVBoxLayout(scripts_group)
        
        script_label = QLabel(
            "Custom script location:\n(e.g., /home/user/server.sh)", 
            self
        )
        script_label.setWordWrap(True)
        
        self.script_path_edit = QLineEdit(self)
        self.script_path_edit.setPlaceholderText("/custom/path/to/start_server.sh")
        self.script_path_edit.setMinimumHeight(35)
        
        # ========================================
        # Connection Test Button Group
        # ========================================
        test_group = QGroupBox("Connection Test", self)
        test_layout = QVBoxLayout(test_group)
        
        self.test_btn = QPushButton("🔌 Test Server Connection", self)
        self.test_btn.setMinimumHeight(40)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.test_status_label = QLabel("Status: Ready to test", self)
        self.test_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.test_status_label.setStyleSheet("""
            font-size: 13px;
            padding: 8px;
            border-radius: 4px;
        """)
        
        # ========================================
        # Additional Settings Group
        # ========================================
        extra_group = QGroupBox("Advanced Settings", self)
        extra_layout = QVBoxLayout(extra_group)
        
        timeout_label = QLabel(
            "Command timeout (seconds):\n(e.g., 600 for 10 minutes)", 
            self
        )
        timeout_label.setWordWrap(True)
        
        self.timeout_spin = QSpinBox(self)
        self.timeout_spin.setRange(30, 3600)
        self.timeout_spin.setValue(300)  # 5 minutes default
        
        # ========================================
        # Buttons Group
        # ========================================
        buttons_group = QGroupBox("", self)
        buttons_layout = QHBoxLayout(buttons_group)
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.apply_btn = QPushButton("Apply", self)
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5E35B1;
            }
        """)
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        
        # ========================================
        # Layout assembly
        # ========================================
        
        # Add main settings to form layout first
        form_layout.addRow("Server IP / Hostname:", self.ip_edit)
        form_layout.addRow("Username:", self.user_edit)
        form_layout.addRow("SSH Port:", self.port_spin)
        form_layout.addRow(self.store_credentials_check)
        form_layout.addRow(self.auto_reconnect_check)
        
        # Add script path to main settings
        form_layout.addRow(
            QLabel("<b>Script Path:</b>"), 
            self.script_path_edit
        )
        form_layout.addRow(None, timeout_label, self.timeout_spin)
        
        # Assemble scroll area with all groups
        groups = [
            connection_group,
            scripts_group,
            test_group,
            extra_group,
            buttons_group
        ]
        
        for group in groups:
            connection_layout.addWidget(group)
        
        connections_layout = QVBoxLayout(connection_group)
        connections_layout.addLayout(form_layout)
        main_layout.addWidget(scroll_area, stretch=1)
        
        # Add test status label
        main_layout.addWidget(test_status_label := self.test_status_label)
    
    def _validate_ip(self, ip: str) -> None:
        """Validate IP address format."""
        if not ip or not ip.strip():
            return
        
        import re
        # Check for valid IP or hostname pattern
        ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^([a-zA-Z0-9.-]+)$'
        if not re.match(ip_pattern, ip.strip()):
            self.test_status_label.setText("Warning: Invalid IP format")
            self.test_status_label.setStyleSheet("color: orange;")
    
    def _on_apply_clicked(self) -> None:
        """Handle Apply button click."""
        # Emit signal to apply settings to SSH client
        if self.ssh_client:
            settings_dict = {
                'ip': self.ip_edit.text().strip(),
                'username': self.user_edit.text().strip(),
                'port': self.port_spin.value(),
                'store_credentials': self.store_credentials_check.isChecked(),
                'auto_reconnect': self.auto_reconnect_check.isChecked(),
                'script_path': self.script_path_edit.text().strip(),
                'timeout': self.timeout_spin.value()
            }
            self.settings_applied.emit(settings_dict)
        
        # Show confirmation message
        QMessageBox.information(
            self,
            "Settings Applied",
            f"✓ Settings saved:\n  • Server: {self.ip_edit.text().strip()}\n  • Username: {self.user_edit.text().strip()}" +
            (f"\n  • Store credentials: {'Yes' if self.store_credentials_check.isChecked() else 'No'}")
        )
        
        self.accept()
