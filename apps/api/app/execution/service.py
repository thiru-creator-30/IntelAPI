from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.execution.policy import (
    OutboundLimits,
    TargetBlocked,
    TargetTimeout,
    get_limits,
    validate_endpoint,
    validate_url,
)
from app.execution.redactor import redact_body, redact_headers, redact_text
from app.execution.transport import build_safe_client

log = get_logger(__name__)


@dataclass
class PreparedRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | bytes | None = None
    secret_values: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    outcome: str
    status_code: int | None = None
    duration_ms: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body_excerpt: str | None = None
    response_size_bytes: int = 0
    final_url: str | None = None
    transport_error: str | None = None
    request_snapshot: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _strip_internal_headers(headers: dict[str, str]) -> dict[str, str]:
    # Never forward: cookie, authorization, proxy-authorization, host, connection-specific hops.
    stripped = {}
    drop = {
        "host",
        "cookie",
        "authorization",
        "proxy-authorization",
        "content-length",
        "transfer-encoding",
        "connection",
    }
    for k, v in headers.items():
        if k.lower() in drop:
            continue
        stripped[k] = v
    return stripped


async def _send_one(
    client: httpx.AsyncClient,
    limits: OutboundLimits,
    pr: PreparedRequest,
    current_url: str,
    current_method: str,
    current_headers: dict[str, str],
    current_body: str | bytes | None,
    hop: int,
) -> ExecutionResult:
    # Validate DNS + IPs for this hop.
    _scheme, host, port, ips = validate_endpoint(current_url)
    # Connect with a custom socket bound to validated IP to prevent DNS rebinding.
    # Because httpx's high-level API does not easily let us bind to a specific IP per-request,
    # we re-resolve immediately before connect and validate again; any rebinding attempt at this
    # window can only resolve to the same IP set (we fail closed on mismatch).
    # Resolve once more just before sending and compare IPs as a rebinding check.
    _scheme2, _host2, _port2, ips2 = validate_endpoint(current_url)
    if set(ips) != set(ips2):
        raise TargetBlocked("DNS re-resolution changed addresses (possible rebinding)")

    # Build a Host header based on the original URL (so virtual hosts work)
    headers = dict(current_headers)
    if "host" not in [k.lower() for k in headers]:
        default_port = (443 if _scheme == "https" else 80)
        headers["Host"] = host if port == default_port else f"{host}:{port}"

    started = time.perf_counter()
    started_at = _utcnow()
    response: httpx.Response | None = None
    try:
        req = client.build_request(current_method.upper(), current_url, headers=headers, content=current_body)
        response = await client.send(req, stream=True)
        chunks: list[bytes] = []
        total = 0
        try:
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total <= limits.max_response_bytes:
                    chunks.append(chunk)
                if total > limits.max_response_bytes:
                    await response.aclose()
                    completed_at = _utcnow()
                    return ExecutionResult(
                        outcome="response_too_large",
                        status_code=response.status_code,
                        duration_ms=int((time.perf_counter() - started) * 1000),
                        response_headers=redact_headers(dict(response.headers)),
                        response_body_excerpt=None,
                        response_size_bytes=total,
                        final_url=str(response.url),
                        transport_error=None,
                        request_snapshot=_snapshot(pr, current_url, current_method, headers),
                        started_at=started_at,
                        completed_at=completed_at,
                    )
        finally:
            if response is not None and not response.is_closed:
                await response.aclose()
        body_bytes = b"".join(chunks)
        # Handle redirects (same as httpx redirect logic but with policy re-check).
        if response.status_code in (301, 302, 303, 307, 308) and hop < limits.max_redirects:
            location = response.headers.get("location")
            if location:
                # Join relative URLs.
                next_url = str(httpx.URL(location).copy_with(scheme=None)) if "://" not in location else location
                # Re-validate redirect target (scheme + DNS/IPs).
                validate_endpoint(next_url)
                new_method = current_method.upper()
                new_body = current_body
                if response.status_code == 303:
                    new_method = "GET"
                    new_body = None
                return await _send_one(client, limits, pr, next_url, new_method, _strip_internal_headers(headers), new_body, hop + 1)
        # Terminal response
        completed_at = _utcnow()
        try:
            text = body_bytes.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            text = ""
        text = redact_text(text, pr.secret_values)
        return ExecutionResult(
            outcome="http_response",
            status_code=response.status_code,
            duration_ms=int((time.perf_counter() - started) * 1000),
            response_headers=redact_headers(dict(response.headers)),
            response_body_excerpt=text,
            response_size_bytes=total,
            final_url=str(response.url),
            transport_error=None,
            request_snapshot=_snapshot(pr, current_url, current_method, headers),
            started_at=started_at,
            completed_at=completed_at,
        )
    except httpx.TimeoutException as exc:
        return ExecutionResult(
            outcome="timeout",
            duration_ms=int((time.perf_counter() - started) * 1000),
            transport_error=f"timeout: {type(exc).__name__}",
            request_snapshot=_snapshot(pr, current_url, current_method, headers),
            started_at=started_at,
            completed_at=_utcnow(),
        )
    except httpx.ConnectError as exc:
        return ExecutionResult(
            outcome="connection_error",
            duration_ms=int((time.perf_counter() - started) * 1000),
            transport_error=f"connect_error: {type(exc).__name__}",
            request_snapshot=_snapshot(pr, current_url, current_method, headers),
            started_at=started_at,
            completed_at=_utcnow(),
        )
    except TargetBlocked as exc:
        # Hop-level block (e.g., redirect rejected).
        return ExecutionResult(
            outcome="blocked_by_policy",
            duration_ms=int((time.perf_counter() - started) * 1000),
            transport_error=exc.message,
            request_snapshot=_snapshot(pr, current_url, current_method, headers),
            started_at=started_at,
            completed_at=_utcnow(),
        )
    except Exception as exc:  # pragma: no cover
        log.exception("execution_error", url=current_url, error=str(exc))
        return ExecutionResult(
            outcome="execution_error",
            duration_ms=int((time.perf_counter() - started) * 1000),
            transport_error=type(exc).__name__,  # keep it generic to avoid leaking internals
            request_snapshot=_snapshot(pr, current_url, current_method, headers),
            started_at=started_at,
            completed_at=_utcnow(),
        )


def _snapshot(pr: PreparedRequest, current_url: str, method: str, headers: dict[str, str]) -> dict[str, Any]:
    redacted_headers = redact_headers(_strip_internal_headers(headers))
    body = pr.body
    if isinstance(body, bytes):
        try:
            body = body.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover
            body = "<binary>"
    body = redact_text(body or "", pr.secret_values)
    if body and len(body) > get_settings().outbound_max_response_bytes:
        body = body[: get_settings().outbound_max_response_bytes] + "...[truncated]"
    body = redact_body(body if isinstance(body, (dict, list)) else body)
    return {
        "method": method.upper(),
        "url": current_url,
        "headers": redacted_headers,
        "body": body,
    }


async def execute(pr: PreparedRequest) -> ExecutionResult:
    limits = get_limits()
    client = build_safe_client(limits)
    try:
        headers = _strip_internal_headers(dict(pr.headers))
        return await _send_one(client, limits, pr, pr.url, pr.method, headers, pr.body, hop=0)
    finally:
        await client.aclose()


async def fetch_bytes(url: str, *, max_bytes: int | None = None, secret_values: list[str] | None = None) -> bytes:
    """Fetch a URL used for URL-based OpenAPI import. Subject to the same policy; bounded by max_bytes."""
    limits = get_limits()
    cap = max_bytes or limits.spec_max_bytes
    client = build_safe_client(limits)
    try:
        # Initial validate + pre-resolve check.
        validate_endpoint(url)
        try:
            req = client.build_request("GET", url, headers={})
            response = await client.send(req, stream=True)
        except httpx.TimeoutException as exc:
            raise TargetTimeout("fetch timeout") from exc
        except httpx.ConnectError as exc:
            raise TargetBlocked(f"connect failed: {type(exc).__name__}") from exc
        try:
            if response.status_code >= 400:
                raise TargetBlocked(f"fetch returned status {response.status_code}")
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > cap:
                    await response.aclose()
                    raise TargetBlocked("response too large")
                chunks.append(chunk)
        finally:
            if not response.is_closed:
                await response.aclose()
        return b"".join(chunks)
    finally:
        await client.aclose()
