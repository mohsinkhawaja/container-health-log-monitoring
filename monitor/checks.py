"""Pure checks and a small HTTP probe."""

import json
import re
from dataclasses import dataclass
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener


ERROR_LEVELS = frozenset({"ERROR", "CRITICAL", "FATAL"})
PLAIN_LEVEL = re.compile(r"^\s*(?:\[(ERROR|CRITICAL|FATAL)\]|(ERROR|CRITICAL|FATAL)\b)", re.I)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def check_state(state):
    status = state.get("Status", "unknown")
    health = (state.get("Health") or {}).get("Status", "missing")
    return Check("container_state", status == "running" and health == "healthy",
                 f"status={status}, health={health}")


def error_lines(raw):
    """Return one-based positions, without copying log content into reports."""
    matches = []
    for number, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
        try:
            record = json.loads(line)
        except ValueError:
            if PLAIN_LEVEL.match(line):
                matches.append(number)
        else:
            if isinstance(record, dict):
                level = record.get("level", record.get("severity", ""))
                if isinstance(level, str) and level.strip().upper() in ERROR_LEVELS:
                    matches.append(number)
    return matches


def check_logs(raw):
    matches = error_lines(raw)
    if matches:
        positions = ", ".join(map(str, matches[:10]))
        return Check("container_logs", False,
                     f"{len(matches)} error signature(s). First matching line(s): {positions}")
    return Check("container_logs", True, "No error signatures in sampled lines")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_http(url, expected_code=200, timeout=5):
    try:
        with build_opener(NoRedirects()).open(url, timeout=timeout) as response:
            if response.status != expected_code:
                return Check("http", False, f"Expected HTTP {expected_code}, got {response.status}")
            if expected_code != 200:
                return Check("http", True, f"HTTP {response.status}")
            if response.headers.get_content_type() != "application/json":
                return Check("http", False, "Expected JSON content type")
            try:
                body = response.read(16_385)
                if len(body) > 16_384:
                    return Check("http", False, "JSON health body exceeds 16 KiB")
                data = json.loads(body)
            except (UnicodeError, ValueError):
                return Check("http", False, "Invalid JSON health body")
            if not isinstance(data, dict) or data.get("status") != "ok":
                return Check("http", False, "Expected JSON status='ok'")
            return Check("http", True, "HTTP 200 and JSON status='ok'")
    except HTTPError as exc:
        with exc:
            return Check("http", exc.code == expected_code,
                         f"Expected HTTP {expected_code}, got {exc.code}")
    except (URLError, HTTPException, OSError, ValueError) as exc:
        return Check("http", False, f"HTTP probe failed ({type(exc).__name__})")
