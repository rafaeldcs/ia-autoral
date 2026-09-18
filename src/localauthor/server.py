from __future__ import annotations
import hmac
import json
import logging
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from .application import Application
from .code_tools import symbols
from .diagnostics import diagnose
from .errors import LocalAIError, PolicyError, ConflictError, NotFoundError
from .safety import PathPolicy
from .util import read_json, write_json, sha256

MAX_BODY = 2_500_000
STATIC = {"/": "chat.html", "/advanced": "index.html", "/app.js": "app.js", "/styles.css": "styles.css", "/chat.js": "chat.js", "/chat.css": "chat.css"}


def make_handler(app: Application, ui_path: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LocalAuthor/0.1"
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, format, *args):
            # Do not print bearer tokens, queries, private code, or full request bodies.
            pass

        def _allowed_origin(self):
            port = self.server.server_port
            allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host = self.headers.get("Host", "")
            if host not in allowed:
                raise PolicyError("Host não autorizado; use o endereço local exibido na inicialização.")
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {"http://"+h for h in allowed}:
                raise PolicyError("Origem externa bloqueada.")
            if self.headers.get("Sec-Fetch-Site") in {"cross-site", "same-site"}:
                raise PolicyError("Requisição fora da mesma origem bloqueada.")

        def _authenticate(self):
            expected = "Bearer " + app.settings.token
            provided = self.headers.get("Authorization", "")
            if not hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8")):
                self.close_connection = True
                self._send(401, {"error": "Token local obrigatório. Execute o comando token no seu computador."})
                return False
            return True

        def _send(self, status, data, content_type="application/json; charset=utf-8"):
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8") if not isinstance(data, bytes) else data
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _body(self):
            if len(self.headers.get_all("Content-Length", [])) > 1:
                raise PolicyError("Content-Length duplicado.")
            if self.headers.get("Transfer-Encoding"):
                raise PolicyError("Transfer-Encoding não aceito.")
            if self.headers.get_content_type() != "application/json":
                raise PolicyError("Use application/json.")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise PolicyError("Content-Length inválido.") from exc
            if not 1 <= length <= MAX_BODY:
                raise PolicyError("Corpo vazio ou excedendo o limite.")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise PolicyError("Corpo incompleto.")
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise PolicyError("O corpo JSON deve ser um objeto.")
            return data

        def _dispatch(self, method):
            try:
                self._allowed_origin()
                parsed = urlsplit(self.path)
                path = parsed.path
                q = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                if method == "GET" and path in STATIC:
                    file = ui_path / STATIC[path]
                    if not file.is_file(): raise NotFoundError("Interface não encontrada; execute a partir do repositório completo.")
                    types = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}
                    self._send(200, file.read_bytes(), types[file.suffix])
                    return
                if not self._authenticate(): return
                body = self._body() if method == "POST" else {}
                result = self._route(method, path, q, body)
                self._send(200, result)
            except NotFoundError as exc:
                self._send(404, {"error": str(exc)})
            except ConflictError as exc:
                self._send(409, {"error": str(exc)})
            except (PolicyError, ValueError, KeyError, TypeError, UnicodeError) as exc:
                self.close_connection = True
                self._send(400, {"error": str(exc)[:1000]})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
            except Exception:
                logging.exception("Falha interna do servidor local")
                self._send(500, {"error": "Erro interno. Consulte o console local; nenhum fallback externo foi utilizado."})

        def _route(self, method, path, q, body):
            if method == "GET":
                if path == "/api/health":
                    return {"status": "ok", "version": "0.1.0", "mode": "platform_and_experimental_cpu_model", "offline": app.settings.offline, "model_qualified": False, "gpu_backend": False, "stats": app.store.stats(), "allowed_domains": app.settings.allowed_domains, "runner_enabled": bool(app.settings.docker_image)}
                if path == "/api/diagnostics": return diagnose(app.settings.home)
                if path == "/api/projects": return app.store.projects()
                if path == "/api/investigations": return app.chat.investigations.list(q["project_id"])
                if path == "/api/conversations": return app.chat.conversations(q["project_id"])
                if path == "/api/conversation": return app.chat.get(q["project_id"], q["id"])
                if path == "/api/project-preferences": return app.chat.preferences(q["project_id"])
                if path == "/api/engineering-report":
                    file = app.settings.home / "exports/engineering-report.json"
                    report = read_json(file) if file.exists() else {}
                    return {k: report[k] for k in ("state", "counts", "evaluation", "limitations") if k in report}
                if path == "/api/communication-report":
                    file = app.settings.home / "exports/communication-report.json"
                    report = read_json(file) if file.exists() else {}
                    return {**{k: report[k] for k in ("state", "counts", "limitations", "chatEnabled") if k in report}, "evaluation": {k: report.get("evaluation", {}).get(k) for k in ("passed", "total")}}
                if path == "/api/sources": return app.store.sources(q.get("scope", "global"))
                if path == "/api/relations": return app.store.relations(q.get("scope", "global"))
                if path == "/api/tasks": return app.tasks.list()
                if path == "/api/jobs": return app.jobs.list()
                if path == "/api/models":
                    reports = []
                    for file in sorted((app.settings.home/"models").glob("*/report.json")):
                        reports.append({"directory": file.parent.name, **read_json(file)})
                    return reports
                match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})", path)
                if match: return app.jobs.get(match[1])
                match = re.fullmatch(r"/api/tasks/([0-9a-f]{32})(/files|/file)?", path)
                if match:
                    ident, action = match[1], match[2]
                    if action == "/files": return read_json(app.tasks.base(ident)/"snapshot.json")
                    if action == "/file":
                        raw = PathPolicy(app.tasks.base(ident)/"tree").read(q["path"])
                        return {"path": q["path"], "sha256": sha256(raw), "content": raw.decode("utf-8")}
                    return app.tasks.preview(ident)
            if method == "POST":
                if path == "/api/projects": return app.store.add_project(body["name"], body["root"])
                if path == "/api/investigations": return app.chat.investigations.create(body["project_id"], body["name"], body["origin"])
                if path == "/api/investigations/observe": return app.chat.investigations.observe(body["project_id"], body["investigation_id"], body["screen"])
                if path == "/api/conversations": return app.chat.create(body["project_id"], body.get("title", "Nova conversa"))
                if path == "/api/project-preferences": return app.chat.save_preferences(body["project_id"], body["method"], body["wip_limit"], body["definition_of_done"])
                if path == "/api/chat":
                    app.chat.get(body["project_id"], body["conversation_id"])
                    app.chat.validate_message(body["message"], body.get("mode", "guide"), body.get("input_format", "text"))
                    if body.get("mode") == "model":
                        return {"job": app.jobs.submit("chat", {k: body[k] for k in ("project_id", "conversation_id", "message", "mode", "input_format") if k in body})}
                    return app.chat.respond(body["project_id"], body["conversation_id"], body["message"], body.get("mode", "guide"), input_format=body.get("input_format", "text"))
                if path == "/api/consult": return app.knowledge.consult(body["query"], body.get("scope", "global"), body.get("include_global") is True)
                if path == "/api/import":
                    scope = body.get("scope", "global")
                    if "path" in body:
                        project = app.store.project(scope)
                        raw = PathPolicy(Path(project["root"]), app.settings.max_file_bytes).read(body["path"])
                        return app.store.ingest(scope, body["path"], body["path"], raw.decode("utf-8"))
                    return app.store.ingest(scope, "note:"+body["title"], body["title"], body["content"], kind="note", training_allowed=False)
                if path == "/api/sources/delete":
                    app.store.delete_source(body["source_id"], body["scope"])
                    return {"deleted": True, "weights_unlearned": False}
                if path == "/api/relations":
                    return app.store.add_relation(body["scope"], body["subject"], body["predicate"], body["object"], body["chunk_id"], body.get("status", "proposed"), "human")
                if path == "/api/symbols":
                    project = app.store.project(body["project_id"])
                    return symbols(Path(project["root"]), body["path"])
                if path == "/api/tasks": return app.tasks.create(body["project_id"], body["instruction"])
                if path == "/api/jobs/index":
                    app.store.project(body["project_id"])
                    return app.jobs.submit("index", {"project_id": body["project_id"]})
                if path == "/api/jobs/research":
                    app.store.check_scope(body.get("scope", "global"))
                    return app.jobs.submit("research", {"urls": body["urls"], "scope": body.get("scope", "global")})
                if path == "/api/jobs/train":
                    if body.get("approved_dataset") is not True:
                        raise PolicyError("Confirme explicitamente a revisão dos direitos e das partições do corpus.")
                    return app.jobs.submit("train", {k: body[k] for k in ("manifest", "steps", "batch_size", "config", "tokenizer") if k in body})
                match = re.fullmatch(r"/api/jobs/([0-9a-f]{32})/cancel", path)
                if match: return app.jobs.cancel(match[1])
                match = re.fullmatch(r"/api/tasks/([0-9a-f]{32})/(proposal|apply|reject|recover|feedback|verify)", path)
                if match:
                    ident, action = match[1], match[2]
                    if action == "proposal": return app.tasks.propose(ident, body["changes"], allow_test_changes=body.get("allow_test_changes") is True)
                    if action == "apply": return app.tasks.apply(ident, body["proposal_hash"], accept_without_tests=body.get("accept_without_tests") is True)
                    if action == "reject": return app.tasks.reject(ident)
                    if action == "recover": return app.tasks.recover(ident)
                    if action == "feedback": return app.tasks.feedback(ident, body["status"], body.get("note", ""))
                    if action == "verify":
                        app.tasks.get(ident)
                        return app.jobs.submit("verify", {"task_id": ident, "kind": body["kind"], "project_file": body.get("project_file", "")})
            raise NotFoundError("Rota não encontrada.")

        def do_GET(self): self._dispatch("GET")
        def do_POST(self): self._dispatch("POST")
        def do_OPTIONS(self): self._send(403, {"error": "CORS não habilitado."})
    return Handler


def create_server(app: Application, ui_path: Path, port: int | None = None):
    # Cannot be bound to 0.0.0.0 through a request or config parameter.
    server = ThreadingHTTPServer(("127.0.0.1", app.settings.port if port is None else port), make_handler(app, ui_path))
    server.daemon_threads = True
    return server


def serve(app: Application, ui_path: Path):
    lock = app.settings.home / "server.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PolicyError("server.lock existente. Encerre a outra instância; se houve queda, confirme que não há processo ativo antes de remover o arquivo.") from exc
    os.write(fd, str(os.getpid()).encode("ascii"))
    os.close(fd)
    try:
        server = create_server(app, ui_path)
        app.start()
        print(f"LocalAuthor: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"Token em {app.settings.home / 'api.token'} (ou use o comando token).", flush=True)
        print("Modo: plataforma local + laboratório CPU; modelo programador não qualificado.", flush=True)
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            app.close()
    finally:
        lock.unlink(missing_ok=True)
