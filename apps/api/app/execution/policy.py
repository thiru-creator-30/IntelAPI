from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


class TargetBlocked(AppError):
    def __init__(self, reason: str) -> None:
        super().__init__(ErrorCode.TARGET_BLOCKED, f"Target rejected by policy: {reason}", details={"reason": reason})


class TargetTimeout(AppError):
    def __init__(self, kind: str = "timeout") -> None:
        super().__init__(ErrorCode.TARGET_TIMEOUT, f"Target {kind}.", details={"kind": kind})


_ALLOWED_SCHEMES = {"http", "https"}


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    settings = get_settings()
    if ip.is_loopback and settings.outbound_block_loopback:
        return "loopback"
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_multicast:
        return "multicast"
    if ip.is_link_local:
        return "link-local"
    if ip.is_reserved:
        return "reserved"
    if isinstance(ip, ipaddress.IPv4Address):
        if settings.outbound_block_private and (ip.is_private or ip.is_private):
            # is_private covers RFC1918 + CGNAT? In 3.11+, is_private covers CGNAT 100.64/10 as well.
            return "private"
        # Cloud metadata (IPv4)
        if ip in ipaddress.ip_network("169.254.169.254/32"):
            return "cloud-metadata"
    else:  # IPv6
        if settings.outbound_block_private and (ip.is_private or ip.is_unique_local):
            return "private"
        if ip.ipv4_mapped is not None:
            mapped = ip.ipv4_mapped
            reason = _is_disallowed_ip(mapped)
            if reason:
                return f"ipv4-mapped-{reason}"
        # Cloud metadata IPv6
        if ip == ipaddress.ip_address("fd00:ec2::254"):
            return "cloud-metadata"
    return None


def resolve_host(host: str, port: int) -> list[tuple[socket.AddressFamily, str]]:
    """Resolve host to addresses with AI_ADDRCONFIG; returns list of (family, ip_str)."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise TargetBlocked(f"DNS resolution failed: {exc}") from exc
    result: list[tuple[socket.AddressFamily, str]] = []
    seen: set[str] = set()
    for fam, _type, _proto, _canon, sockaddr in infos:
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        result.append((fam, ip_str))
    return result


def validate_url(url: str) -> tuple[str, str, int]:
    """Parse URL and enforce scheme/host; return (scheme, host, port). Does NOT resolve DNS."""
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise TargetBlocked("invalid URL") from exc
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise TargetBlocked(f"scheme '{scheme}' not allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise TargetBlocked("missing host")
    # Disallow obvious IP-literal blocked ranges here (fast path). DNS path below covers hostname resolves.
    try:
        ip = ipaddress.ip_address(host)
        reason = _is_disallowed_ip(ip)
        if reason:
            raise TargetBlocked(f"IP {ip} is {reason}")
    except ValueError:
        pass  # hostname, not IP literal
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80
    return scheme, host, port


def validate_endpoint(url: str) -> tuple[str, str, int, list[str]]:
    """
    Policy-validate a URL: scheme/host parsing + DNS resolution, every resolved address must pass
    disallowed-IP checks. Returns (scheme, host, port, resolved_ips).

    DNS-rebinding defense is enforced at the transport layer by connecting only to these pre-resolved
    IPs while sending the original Host header.
    """
    scheme, host, port = validate_url(url)
    infos = resolve_host(host, port)
    ips: list[str] = []
    for _fam, ip_str in infos:
        ip = ipaddress.ip_address(ip_str)
        reason = _is_disallowed_ip(ip)
        if reason:
            raise TargetBlocked(f"host {host} resolves to {ip_str} which is {reason}")
        ips.append(ip_str)
    if not ips:
        raise TargetBlocked("no addresses resolved")
    return scheme, host, port, ips


@dataclass
class OutboundLimits:
    connect_timeout: float
    read_timeout: float
    total_timeout: float
    max_response_bytes: int
    max_redirects: int
    spec_max_bytes: int


def get_limits() -> OutboundLimits:
    s = get_settings()
    return OutboundLimits(
        connect_timeout=s.outbound_connect_timeout_seconds,
        read_timeout=s.outbound_read_timeout_seconds,
        total_timeout=s.outbound_total_timeout_seconds,
        max_response_bytes=s.outbound_max_response_bytes,
        max_redirects=s.outbound_max_redirects,
        spec_max_bytes=s.outbound_spec_max_bytes,
    )
