# ThunderX Download Manager

High-speed download manager with multi-threaded downloading, P2P acceleration, and browser integration.

## Features

- **Multi-threaded Downloading**: Split files into chunks and download simultaneously
- **Resume Support**: Continue interrupted downloads from where they left off
- **Browser Integration**: Capture downloads from browser via extension
- **P2P Acceleration**: Peer-to-peer download acceleration
- **Multiple Protocols**: HTTP, HTTPS, FTP support
- **Modern GUI**: PyQt6-based graphical interface

## Installation

```bash
pip install -e .
```

## Usage

### GUI Application

```bash
# Launch GUI
python run_gui.py

# Or use the command
thunderx-gui
```

### Command Line

```bash
# Download a file
thunderx download https://example.com/file.zip

# Download with multiple connections
thunderx download -c 16 https://example.com/file.zip

# Download to specific directory
thunderx download -o /path/to/save https://example.com/file.zip

# List all tasks
thunderx list

# Pause a task
thunderx pause <task_id>

# Resume a task
thunderx resume <task_id>

# Show configuration
thunderx config

# Set configuration
thunderx set max_connections_per_task 16
```

### As Python Library

```python
import asyncio
from thunderx import DownloadEngine

async def main():
    engine = DownloadEngine()
    await engine.initialize()
    
    task = await engine.add_task(
        url="https://example.com/file.zip",
        save_path="./downloads",
    )
    
    await engine.start_task(task.task_id)
    
    # Wait for completion
    while task.status != TaskStatus.COMPLETED:
        print(f"Progress: {task.progress:.1f}%")
        await asyncio.sleep(1)
    
    await engine.shutdown()

asyncio.run(main())
```

## Configuration

Configuration file is stored at `~/.thunderx/config.yaml`

```yaml
max_concurrent_tasks: 3
max_connections_per_task: 8
chunk_size: 1048576
default_save_path: ~/Downloads/ThunderX
enable_p2p: true
p2p_port: 6881
enable_browser_extension: true
browser_port: 9527
```

## Browser Extension

1. Start ThunderX: `thunderx download --enable-browser`
2. Install browser extension from `thunderx/browser/extension/`
3. Downloads will be automatically captured

## License

MIT License
