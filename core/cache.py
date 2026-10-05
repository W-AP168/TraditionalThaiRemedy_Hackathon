"""Disk cache for analysis results.

Apriori and permutation tests should not rerun every time someone clicks.
Results are stored under .cache/ keyed by (dataset fingerprint, parameters),
so they are recomputed only when the data or the settings change.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def _key(name: str, fingerprint: str, params: dict) -> str:
    raw = json.dumps({"name": name, "fp": fingerprint, "params": params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def cached(name: str, fingerprint: str, params: dict, compute: Callable[[], Any], cache_dir: Path = CACHE_DIR) -> Any:
    cache_dir.mkdir(exist_ok=True)
    path = cache_dir / f"{name}-{_key(name, fingerprint, params)}.pkl"
    if path.exists():
        try:
            return pickle.loads(path.read_bytes())
        except Exception:  # corrupt or from an incompatible version: recompute
            path.unlink(missing_ok=True)
    value = compute()
    path.write_bytes(pickle.dumps(value))
    return value


def clear(cache_dir: Path = CACHE_DIR) -> int:
    if not cache_dir.exists():
        return 0
    files = list(cache_dir.glob("*.pkl"))
    for f in files:
        f.unlink()
    return len(files)
