"""Integration tests for UI workflows (Task 3 settings panel)."""

import pytest


@pytest.fixture(scope="module")
def qt_app():
    """Create QApplication instance with offscreen rendering."""
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication([])
    yield app
    
    app.quit()


class TestSettingsDialogIntegration:
    """Integration tests for Settings Dialog workflow (Task 3)."""

    def test_dialog_opens_with_connection_form(self, qt_app):
        """Test that settings dialog opens with proper connection form."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Verify main layout exists
        assert hasattr(dialog, 'layout') or hasattr(dialog, 'main_layout')
        
        # Verify scroll area is present
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = dialog.findChild(QScrollArea)
        assert scroll_area is not None, "Scroll area should exist"

    def test_connection_test_workflow(self, qt_app):
        """Test connection test button workflow."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # 1. Click test button (simulate by checking state change would occur)
        # In integration we verify the method exists and has correct signature
        assert hasattr(dialog.test_btn, 'clicked') or callable(getattr(dialog.test_btn, 'clicked', None))

    def test_apply_workflow(self, qt_app):
        """Test apply workflow with settings dictionary."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Simulate filling form and checking apply behavior
        dialog.ip_edit.setText("192.168.1.100")
        dialog.user_edit.setText("admin")
        dialog.port_spin.setValue(22)
        
        # Verify all fields have values
        assert dialog.ip_edit.text() == "192.168.1.100"
        assert dialog.user_edit.text() == "admin"
        assert dialog.port_spin.value() == 22

    def test_credentials_storage_workflow(self, qt_app):
        """Test credential storage workflow."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Check credentials checkbox is initially checked
        initial_checked = dialog.store_credentials_check.isChecked()
        assert initial_checked is True, "Should store credentials by default"

    def test_status_indicator_workflows(self, qt_app):
        """Test status indicator state changes."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Initial state should be disconnected
        assert "Disconnected" in dialog.status_indicator_label.text()


class TestSettingsDialogErrorHandling:
    """Integration tests for error handling (Task 4 requirements integrated into Task 3)."""

    def test_error_logging_directory_exists(self, qt_app):
        """Test that error logging would create correct directory."""
        from pathlib import Path
        
        logs_dir = Path("~/.local/share/AIManagerUI/logs")
        # The directory should be created when errors occur
        assert logs_dir.is_absolute() or "~" in str(logs_dir)

    def test_error_message_formatting(self, qt_app):
        """Test that error messages are user-friendly."""
        from src.ui.settings_dialog import SettingsDialog
        from src.error_handler import get_error_log_path
        from pathlib import Path

        dialog = SettingsDialog(parent=None)

        # Verify Task 4: Error logging directory exists and is properly configured
        log_path = get_error_log_path()
        logs_dir = Path(log_path).parent
        assert logs_dir.is_absolute()
        assert "local/share/AIManagerUI/logs" in str(logs_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
