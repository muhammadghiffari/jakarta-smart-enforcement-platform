# services/api/app/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_violation(self, violation_data: dict):
        message = json.dumps({"type": "NEW_VIOLATION", "data": violation_data})
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass # Connection dropped

manager = ConnectionManager()

@router.websocket("/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We just keep the connection alive, 
            # the client doesn't need to send us anything
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
