"""Chunk management for parallel downloading"""

import asyncio
from typing import List, Optional, BinaryIO
from .task import ChunkInfo


class ChunkManager:
    """Manages download chunks and their states"""

    def __init__(self, chunk_size: int = 1024 * 1024):
        self.chunk_size = chunk_size
        self._locks: dict = {}

    def calculate_chunks(self, total_size: int, num_connections: int) -> List[ChunkInfo]:
        """Calculate optimal chunk distribution"""
        if total_size <= 0:
            return [ChunkInfo(0, 0, 0)]

        # Limit chunks based on file size
        max_chunks = total_size // (256 * 1024)  # Minimum 256KB per chunk
        num_chunks = min(num_connections, max_chunks, 32)  # Max 32 chunks
        
        if num_chunks == 0:
            num_chunks = 1

        chunk_size = total_size // num_chunks
        chunks = []

        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < num_chunks - 1 else total_size - 1
            chunks.append(ChunkInfo(
                index=i,
                start=start,
                end=end,
                downloaded=0,
            ))

        return chunks

    def merge_chunks(self, chunks: List[ChunkInfo], target_file: BinaryIO, temp_files: List[BinaryIO]):
        """Merge downloaded chunks into final file"""
        for chunk in sorted(chunks, key=lambda c: c.index):
            if chunk.index < len(temp_files):
                temp_files[chunk.index].seek(0)
                while True:
                    data = temp_files[chunk.index].read(8192)
                    if not data:
                        break
                    target_file.write(data)

    def get_chunk_progress(self, chunks: List[ChunkInfo]) -> dict:
        """Get progress information for all chunks"""
        total = sum(c.end - c.start + 1 for c in chunks)
        downloaded = sum(c.downloaded for c in chunks)
        
        return {
            "total_chunks": len(chunks),
            "completed_chunks": sum(1 for c in chunks if c.downloaded >= (c.end - c.start + 1)),
            "total_bytes": total,
            "downloaded_bytes": downloaded,
            "progress": (downloaded / total * 100) if total > 0 else 0,
        }

    def optimize_chunk_size(self, speed_history: List[float]) -> int:
        """Dynamically adjust chunk size based on download speed"""
        if not speed_history:
            return self.chunk_size

        avg_speed = sum(speed_history) / len(speed_history)
        
        # Adjust chunk size based on speed
        if avg_speed > 10 * 1024 * 1024:  # > 10MB/s
            return 4 * 1024 * 1024  # 4MB chunks
        elif avg_speed > 1 * 1024 * 1024:  # > 1MB/s
            return 2 * 1024 * 1024  # 2MB chunks
        else:
            return 1 * 1024 * 1024  # 1MB chunks
