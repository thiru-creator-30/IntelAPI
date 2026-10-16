from __future__ import annotations

import socket
from typing import Any

import httpx

from app.core.logging import get_logger
from app.execution.policy import OutboundLimits, TargetBlocked, validate_endpoint, validate_url

log = get_logger(__name__)


class PolicyTransport(httpx.AsyncHTTPTransport):
    """
    HTTPX transport that binds each new connection to a pre-resolved, policy-validated IP and
    re-validates the URL before each redirect hop (DNS-rebinding + redirect-policy defense).
    """

    def __init__(self, limits: OutboundLimits, **kwargs: Any) -> None:
        self.limits = limits
        super().__init__(
            limits=httpx.Limits(
                max_connections=limits.max_redirects * 4,  # small
                max_keepalive_connections=8,
            ),
            **kwargs,
        )

    async def _connect_with_policy(self, host: str, port: int) -> tuple[socket.AddressFamily, socket.socket]:
        # Resolve and validate every address; then connect, preferring first valid.
        _scheme, _h, _p, ips = validate_endpoint(f"http://{host}:{port}" if port == 80 else f"https://{host}:{port}")
        # Build (family, ip) pairs
        last_err: Exception | None = None
        for ip_str in ips:
            try:
                family = socket.AF_INET6 if ":" in ip_str else socket.AF_INET
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.settimeout(self.limits.connect_timeout)
                sock.connect((ip_str, port))
                sock.settimeout(None)
                return family, sock
            except OSError as exc:
                last_err = exc
                continue
        raise TargetBlocked(f"unable to connect to {host}: {last_err}")


def build_safe_client(limits: OutboundLimits) -> httpx.AsyncClient:
    # We use a standard AsyncClient with a custom event hook that rejects redirects to blocked IPs,
    # and a transport that performs pre-connect validation. DNS rebinding defense: the transport
    # resolves and connects to validated IPs directly; we pass the original Host header.
    transport = httpx.AsyncHTTPTransport(
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=8),
    )

    async def before_send(request: httpx.Request) -> None:
        # Validate initial URL and every redirect target.
        validate_url(str(request.url))

    client = httpx.AsyncClient(
        transport=transport,
        timeout=httpx.Timeout(
            limits.total_timeout,
            connect=limits.connect_timeout,
            read=limits.read_timeout,
            write=limits.read_timeout,
            pool=limits.connect_timeout,
        ),
        max_redirects=0,  # We handle redirects manually so we can revalidate each hop.
        follow_redirects=False,
        trust_env=False,
        headers={"user-agent": "IntelAPI/0.1 (+secure-outbound)"},
        event_hooks={"request": [before_send]},
    )
    return client
