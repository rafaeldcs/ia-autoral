from __future__ import annotations
import http.client
import ipaddress
import re
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from .config import Settings
from .errors import PolicyError
from .store import Store

USER_AGENT = "LocalAuthorResearch/0.1"


def validate_url(url: str, allowed_domains: list[str]) -> urllib.parse.SplitResult:
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 32 for c in url) or "\\" in url:
        raise PolicyError("URL inválida.")
    try:
        p = urllib.parse.urlsplit(url)
        host = (p.hostname or "").lower()
        port = p.port
    except ValueError as exc:
        raise PolicyError("URL inválida.") from exc
    if p.scheme != "https" or port not in {None, 443} or p.username or p.password or not host or p.fragment:
        raise PolicyError("Somente HTTPS padrão, sem credenciais ou fragmentos.")
    if host not in {d.lower() for d in allowed_domains}:
        raise PolicyError("Domínio fora da lista explicitamente autorizada.")
    if host.endswith(".") or host in {"localhost", "metadata.google.internal"}:
        raise PolicyError("Destino local bloqueado.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise PolicyError("Use um domínio público autorizado, não um IP literal.")
    for key, _ in urllib.parse.parse_qsl(p.query):
        if any(s in key.lower() for s in ("token", "password", "secret", "api_key", "apikey", "code")):
            raise PolicyError("Parâmetro potencialmente sensível não pode ser enviado pelo pesquisador.")
    return p


def public_addresses(host: str) -> list[str]:
    addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    if not addresses:
        raise PolicyError("DNS sem endereço válido.")
    # Reject the entire resolution when ANY result is non-public (mixed DNS included).
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise PolicyError("DNS aponta para endereço não público; requisição bloqueada.")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str):
        super().__init__(host, port=443, timeout=12, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Connect to the checked IP directly; retain certificate validation/SNI for the original host.
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


class SafeTransport:
    def __init__(self, settings: Settings):
        self.settings = settings

    def request(self, url: str, headers: dict[str, str], cancel: threading.Event | None = None) -> Response:
        if self.settings.offline:
            raise PolicyError("Rede desativada na configuração.")
        p = validate_url(url, self.settings.allowed_domains)
        addresses = public_addresses(p.hostname or "")
        conn = PinnedHTTPSConnection(p.hostname or "", addresses[0])
        try:
            path = urllib.parse.urlunsplit(("", "", p.path or "/", p.query, ""))
            conn.request("GET", path, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity", **headers})
            response = conn.getresponse()
            response_headers = {k.lower(): v for k, v in response.getheaders()}
            if response_headers.get("content-encoding", "identity").lower() != "identity":
                raise PolicyError("Conteúdo comprimido não aceito pelo coletor limitado.")
            length = response_headers.get("content-length")
            if length is not None and (not length.isdigit() or int(length) > 2_000_000):
                raise PolicyError("Resposta excede o limite de coleta.")
            chunks, total = [], 0
            while True:
                if cancel and cancel.is_set():
                    raise PolicyError("Coleta cancelada.")
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > 2_000_000:
                    raise PolicyError("Resposta excede o limite de coleta.")
                chunks.append(chunk)
            return Response(response.status, response_headers, b"".join(chunks))
        finally:
            conn.close()


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1
        if not self.hidden:
            if tag in {"p", "br", "div", "li", "h1", "h2", "h3", "pre", "tr"}:
                self.parts.append("\n")
            if tag == "a":
                href = dict(attrs).get("href")
                if href and len(self.links) < 100:
                    self.links.append(href)

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in {"p", "div", "li", "pre", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{4,}", "\n\n\n", "".join(self.parts)).strip()


class ResearchService:
    def __init__(self, store: Store, settings: Settings, transport=None):
        self.store, self.settings = store, settings
        self.transport = transport or SafeTransport(settings)
        self.robots: dict[str, tuple[float, urllib.robotparser.RobotFileParser]] = {}
        self.last_request: dict[str, float] = {}
        self.lock = threading.RLock()

    def _request(self, url: str, headers: dict, cancel=None) -> Response:
        host = validate_url(url, self.settings.allowed_domains).hostname or ""
        wait = max(0.0, 0.5 - (time.monotonic() - self.last_request.get(host, 0)))
        if cancel:
            if cancel.wait(wait): raise PolicyError("Coleta cancelada.")
        else:
            time.sleep(wait)
        self.last_request[host] = time.monotonic()
        try:
            response = self.transport.request(url, headers, cancel)
            self.store.audit("research.http", {"url": url, "status": response.status, "bytes": len(response.body)})
            return response
        except Exception:
            self.store.audit("research.http_failed", {"url": url})
            raise

    def _robots_allowed(self, url: str, cancel=None) -> bool:
        p = validate_url(url, self.settings.allowed_domains)
        origin = f"https://{p.hostname}"
        cached = self.robots.get(origin)
        if not cached or time.monotonic() - cached[0] > 3600:
            response = self._request(origin + "/robots.txt", {}, cancel)
            parser = urllib.robotparser.RobotFileParser()
            if response.status == 404:
                parser.parse(["User-agent: *", "Disallow:"])
            elif response.status == 200:
                parser.parse(response.body.decode("utf-8", errors="replace").splitlines())
            else:
                # Redirects and errors fail closed instead of silently ignoring robots.
                return False
            self.robots[origin] = (time.monotonic(), parser)
        parser = self.robots[origin][1]
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
        if delay > 0:
            last = self.last_request.get(p.hostname or "", 0)
            wait = max(0, delay - (time.monotonic() - last))
            if wait > 30:
                raise PolicyError("Crawl-delay maior que o orçamento desta execução.")
            if cancel:
                if cancel.wait(wait): raise PolicyError("Coleta cancelada.")
            else:
                time.sleep(wait)
        return parser.can_fetch(USER_AGENT, url)

    def fetch(self, url: str, scope: str = "global", *, force_refresh: bool = False, cancel=None) -> dict:
        with self.lock:
            self.store.check_scope(scope)
            validate_url(url, self.settings.allowed_domains)
            existing = self.store.source(scope, url)
            if existing and not force_refresh:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(existing["checked_at"])).total_seconds()
                if age < self.settings.cache_ttl_seconds or self.settings.offline:
                    return {"id": existing["id"], "reused": True, "network_requests": 0, "stale": age >= self.settings.cache_ttl_seconds}
            if self.settings.offline:
                raise PolicyError("Sem fonte local válida e rede desativada; nenhuma requisição foi feita.")
            current = url
            for _ in range(4):
                if not self._robots_allowed(current, cancel):
                    raise PolicyError("Coleta não autorizada por robots.txt ou regras não verificáveis.")
                headers = {}
                if existing and current == url:
                    if existing.get("etag"): headers["If-None-Match"] = existing["etag"]
                    if existing.get("last_modified"): headers["If-Modified-Since"] = existing["last_modified"]
                response = self._request(current, headers, cancel)
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise PolicyError("Redirecionamento sem destino.")
                    current = urllib.parse.urljoin(current, location)
                    validate_url(current, self.settings.allowed_domains)
                    continue
                if response.status == 304 and existing:
                    self.store.touch_source(existing["id"])
                    return {"id": existing["id"], "reused": True, "not_modified": True}
                if response.status != 200:
                    raise PolicyError(f"A fonte retornou HTTP {response.status}.")
                content_type = response.headers.get("content-type", "").split(";")[0].lower().strip()
                if content_type not in {"text/plain", "text/html", "text/markdown", "application/xhtml+xml"}:
                    raise PolicyError("Coletor aceita somente texto e HTML; PDFs não são processados nesta versão.")
                try:
                    body = response.body.decode("utf-8", errors="strict")
                except UnicodeError as exc:
                    raise PolicyError("Fonte não está em UTF-8; importe uma cópia convertida e revisada.") from exc
                links = []
                if "html" in content_type:
                    parser = TextExtractor()
                    parser.feed(body)
                    body = parser.text()
                    for link in parser.links:
                        candidate = urllib.parse.urldefrag(urllib.parse.urljoin(current, link))[0]
                        try:
                            validate_url(candidate, self.settings.allowed_domains)
                        except PolicyError:
                            continue
                        if candidate not in links: links.append(candidate)
                result = self.store.ingest(scope, url, current[:240], body, kind="web", training_allowed=False, etag=response.headers.get("etag"), last_modified=response.headers.get("last-modified"))
                return {**result, "reused": False, "final_url": current, "candidate_links": links[:20], "training_allowed": False}
            raise PolicyError("Limite de redirecionamentos atingido.")

    def collect(self, urls: list[str], scope: str, cancel=None) -> list[dict]:
        if not isinstance(urls, list) or not 1 <= len(urls) <= 5:
            raise PolicyError("Uma rodada recebe de 1 a 5 URLs explícitas.")
        # No recursive crawling or automatic disclosure of project instructions.
        return [self.fetch(url, scope, cancel=cancel) for url in dict.fromkeys(urls)]
