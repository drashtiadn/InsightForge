"""Domain-level exceptions raised by the service layer."""

import uuid

from app.models.research_session import ResearchSessionStatus


class ResearchSessionNotFoundError(Exception):
    """Raised when a research session does not exist."""

    def __init__(self, session_id: uuid.UUID) -> None:
        self.session_id = session_id
        super().__init__(f"Research session {session_id} not found")


class InvalidResearchStateTransition(Exception):
    """Raised when a research session status change violates the workflow."""

    def __init__(
        self,
        current_status: ResearchSessionStatus,
        target_status: ResearchSessionStatus,
    ) -> None:
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition research session from {current_status.value} "
            f"to {target_status.value}"
        )


class ResearchAlreadyCompleted(Exception):
    """Raised when a completed research session is started again."""

    def __init__(self, session_id: uuid.UUID) -> None:
        self.session_id = session_id
        super().__init__(f"Research session {session_id} is already completed")


class ResearchAlreadyRunning(Exception):
    """Raised when an active research session is started again."""

    def __init__(
        self,
        session_id: uuid.UUID,
        status: ResearchSessionStatus,
    ) -> None:
        self.session_id = session_id
        self.status = status
        super().__init__(
            f"Research session {session_id} is already running in {status.value}"
        )
