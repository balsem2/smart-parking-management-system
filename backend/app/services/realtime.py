import asyncio
import json
import logging

from fastapi import WebSocket
from redis.exceptions import RedisError

from app.core.redis import redis_client

logger = logging.getLogger(__name__)
CHANNEL = "smartpark:dashboard-events"


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, event: dict) -> None:
        disconnected: list[WebSocket] = []
        for websocket in self.connections:
            try:
                await websocket.send_json(event)
            except Exception:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


async def publish_dashboard_event(event: dict) -> None:
    """Publish once through Redis; the subscriber broadcasts to WebSocket clients."""
    try:
        await redis_client.publish(CHANNEL, json.dumps(event, default=str))
    except RedisError:
        logger.warning("Redis is unavailable; broadcasting to local clients only")
        await manager.broadcast(event)


async def listen_for_dashboard_events() -> None:
    """Forward Redis events to every WebSocket client in this API process."""
    while True:
        pubsub = None
        try:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(CHANNEL)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await manager.broadcast(json.loads(message["data"]))
        except asyncio.CancelledError:
            raise
        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Realtime listener reconnecting: %s", exc)
            await asyncio.sleep(3)
        finally:
            if pubsub:
                await pubsub.aclose()


async def close_redis_connection() -> None:
    await redis_client.aclose()
