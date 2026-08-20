from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime import manager

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
