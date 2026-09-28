class FollowupError(Exception):
    """Base error carrying a human-readable, locatable message."""


class InputError(FollowupError):
    """Invalid CSV data; message identifies the offending row."""


class ConfigError(FollowupError):
    """Invalid JSON config; message identifies the offending item."""
