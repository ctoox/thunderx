"""File utility functions"""

import os
from pathlib import Path
from typing import Optional


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if not"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_size(path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """Format speed to human readable string"""
    return f"{format_size(int(bytes_per_sec))}/s"


def format_time(seconds: float) -> str:
    """Format seconds to human readable time string"""
    if seconds < 0:
        return "Unknown"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename


def get_unique_filename(path: Path) -> Path:
    """Get unique filename if file already exists"""
    if not path.exists():
        return path
    
    counter = 1
    while True:
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
