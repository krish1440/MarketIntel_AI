import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.api.ws.connection_manager import ws_manager

logger = logging.getLogger("WSEndpoints")
router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/live")
async def websocket_live_ticks(websocket: WebSocket):
    """
    Real-time streaming WebSocket endpoint for live stock ticks and price updates.
    Sends heartbeats and accepts ping/subscribe commands from frontend.
    """
    await ws_manager.connect(websocket, channel="live")
    try:
        # Send initial connection confirmation
        await websocket.send_json({"type": "CONNECTION_ACK", "status": "CONNECTED", "channel": "live"})
        
        while True:
            # Keep connection alive, listen for incoming client commands (e.g., ping or symbol subscriptions)
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("action") == "subscribe":
                symbols = data.get("symbols", [])
                await websocket.send_json({
                    "type": "SUBSCRIPTION_CONFIRMED",
                    "symbols": symbols
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="live")
    except Exception as e:
        logger.debug(f"Live WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel="live")


@router.websocket("/trades")
async def websocket_trade_alerts(websocket: WebSocket):
    """
    Real-time streaming WebSocket endpoint for paper trade execution alerts,
    target 1 hits, trailing stop adjustments, and circuit breaker events.
    """
    await ws_manager.connect(websocket, channel="trades")
    try:
        await websocket.send_json({"type": "CONNECTION_ACK", "status": "CONNECTED", "channel": "trades"})
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="trades")
    except Exception as e:
        logger.debug(f"Trade WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel="trades")
