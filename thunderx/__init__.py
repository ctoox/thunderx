"""ThunderX - High-speed download manager with P2P acceleration"""

__version__ = "1.0.0"
__author__ = "ThunderX Team"

from .engine.download_engine import DownloadEngine
from .engine.task import DownloadTask, TaskStatus

__all__ = ["DownloadEngine", "DownloadTask", "TaskStatus"]
