"""Commander session store — persistent session storage"""
from typing import Dict, Optional
from commander.models import CommanderSession


class CommanderStore:
    """In-memory session store (singleton)"""

    def __init__(self):
        self._sessions: Dict[str, CommanderSession] = {}

    def get(self, session_id: str) -> Optional[CommanderSession]:
        return self._sessions.get(session_id)

    def put(self, session: CommanderSession):
        self._sessions[session.id] = session

    def delete(self, session_id: str):
        self._sessions.pop(session_id, None)

    def list_ids(self) -> list[str]:
        return list(self._sessions.keys())


commander_store = CommanderStore()
