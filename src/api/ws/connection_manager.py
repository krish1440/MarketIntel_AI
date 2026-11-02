import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("WSConnectionManager")

class ConnectionManager:
    """
    Manages active WebSocket client connections for real-time market data streaming
    and simulated paper trading alerts.
    """
    def __init__(self):
        # channel_name -> set of WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "live": set(),
            "trades": set()
        }

    async def connect(self, websocket: WebSocket, channel: str = "live"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket client connected to '{channel}'. Total clients: {len(self.active_connections[channel])}")

    def disconnect(self, websocket: WebSocket, channel: str = "live"):
        if channel in self.active_connections and websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
            logger.info(f"WebSocket client disconnected from '{channel}'. Remaining: {len(self.active_connections[channel])}")

    async def broadcast(self, channel: str, message: Dict[str, Any]):
        """Broadcasts JSON payload to all connected clients on a specific channel."""
        if channel not in self.active_connections:
            return

        dead_sockets = set()
        for connection in list(self.active_connections[channel]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to client on '{channel}': {e}")
                dead_sockets.add(connection)

        for dead in dead_sockets:
            self.disconnect(dead, channel)

    async def broadcast_tick(self, tick_data: Dict[str, Any]):
        """Helper to broadcast market tick updates."""
        await self.broadcast("live", {"type": "TICK", "data": tick_data})

    async def broadcast_trade(self, trade_data: Dict[str, Any]):
        """Helper to broadcast trade executions and target/stop hits."""
        await self.broadcast("trades", {"type": "TRADE_EVENT", "data": trade_data})

# Global singleton
ws_manager = ConnectionManager()
