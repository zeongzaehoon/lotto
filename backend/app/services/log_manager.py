"""실시간 로그 스트리밍 관리자"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class LogEntry:
    source: str  # "training" | "system"
    message: str
    task_id: str = ""


class LogManager:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._active_run_id: str | None = None

    def register(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._queues[run_id].append(queue)
        return queue

    def unregister(self, run_id: str, queue: asyncio.Queue):
        if run_id in self._queues:
            self._queues[run_id] = [q for q in self._queues[run_id] if q is not queue]
            if not self._queues[run_id]:
                del self._queues[run_id]

    async def emit(self, run_id: str, entry: LogEntry):
        for queue in self._queues.get(run_id, []):
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    @property
    def active_run_id(self) -> str | None:
        return self._active_run_id

    @active_run_id.setter
    def active_run_id(self, value: str | None):
        self._active_run_id = value


log_manager = LogManager()
