"""Rate Limiter Utility.

Provides lightweight IP-based sliding window rate limiting for sensitive endpoints
such as registration and login to defend against brute-force and credential stuffing.
Bypasses rate limiting automatically in TESTING mode.
"""

import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, current_app

# Maps client IP -> list of timestamps
_request_history = defaultdict(list)


def rate_limit(max_requests: int = 15, window_seconds: int = 60):
    """Decorator to enforce maximum requests per IP address within a rolling time window."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Bypass rate limiting in testing mode unless explicitly configured otherwise
            if current_app and current_app.config.get("TESTING"):
                # Allow test_rate_limiting test to still test rate limiting if requested
                if not getattr(current_app, "enable_test_rate_limit", False):
                    return fn(*args, **kwargs)

            client_ip = (
                request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.remote_addr
                or "unknown"
            )

            now = time.time()
            cutoff = now - window_seconds

            # Filter out timestamps older than the sliding window
            timestamps = [ts for ts in _request_history[client_ip] if ts > cutoff]
            _request_history[client_ip] = timestamps

            if len(timestamps) >= max_requests:
                return jsonify({
                    "status": "error",
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds. Please try again shortly.",
                    "status_code": 429
                }), 429

            # Record current request timestamp
            _request_history[client_ip].append(now)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def clear_rate_limits():
    """Utility function to clear IP history during test executions."""
    _request_history.clear()
