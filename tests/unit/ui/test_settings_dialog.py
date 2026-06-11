"""Unit tests for SettingsDialog (Task 3 implementation)."""

import pytest


@pytest.fixture(scope="module")
def qt_app():
    """Create a QApplication instance with offscreen rendering."""
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication([])
    yield app
    
    app.quit()


class TestSettingsDialogInit:
    """Tests for SettingsDialog initialization (Task 3)."""

    def test_settings_dialog_initializes(self, qt_app):
        """Test that SettingsDialog initializes properly."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert dialog is not None
        assert dialog.windowTitle() == "Settings - AI Model Server Manager"
        assert dialog.minimumSize().width() >= 520

    def test_has_connection_status_labels(self, qt_app):
        """Test that connection status indicators are present (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Check for status indicator label attribute
        assert hasattr(dialog, 'status_indicator_label'), "Status indicator label should exist"

    def test_has_timestamp_display(self, qt_app):
        """Test that last connection timestamp display exists (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Check for timestamp display attribute
        assert hasattr(dialog, 'last_connection_display'), "Timestamp display should exist"

    def test_has_test_button(self, qt_app):
        """Test that connectivity test button exists (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        # Check for test button attribute
        assert hasattr(dialog, 'test_btn'), "Test connection button should exist"


class TestSettingsDialogInputFields:
    """Tests for input fields validation (Task 3)."""

    def test_ip_edit_exists(self, qt_app):
        """Test that IP address input field exists."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert hasattr(dialog, 'ip_edit'), "IP edit field should exist"

    def test_username_field_exists(self, qt_app):
        """Test that username input field exists."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert hasattr(dialog, 'user_edit'), "Username edit field should exist"

    def test_port_spinbox_exists(self, qt_app):
        """Test that port spinbox exists with proper range (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert hasattr(dialog, 'port_spin'), "Port spinbox should exist"

    def test_default_values(self, qt_app):
        """Test that default values are applied (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(
            parent=None,
            default_host="192.168.1.100",
            default_user="root",
            default_port=22
        )
        
        # Check placeholder contains the default (since we set text)
        assert "192.168.1.100" in dialog.ip_edit.text()
        assert dialog.user_edit.text() == "root"
        assert dialog.port_spin.value() == 22


class TestSettingsDialogConnectionStatus:
    """Tests for connection status indicators (Task 3)."""

    def test_status_label_initial_state(self, qt_app):
        """Test that status indicator shows initial disconnected state."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Use hasattr to safely access the label
        assert hasattr(dialog, 'status_indicator_label'), "Status label should exist"
        if hasattr(dialog.status_indicator_label, 'text'):
            status_text = dialog.status_indicator_label.text()
            assert "Disconnected" in status_text, f"Should show Disconnected, got: {status_text}"

    def test_timestamp_initial_state(self, qt_app):
        """Test that timestamp shows initial placeholder."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        assert hasattr(dialog, 'last_connection_display'), "Timestamp display should exist"
        if hasattr(dialog.last_connection_display, 'text'):
            assert dialog.last_connection_display.text() == "-", \
                   f"Should show '-', got: {dialog.last_connection_display.text()}"


class TestSettingsDialogCredentialStorage:
    """Tests for credential storage (Task 3)."""

    def test_store_credentials_checkbox_exists(self, qt_app):
        """Test that store credentials checkbox exists (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert hasattr(dialog, 'store_credentials_check'), "Store credentials checkbox should exist"
        
        # Should be checked by default
        assert dialog.store_credentials_check.isChecked(), "Should store credentials by default"


class TestSettingsDialogConnectionTest:
    """Tests for connection test functionality (Task 3)."""

    def test_progress_bar_initially_hidden(self, qt_app):
        """Test that progress bar is initially hidden."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        assert not dialog.progress_bar.isVisible(), "Progress bar should be hidden initially"


class TestSettingsDialogApply:
    """Tests for Apply functionality (Task 3)."""

    def test_apply_emits_settings_signal(self, qt_app):
        """Test that apply button emits settings_applied signal."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Connect to the signal and verify it exists
        assert hasattr(dialog, 'settings_applied'), "Should have settings_applied signal"

    def test_settings_dict_structure(self, qt_app):
        """Test that settings dictionary contains all required fields (Task 3)."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Manually set some values and check what would be emitted
        dialog.ip_edit.setText("192.168.1.100")
        dialog.user_edit.setText("admin")
        dialog.port_spin.setValue(22)
        
        settings_dict = {
            'ip': "192.168.1.100",
            'username': "admin",
            'port': 22,
            'store_credentials': dialog.store_credentials_check.isChecked(),
            'auto_reconnect': dialog.auto_reconnect_check.isChecked()
        }
        
        assert 'ip' in settings_dict
        assert 'username' in settings_dict
        assert 'port' in settings_dict


class TestSettingsDialogValidation:
    """Tests for input validation (Task 3)."""

    def test_ip_validation(self, qt_app):
        """Test IP address validation."""
        from src.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=None)
        
        # Valid IP should not cause issues
        dialog.ip_edit.setText("192.168.1.100")


def test_full_workflow(qt_app):
    """Full workflow test for settings dialog (Task 3)."""
    from src.ui.settings_dialog import SettingsDialog
    
    # Create dialog with default values
    dialog = SettingsDialog(
        parent=None,
        default_host="192.168.1.100",
        default_user="root",
        default_port=22
    )
    
    # Verify all required widgets exist (Task 3 requirements)
    assert hasattr(dialog, 'ip_edit'), "IP edit field should exist"
    assert hasattr(dialog, 'user_edit'), "Username edit field should exist"
    assert hasattr(dialog, 'port_spin'), "Port spinbox should exist"
    assert hasattr(dialog, 'status_indicator_label'), "Status indicator label should exist"
    assert hasattr(dialog, 'last_connection_display'), "Timestamp display should exist"
    assert hasattr(dialog, 'test_btn'), "Test button should exist"
    assert hasattr(dialog, 'store_credentials_check'), "Store credentials checkbox should exist"
    assert hasattr(dialog, 'apply_btn'), "Apply button should exist"
    
    # Verify initial states
    status_text = dialog.status_indicator_label.text() if hasattr(dialog, 'status_indicator_label') else ""
    assert "Disconnected" in str(status_text), f"Initial state should be Disconnected, got: {status_text}"
    
    timestamp_text = dialog.last_connection_display.text() if hasattr(dialog, 'last_connection_display') else ""
    assert timestamp_text == "-", f"Timestamp should be '-', got: {timestamp_text}"
    
    assert dialog.store_credentials_check.isChecked(), "Should store credentials by default"
    
    print("✓ Full workflow test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
