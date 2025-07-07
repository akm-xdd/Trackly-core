import asyncio
import json
from typing import Set, Dict, Any
from datetime import datetime
from app.models.events import IssueEvent, EventType


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class EventBroadcaster:
    def __init__(self):
        self._connections: Set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._connections.add(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue):
        self._connections.discard(queue)

    async def broadcast_issue_event(self, event: IssueEvent):
        if not self._connections:
            return

        event_data = {
            "type": event.event_type.value,
            "issue_id": event.issue_id,
            "user_id": event.user_id,
            "user_name": event.user_name,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }

        message = f"data: {json.dumps(event_data, cls=DateTimeEncoder)}\n\n"

        disconnected = set()
        for queue in self._connections:
            try:
                await queue.put(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.add(queue)

        for queue in disconnected:
            self._connections.discard(queue)

    def get_connection_count(self) -> int:
        return len(self._connections)


broadcaster = EventBroadcaster()
