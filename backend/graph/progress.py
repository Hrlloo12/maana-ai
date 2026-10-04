from __future__ import annotations

import functools
import threading
import time
from typing import Callable

_lock = threading.Lock()
_progress: dict[str, dict] = {}


def get_progress(session_id: str) -> dict:
    with _lock:
        p = _progress.get(session_id, {"active": None, "completed": [], "error": None})
        return {"active": p["active"], "completed": list(p["completed"]), "error": p["error"]}


def _update(session_id: str, **changes) -> None:
    with _lock:
        p = _progress.setdefault(session_id, {"active": None, "completed": [], "error": None})
        p.update(changes)


def tracked(node_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(state):
            sid = state.get("session_id", "")
            _update(sid, active=node_name, error=None, started_at=time.time())
            try:
                result = fn(state)
            except Exception as exc:
                _update(sid, active=None, error=f"{node_name}: {exc}")
                raise
            with _lock:
                p = _progress[sid]
                p["completed"].append(node_name)
                p["active"] = None
            return result

        return wrapper

    return decorator
