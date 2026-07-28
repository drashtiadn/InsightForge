"""Domain-level exceptions raised by the service layer."""

import uuid


class ResearchSessionNotFoundError(Exception):
    """Raised when a research session does not exist."""

    def __init__(self, session_id: uuid.UUID) -> None:
        self.session_id = session_id
        super().__init__(f"Research session {session_id} not found")
