"""
AI Model Server Manager - Main Window

Provides the main application interface for managing remote AI model servers.
Supports both X11 and Wayland display servers.
"""

import sys
import os
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QLineEdit, QSpinBox, QGroupBox, QFormLayout, QMessageBox,
    QScrollArea, QToolBar, QStatusBar, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal


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
        
        # Create start/stop buttons layout
        status_label = QLabel("Status: Disconnected", self)
        status_label.setObjectName("status")
        status_label.setStyleSheet("color: #808080; padding: 8px;")
        toolbar.addWidget(status_label)
        
        # Start button
        start_btn = QPushButton("▶ Start Server", self)
        start_btn.setMinimumHeight(45)
        start_btn.clicked.connect(self._on_start_clicked)
        
        # Stop button  
        stop_btn = QPushButton("⏹ Stop Server", self)
        stop_btn.setMinimumHeight(45)
        stop_btn.clicked.connect(self._on_stop_clicked)
        
        toolbar.addWidget(start_btn)
        toolbar.addWidget(stop_btn)
        
        layout.addLayout(QHBoxLayout())
    
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
        """Handle start button click."""
        if self.is_connected:
            QMessageBox.warning(self, "Already Connected", 
                "Server is already connected!")
        else:
            self.is_connected = True
            status_label = self.findChild(QLabel, "status")
            if status_label:
                status_label.setText("Status: Connected")
                status_label.setStyleSheet("color: #4ade80; padding: 8px;")
        
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        if not self.is_connected:
            QMessageBox.information(self, "Not Connected",
                "Please connect to a server first.")
        else:
            self.is_connected = False
            status_label = self.findChild(QLabel, "status")
            if status_label:
                status_label.setText("Status: Disconnected")


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
