"""HTTP/HTTPS protocol handler"""

import aiohttp
from typing import Optional, Dict, Any, AsyncIterator
from .base_handler import BaseHandler


class HTTPHandler(BaseHandler):
    """Handler for HTTP/HTTPS downloads"""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def supports(self, url: str) -> bool:
        """Check if URL is HTTP/HTTPS"""
        return url.startswith(("http://", "https://"))

    async def get_file_info(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get HTTP file information"""
        session = await self._get_session()
        
        async with session.head(url, headers=headers, allow_redirects=True) as response:
            content_length = response.headers.get("Content-Length")
            accept_ranges = response.headers.get("Accept-Ranges", "")
            
            return {
                "size": int(content_length) if content_length else None,
                "supports_range": "bytes" in accept_ranges.lower(),
                "content_type": response.headers.get("Content-Type", ""),
                "filename": self._extract_filename(response),
            }

    async def download(
        self,
        url: str,
        headers: Dict[str, str],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Download HTTP content"""
        session = await self._get_session()
        
        # Add range header if specified
        request_headers = headers.copy()
        if start is not None:
            range_header = f"bytes={start}-"
            if end is not None:
                range_header += str(end)
            request_headers["Range"] = range_header

        async with session.get(url, headers=request_headers) as response:
            async for chunk in response.content.iter_chunked(8192):
                yield chunk

    def _extract_filename(self, response) -> Optional[str]:
        """Extract filename from response headers"""
        content_disposition = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disposition:
            # Parse filename from Content-Disposition
            parts = content_disposition.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip('" ')
                return filename
        return None
