"""Peer management for P2P acceleration"""

import asyncio
import hashlib
import random
import socket
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from ..utils.logger import setup_logger


@dataclass
class Peer:
    """Represents a peer in the P2P network"""
    peer_id: str
    address: str
    port: int
    pieces: Set[int]
    speed: float = 0.0
    last_seen: float = 0.0

    @property
    def endpoint(self) -> Tuple[str, int]:
        return (self.address, self.port)


class PeerManager:
    """Manages P2P peers and piece distribution"""

    def __init__(self, port: int = 6881):
        self.logger = setup_logger("p2p")
        self.port = port
        self.peer_id = self._generate_peer_id()
        self._peers: Dict[str, Peer] = {}
        self._piece_availability: Dict[int, Set[str]] = {}  # piece -> set of peer_ids
        self._server: Optional[asyncio.Server] = None
        self._running = False

    def _generate_peer_id(self) -> str:
        """Generate unique peer ID"""
        prefix = "-TX1000-"
        suffix = "".join([str(random.randint(0, 9)) for _ in range(12)])
        return prefix + suffix

    async def start(self):
        """Start P2P server"""
        if self._running:
            return

        try:
            self._server = await asyncio.start_server(
                self._handle_peer_connection,
                "0.0.0.0",
                self.port,
            )
            self._running = True
            self.logger.info(f"P2P server started on port {self.port}")
        except Exception as e:
            self.logger.warning(f"Could not start P2P server: {e}")

    async def stop(self):
        """Stop P2P server"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._running = False
        self.logger.info("P2P server stopped")

    async def _handle_peer_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle incoming peer connection"""
        peer_addr = writer.get_extra_info("peername")
        self.logger.debug(f"Peer connected: {peer_addr}")

        try:
            # Simple handshake protocol
            # In real implementation, this would follow BitTorrent-like protocol
            data = await reader.read(68)  # Standard handshake size
            if len(data) < 68:
                writer.close()
                return

            # Process handshake
            peer_id = data[48:68].decode("ascii", errors="ignore")
            
            # Send our handshake
            handshake = self._create_handshake()
            writer.write(handshake)
            await writer.drain()

            # Add peer
            peer = Peer(
                peer_id=peer_id,
                address=peer_addr[0],
                port=peer_addr[1],
                pieces=set(),
            )
            self._peers[peer_id] = peer

            # Handle peer messages
            await self._handle_peer_messages(reader, writer, peer)

        except Exception as e:
            self.logger.debug(f"Peer connection error: {e}")
        finally:
            writer.close()

    def _create_handshake(self) -> bytes:
        """Create handshake message"""
        # Protocol name
        pstr = b"BitTorrent protocol"
        pstr_len = bytes([len(pstr)])
        
        # Reserved bytes
        reserved = b"\x00" * 8
        
        # Info hash (placeholder - would be actual file hash)
        info_hash = b"\x00" * 20
        
        # Peer ID
        peer_id = self.peer_id.encode("ascii")
        
        return pstr_len + pstr + reserved + info_hash + peer_id

    async def _handle_peer_messages(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        peer: Peer,
    ):
        """Handle messages from peer"""
        try:
            while True:
                # Read message length
                length_bytes = await reader.read(4)
                if not length_bytes:
                    break
                
                length = int.from_bytes(length_bytes, "big")
                if length == 0:
                    continue  # Keep-alive
                
                # Read message
                message = await reader.read(length)
                if not message:
                    break
                
                # Parse message type
                msg_type = message[0]
                payload = message[1:]
                
                # Handle different message types
                if msg_type == 5:  # Have
                    piece_index = int.from_bytes(payload[:4], "big")
                    peer.pieces.add(piece_index)
                    self._update_piece_availability(piece_index, peer.peer_id)
                
                elif msg_type == 7:  # Piece
                    # Handle piece data
                    pass

        except Exception as e:
            self.logger.debug(f"Message handling error: {e}")
        finally:
            if peer.peer_id in self._peers:
                del self._peers[peer.peer_id]

    def _update_piece_availability(self, piece_index: int, peer_id: str):
        """Update piece availability tracking"""
        if piece_index not in self._piece_availability:
            self._piece_availability[piece_index] = set()
        self._piece_availability[piece_index].add(peer_id)

    def get_peers_for_piece(self, piece_index: int) -> List[Peer]:
        """Get peers that have a specific piece"""
        peer_ids = self._piece_availability.get(piece_index, set())
        return [self._peers[pid] for pid in peer_ids if pid in self._peers]

    def get_rarest_pieces(self) -> List[int]:
        """Get pieces sorted by rarity (rarest first)"""
        if not self._piece_availability:
            return []
        
        return sorted(
            self._piece_availability.keys(),
            key=lambda p: len(self._piece_availability.get(p, set())),
        )

    async def connect_to_peer(self, address: str, port: int, info_hash: bytes):
        """Connect to a specific peer"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(address, port),
                timeout=10,
            )
            
            # Send handshake
            handshake = self._create_handshake()
            writer.write(handshake)
            await writer.drain()
            
            # Wait for response
            response = await reader.read(68)
            if len(response) >= 68:
                peer_id = response[48:68].decode("ascii", errors="ignore")
                peer = Peer(
                    peer_id=peer_id,
                    address=address,
                    port=port,
                    pieces=set(),
                )
                self._peers[peer_id] = peer
                self.logger.info(f"Connected to peer: {address}:{port}")
                
                # Start message handler
                asyncio.create_task(self._handle_peer_messages(reader, writer, peer))
                
        except Exception as e:
            self.logger.debug(f"Could not connect to peer {address}:{port}: {e}")

    def get_peer_count(self) -> int:
        """Get number of connected peers"""
        return len(self._peers)

    def get_stats(self) -> Dict:
        """Get P2P statistics"""
        return {
            "peer_count": len(self._peers),
            "piece_count": len(self._piece_availability),
            "peer_id": self.peer_id,
        }
