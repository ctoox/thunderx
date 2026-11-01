"""Command Line Interface for ThunderX"""

import asyncio
import sys
from typing import Optional, List
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.panel import Panel
from rich.live import Live

from ..engine.download_engine import DownloadEngine
from ..engine.task import DownloadTask, TaskStatus
from ..utils.config import Config
from ..utils.file_utils import format_size, format_speed, format_time
from ..utils.logger import setup_logger


console = Console()
logger = setup_logger("cli")


class CLI:
    """ThunderX Command Line Interface"""

    def __init__(self):
        self.config = Config()
        self.engine: Optional[DownloadEngine] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop"""
        if not self._loop or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    async def _init_engine(self):
        """Initialize download engine"""
        self.engine = DownloadEngine(self.config)
        await self.engine.initialize()
        
        # Setup event handlers
        self.engine.on("progress", self._on_progress)
        self.engine.on("complete", self._on_complete)
        self.engine.on("error", self._on_error)

    def _on_progress(self, task: DownloadTask):
        """Handle progress update"""
        # Progress is handled by Rich progress bar
        pass

    def _on_complete(self, task: DownloadTask):
        """Handle download complete"""
        console.print(f"\n[green]Download completed: {task.filename}[/green]")

    def _on_error(self, task: DownloadTask, error: Exception):
        """Handle download error"""
        console.print(f"\n[red]Download failed: {task.filename} - {error}[/red]")

    def download(self, urls: List[str], output: str = ".", connections: int = 8):
        """Download files from URLs"""
        loop = self._get_loop()
        loop.run_until_complete(self._async_download(urls, output, connections))

    async def _async_download(self, urls: List[str], output: str, connections: int):
        """Async download implementation"""
        await self._init_engine()
        
        try:
            tasks = []
            for url in urls:
                task = await self.engine.add_task(
                    url=url,
                    save_path=output,
                    num_connections=connections,
                )
                tasks.append(task)
            
            # Display tasks
            self._display_tasks(tasks)
            
            # Start downloads with progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TextColumn("[cyan]{task.fields[speed]}"),
                TextColumn("[yellow]{task.fields[eta]}"),
            ) as progress:
                
                # Create progress bars for each task
                task_progress = {}
                for task in tasks:
                    task_progress[task.task_id] = progress.add_task(
                        f"[cyan]{task.filename}",
                        total=task.total_size or 100,
                        speed="0 B/s",
                        eta="Unknown",
                    )
                
                # Start all downloads
                for task in tasks:
                    await self.engine.start_task(task.task_id)
                
                # Update progress
                while any(t.status == TaskStatus.DOWNLOADING for t in tasks):
                    for task in tasks:
                        if task.task_id in task_progress:
                            speed = self.engine.get_speed(task.task_id)
                            speed_str = format_speed(speed)
                            
                            if task.total_size > 0:
                                progress.update(
                                    task_progress[task.task_id],
                                    completed=task.downloaded_size,
                                    speed=speed_str,
                                    eta=format_time(
                                        (task.total_size - task.downloaded_size) / speed
                                        if speed > 0 else -1
                                    ),
                                )
                            else:
                                progress.update(
                                    task_progress[task.task_id],
                                    completed=task.downloaded_size,
                                    speed=speed_str,
                                )
                    
                    await asyncio.sleep(0.1)
            
            # Final status
            console.print("\n[bold green]All downloads completed![/bold green]")
            
        finally:
            await self.engine.shutdown()

    def list_tasks(self):
        """List all download tasks"""
        loop = self._get_loop()
        loop.run_until_complete(self._async_list_tasks())

    async def _async_list_tasks(self):
        """Async list tasks implementation"""
        await self._init_engine()
        
        try:
            await self.engine.load_saved_tasks()
            tasks = self.engine.get_all_tasks()
            
            if not tasks:
                console.print("[yellow]No download tasks found[/yellow]")
                return
            
            self._display_tasks(tasks)
            
        finally:
            await self.engine.shutdown()

    def _display_tasks(self, tasks: List[DownloadTask]):
        """Display tasks in a table"""
        table = Table(title="ThunderX Downloads")
        table.add_column("ID", style="cyan")
        table.add_column("Filename", style="green")
        table.add_column("Size", justify="right")
        table.add_column("Progress", justify="right")
        table.add_column("Status", style="bold")
        
        for task in tasks:
            status_style = {
                TaskStatus.PENDING: "yellow",
                TaskStatus.DOWNLOADING: "cyan",
                TaskStatus.PAUSED: "yellow",
                TaskStatus.COMPLETED: "green",
                TaskStatus.FAILED: "red",
            }.get(task.status, "white")
            
            table.add_row(
                task.task_id,
                task.filename[:40],
                format_size(task.total_size) if task.total_size > 0 else "Unknown",
                f"{task.progress:.1f}%",
                f"[{status_style}]{task.status.value}[/{status_style}]",
            )
        
        console.print(table)

    def pause(self, task_id: str):
        """Pause a download task"""
        loop = self._get_loop()
        loop.run_until_complete(self._async_pause(task_id))

    async def _async_pause(self, task_id: str):
        """Async pause implementation"""
        await self._init_engine()
        try:
            await self.engine.load_saved_tasks()
            await self.engine.pause_task(task_id)
            console.print(f"[yellow]Task paused: {task_id}[/yellow]")
        finally:
            await self.engine.shutdown()

    def resume(self, task_id: str):
        """Resume a download task"""
        loop = self._get_loop()
        loop.run_until_complete(self._async_resume(task_id))

    async def _async_resume(self, task_id: str):
        """Async resume implementation"""
        await self._init_engine()
        try:
            await self.engine.load_saved_tasks()
            await self.engine.resume_task(task_id)
            console.print(f"[green]Task resumed: {task_id}[/green]")
        finally:
            await self.engine.shutdown()

    def remove(self, task_id: str, delete_file: bool = False):
        """Remove a download task"""
        loop = self._get_loop()
        loop.run_until_complete(self._async_remove(task_id, delete_file))

    async def _async_remove(self, task_id: str, delete_file: bool):
        """Async remove implementation"""
        await self._init_engine()
        try:
            await self.engine.load_saved_tasks()
            await self.engine.remove_task(task_id, delete_file)
            console.print(f"[red]Task removed: {task_id}[/red]")
        finally:
            await self.engine.shutdown()

    def show_config(self):
        """Show current configuration"""
        config_dict = self.config.to_dict()
        
        table = Table(title="ThunderX Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in config_dict.items():
            table.add_row(key, str(value))
        
        console.print(table)

    def set_config(self, key: str, value: str):
        """Set configuration value"""
        # Try to convert value to appropriate type
        try:
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
        except Exception:
            pass
        
        self.config.set(key, value)
        self.config.save()
        console.print(f"[green]Configuration updated: {key} = {value}[/green]")


@click.group()
def main():
    """ThunderX - High-speed Download Manager"""
    pass


@main.command()
@click.argument("urls", nargs=-1, required=True)
@click.option("-o", "--output", default=".", help="Output directory")
@click.option("-c", "--connections", default=8, help="Number of connections")
def download(urls: tuple, output: str, connections: int):
    """Download files from URLs"""
    cli = CLI()
    cli.download(list(urls), output, connections)


@main.command()
def list():
    """List all download tasks"""
    cli = CLI()
    cli.list_tasks()


@main.command()
@click.argument("task_id")
def pause(task_id: str):
    """Pause a download task"""
    cli = CLI()
    cli.pause(task_id)


@main.command()
@click.argument("task_id")
def resume(task_id: str):
    """Resume a download task"""
    cli = CLI()
    cli.resume(task_id)


@main.command()
@click.argument("task_id")
@click.option("-d", "--delete-file", is_flag=True, help="Delete downloaded file")
def remove(task_id: str, delete_file: bool):
    """Remove a download task"""
    cli = CLI()
    cli.remove(task_id, delete_file)


@main.command()
def config():
    """Show configuration"""
    cli = CLI()
    cli.show_config()


@main.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set configuration value"""
    cli = CLI()
    cli.set_config(key, value)


if __name__ == "__main__":
    main()
