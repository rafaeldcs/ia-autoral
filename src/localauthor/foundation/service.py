"""One LocalAuthor service, separate compatible local engines per capability."""
from __future__ import annotations

import base64
import hashlib
import io
import os
from pathlib import Path
import threading
import uuid

from ..errors import PolicyError
from .context import build_context, markdown_evidence
from .experience import ExperienceStore
from .models import ModelSpec, child, identifier, local_path
from .runtime import ImageRuntime, TextRuntime, check_cancel

MAX_ARTIFACT_BYTES = 256_000_000


class FoundationService:
    def __init__(self, home: Path, *, text_factory=TextRuntime, image_factory=ImageRuntime):
        self.home = Path(home)
        self.factories = {"text": text_factory, "image": image_factory}
        self._cache = {}
        self._lock = threading.RLock()

    def status(self) -> dict:
        base = local_path(self.home / "foundation")
        return {"capabilities": {kind: {"registered": (base / f"{kind}-model.json").is_file(),
                "loaded": kind in self._cache} for kind in self.factories},
                "remote_fallback": False, "weights_trained_here": False,
                "image_understanding": False, "generated_code_execution": False}

    def _engine(self, kind: str, cancel=None):
        check_cancel(cancel)
        spec = ModelSpec.load(self.home / "foundation" / f"{kind}-model.json", kind)
        cached = self._cache.get(kind)
        if cached and cached[0].manifest_sha256 == spec.manifest_sha256:
            if spec.signature() != cached[1]:
                self._cache.pop(kind, None)
                raise PolicyError("Arquivos de modelo mudaram durante a sessão. Reinicie após revisão.")
            return cached[0], cached[2]
        self._cache.pop(kind, None)
        signature = spec.verify()
        check_cancel(cancel)
        engine = self.factories[kind](spec)
        check_cancel(cancel)
        if spec.signature() != signature:
            raise PolicyError("O modelo mudou durante o carregamento.")
        self._cache[kind] = (spec, signature, engine)
        return spec, engine

    def answer(self, project_id: str, message: str, history: list[dict], evidence: list[dict],
               cancel=None, *, input_format: str = "text") -> dict:
        project_id = identifier(project_id)
        with self._lock:
            spec, engine = self._engine("text", cancel)
            notes = markdown_evidence(self.home / "foundation" / "knowledge" / project_id, message, project_id)
            context = build_context(message, history, [*evidence, *notes], scope=project_id,
                       count=engine.count, context_tokens=spec.context_tokens, output_tokens=spec.output_tokens)
            content, truncated = engine.generate(context.messages, cancel)
            check_cancel(cancel)
            if not isinstance(content, str) or not content.strip():
                raise PolicyError("O modelo local não produziu conteúdo válido.")
            result = {"origin": "foundation_text", "content": content, "sources": [],
                "model": spec.provenance(), "evidence": context.evidence,
                "input_tokens": context.input_tokens, "history_used": bool(context.history_used),
                "history_messages_used": context.history_used,
                "omitted_history": context.omitted_history, "omitted_evidence": context.omitted_evidence,
                "possibly_truncated": truncated,
                "notice": "Modelo local de origem registrada. Código não executado nem aplicado. "
                          "Memória não é treinamento; nenhuma experiência foi autorizada para treino automaticamente."}
            if truncated:
                result["notice"] += " Saída possivelmente incompleta: limite de tokens atingido."
            metadata = {k: v for k, v in result.items() if k != "content"}
            metadata["generation_context"] = context.messages
            result["experience_id"] = ExperienceStore(self.home).record(project_id,
                "code" if input_format == "code" else "text", message, content, metadata)
            return result

    def create_image(self, project_id: str, prompt: str, cancel=None, *, options=None) -> dict:
        from .visual import ImageOptions, verify_png
        profile = ImageOptions.parse(options)
        project_id = identifier(project_id)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
            raise PolicyError("Descrição de imagem vazia ou excessiva.")
        with self._lock:
            spec, engine = self._engine("image", cancel)
            image = engine.generate(prompt, cancel) if options is None else engine.generate(prompt, cancel, options=profile.metadata())
            check_cancel(cancel)
            if getattr(image, "size", None) != (profile.width, profile.height):
                raise PolicyError("Pipeline retornou dimensões inesperadas.")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            raw = buffer.getvalue()
            verify_png(raw, (profile.width, profile.height))
            base = local_path(self.home / "foundation" / "artifacts")
            used = 0
            def fail_walk(error):
                raise PolicyError("Não foi possível verificar a quota de imagens.") from error
            for directory, folders, names in os.walk(base, onerror=fail_walk, followlinks=False) if base.exists() else []:
                for name in folders + names:
                    item = local_path(Path(directory) / name)
                    if item.is_file():
                        used += item.stat().st_size
            if used + len(raw) > MAX_ARTIFACT_BYTES:
                raise PolicyError("Quota local de imagens atingida; revise os artefatos antes de continuar.")
            run_id = uuid.uuid4().hex
            path = child(self.home / "foundation" / "artifacts", f"{project_id}/{run_id}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            result = {"origin": "foundation_image", "content": "Imagem gerada pelo LocalAuthor com o modelo visual local registrado.",
                "sources": [], "model": spec.provenance(), "artifact_id": run_id,
                "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                **profile.metadata(),
                "notice": "Geração visual não é capacidade do Nemotron textual. Revise a imagem; não houve treinamento nem edição dos seus arquivos."}
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                check_cancel(cancel)
                ExperienceStore(self.home).record(project_id, "image", prompt, result["content"],
                    {k: v for k, v in result.items() if k != "content"}, run_id=run_id)
            except Exception:
                path.unlink(missing_ok=True)
                raise
            result["experience_id"] = run_id
            return result

    def image(self, project_id: str, run_id: str) -> dict:
        project_id, run_id = identifier(project_id), identifier(run_id)
        row = ExperienceStore(self.home).get(project_id, run_id)
        if row["kind"] != "image":
            raise PolicyError("Esta experiência não contém imagem.")
        path = child(self.home / "foundation" / "artifacts", f"{project_id}/{run_id}.png")
        try:
            with path.open("rb") as stream:
                raw = stream.read(8000001)
        except OSError as exc:
            raise PolicyError("Artefato removido ou indisponível.") from exc
        if (len(raw) > 8000000 or not raw.startswith(b"\x89PNG\r\n\x1a\n")
                or hashlib.sha256(raw).hexdigest() != row["metadata"].get("artifact_sha256")):
            raise PolicyError("Integridade da imagem não confere.")
        from .visual import verify_png
        verify_png(raw, (row["metadata"]["width"], row["metadata"]["height"]))
        return {"data": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
                "sha256": row["metadata"]["artifact_sha256"]}
