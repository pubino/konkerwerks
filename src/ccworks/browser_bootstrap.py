"""Lazy install of Playwright's chromium browser.

Homebrew (and any pip-based install) provides the Python `playwright` package
but not its ~180 MB chromium binary — that binary lives in a user cache
(~/Library/Caches/ms-playwright on macOS). Rather than making `brew install`
touch a user cache, we detect the missing binary on first browser use and
install it then, with a TTY prompt when interactive.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("ccworks.browser_bootstrap")

_chromium_verified = False


def _chromium_installed() -> bool:
    """Return True if Playwright's chromium binary is present on disk."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as p:
            exe = p.chromium.executable_path
    except Exception:
        return False

    return bool(exe) and Path(exe).exists()


def _install_chromium() -> None:
    """Invoke `python -m playwright install chromium` in a subprocess."""
    logger.info("Downloading Playwright chromium browser (~180 MB)...")
    print(
        "\n[ccworks] Playwright chromium browser is not installed.\n"
        "         Downloading it now (~180 MB). This is a one-time step.\n",
        file=sys.stderr,
    )
    subprocess.check_call(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    print("[ccworks] Chromium install complete.\n", file=sys.stderr)


def ensure_chromium() -> None:
    """Install Playwright's chromium binary if missing.

    Idempotent within a single process. Prompts on TTY; installs silently
    (non-interactive) when stdin is not a TTY (CI, piped invocations).
    Honors CCWORKS_SKIP_BROWSER_BOOTSTRAP=1 for callers that want to manage
    the browser binary themselves.
    """
    global _chromium_verified
    if _chromium_verified:
        return

    if os.environ.get("CCWORKS_SKIP_BROWSER_BOOTSTRAP") == "1":
        _chromium_verified = True
        return

    if _chromium_installed():
        _chromium_verified = True
        return

    if sys.stdin.isatty():
        try:
            sys.stderr.write(
                "\n[ccworks] Chromium browser not found. Download now? (~180 MB) [Y/n]: "
            )
            sys.stderr.flush()
            answer = sys.stdin.readline().strip().lower()
            if answer and answer[0] == "n":
                sys.stderr.write(
                    "[ccworks] Skipping browser install. Run "
                    "`python -m playwright install chromium` manually when ready.\n"
                )
                _chromium_verified = True
                return
        except (EOFError, KeyboardInterrupt):
            print("\n[ccworks] Prompt cancelled; will attempt install anyway.", file=sys.stderr)

    _install_chromium()
    _chromium_verified = True
