"""Planning-specific domain exceptions.

Raised by planners and translated from LLM transport failures.
Services remain provider-agnostic by catching these, not SDK errors.
"""


class PlanningFailed(Exception):
    """Raised when planning cannot be completed for any reason."""

    def __init__(self, message: str = "Research planning failed") -> None:
        super().__init__(message)


class InvalidPlannerResponse(Exception):
    """Raised when an LLM response cannot be mapped to a ResearchPlan."""

    def __init__(self, message: str = "Planner returned an invalid response") -> None:
        super().__init__(message)


class LLMUnavailable(Exception):
    """Raised when the LLM provider is not configured or unreachable."""

    def __init__(self, message: str = "LLM provider is unavailable") -> None:
        super().__init__(message)
