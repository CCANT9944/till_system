"""Till package for point-of-sale interface.
"""

# avoid importing UI modules at import time so tests can run without PyQt6

def run():
    """Launch the till application."""
    from .main import run as _run
    return _run()

__all__ = ["run"]
