"""Download task list widget"""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QMenu, QWidget, QHBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QAction

from ..engine.task import DownloadTask, TaskStatus
from ..utils.file_utils import format_size, format_speed, format_time
from .styles import COLORS


class TaskListWidget(QTableWidget):
    """Widget displaying download tasks"""

    # Signals
    task_selected = pyqtSignal(str)  # task_id
    pause_requested = pyqtSignal(str)
    resume_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    open_folder_requested = pyqtSignal(str)

    COLUMNS = ["Filename", "Size", "Progress", "Speed", "ETA", "Status"]
    COLUMN_WIDTHS = [300, 100, 150, 100, 80, 100]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks: dict[str, DownloadTask] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup table widget"""
        # Configure table
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.horizontalHeader()
        for i, width in enumerate(self.COLUMN_WIDTHS):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed if i > 0 else QHeaderView.ResizeMode.Stretch)
            if i > 0:
                self.setColumnWidth(i, width)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Selection change
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def add_task(self, task: DownloadTask):
        """Add a new task to the list"""
        self._tasks[task.task_id] = task
        row = self.rowCount()
        self.insertRow(row)
        self._update_row(row, task)

    def update_task(self, task: DownloadTask):
        """Update existing task in the list"""
        self._tasks[task.task_id] = task
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task.task_id:
                self._update_row(row, task)
                break

    def remove_task(self, task_id: str):
        """Remove task from the list"""
        if task_id in self._tasks:
            del self._tasks[task_id]
        
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self.removeRow(row)
                break

    def _update_row(self, row: int, task: DownloadTask):
        """Update a row with task data"""
        # Filename
        filename_item = QTableWidgetItem(task.filename)
        filename_item.setData(Qt.ItemDataRole.UserRole, task.task_id)
        filename_item.setToolTip(task.url)
        self.setItem(row, 0, filename_item)

        # Size
        size_text = format_size(task.total_size) if task.total_size > 0 else "Unknown"
        self.setItem(row, 1, QTableWidgetItem(size_text))

        # Progress bar
        progress_widget = self._create_progress_widget(task)
        self.setCellWidget(row, 2, progress_widget)

        # Speed
        speed = self._get_task_speed(task)
        self.setItem(row, 3, QTableWidgetItem(format_speed(speed)))

        # ETA
        if speed > 0 and task.total_size > 0:
            remaining = task.total_size - task.downloaded_size
            eta = remaining / speed
            self.setItem(row, 4, QTableWidgetItem(format_time(eta)))
        else:
            self.setItem(row, 4, QTableWidgetItem("--:--"))

        # Status
        status_item = QTableWidgetItem(self._get_status_text(task.status))
        status_item.setForeground(self._get_status_color(task.status))
        self.setItem(row, 5, status_item)

    def _create_progress_widget(self, task: DownloadTask) -> QWidget:
        """Create progress bar widget with percentage label"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(task.progress))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(8)
        layout.addWidget(progress_bar)

        label = QLabel(f"{task.progress:.1f}%")
        label.setFixedWidth(45)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        layout.addWidget(label)

        return widget

    def _get_task_speed(self, task: DownloadTask) -> float:
        """Get current task speed (placeholder)"""
        # In real implementation, this would get speed from engine
        return 0.0

    def _get_status_text(self, status: TaskStatus) -> str:
        """Get status display text"""
        return {
            TaskStatus.PENDING: "Pending",
            TaskStatus.DOWNLOADING: "Downloading",
            TaskStatus.PAUSED: "Paused",
            TaskStatus.COMPLETED: "Completed",
            TaskStatus.FAILED: "Failed",
            TaskStatus.VERIFYING: "Verifying",
        }.get(status, "Unknown")

    def _get_status_color(self, status: TaskStatus) -> QColor:
        """Get status text color"""
        return {
            TaskStatus.PENDING: QColor(COLORS['text_secondary']),
            TaskStatus.DOWNLOADING: QColor(COLORS['accent']),
            TaskStatus.PAUSED: QColor(COLORS['warning']),
            TaskStatus.COMPLETED: QColor(COLORS['success']),
            TaskStatus.FAILED: QColor(COLORS['error']),
        }.get(status, QColor(COLORS['text_primary']))

    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.itemAt(position)
        if not item:
            return

        row = item.row()
        task_id = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
        task = self._tasks.get(task_id)
        if not task:
            return

        menu = QMenu(self)

        if task.status == TaskStatus.DOWNLOADING:
            pause_action = QAction("Pause", self)
            pause_action.triggered.connect(lambda: self.pause_requested.emit(task_id))
            menu.addAction(pause_action)
        elif task.status == TaskStatus.PAUSED:
            resume_action = QAction("Resume", self)
            resume_action.triggered.connect(lambda: self.resume_requested.emit(task_id))
            menu.addAction(resume_action)

        menu.addSeparator()

        open_folder_action = QAction("Open Folder", self)
        open_folder_action.triggered.connect(lambda: self.open_folder_requested.emit(task_id))
        menu.addAction(open_folder_action)

        copy_url_action = QAction("Copy URL", self)
        copy_url_action.triggered.connect(lambda: self._copy_url(task))
        menu.addAction(copy_url_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(task_id))
        menu.addAction(delete_action)

        menu.exec(self.mapToGlobal(position))

    def _copy_url(self, task: DownloadTask):
        """Copy task URL to clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(task.url)

    def _on_selection_changed(self):
        """Handle selection change"""
        selected = self.selectedItems()
        if selected:
            row = selected[0].row()
            task_id = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.task_selected.emit(task_id)

    def get_selected_task_id(self) -> str | None:
        """Get currently selected task ID"""
        selected = self.selectedItems()
        if selected:
            row = selected[0].row()
            return self.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return None

    def clear_all(self):
        """Clear all tasks"""
        self.setRowCount(0)
        self._tasks.clear()
