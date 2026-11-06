import asyncio
import socket
from types import SimpleNamespace

import pytest

from app.services import lti_service


def _addrinfo(address, port):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


class FakeResolverLoop:
    def __init__(self, addresses=None, error=None):
        self.addresses = addresses or []
        self.error = error
        self.calls = []

    async def getaddrinfo(self, hostname, port, *, type):
        self.calls.append((hostname, port, type))
        if self.error:
            raise self.error
        return [_addrinfo(address, port) for address in self.addresses]


def _stub_resolver(monkeypatch, loop):
    monkeypatch.setattr(
        lti_service,
        "asyncio",
        SimpleNamespace(get_running_loop=lambda: loop),
    )


def test_lti_dns_resolution_pins_first_public_address_and_checks_every_answer(monkeypatch):
    loop = FakeResolverLoop(["8.8.8.8", "1.1.1.1", "8.8.8.8"])
    _stub_resolver(monkeypatch, loop)

    pinned_url, headers, extensions = asyncio.run(
        lti_service.resolve_lti_platform_endpoint_url(
            "https://moodle.example.test:8443/jwks"
        )
    )

    assert loop.calls == [("moodle.example.test", 8443, socket.SOCK_STREAM)]
    assert pinned_url == "https://8.8.8.8:8443/jwks"
    assert headers == {"Host": "moodle.example.test:8443"}
    assert extensions == {"sni_hostname": "moodle.example.test"}


def test_lti_dns_resolution_fails_closed_when_any_answer_is_private(monkeypatch):
    loop = FakeResolverLoop(["8.8.8.8", "10.20.30.40"])
    _stub_resolver(monkeypatch, loop)

    with pytest.raises(ValueError, match="non-public IP"):
        asyncio.run(
            lti_service.resolve_lti_platform_endpoint_url(
                "https://moodle.example.test/jwks"
            )
        )


def test_lti_dns_resolution_fails_closed_when_no_addresses_are_returned(monkeypatch):
    loop = FakeResolverLoop([])
    _stub_resolver(monkeypatch, loop)

    with pytest.raises(ValueError, match="no addresses"):
        asyncio.run(
            lti_service.resolve_lti_platform_endpoint_url(
                "https://moodle.example.test/jwks"
            )
        )


def test_lti_dns_resolution_wraps_resolver_errors(monkeypatch):
    loop = FakeResolverLoop(error=OSError("resolver unavailable"))
    _stub_resolver(monkeypatch, loop)

    with pytest.raises(ValueError, match="Unable to resolve"):
        asyncio.run(
            lti_service.resolve_lti_platform_endpoint_url(
                "https://moodle.example.test/jwks"
            )
        )


def test_lti_dns_resolution_allows_local_loopback_only_in_test_environment(monkeypatch):
    monkeypatch.setattr(lti_service.settings, "ENVIRONMENT", "test")
    loop = FakeResolverLoop(["127.0.0.1"])
    _stub_resolver(monkeypatch, loop)

    pinned_url, headers, extensions = asyncio.run(
        lti_service.resolve_lti_platform_endpoint_url("http://localhost:8080/jwks")
    )

    assert pinned_url == "http://127.0.0.1:8080/jwks"
    assert headers == {"Host": "localhost:8080"}
    assert extensions == {}


class FakeJWKSResponse:
    def __init__(self, body=b"", status_code=200):
        self.body = body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    async def aiter_bytes(self):
        midpoint = len(self.body) // 2
        if midpoint:
            yield self.body[:midpoint]
            yield self.body[midpoint:]
        elif self.body:
            yield self.body


class FakeJWKSStream:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def _stub_jwks_http(monkeypatch, response):
    instances = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.stream_call = None
            instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        def stream(self, method, url, **kwargs):
            self.stream_call = (method, url, kwargs)
            return FakeJWKSStream(response)

    async def fake_resolve(url):
        return (
            "https://8.8.8.8/jwks",
            {"Host": "moodle.example.test"},
            {"sni_hostname": "moodle.example.test"},
        )

    monkeypatch.setattr(
        lti_service,
        "httpx",
        SimpleNamespace(AsyncClient=FakeAsyncClient),
    )
    monkeypatch.setattr(lti_service, "resolve_lti_platform_endpoint_url", fake_resolve)
    return instances


def test_fetch_platform_public_key_uses_pinned_transport_options(monkeypatch):
    expected_key = {"kid": "platform-key", "kty": "RSA", "use": "sig"}
    response = FakeJWKSResponse(
        b'{"keys":[{"kid":"other-key","kty":"RSA"},{"kid":"platform-key","kty":"RSA","use":"sig"}]}'
    )
    clients = _stub_jwks_http(monkeypatch, response)

    result = asyncio.run(
        lti_service.fetch_platform_public_key(
            "https://moodle.example.test/jwks", "platform-key"
        )
    )

    assert result == expected_key
    assert len(clients) == 1
    assert clients[0].options == {
        "timeout": 15.0,
        "follow_redirects": False,
        "trust_env": False,
    }
    assert clients[0].stream_call == (
        "GET",
        "https://8.8.8.8/jwks",
        {
            "headers": {"Host": "moodle.example.test"},
            "extensions": {"sni_hostname": "moodle.example.test"},
        },
    )


def test_fetch_platform_public_key_rejects_redirects(monkeypatch):
    clients = _stub_jwks_http(
        monkeypatch,
        FakeJWKSResponse(status_code=302),
    )

    with pytest.raises(ValueError, match="redirects are not allowed"):
        asyncio.run(
            lti_service.fetch_platform_public_key(
                "https://moodle.example.test/jwks", "platform-key"
            )
        )

    assert len(clients) == 1


def test_fetch_platform_public_key_rejects_responses_over_one_mib(monkeypatch):
    oversized = FakeJWKSResponse(b"x" * (1024 * 1024 + 1))
    _stub_jwks_http(monkeypatch, oversized)

    with pytest.raises(ValueError, match="1 MiB limit"):
        asyncio.run(
            lti_service.fetch_platform_public_key(
                "https://moodle.example.test/jwks", "platform-key"
            )
        )


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        (b"{not-json", "valid JSON"),
        (b'{"keys":{}}', "keys array"),
        (b'{"keys":[{"kid":"another-key"}]}', "ما لقينا مفتاح مطابق"),
    ],
)
def test_fetch_platform_public_key_rejects_invalid_or_unmatched_jwks(
    monkeypatch, body, expected_error
):
    _stub_jwks_http(monkeypatch, FakeJWKSResponse(body))

    with pytest.raises(ValueError, match=expected_error):
        asyncio.run(
            lti_service.fetch_platform_public_key(
                "https://moodle.example.test/jwks", "platform-key"
            )
        )
