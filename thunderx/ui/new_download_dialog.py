"""New download dialog"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QGroupBox, QFormLayout, QFileDialog,
    QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard

from .styles import COLORS, BUTTON_PRIMARY_STYLE


class NewDownloadDialog(QDialog):
    """Dialog for adding new download"""

    def __init__(self, url: str = "", parent=None):
        super().__init__(parent)
        self.url = url
        self.save_path = ""
        self.filename = ""
        self._setup_ui()

        # Auto-paste URL from clipboard if empty
        if not url:
            self._paste_from_clipboard()

    def _setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("New Download")
        self.setMinimumWidth(550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # URL group
        url_group = QGroupBox("Download URL")
        url_layout = QVBoxLayout(url_group)

        url_input_layout = QHBoxLayout()
        self.url_input = QLineEdit(self.url)
        self.url_input.setPlaceholderText("Enter download URL...")
        self.url_input.setMinimumHeight(36)
        url_input_layout.addWidget(self.url_input)

        paste_btn = QPushButton("Paste")
        paste_btn.setFixedWidth(70)
        paste_btn.clicked.connect(self._paste_from_clipboard)
        url_input_layout.addWidget(paste_btn)

        url_layout.addLayout(url_input_layout)
        layout.addWidget(url_group)

        # Save location group
        save_group = QGroupBox("Save Location")
        save_layout = QVBoxLayout(save_group)

        # Filename
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Filename:"))
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Auto-detect from URL")
        self.filename_input.setMinimumHeight(36)
        filename_layout.addWidget(self.filename_input)
        save_layout.addLayout(filename_layout)

        # Directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Save to:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select download folder...")
        self.dir_input.setMinimumHeight(36)
        dir_layout.addWidget(self.dir_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)
        save_layout.addLayout(dir_layout)

        layout.addWidget(save_group)

        # Options group
        options_group = QGroupBox("Download Options")
        options_form = QFormLayout(options_group)

        self.connections_spin = QSpinBox()
        self.connections_spin.setRange(1, 32)
        self.connections_spin.setValue(8)
        self.connections_spin.setMinimumHeight(36)
        options_form.addRow("Connections:", self.connections_spin)

        self.speed_limit_combo = QComboBox()
        self.speed_limit_combo.addItems(["Unlimited", "1 MB/s", "2 MB/s", "5 MB/s", "10 MB/s"])
        self.speed_limit_combo.setMinimumHeight(36)
        options_form.addRow("Speed Limit:", self.speed_limit_combo)

        self.auto_start_check = QCheckBox("Start download immediately")
        self.auto_start_check.setChecked(True)
        options_form.addRow(self.auto_start_check)

        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        download_btn = QPushButton("Download")
        download_btn.setMinimumHeight(40)
        download_btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
        download_btn.clicked.connect(self._on_download)
        button_layout.addWidget(download_btn)

        layout.addLayout(button_layout)

    def _paste_from_clipboard(self):
        """Paste URL from clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            text = clipboard.text()
            if text and (text.startswith("http://") or text.startswith("https://") or text.startswith("ftp://")):
                self.url_input.setText(text)
                self._auto_detect_filename(text)

    def _auto_detect_filename(self, url: str):
        """Auto-detect filename from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = parsed.path.split("/")[-1]
        if filename:
            self.filename_input.setText(filename)

    def _browse_directory(self):
        """Browse for save directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self.dir_input.text()
        )
        if directory:
            self.dir_input.setText(directory)

    def _on_download(self):
        """Handle download button click"""
        if not self.url_input.text().strip():
            self.url_input.setFocus()
            return

        if not self.dir_input.text().strip():
            self._browse_directory()
            if not self.dir_input.text().strip():
                return

        self.accept()

    def get_download_info(self) -> dict:
        """Get download information"""
        speed_limits = {
            "Unlimited": 0,
            "1 MB/s": 1024 * 1024,
            "2 MB/s": 2 * 1024 * 1024,
            "5 MB/s": 5 * 1024 * 1024,
            "10 MB/s": 10 * 1024 * 1024,
        }

        return {
            "url": self.url_input.text().strip(),
            "filename": self.filename_input.text().strip() or None,
            "save_path": self.dir_input.text().strip(),
            "num_connections": self.connections_spin.value(),
            "speed_limit": speed_limits.get(self.speed_limit_combo.currentText(), 0),
            "auto_start": self.auto_start_check.isChecked(),
        }
