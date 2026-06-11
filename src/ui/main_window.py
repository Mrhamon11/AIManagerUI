"""
AI Model Server Manager - Main Window
Simple server connection interface with toggle-style connect button.
"""

import sys
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGroupBox, 
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QMessageBox, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer
from src.error_handler import ErrorHandler


if TYPE_CHECKING:
    from ssh_client import SSHConnectionManager

# Import ConfigManager for persistence (optional - graceful fallback if missing)
try:
    from src.config_manager import ConfigManager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    CONFIG_MANAGER_AVAILABLE = False
    ConfigManager = None


class MainWindow(QMainWindow):
    """Simple server connection window with toggle-style connect button."""

    def __init__(self) -> None:
        super().__init__()
        
        self._display_type = "wayland" if os.environ.get("WAYLAND_DISPLAY") else ("x11" if os.environ.get("DISPLAY") else "headless")
        print(f"[MainWindow] Starting on {self._display_type} display", file=sys.stderr)
        
        self.setObjectName("AI Model Server Manager")
        self.setWindowTitle("AI Model Server Manager (UI Simulation Mode)")
        self.setMinimumSize(500, 600)
        
        # Connection state - NOTE: Currently in UI SIMULATION mode until Phase 3
        self.ssh_manager: Optional["SSHConnectionManager"] = None
        self.is_connected = False
        
        # Initialize configuration manager for persistence (optional - graceful fallback)
        if CONFIG_MANAGER_AVAILABLE:
            try:
                self.config_manager = ConfigManager()
                print("[MainWindow] Configuration manager initialized", file=sys.stderr)
            except Exception as e:
                ErrorHandler.log_error("config_init", str(e))
                self.config_manager = None
                print(f"[MainWindow] ConfigManager initialization failed, using in-memory storage: {str(e)}", file=sys.stderr)
        else:
            self.config_manager = None
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(12)
        
        # Status bar at bottom
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.setStyleSheet("QStatusBar { background-color: #0f3460; color: white; border-top: 2px solid #1a5276; padding: 8px 12px; }")
        
        ErrorHandler.set_logs_directory(Path.home() / ".local" / "share" / "AIManagerUI" / "logs")
        
        # SECTION 1: Status indicator (top) - NOTE: UI simulation mode until Phase 3
        self.status_label = QLabel("Status: DISCONNECTED", self)
        self.status_label.setStyleSheet("color: #e76f51; font-weight: bold; padding: 8px 12px; font-size: 14px;")
        main_layout.addWidget(self.status_label)
        
        # SECTION 2: Single toggle-style action button (CONNECT when disconnected, DISCONNECT when connected)
        self.action_btn = QPushButton("CONNECT", self)
        self.action_btn.setMinimumHeight(50)
        self.action_btn.setMinimumWidth(140)
        # Green style when disconnected
        self.action_btn.setStyleSheet("""
            background-color: #06b6d4; color: white; border: none; 
            border-radius: 6px; padding: 12px; font-weight: bold; min-width: 140px;
        """)
        self.action_btn.clicked.connect(self._on_action)
        main_layout.addWidget(self.action_btn)
        
        # SECTION 3: Server Connection Details Form
        form_group = QGroupBox("Server Connection Details", self)
        form_layout = QVBoxLayout(form_group)
        
        # HOST INPUT - where to enter server address!
        host_row = QHBoxLayout()
        host_label = QLabel("🌐 Server Address:", self)
        host_label.setStyleSheet("color: #aaddff; font-weight: bold; padding-right: 6px;")
        self.host_input = QLineEdit(self)
        self.host_input.setPlaceholderText("e.g., 192.168.1.100, localhost, server.example.com")
        self.host_input.setMinimumHeight(35)
        self.host_input.setStyleSheet("background-color: #2a2a3e; color: white; border: 2px solid #444; padding: 8px; border-radius: 5px; font-size: 13px; min-width: 220px;")
        
        host_row.addWidget(host_label)
        host_row.addWidget(self.host_input, 1)
        form_layout.addLayout(host_row)
        
        # PORT INPUT - SSH port!
        port_row = QHBoxLayout()
        port_label = QLabel("🔐 SSH Port:", self)
        port_label.setStyleSheet("color: #aaddff; font-weight: bold; padding-right: 6px;")
        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        self.port_spin.setMinimumHeight(35)
        self.port_spin.setStyleSheet("background-color: #2a2a3e; color: white; border: 2px solid #444; padding: 7px 10px; border-radius: 5px; font-size: 13px; min-width: 70px;")
        
        port_row.addWidget(port_label)
        port_row.addWidget(self.port_spin)
        port_row.addStretch()
        form_layout.addLayout(port_row)
        
        # USERNAME INPUT - where to enter username!
        user_row = QHBoxLayout()
        user_label = QLabel("👤 Username:", self)
        user_label.setStyleSheet("color: #aaddff; font-weight: bold; padding-right: 6px;")
        self.user_input = QLineEdit(self)
        self.user_input.setPlaceholderText("e.g., root, admin, deploy, ubuntu")
        self.user_input.setMinimumHeight(35)
        self.user_input.setStyleSheet("background-color: #2a2a3e; color: white; border: 2px solid #444; padding: 8px; border-radius: 5px; font-size: 13px; min-width: 220px;")
        
        user_row.addWidget(user_label)
        user_row.addWidget(self.user_input, 1)
        form_layout.addLayout(user_row)
        
        # PASSWORD INPUT - where to enter password! (characters hidden for security!)
        pwd_row = QHBoxLayout()
        pwd_label = QLabel("🔑 Password:", self)
        pwd_label.setStyleSheet("color: #aaddff; font-weight: bold; padding-right: 6px;")
        self.pwd_input = QLineEdit(self)
        self.pwd_input.setPlaceholderText("Enter password (won't show as you type)")
        self.pwd_input.setMinimumHeight(35)
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)  # Hides password!
        self.pwd_input.setStyleSheet("background-color: #2a2a3e; color: white; border: 2px solid #444; padding: 8px; border-radius: 5px; font-size: 13px; min-width: 220px;")
        
        pwd_row.addWidget(pwd_label)
        pwd_row.addWidget(self.pwd_input, 1)
        form_layout.addLayout(pwd_row)
        
        # Status message area (shows messages like "Success", "Error", etc.)
        msg_row = QHBoxLayout()
        msg_row.setContentsMargins(0, 2, 0, 6)
        self.msg_label = QLabel("", self)
        self.msg_label.setStyleSheet("color: #888; padding: 4px 6px; background-color: transparent; font-size: 11px;")
        msg_row.addWidget(self.msg_label)
        
        form_layout.addLayout(msg_row)
        
        main_layout.addWidget(form_group)

    def _save_config(self) -> None:
        """Save current connection details to config file."""
        if not self.config_manager:
            return
        
        try:
            # Save values with encryption for password
            self.config_manager.set("server_ip_address", self.host_input.text().strip())
            self.config_manager.set("server_port", self.port_spin.value())
            self.config_manager.set("auth_username", self.user_input.text().strip())
            
            # Encrypt and save password
            if self.pwd_input.text():
                pwd = self.pwd_input.text()
            else:
                pwd = ""
            
            self.config_manager.set_encrypted("auth_password", pwd)
            
            print(f"[MainWindow] [CONFIG SAVE] Saved connection to {self.config_manager.config_path}", file=sys.stderr)
        except Exception as e:
            ErrorHandler.log_error("config_save", str(e))

    def _load_config(self) -> None:
        """Load saved connection details from config file."""
        if not self.config_manager:
            return
        
        try:
            # Load values (with decryption for password)
            ip = self.config_manager.get("server_ip_address") or ""
            port = self.config_manager.get("server_port") or 22
            user = self.config_manager.get("auth_username") or ""
            
            # Decrypt and load password (handle both bytes and string returns)
            pwd_encrypted = self.config_manager.get_decrypted("auth_password")
            if pwd_encrypted:
                try:
                    if isinstance(pwd_encrypted, bytes):
                        pwd = pwd_encrypted.decode('utf-8')
                    else:
                        # Already a string (from encrypted JSON or empty password)
                        pwd = str(pwd_encrypted) if pwd_encrypted else ""
                except AttributeError:
                    pwd = ""
            else:
                pwd = ""
            
            print(f"[MainWindow] [CONFIG LOAD] Loaded connection from {self.config_manager.config_path}", file=sys.stderr)
            
            # Apply to UI inputs
            self.host_input.setText(ip)
            self.port_spin.setValue(port)
            self.user_input.setText(user)
            
            if pwd:
                self.pwd_input.setText(pwd)
                # Clear echo mode so password is visible (already set by user)
        except Exception as e:
            ErrorHandler.log_error("config_load", str(e))

    def _on_action(self) -> None:
        """Handle action button click - toggles between connect and disconnect."""
        try:
            # Ensure config is saved on any state change (connect/disconnect)
            self._save_config()
            
            # Check current connection state and act accordingly
            if self.is_connected:
                print(f"[MainWindow] [ACTION CLICK] State: CONNECTED → will DISCONNECT", file=sys.stderr)
                self._disconnect()
            else:
                print(f"[MainWindow] [ACTION CLICK] State: DISCONNECTED → will CONNECT", file=sys.stderr)
                self._connect()
        except Exception as e:
            ErrorHandler.log_error("action", str(e))
            QMessageBox.critical(self, "Action Error", f"❌ Failed:\n\n{str(e)}\n\nCheck logs in ~/.local/share/AIManagerUI/logs/")

    def _connect(self) -> None:
        """Establish connection (simulated until Phase 3)."""
        try:
            host = self.host_input.text().strip()
            user = self.user_input.text().strip()
            
            if not host:
                QMessageBox.critical(self, "Missing Information", "❗ Please enter a server address.")
                return
            if not user:
                QMessageBox.critical(self, "Missing Information", "❗ Please enter a username.")
                return
            
            print(f"[MainWindow] [SIMULATION] Establishing connection to {host}", file=sys.stderr)
            
            # Update connection state
            self.is_connected = True
            
            # Update UI - status label (green)
            self.status_label.setText("Status: CONNECTED")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; padding: 8px 12px;")
            
            # Update UI - button (red/disconnect style)
            self.action_btn.setText("DISCONNECT")
            self.action_btn.setStyleSheet("""
                background-color: #e76f51; color: white; border: none; 
                border-radius: 6px; padding: 12px; font-weight: bold; min-width: 140px;
            """)
            
            # Disable inputs while connected
            self.host_input.setEnabled(False)
            self.user_input.setEnabled(False)
            self.pwd_input.setEnabled(False)
            
            # Update status bar
            self._status_bar.showMessage("⚠️ UI SIMULATION: Connected (no real SSH - Phase 3)", 20000)
            
        except Exception as e:
            ErrorHandler.log_error("connect", str(e))
            QMessageBox.critical(self, "Connection Error", f"❌ Failed:\n\n{str(e)}")

    def _disconnect(self) -> None:
        """Disconnect and return to editing mode."""
        try:
            print(f"[MainWindow] Disconnecting...", file=sys.stderr)
            
            # Update connection state
            self.is_connected = False
            
            # Update UI - status label (red)
            self.status_label.setText("Status: DISCONNECTED")
            self.status_label.setStyleSheet("color: #e76f51; font-weight: bold; padding: 8px 12px;")
            
            # Update UI - button (green/connect style)
            self.action_btn.setText("CONNECT")
            self.action_btn.setStyleSheet("""
                background-color: #06b6d4; color: white; border: none; 
                border-radius: 6px; padding: 12px; font-weight: bold; min-width: 140px;
            """)
            
            # Re-enable inputs
            self.host_input.setEnabled(True)
            self.user_input.setEnabled(True)
            self.pwd_input.setEnabled(True)
            
            # Update status bar
            self._status_bar.showMessage("Disconnected", 5000)
            
        except Exception as e:
            ErrorHandler.log_error("disconnect", str(e))

    def _on_close(self) -> None:
        """Handle window close - save config."""
        try:
            if self.config_manager:
                self._save_config()
                print("[MainWindow] [CLOSE] Saved connection details to config", file=sys.stderr)
        except Exception as e:
            ErrorHandler.log_error("close_save", str(e))

    def closeEvent(self, event) -> None:
        """Handle window close."""
        try:
            if self.is_connected:
                print("[MainWindow] Disconnecting on exit...", file=sys.stderr)
                self._disconnect()  # Will also save config
                
                # Give UI time to update before close
                QTimer.singleShot(100, event.accept)
                return
        except Exception as e:
            ErrorHandler.log_error("exit", str(e))
        
        # Always save config on close (whether connected or not)
        try:
            if self.config_manager:
                self._save_config()
        except Exception as e:
            ErrorHandler.log_error("close_save", str(e))
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Model Server Manager")
    
    window = MainWindow()
    
    # Load saved config on startup (after widgets are created in __init__)
    window._load_config()
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
