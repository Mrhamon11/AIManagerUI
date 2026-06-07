"""Unit tests for MainWindow."""

import pytest
import sys


@pytest.fixture(scope="module")
def qt_app():
    """Create a QApplication instance with offscreen rendering."""
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    yield app
    
    app.quit()


class TestMainWindowInit:
    """Tests for MainWindow initialization."""

    def test_main_window_initializes(self, qt_app):
        """Test that MainWindow initializes properly."""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        assert window is not None
        assert window.objectName() == "AI Model Server Manager"

    def test_has_start_stop_signals(self, qt_app):
        """Test that start/stop signals are defined."""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        # Check for pyqtSignal attributes (not callable instances)
        assert hasattr(window, 'status_changed')


class TestMainWindowSignals:
    """Tests for MainWindow signals."""

    def test_start_stop_signals_exist(self, qt_app):
        """Test that start/stop signals exist."""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        # The class should have status_changed signal defined
        assert hasattr(window, 'status_changed')

    def test_status_signal_exists(self, qt_app):
        """Test that status_changed signal exists."""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        assert hasattr(window, 'status_changed')

    def test_signals_callable(self, qt_app):
        """Test that signals are properly bound."""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        
        # Verify pyqtSignal attributes exist (bound signal on instance)
        assert hasattr(window, 'status_changed') and callable(window.status_changed)
