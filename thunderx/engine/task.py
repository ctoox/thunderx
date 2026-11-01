"""Download task management"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse


class TaskStatus(Enum):
    """Download task status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"


@dataclass
class ChunkInfo:
    """Information about a download chunk"""
    index: int
    start: int
    end: int
    downloaded: int = 0
    status: str = "pending"


@dataclass
class DownloadTask:
    """Represents a single download task"""
    url: str
    filename: str
    save_path: str
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    total_size: int = 0
    downloaded_size: int = 0
    chunks: List[ChunkInfo] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    num_connections: int = 8
    speed_limit: int = 0  # 0 means no limit
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique task ID"""
        content = f"{self.url}_{self.save_path}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    @property
    def progress(self) -> float:
        """Calculate download progress percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded_size / self.total_size) * 100

    @property
    def speed(self) -> float:
        """Calculate current download speed (bytes/sec)"""
        # This would be calculated by the engine
        return 0.0

    @property
    def file_path(self) -> Path:
        """Get full file path"""
        return Path(self.save_path) / self.filename

    @property
    def temp_path(self) -> Path:
        """Get temporary download file path"""
        return Path(self.save_path) / f".{self.filename}.thx"

    @property
    def metadata_path(self) -> Path:
        """Get metadata file path"""
        return Path(self.save_path) / f".{self.filename}.thx.meta"

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "url": self.url,
            "filename": self.filename,
            "save_path": self.save_path,
            "status": self.status.value,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "chunks": [
                {
                    "index": c.index,
                    "start": c.start,
                    "end": c.end,
                    "downloaded": c.downloaded,
                    "status": c.status,
                }
                for c in self.chunks
            ],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "headers": self.headers,
            "num_connections": self.num_connections,
            "speed_limit": self.speed_limit,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadTask":
        """Create task from dictionary"""
        task = cls(
            url=data["url"],
            filename=data["filename"],
            save_path=data["save_path"],
            task_id=data["task_id"],
        )
        task.status = TaskStatus(data["status"])
        task.total_size = data["total_size"]
        task.downloaded_size = data["downloaded_size"]
        task.chunks = [ChunkInfo(**c) for c in data.get("chunks", [])]
        task.created_at = data["created_at"]
        task.completed_at = data.get("completed_at")
        task.error_message = data.get("error_message", "")
        task.headers = data.get("headers", {})
        task.num_connections = data.get("num_connections", 8)
        task.speed_limit = data.get("speed_limit", 0)
        task.metadata = data.get("metadata", {})
        return task

    def save_metadata(self):
        """Save task metadata to file"""
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_metadata(cls, path: Path) -> Optional["DownloadTask"]:
        """Load task metadata from file"""
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return None

    def setup_chunks(self, chunk_size: int = 1024 * 1024):
        """Setup download chunks for parallel downloading"""
        if self.total_size <= 0:
            # Single chunk for unknown size
            self.chunks = [ChunkInfo(0, 0, 0)]
            return

        self.chunks = []
        num_chunks = min(self.num_connections, max(1, self.total_size // chunk_size))
        actual_chunk_size = self.total_size // num_chunks

        for i in range(num_chunks):
            start = i * actual_chunk_size
            end = start + actual_chunk_size - 1 if i < num_chunks - 1 else self.total_size - 1
            self.chunks.append(ChunkInfo(
                index=i,
                start=start,
                end=end,
                downloaded=0,
            ))

    def get_incomplete_chunks(self) -> List[ChunkInfo]:
        """Get list of chunks that haven't been fully downloaded"""
        return [c for c in self.chunks if c.downloaded < (c.end - c.start + 1)]
