"""FTP protocol handler"""

import asyncio
import aioftp
from typing import Optional, Dict, Any, AsyncIterator
from .base_handler import BaseHandler


class FTPHandler(BaseHandler):
    """Handler for FTP downloads"""

    def __init__(self):
        self._client = None

    async def supports(self, url: str) -> bool:
        """Check if URL is FTP"""
        return url.startswith("ftp://")

    async def get_file_info(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get FTP file information"""
        parsed = self._parse_url(url)
        
        try:
            async with aioftp.ClientSession(
                parsed["host"],
                parsed["port"] or 21,
                parsed["username"],
                parsed["password"],
            ) as client:
                stat = await client.stat(parsed["path"])
                
                return {
                    "size": stat.get("size"),
                    "supports_range": True,  # FTP supports REST
                    "content_type": "",
                    "filename": parsed["path"].name,
                }
        except Exception as e:
            raise ConnectionError(f"FTP connection failed: {e}")

    async def download(
        self,
        url: str,
        headers: Dict[str, str],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Download FTP content"""
        parsed = self._parse_url(url)
        
        async with aioftp.ClientSession(
            parsed["host"],
            parsed["port"] or 21,
            parsed["username"],
            parsed["password"],
        ) as client:
            # Set restart point for resume
            if start:
                await client.command(f"REST {start}", "350")
            
            async with client.download_stream(parsed["path"]) as stream:
                async for chunk in stream.iter_by_block(8192):
                    yield chunk

    def _parse_url(self, url: str) -> Dict[str, Any]:
        """Parse FTP URL"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        username = parsed.username or "anonymous"
        password = parsed.password or ""
        
        return {
            "host": parsed.hostname,
            "port": parsed.port,
            "path": parsed.path,
            "username": username,
            "password": password,
        }
