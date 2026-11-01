"""Settings dialog"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QGroupBox, QFormLayout, QTabWidget,
    QWidget, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt

from ..utils.config import Config
from .styles import COLORS, BUTTON_PRIMARY_STYLE


class SettingsDialog(QDialog):
    """Settings dialog"""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 450)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_download_tab(), "Download")
        tabs.addTab(self._create_network_tab(), "Network")
        tabs.addTab(self._create_advanced_tab(), "Advanced")
        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setMinimumHeight(40)
        save_btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("General Settings")
        form = QFormLayout(group)

        self.save_path_input = QLineEdit()
        self.save_path_input.setMinimumHeight(36)
        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.save_path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_save_path)
        browse_layout.addWidget(browse_btn)
        form.addRow("Default Save Path:", browse_layout)

        self.max_tasks_spin = QSpinBox()
        self.max_tasks_spin.setRange(1, 20)
        self.max_tasks_spin.setMinimumHeight(36)
        form.addRow("Max Concurrent Tasks:", self.max_tasks_spin)

        self.auto_start_check = QCheckBox("Auto-start downloads")
        form.addRow(self.auto_start_check)

        self.show_notifications_check = QCheckBox("Show notifications")
        form.addRow(self.show_notifications_check)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_download_tab(self) -> QWidget:
        """Create download settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Download Settings")
        form = QFormLayout(group)

        self.connections_spin = QSpinBox()
        self.connections_spin.setRange(1, 32)
        self.connections_spin.setMinimumHeight(36)
        form.addRow("Default Connections:", self.connections_spin)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(64, 4096)
        self.chunk_size_spin.setSuffix(" KB")
        self.chunk_size_spin.setMinimumHeight(36)
        form.addRow("Chunk Size:", self.chunk_size_spin)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 20)
        self.retries_spin.setMinimumHeight(36)
        form.addRow("Max Retries:", self.retries_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setMinimumHeight(36)
        form.addRow("Connection Timeout:", self.timeout_spin)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_network_tab(self) -> QWidget:
        """Create network settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # P2P settings
        p2p_group = QGroupBox("P2P Settings")
        p2p_form = QFormLayout(p2p_group)

        self.enable_p2p_check = QCheckBox("Enable P2P acceleration")
        p2p_form.addRow(self.enable_p2p_check)

        self.p2p_port_spin = QSpinBox()
        self.p2p_port_spin.setRange(1024, 65535)
        self.p2p_port_spin.setMinimumHeight(36)
        p2p_form.addRow("P2P Port:", self.p2p_port_spin)

        layout.addWidget(p2p_group)

        # Browser extension settings
        browser_group = QGroupBox("Browser Extension")
        browser_form = QFormLayout(browser_group)

        self.enable_browser_check = QCheckBox("Enable browser integration")
        browser_form.addRow(self.enable_browser_check)

        self.browser_port_spin = QSpinBox()
        self.browser_port_spin.setRange(1024, 65535)
        self.browser_port_spin.setMinimumHeight(36)
        browser_form.addRow("Extension Port:", self.browser_port_spin)

        layout.addWidget(browser_group)
        layout.addStretch()
        return widget

    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Advanced Settings")
        form = QFormLayout(group)

        self.user_agent_input = QLineEdit()
        self.user_agent_input.setMinimumHeight(36)
        form.addRow("User Agent:", self.user_agent_input)

        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setRange(1024, 65536)
        self.buffer_size_spin.setSuffix(" bytes")
        self.buffer_size_spin.setMinimumHeight(36)
        form.addRow("Buffer Size:", self.buffer_size_spin)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _browse_save_path(self):
        """Browse for default save path"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Default Save Path", self.save_path_input.text()
        )
        if directory:
            self.save_path_input.setText(directory)

    def _load_settings(self):
        """Load settings from config"""
        self.save_path_input.setText(self.config.default_save_path)
        self.max_tasks_spin.setValue(self.config.max_concurrent_tasks)
        self.connections_spin.setValue(self.config.max_connections_per_task)
        self.chunk_size_spin.setValue(self.config.chunk_size // 1024)
        self.retries_spin.setValue(self.config.max_retries)
        self.timeout_spin.setValue(self.config.timeout)
        self.enable_p2p_check.setChecked(self.config.enable_p2p)
        self.p2p_port_spin.setValue(self.config.p2p_port)
        self.enable_browser_check.setChecked(self.config.enable_browser_extension)
        self.browser_port_spin.setValue(self.config.browser_port)
        self.user_agent_input.setText(self.config.user_agent)
        self.buffer_size_spin.setValue(self.config.buffer_size)

    def _save_settings(self):
        """Save settings to config"""
        self.config.set("default_save_path", self.save_path_input.text())
        self.config.set("max_concurrent_tasks", self.max_tasks_spin.value())
        self.config.set("max_connections_per_task", self.connections_spin.value())
        self.config.set("chunk_size", self.chunk_size_spin.value() * 1024)
        self.config.set("max_retries", self.retries_spin.value())
        self.config.set("timeout", self.timeout_spin.value())
        self.config.set("enable_p2p", self.enable_p2p_check.isChecked())
        self.config.set("p2p_port", self.p2p_port_spin.value())
        self.config.set("enable_browser_extension", self.enable_browser_check.isChecked())
        self.config.set("browser_port", self.browser_port_spin.value())
        self.config.set("user_agent", self.user_agent_input.text())
        self.config.set("buffer_size", self.buffer_size_spin.value())
        self.config.save()
        self.accept()
