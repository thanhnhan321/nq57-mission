from __future__ import annotations

import hashlib
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from django.core.cache import cache

from utils.json import jsonify

P = ParamSpec("P")
R = TypeVar("R")

_MISSING = object()


def _stable_arg_hash(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    payload = jsonify({"args": args, "kwargs": kwargs}).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _make_cache_key(key: str, func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    return f"{key}:{func.__module__}.{func.__qualname__}:{_stable_arg_hash(args, kwargs)}"


def cached(
    key: str,
    ttl: int | None,
    *,
    vary_on_args: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Cache a function's return value using Django's default cache backend.

    Args:
        key: Base cache key.
        ttl: Time-to-live in seconds. Pass None to use the backend default timeout.
        vary_on_args: If True, include a stable hash of args/kwargs in the cache key.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cache_key = _make_cache_key(key, fn, args, kwargs) if vary_on_args else key

            cached_value = cache.get(cache_key, default=_MISSING)
            if cached_value is not _MISSING:
                return cached_value  # type: ignore[return-value]

            result = fn(*args, **kwargs)
            cache.set(cache_key, result, timeout=ttl)
            return result

        return wrapper

    return decorator

