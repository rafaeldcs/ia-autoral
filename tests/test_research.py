import socket
from unittest.mock import patch
from localauthor.research import ResearchService, Response, validate_url, public_addresses, TextExtractor
from localauthor.errors import PolicyError
from tests.helpers import WorkspaceCase


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
    def request(self, url, headers, cancel=None):
        self.calls.append((url, headers))
        if not self.responses: raise AssertionError("Requisição inesperada: "+url)
        return self.responses.pop(0)


class ResearchTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.settings.allowed_domains = ["example.com"]
        self.settings.offline = False
        self.sleep = patch("localauthor.research.time.sleep")
        self.sleep.start()
    def tearDown(self):
        self.sleep.stop()
        super().tearDown()
    def service(self, responses):
        t = FakeTransport(responses)
        return ResearchService(self.store, self.settings, t), t
    def robots(self, body=b"User-agent: *\nDisallow:\n"):
        return Response(200, {"content-type": "text/plain"}, body)
    def page(self, text=b"Stock documentation", headers=None):
        return Response(200, headers or {"content-type": "text/plain", "etag": '"v1"'}, text)

    def test_exact_domain_allowlist(self):
        with self.assertRaises(PolicyError): validate_url("https://evil.example.com/page", ["example.com"])
        validate_url("https://example.com/page", ["example.com"])

    def test_rejects_unsafe_scheme_ports_and_credentials(self):
        for url in ["http://example.com", "file:///etc/passwd", "https://user:pass@example.com", "https://example.com:8080", "https://example.com/#secret", "https://example.com/?api_key=x"]:
            with self.subTest(url=url), self.assertRaises(PolicyError): validate_url(url, ["example.com"])

    def test_dns_private_address_blocked(self):
        for address in ["127.0.0.1", "10.1.1.1", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "224.0.0.1"]:
            with self.subTest(address=address), patch("localauthor.research.socket.getaddrinfo", return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,"",(address,443))]), self.assertRaises(PolicyError):
                public_addresses("example.com")

    def test_dns_mixed_public_private_rejected(self):
        addresses = [(socket.AF_INET,socket.SOCK_STREAM,6,"",(a,443)) for a in ["8.8.8.8", "127.0.0.1"]]
        with patch("localauthor.research.socket.getaddrinfo", return_value=addresses), self.assertRaises(PolicyError): public_addresses("example.com")

    def test_dns_public_address_allowed(self):
        with patch("localauthor.research.socket.getaddrinfo", return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,"",("8.8.8.8",443))]):
            self.assertEqual(public_addresses("example.com"), ["8.8.8.8"])

    def test_offline_never_calls_network(self):
        self.settings.offline = True
        service, t = self.service([])
        with self.assertRaises(PolicyError): service.fetch("https://example.com/doc")
        self.assertEqual(t.calls, [])

    def test_second_query_reuses_cache_without_http(self):
        service, t = self.service([self.robots(), self.page()])
        first = service.fetch("https://example.com/doc")
        second = service.fetch("https://example.com/doc")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(second["network_requests"], 0)

    def test_conditional_304_does_not_duplicate_content(self):
        service, t = self.service([self.robots(), self.page(), Response(304, {}, b"")])
        service.fetch("https://example.com/doc")
        result = service.fetch("https://example.com/doc", force_refresh=True)
        self.assertTrue(result["not_modified"])
        self.assertEqual(t.calls[-1][1]["If-None-Match"], '"v1"')
        self.assertEqual(self.store.stats()["versions"], 1)

    def test_robots_disallow_blocks_page(self):
        service, t = self.service([self.robots(b"User-agent: *\nDisallow: /private\n")])
        with self.assertRaises(PolicyError): service.fetch("https://example.com/private/doc")
        self.assertEqual(len(t.calls), 1)

    def test_robots_error_fails_closed(self):
        service, t = self.service([Response(503, {}, b"")])
        with self.assertRaises(PolicyError): service.fetch("https://example.com/doc")
        self.assertEqual(len(t.calls), 1)

    def test_redirect_outside_allowlist_blocked(self):
        service, t = self.service([self.robots(), Response(302, {"location": "https://evil.test/doc"}, b"")])
        with self.assertRaises(PolicyError): service.fetch("https://example.com/doc")
        self.assertEqual(len(t.calls), 2)

    def test_html_does_not_run_or_store_scripts(self):
        service, t = self.service([self.robots(), self.page(b'<h1>Stock</h1><script>fetch("secret")</script><p>Valida quantity.</p>', {"content-type":"text/html"})])
        service.fetch("https://example.com/doc")
        source = self.store.source("global", "https://example.com/doc")
        self.assertNotIn("fetch", source["content"])
        self.assertIn("Valida", source["content"])
        self.assertEqual(source["training_allowed"], 0)

    def test_pdf_not_silently_processed(self):
        service, _ = self.service([self.robots(), self.page(b"%PDF", {"content-type":"application/pdf"})])
        with self.assertRaises(PolicyError): service.fetch("https://example.com/paper.pdf")

    def test_collection_limit(self):
        service, _ = self.service([])
        with self.assertRaises(PolicyError): service.collect(["https://example.com"]*6, "global")
