"""Pure filename helpers used by result writers."""

import os


def source_stem(source_name: str) -> str:
    """Return a source name without its directory or extension."""
    return os.path.splitext(os.path.basename(source_name))[0]
