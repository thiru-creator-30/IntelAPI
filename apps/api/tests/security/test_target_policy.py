import ipaddress
import pytest

from app.execution.policy import TargetBlocked, validate_endpoint, validate_url
import app.execution.policy as policy


def test_file_scheme_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("file:///etc/passwd")


def test_loopback_ipv4_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://127.0.0.1/")


def test_loopback_ipv6_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://[::1]/")


def test_private_10_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://10.0.0.1/")


def test_private_192_168_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://192.168.1.1/")


def test_link_local_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://169.254.1.1/")


def test_metadata_ip_blocked():
    with pytest.raises(TargetBlocked):
        validate_url("http://169.254.169.254/")


def test_public_ip_parses_ok(monkeypatch):
    def fake_resolve(host, port):
        # 1.1.1.1 is public
        return [(None, "1.1.1.1")]
    monkeypatch.setattr(policy, "resolve_host", fake_resolve)
    scheme, host, port, ips = validate_endpoint("https://example.com/")
    assert host == "example.com"
    assert "1.1.1.1" in ips


def test_resolved_private_ip_blocked(monkeypatch):
    def fake_resolve(host, port):
        return [(None, "10.0.0.1")]
    monkeypatch.setattr(policy, "resolve_host", fake_resolve)
    with pytest.raises(TargetBlocked):
        validate_endpoint("https://attacker.example/")


def test_mixed_resolved_addresses_fail_closed(monkeypatch):
    def fake_resolve(host, port):
        return [(None, "1.1.1.1"), (None, "10.0.0.1")]
    monkeypatch.setattr(policy, "resolve_host", fake_resolve)
    with pytest.raises(TargetBlocked):
        validate_endpoint("https://rebind.example/")
