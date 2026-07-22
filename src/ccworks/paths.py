"""Resolve per-user state paths for ccworks.

State (session cookies, screenshots, lock files) lives outside the CWD so that
`ccworks` can be invoked from any directory — including a Homebrew install —
without dropping files into the user's current directory.

Precedence:
    1. $CCWORKS_STATE_DIR (explicit override)
    2. macOS: ~/Library/Application Support/ccworks
    3. Linux/other: $XDG_STATE_HOME/ccworks (default ~/.local/state/ccworks)
"""

import os
import sys
from pathlib import Path


def state_dir() -> Path:
    override = os.environ.get("CCWORKS_STATE_DIR")
    if override:
        d = Path(override).expanduser()
    elif sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "ccworks"
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
        d = base / "ccworks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def session_file() -> Path:
    return state_dir() / "concur_session.json"


def screenshot_dir() -> Path:
    d = state_dir() / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d
