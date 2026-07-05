"""
WebSocket Connection Manager

Tracks all active WebSocket clients and provides
a single broadcast() call to push data to all of them.
Disconnected clients are silently removed on send failure.
"""
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self._clients.remove(ws)

    async def broadcast(self, payload: list | dict):
        """Send JSON to every connected client; drop dead connections."""
        data = json.dumps(payload)
        dead = []
        for client in self._clients:
            try:
                await client.send_text(data)
            except Exception:
                dead.append(client)
        for c in dead:
            self._clients.remove(c)

    @property
    def client_count(self) -> int:
        return len(self._clients)


# Singleton — imported by the route module
manager = ConnectionManager()
