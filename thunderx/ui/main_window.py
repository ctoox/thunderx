"""Main application window"""

import asyncio
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QLabel, QMessageBox, QApplication,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from ..engine.download_engine import DownloadEngine
from ..engine.task import DownloadTask, TaskStatus
from ..utils.config import Config
from ..utils.file_utils import format_size, format_speed
from .task_list_widget import TaskListWidget
from .new_download_dialog import NewDownloadDialog
from .settings_dialog import SettingsDialog
from .styles import MAIN_STYLE, COLORS, BUTTON_PRIMARY_STYLE


class DownloadWorker(QThread):
    """Worker thread for async operations"""
    task_added = pyqtSignal(object)
    task_updated = pyqtSignal(object)
    task_completed = pyqtSignal(object)
    task_failed = pyqtSignal(object, str)

    def __init__(self, engine: DownloadEngine):
        super().__init__()
        self.engine = engine
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        """Run event loop in thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self):
        """Stop event loop"""
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def add_task(self, url: str, save_path: str, filename: Optional[str] = None,
                 num_connections: int = 8, auto_start: bool = True):
        """Add download task"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._async_add_task(url, save_path, filename, num_connections, auto_start),
                self._loop
            )

    async def _async_add_task(self, url, save_path, filename, num_connections, auto_start):
        """Async add task"""
        try:
            task = await self.engine.add_task(url, save_path, filename, num_connections)
            self.task_added.emit(task)

            if auto_start:
                await self.engine.start_task(task.task_id)
        except Exception as e:
            self.task_failed.emit(None, str(e))

    def pause_task(self, task_id: str):
        """Pause download task"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.engine.pause_task(task_id), self._loop
            )

    def resume_task(self, task_id: str):
        """Resume download task"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.engine.resume_task(task_id), self._loop
            )

    def delete_task(self, task_id: str, delete_file: bool = False):
        """Delete download task"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self.engine.remove_task(task_id, delete_file), self._loop
            )


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.engine = DownloadEngine(self.config)
        self.worker: Optional[DownloadWorker] = None
        self._setup_ui()
        self._setup_engine()
        self._setup_shortcuts()

    def _setup_ui(self):
        """Setup main window UI"""
        self.setWindowTitle("ThunderX Download Manager")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(MAIN_STYLE)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Task list
        self.task_list = TaskListWidget()
        self.task_list.pause_requested.connect(self._on_pause_task)
        self.task_list.resume_requested.connect(self._on_resume_task)
        self.task_list.delete_requested.connect(self._on_delete_task)
        self.task_list.open_folder_requested.connect(self._on_open_folder)
        layout.addWidget(self.task_list)

        # Status bar
        self._create_status_bar()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)

    def _create_toolbar(self):
        """Create main toolbar"""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # New download button
        new_action = QAction("New Download", self)
        new_action.triggered.connect(self._on_new_download)
        self.toolbar.addAction(new_action)

        self.toolbar.addSeparator()

        # Batch download
        batch_action = QAction("Batch Download", self)
        batch_action.triggered.connect(self._on_batch_download)
        self.toolbar.addAction(batch_action)

        self.toolbar.addSeparator()

        # Control buttons
        pause_all_action = QAction("Pause All", self)
        pause_all_action.triggered.connect(self._on_pause_all)
        self.toolbar.addAction(pause_all_action)

        resume_all_action = QAction("Resume All", self)
        resume_all_action.triggered.connect(self._on_resume_all)
        self.toolbar.addAction(resume_all_action)

        self.toolbar.addSeparator()

        # Settings
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._on_settings)
        self.toolbar.addAction(settings_action)

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Speed label
        self.speed_label = QLabel("Speed: 0 B/s")
        self.status_bar.addPermanentWidget(self.speed_label)

        # Task count label
        self.task_count_label = QLabel("Tasks: 0")
        self.status_bar.addPermanentWidget(self.task_count_label)

    def _setup_engine(self):
        """Setup download engine"""
        self.worker = DownloadWorker(self.engine)
        self.worker.task_added.connect(self._on_task_added)
        self.worker.task_completed.connect(self._on_task_completed)
        self.worker.task_failed.connect(self._on_task_failed)
        self.worker.start()

        # Setup engine callbacks
        self.engine.on("progress", self._on_progress)
        self.engine.on("complete", self._on_complete)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+N: New download
        new_shortcut = QAction("New Download", self)
        new_shortcut.setShortcut(QKeySequence("Ctrl+N"))
        new_shortcut.triggered.connect(self._on_new_download)
        self.addAction(new_shortcut)

        # Delete: Delete selected
        delete_shortcut = QAction("Delete", self)
        delete_shortcut.setShortcut(QKeySequence("Delete"))
        delete_shortcut.triggered.connect(self._on_delete_selected)
        self.addAction(delete_shortcut)

        # Space: Pause/Resume selected
        space_shortcut = QAction("Toggle Pause", self)
        space_shortcut.setShortcut(QKeySequence("Space"))
        space_shortcut.triggered.connect(self._on_toggle_selected)
        self.addAction(space_shortcut)

    def _on_new_download(self):
        """Handle new download action"""
        dialog = NewDownloadDialog(parent=self)
        if dialog.exec():
            info = dialog.get_download_info()
            self.worker.add_task(
                url=info["url"],
                save_path=info["save_path"],
                filename=info["filename"],
                num_connections=info["num_connections"],
                auto_start=info["auto_start"],
            )

    def _on_batch_download(self):
        """Handle batch download action"""
        dialog = NewDownloadDialog(parent=self)
        if dialog.exec():
            info = dialog.get_download_info()
            # Parse multiple URLs (one per line)
            urls = info["url"].strip().split("\n")
            for url in urls:
                url = url.strip()
                if url:
                    self.worker.add_task(
                        url=url,
                        save_path=info["save_path"],
                        num_connections=info["num_connections"],
                        auto_start=info["auto_start"],
                    )

    def _on_pause_task(self, task_id: str):
        """Handle pause task"""
        self.worker.pause_task(task_id)

    def _on_resume_task(self, task_id: str):
        """Handle resume task"""
        self.worker.resume_task(task_id)

    def _on_delete_task(self, task_id: str):
        """Handle delete task"""
        reply = QMessageBox.question(
            self, "Delete Task",
            "Do you want to delete the downloaded file as well?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply != QMessageBox.StandardButton.Cancel:
            delete_file = reply == QMessageBox.StandardButton.Yes
            self.worker.delete_task(task_id, delete_file)
            self.task_list.remove_task(task_id)

    def _on_open_folder(self, task_id: str):
        """Handle open folder"""
        task = self.engine.get_task(task_id)
        if task:
            import subprocess
            import platform
            folder = str(Path(task.save_path).absolute())
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", folder])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _on_pause_all(self):
        """Handle pause all tasks"""
        for task in self.engine.get_all_tasks():
            if task.status == TaskStatus.DOWNLOADING:
                self.worker.pause_task(task.task_id)

    def _on_resume_all(self):
        """Handle resume all tasks"""
        for task in self.engine.get_all_tasks():
            if task.status == TaskStatus.PAUSED:
                self.worker.resume_task(task.task_id)

    def _on_settings(self):
        """Handle settings action"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Apply new settings
            pass

    def _on_delete_selected(self):
        """Handle delete selected task"""
        task_id = self.task_list.get_selected_task_id()
        if task_id:
            self._on_delete_task(task_id)

    def _on_toggle_selected(self):
        """Handle toggle pause/resume selected task"""
        task_id = self.task_list.get_selected_task_id()
        if task_id:
            task = self.engine.get_task(task_id)
            if task:
                if task.status == TaskStatus.DOWNLOADING:
                    self.worker.pause_task(task_id)
                elif task.status == TaskStatus.PAUSED:
                    self.worker.resume_task(task_id)

    def _on_task_added(self, task: DownloadTask):
        """Handle task added"""
        self.task_list.add_task(task)
        self.status_bar.showMessage(f"Download started: {task.filename}", 3000)

    def _on_task_completed(self, task: DownloadTask):
        """Handle task completed"""
        self.task_list.update_task(task)
        self.status_bar.showMessage(f"Download completed: {task.filename}", 5000)

    def _on_task_failed(self, task: Optional[DownloadTask], error: str):
        """Handle task failed"""
        if task:
            self.task_list.update_task(task)
        self.status_bar.showMessage(f"Download failed: {error}", 5000)

    def _on_progress(self, task: DownloadTask):
        """Handle progress update"""
        # Update will happen in timer
        pass

    def _on_complete(self, task: DownloadTask):
        """Handle download complete"""
        self.worker.task_completed.emit(task)

    def _update_status(self):
        """Update status bar"""
        tasks = self.engine.get_all_tasks()
        downloading = [t for t in tasks if t.status == TaskStatus.DOWNLOADING]

        # Update task count
        self.task_count_label.setText(f"Tasks: {len(tasks)}")

        # Update speed
        total_speed = sum(self.engine.get_speed(t.task_id) for t in downloading)
        self.speed_label.setText(f"Speed: {format_speed(total_speed)}")

        # Update task list
        for task in tasks:
            self.task_list.update_task(task)

    def closeEvent(self, event):
        """Handle window close"""
        # Stop worker thread
        if self.worker:
            self.worker.stop()
            self.worker.wait()

        # Shutdown engine
        asyncio.run(self.engine.shutdown())
        event.accept()
