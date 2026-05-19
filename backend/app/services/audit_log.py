from __future__ import annotations

from app.core.security import AuditEvent


class InMemoryAuditLog:
    """Production'da PostgreSQL/ClickHouse gibi kalıcı audit store ile değiştirilir."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_recent(self, limit: int = 50) -> list[AuditEvent]:
        return list(reversed(self._events[-limit:]))
