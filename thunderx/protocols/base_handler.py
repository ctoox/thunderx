"""Base protocol handler"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncIterator


class BaseHandler(ABC):
    """Base class for protocol handlers"""

    @abstractmethod
    async def get_file_info(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get file information (size, supports range, etc.)"""
        pass

    @abstractmethod
    async def download(
        self,
        url: str,
        headers: Dict[str, str],
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> AsyncIterator[bytes]:
        """Download file content as async iterator"""
        pass

    @abstractmethod
    async def supports(self, url: str) -> bool:
        """Check if this handler supports the given URL"""
        pass
