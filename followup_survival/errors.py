"""Error types carrying a locatable reference (CSV row or config item)."""


class FollowupError(Exception):
    """Base error. ``location`` points at a CSV row or config item."""

    def __init__(self, message: str, location: str | None = None):
        if location:
            full = f"{location}: {message}"
        else:
            full = message
        super().__init__(full)
        self.location = location
        self.message = message
