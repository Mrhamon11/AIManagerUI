"""
AI Model Server Manager - Main Window
Simple server connection interface.
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
from PyQt6.QtCore import Qt
from src.error_handler import ErrorHandler


if TYPE_CHECKING:
    from ssh_client import SSHConnectionManager

class MainWindow(QMainWindow):
    """Simple server connection window."""

    def __init__(self) -> None:
        super().__init__()
        
        self._display_type = "wayland" if os.environ.get("WAYLAND_DISPLAY") else ("x11" if os.environ.get("DISPLAY") else "headless")
        print(f"[MainWindow] Starting on {self._display_type} display", file=sys.stderr)
        
        self.setObjectName("AI Model Server Manager")
        self.setWindowTitle("AI Model Server Manager (UI Simulation Mode)")
        self.setMinimumSize(500, 600)
        
        # Connection state - NOTE: Currently in UI SIMULATION mode
        # Phase 3 will implement actual SSH connection with SSHConnectionManager
        self.ssh_manager: Optional["SSHConnectionManager"] = None
        self.is_connected = False
        
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
        
        # SECTION 2: Toolbar buttons (3 buttons side-by-side)
        btn_container = QHBoxLayout()
        btn_container.setSpacing(10)
        main_layout.addLayout(btn_container)
        
        # Test button - NOTE: Currently in simulation mode until Phase 3
        self.test_btn = QPushButton("TEST", self)
        self.test_btn.setMinimumHeight(36)
        self.test_btn.setMinimumWidth(100)
        self.test_btn.setDisabled(True)
        self.test_btn.setStyleSheet("""
            background-color: #28a745; color: white; border: none; 
            border-radius: 4px; padding: 8px; font-weight: bold; min-width: 100px;
        """)
        self.test_btn.clicked.connect(self._on_test_connection)
        btn_container.addWidget(self.test_btn)
        
        # Connect button - NOTE: Currently in simulation mode until Phase 3
        self.connect_btn = QPushButton("CONNECT", self)
        self.connect_btn.setMinimumHeight(36)
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.setStyleSheet("""
            background-color: #06b6d4; color: white; border: none; 
            border-radius: 4px; padding: 8px; font-weight: bold; min-width: 120px;
        """)
        self.connect_btn.clicked.connect(self._on_connect)
        btn_container.addWidget(self.connect_btn)
        
        # Disconnect button - NOTE: Currently in simulation mode until Phase 3
        self.disconnect_btn = QPushButton("DISCONNECT", self)
        self.disconnect_btn.setMinimumHeight(36)
        self.disconnect_btn.setMinimumWidth(120)
        self.disconnect_btn.setDisabled(True)
        self.disconnect_btn.setStyleSheet("""
            background-color: #e76f51; color: white; border: none; 
            border-radius: 4px; padding: 8px; font-weight: bold; min-width: 120px;
        """)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        btn_container.addWidget(self.disconnect_btn)
        
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

    def _on_connect(self) -> None:
        """Handle connect button click - NOTE: Currently in UI SIMULATION mode until Phase 3."""
        try:
            # Save connection details for later use (will be used in Phase 3)
            host = self.host_input.text().strip()
            user = self.user_input.text().strip()
            port = self.port_spin.value()
            
            if not host:
                QMessageBox.critical(self, "Missing Information", "❗ Please enter a server address.")
                return
            if not user:
                QMessageBox.critical(self, "Missing Information", "❗ Please enter a username.")
                return
            
            print(f"[MainWindow] [SIMULATION MODE] Clicked CONNECT to {host}", file=sys.stderr)
            
            # Update UI - this is currently just faking the connection
            self.is_connected = True
            
            # Update UI
            self.status_label.setText("Status: CONNECTED")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; padding: 8px 12px;")
            
            self.connect_btn.setDisabled(True)
            self.disconnect_btn.setDisabled(False)
            self.test_btn.setDisabled(True)
            self.host_input.setEnabled(False)
            self.user_input.setEnabled(False)
            self.pwd_input.setEnabled(False)
            
            port = self.port_spin.value()
            self._status_bar.showMessage("⚠️ UI SIMULATION: Connected (no real SSH connection yet - Phase 3 will implement actual)", 20000)
            
        except Exception as e:
            ErrorHandler.log_error("connect", str(e))
            QMessageBox.critical(self, "Connection Error", f"❌ Failed:\n\n{str(e)}\n\nCheck logs in ~/.local/share/AIManagerUI/logs/")

    def _on_disconnect(self) -> None:
        """Handle disconnect button click - NOTE: Currently in UI SIMULATION mode until Phase 3."""
        if not self.is_connected:
            return
        
        try:
            print(f"[MainWindow] [SIMULATION MODE] Clicked DISCONNECT", file=sys.stderr)
            self.is_connected = False
            
            # Update UI
            self.status_label.setText("Status: DISCONNECTED")
            self.status_label.setStyleSheet("color: #e76f51; font-weight: bold; padding: 8px 12px;")
            
            self.connect_btn.setDisabled(False)
            self.disconnect_btn.setDisabled(True)
            self.test_btn.setDisabled(False)
            self.host_input.setEnabled(True)
            self.user_input.setEnabled(True)
            self.pwd_input.setEnabled(True)
            
            self._status_bar.showMessage("Disconnected", 5000)
            
        except Exception as e:
            ErrorHandler.log_error("disconnect", str(e))

    def _on_test_connection(self) -> None:
        """Handle test connection button click - NOTE: Currently in simulation mode until Phase 3."""
        try:
            host = self.host_input.text().strip()
            
            if not host:
                status_msg = self.findChild(QLabel, "status_message")
                if status_msg and hasattr(status_msg, 'setText'):
                    status_msg.setText("Please enter a server address first")
                return
            
            print(f"[MainWindow] [SIMULATION MODE] Testing connection to {host}", file=sys.stderr)
            
            import socket
            
            socket.setdefaulttimeout(3)
            ip = socket.gethostbyname(host)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, self.port_spin.value()))
            sock.close()
            
            status_msg = self.findChild(QLabel, "status_message")
            if status_msg and hasattr(status_msg, 'setText'):
                status_msg.setText(f"✅ Port {self.port_spin.value()} is open on {ip}")
                
        except socket.gaierror as e:
            ErrorHandler.log_error("test", f"DNS error: {str(e)}")
            status_msg = self.findChild(QLabel, "status_message")
            if status_msg and hasattr(status_msg, 'setText'):
                status_msg.setText(f"❌ Cannot resolve hostname: {host}")
        except socket.timeout:
            ErrorHandler.log_error("test", "Connection timeout")
            status_msg = self.findChild(QLabel, "status_message")
            if status_msg and hasattr(status_msg, 'setText'):
                status_msg.setText(f"⏱ Connection timed out")
        except ConnectionRefusedError as e:
            ErrorHandler.log_error("test", str(e))
            status_msg = self.findChild(QLabel, "status_message")
            if status_msg and hasattr(status_msg, 'setText'):
                status_msg.setText(f"❌ Connection refused on port {self.port_spin.value()}")
        except Exception as e:
            ErrorHandler.log_error("test", str(e))
            status_msg = self.findChild(QLabel, "status_message")
            if status_msg and hasattr(status_msg, 'setText'):
                status_msg.setText(f"❌ Error: {str(e)}")

    def closeEvent(self, event) -> None:
        """Handle window close."""
        try:
            if self.is_connected:
                print("[MainWindow] Disconnecting on exit...", file=sys.stderr)
                self._on_disconnect()
        except Exception as e:
            ErrorHandler.log_error("exit", str(e))
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Model Server Manager")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
