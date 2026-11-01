"""Main download engine with multi-threaded chunk downloading"""

import asyncio
import aiohttp
import aiofiles
import time
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from .task import DownloadTask, TaskStatus, ChunkInfo
from .chunk_manager import ChunkManager
from ..utils.logger import setup_logger
from ..utils.config import Config


class DownloadEngine:
    """Core download engine with multi-threaded chunk support"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.logger = setup_logger("engine")
        self.chunk_manager = ChunkManager()
        self._tasks: Dict[str, DownloadTask] = {}
        self._active_downloads: Dict[str, asyncio.Task] = {}
        self._speed_trackers: Dict[str, List[float]] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "progress": [],
            "complete": [],
            "error": [],
            "status_change": [],
        }
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

    async def initialize(self):
        """Initialize the download engine"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": self.config.user_agent},
        )
        self.logger.info("Download engine initialized")

    async def shutdown(self):
        """Shutdown the engine and cleanup resources"""
        # Cancel all active downloads
        for task_id, task in self._active_downloads.items():
            task.cancel()
        
        if self._session:
            await self._session.close()
        
        self.logger.info("Download engine shutdown")

    def on(self, event: str, callback: Callable):
        """Register event callback"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit(self, event: str, *args, **kwargs):
        """Emit event to registered callbacks"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")

    async def add_task(
        self,
        url: str,
        save_path: str = ".",
        filename: Optional[str] = None,
        num_connections: int = 8,
        headers: Optional[Dict[str, str]] = None,
    ) -> DownloadTask:
        """Add a new download task"""
        # Parse filename from URL if not provided
        if not filename:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "download"
        
        # Create task
        task = DownloadTask(
            url=url,
            filename=filename,
            save_path=save_path,
            num_connections=num_connections,
            headers=headers or {},
        )
        
        # Get file info
        await self._get_file_info(task)
        
        # Setup chunks
        task.setup_chunks(self.config.chunk_size)
        
        # Save task
        self._tasks[task.task_id] = task
        task.save_metadata()
        
        self.logger.info(f"Task added: {task.task_id} - {filename}")
        self._emit("status_change", task)
        
        return task

    async def _get_file_info(self, task: DownloadTask):
        """Get remote file information"""
        try:
            async with self._session.head(
                task.url,
                headers=task.headers,
                allow_redirects=True,
            ) as response:
                # Get file size
                content_length = response.headers.get("Content-Length")
                if content_length:
                    task.total_size = int(content_length)
                
                # Check for range support
                accept_ranges = response.headers.get("Accept-Ranges", "")
                task.metadata["supports_range"] = "bytes" in accept_ranges.lower()
                
                # Get content type
                content_type = response.headers.get("Content-Type", "")
                task.metadata["content_type"] = content_type
                
        except Exception as e:
            self.logger.warning(f"Could not get file info: {e}")
            task.metadata["supports_range"] = False

    async def start_task(self, task_id: str):
        """Start downloading a task"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.status == TaskStatus.DOWNLOADING:
            return

        task.status = TaskStatus.DOWNLOADING
        self._emit("status_change", task)

        # Create download coroutine
        async def download_wrapper():
            async with self._semaphore:
                try:
                    await self._download_task(task)
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    self.logger.error(f"Download failed: {e}")
                    self._emit("error", task, e)
                finally:
                    self._emit("status_change", task)

        self._active_downloads[task_id] = asyncio.create_task(download_wrapper())

    async def _download_task(self, task: DownloadTask):
        """Execute the download for a task"""
        self.logger.info(f"Starting download: {task.filename}")
        
        # Create temp directory
        temp_dir = Path(task.save_path) / ".thx_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Download chunks in parallel
        if task.metadata.get("supports_range", False) and task.total_size > 0:
            await self._download_chunks(task, temp_dir)
        else:
            await self._download_single(task)

        # Merge chunks if needed
        if len(task.chunks) > 1:
            await self._merge_chunks(task, temp_dir)

        # Rename temp file to final
        temp_file = task.temp_path
        final_file = task.file_path
        if temp_file.exists():
            temp_file.rename(final_file)

        # Cleanup
        self._cleanup_temp(temp_dir, task)

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.save_metadata()
        
        self.logger.info(f"Download completed: {task.filename}")
        self._emit("complete", task)

    async def _download_chunks(self, task: DownloadTask, temp_dir: Path):
        """Download file using multiple chunks"""
        tasks = []
        for chunk in task.chunks:
            chunk_file = temp_dir / f"chunk_{chunk.index}"
            tasks.append(self._download_chunk(task, chunk, chunk_file))
        
        await asyncio.gather(*tasks)

    async def _download_chunk(
        self, task: DownloadTask, chunk: ChunkInfo, chunk_file: Path
    ):
        """Download a single chunk"""
        headers = {**task.headers}
        
        # Add range header
        start = chunk.start + chunk.downloaded
        if start > chunk.start:
            headers["Range"] = f"bytes={start}-{chunk.end}"
        else:
            headers["Range"] = f"bytes={chunk.start}-{chunk.end}"

        retry_count = 0
        max_retries = self.config.max_retries

        while retry_count < max_retries:
            try:
                async with self._session.get(task.url, headers=headers) as response:
                    if response.status not in (200, 206):
                        raise aiohttp.ClientError(f"HTTP {response.status}")

                    async with aiofiles.open(chunk_file, "ab" if chunk.downloaded > 0 else "wb") as f:
                        async for data in response.content.iter_chunked(self.config.buffer_size):
                            await f.write(data)
                            chunk.downloaded += len(data)
                            task.downloaded_size += len(data)
                            
                            # Speed tracking
                            self._update_speed(task.task_id, len(data))
                            
                            # Progress callback
                            self._emit("progress", task)

                            # Speed limit
                            if task.speed_limit > 0:
                                await self._apply_speed_limit(task.speed_limit)

                break  # Success

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                self.logger.warning(f"Chunk {chunk.index} retry {retry_count}: {e}")
                await asyncio.sleep(1 * retry_count)

    async def _download_single(self, task: DownloadTask):
        """Download file as single stream (no range support)"""
        headers = task.headers.copy()
        
        async with self._session.get(task.url, headers=headers) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}")

            # Update total size if available
            content_length = response.headers.get("Content-Length")
            if content_length:
                task.total_size = int(content_length)

            async with aiofiles.open(task.temp_path, "wb") as f:
                async for data in response.content.iter_chunked(self.config.buffer_size):
                    await f.write(data)
                    task.downloaded_size += len(data)
                    
                    self._update_speed(task.task_id, len(data))
                    self._emit("progress", task)

                    if task.speed_limit > 0:
                        await self._apply_speed_limit(task.speed_limit)

    async def _merge_chunks(self, task: DownloadTask, temp_dir: Path):
        """Merge downloaded chunks into final file"""
        self.logger.info(f"Merging {len(task.chunks)} chunks")
        
        async with aiofiles.open(task.temp_path, "wb") as target:
            for chunk in sorted(task.chunks, key=lambda c: c.index):
                chunk_file = temp_dir / f"chunk_{chunk.index}"
                if chunk_file.exists():
                    async with aiofiles.open(chunk_file, "rb") as source:
                        while True:
                            data = await source.read(8192)
                            if not data:
                                break
                            await target.write(data)

    def _cleanup_temp(self, temp_dir: Path, task: DownloadTask):
        """Clean up temporary files"""
        try:
            for chunk_file in temp_dir.glob("chunk_*"):
                chunk_file.unlink()
            temp_dir.rmdir()
        except Exception as e:
            self.logger.warning(f"Cleanup error: {e}")

    def _update_speed(self, task_id: str, bytes_count: int):
        """Update speed tracking"""
        if task_id not in self._speed_trackers:
            self._speed_trackers[task_id] = []
        
        self._speed_trackers[task_id].append(bytes_count)
        
        # Keep only last 100 entries
        if len(self._speed_trackers[task_id]) > 100:
            self._speed_trackers[task_id].pop(0)

    def get_speed(self, task_id: str) -> float:
        """Get current download speed in bytes/sec"""
        tracker = self._speed_trackers.get(task_id, [])
        if not tracker:
            return 0.0
        return sum(tracker) / len(tracker) * 10  # Approximate bytes/sec

    async def _apply_speed_limit(self, limit: int):
        """Apply speed limit by adding delay"""
        # Simple token bucket implementation
        await asyncio.sleep(0.01)

    async def pause_task(self, task_id: str):
        """Pause a download task"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.status == TaskStatus.DOWNLOADING:
            # Cancel active download
            if task_id in self._active_downloads:
                self._active_downloads[task_id].cancel()
                del self._active_downloads[task_id]
            
            task.status = TaskStatus.PAUSED
            task.save_metadata()
            self._emit("status_change", task)

    async def resume_task(self, task_id: str):
        """Resume a paused download task"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.status == TaskStatus.PAUSED:
            await self.start_task(task_id)

    async def remove_task(self, task_id: str, delete_file: bool = False):
        """Remove a download task"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Stop if downloading
        if task.status == TaskStatus.DOWNLOADING:
            await self.pause_task(task_id)

        # Delete file if requested
        if delete_file and task.file_path.exists():
            task.file_path.unlink()
        
        # Remove metadata
        if task.metadata_path.exists():
            task.metadata_path.unlink()

        del self._tasks[task_id]
        self.logger.info(f"Task removed: {task_id}")

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[DownloadTask]:
        """Get all download tasks"""
        return list(self._tasks.values())

    async def load_saved_tasks(self):
        """Load tasks from saved metadata files"""
        save_path = Path(self.config.default_save_path)
        for meta_file in save_path.glob("*.thx.meta"):
            task = DownloadTask.load_metadata(meta_file)
            if task:
                self._tasks[task.task_id] = task
                if task.status == TaskStatus.DOWNLOADING:
                    task.status = TaskStatus.PAUSED
                self.logger.info(f"Loaded task: {task.task_id}")
