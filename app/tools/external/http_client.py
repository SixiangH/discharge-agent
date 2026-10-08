"""Small dependency-free HTTPS JSON client with an injectable test transport."""

import json
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

JsonFetcher = Callable[[str, dict[str, str]], dict[str, Any]]


def fetch_json(url: str, params: dict[str, str], timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Issue a GET request only; callers must provide a fixed trusted base URL."""
    query = urlencode(params)
    request = Request(f"{url}?{query}", headers={"Accept": "application/json", "User-Agent": "discharge-agent-teaching-prototype/0.1"})
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: fixed HTTPS endpoints only
        return json.loads(response.read().decode("utf-8"))
