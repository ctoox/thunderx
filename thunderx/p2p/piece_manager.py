"""Piece management for P2P downloads"""

import hashlib
from typing import Dict, List, Set, Optional
from dataclasses import dataclass


@dataclass
class Piece:
    """Represents a piece of a file"""
    index: int
    hash: str
    size: int
    downloaded: bool = False
    data: Optional[bytes] = None


class PieceManager:
    """Manages file pieces for P2P downloading"""

    def __init__(self, piece_size: int = 256 * 1024):  # 256KB default
        self.piece_size = piece_size
        self._pieces: Dict[int, Piece] = {}
        self._completed: Set[int] = set()
        self._pending: Set[int] = set()

    def setup_pieces(self, total_size: int, piece_hashes: Optional[List[str]] = None):
        """Setup pieces for a file"""
        num_pieces = (total_size + self.piece_size - 1) // self.piece_size
        
        for i in range(num_pieces):
            size = min(self.piece_size, total_size - i * self.piece_size)
            hash_value = piece_hashes[i] if piece_hashes and i < len(piece_hashes) else ""
            
            self._pieces[i] = Piece(
                index=i,
                hash=hash_value,
                size=size,
            )
            self._pending.add(i)

    def mark_completed(self, index: int, data: bytes) -> bool:
        """Mark a piece as completed after verification"""
        if index not in self._pieces:
            return False

        piece = self._pieces[index]
        
        # Verify hash if available
        if piece.hash:
            data_hash = hashlib.sha1(data).hexdigest()
            if data_hash != piece.hash:
                return False

        piece.downloaded = True
        piece.data = data
        
        self._completed.add(index)
        self._pending.discard(index)
        
        return True

    def get_pending_pieces(self) -> List[int]:
        """Get list of pending piece indices"""
        return list(self._pending)

    def get_rarest_first(self, peer_pieces: Dict[str, Set[int]]) -> List[int]:
        """Get pieces sorted by rarity (rarest first)"""
        # Count availability
        availability: Dict[int, int] = {}
        for pieces in peer_pieces.values():
            for p in pieces:
                if p in self._pending:
                    availability[p] = availability.get(p, 0) + 1
        
        # Sort by availability (rarest first)
        return sorted(self._pending, key=lambda p: availability.get(p, 0))

    @property
    def progress(self) -> float:
        """Get download progress percentage"""
        if not self._pieces:
            return 0.0
        return len(self._completed) / len(self._pieces) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all pieces are downloaded"""
        return len(self._pending) == 0

    def get_piece_data(self, index: int) -> Optional[bytes]:
        """Get data for a completed piece"""
        piece = self._pieces.get(index)
        if piece and piece.downloaded:
            return piece.data
        return None

    def get_completed_pieces(self) -> Set[int]:
        """Get set of completed piece indices"""
        return self._completed.copy()

    def merge_pieces(self) -> bytes:
        """Merge all pieces into complete file data"""
        data = bytearray()
        for i in range(len(self._pieces)):
            piece_data = self.get_piece_data(i)
            if piece_data:
                data.extend(piece_data)
        return bytes(data)

    def reset(self):
        """Reset piece manager state"""
        self._completed.clear()
        self._pending = set(self._pieces.keys())
        for piece in self._pieces.values():
            piece.downloaded = False
            piece.data = None
