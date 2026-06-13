"""Progress logging for long-running PawPath supplier pipelines."""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Iterator, Optional

# Module-level default; CLI sets via configure()
_log: Optional["ProgressLogger"] = None


class ProgressLogger:
    """Timestamped, flushed stdout progress for CJ/Shopify pipelines."""

    def __init__(self, *, verbose: bool = True) -> None:
        self.verbose = verbose
        self._t0 = time.monotonic()

    def _elapsed(self) -> str:
        secs = time.monotonic() - self._t0
        if secs < 60:
            return f"{secs:.0f}s"
        mins = int(secs // 60)
        rem = int(secs % 60)
        return f"{mins}m{rem:02d}s"

    def _write(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)
            sys.stdout.flush()

    def info(self, msg: str) -> str:
        line = f"[{self._elapsed()}] {msg}"
        self._write(line)
        return line

    def phase(self, title: str) -> None:
        self._write("")
        self.info(f"━━ {title} ━━")

    def detail(self, msg: str) -> None:
        """Indented sub-step (search hits, import step, etc.)."""
        self._write(f"[{self._elapsed()}]   {msg}")

    def warn(self, msg: str) -> None:
        self._write(f"[{self._elapsed()}] ⚠ {msg}")

    def counter(
        self,
        current: int,
        total: int,
        msg: str,
        *,
        every: int = 1,
        force: bool = False,
    ) -> None:
        if not self.verbose:
            return
        if not force and total > 0 and every > 1:
            if current not in (1, total) and current % every != 0:
                return
        pct = f" ({current * 100 // total}%)" if total > 0 else ""
        self.detail(f"[{current}/{total}]{pct} {msg}")

    @contextmanager
    def span(self, label: str) -> Iterator[None]:
        self.info(f"▶ {label}")
        start = time.monotonic()
        try:
            yield
        except Exception as exc:
            self.warn(f"✗ {label} failed after {time.monotonic() - start:.1f}s: {exc}")
            raise
        else:
            self.info(f"✓ {label} ({time.monotonic() - start:.1f}s)")


def configure(*, verbose: bool = True) -> ProgressLogger:
    global _log
    _log = ProgressLogger(verbose=verbose)
    return _log


def get_logger() -> ProgressLogger:
    global _log
    if _log is None:
        _log = ProgressLogger(verbose=True)
    return _log
