#!/usr/bin/env python3
"""
AI Model Server Manager - Main Entry Point

Starts the GUI application for managing remote AI model servers.
Run with: python main.py

Requires PyQt6 to be installed (see requirements.txt).
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def main() -> int:
    """Main application entry point."""
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from src.ui.main_window import MainWindow
        
        # Setup application
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("AI Model Server Manager")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("AIGroupAdmin")
        app.setOrganizationDomain("example.com")
        
        # Configure default font (Ubuntu/system default)
        font = QFont()
        font.setPointSize(12)
        app.setFont(font)
        
        # Setup logging configuration
        setup_logging()
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Run application event loop
        sys.exit(app.exec())
    
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        return 1
    
    except Exception as e:
        logging.exception("Unhandled application error")
        print(f"\n❌ Unexpected error: {e}")
        return 1


def setup_logging() -> None:
    """Configure application logging."""
    from rich.console import Console
    from rich.logging import RichHandler
    
    # Create console for colored output
    console = Console(
        width=100,
        force_terminal=True,
        color_system="auto",
        file=sys.stderr if sys.stdout.isatty() else None
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            RichHandler(console=console)
        ]
    )


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
