"""Operator-only atomic model pointer changes with recoverable journals."""
from contextlib import contextmanager
import os
from pathlib import Path
import uuid

from ..errors import PolicyError
from .models import ModelSpec, digest, local_path, read_object, write_new


def replace_json(path: Path, data: dict):
    temporary = local_path(path.parent / (uuid.uuid4().hex + ".json"))
    try:
        write_new(temporary, data)
        # Windows _commit/fsync rejects a read-only descriptor (errno 9).
        # This is our newly created temporary file, opened writable before the
        # atomic replacement; the previous active pointer remains untouched.
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, local_path(path))
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def registry_lock(home: Path):
    home = local_path(home)
    if (home / "server.lock").exists():
        raise PolicyError("Pare o servidor antes da troca do modelo.")
    root = local_path(home / "foundation")
    root.mkdir(parents=True, exist_ok=True)
    lock = local_path(root / "promotion.lock")
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.close(fd)
        yield root
    finally:
        lock.unlink(missing_ok=True)


def promote(home: Path, candidate: Path, evaluation: Path, approval: Path, kind: str = "text") -> dict:
    if kind not in {"text", "image"}:
        raise PolicyError("Capacidade inválida.")
    candidate, evaluation, approval = map(local_path, (candidate, evaluation, approval))
    spec = ModelSpec.load(candidate, kind)
    spec.verify()
    report, decision = read_object(evaluation), read_object(approval)
    if (report.get("status") != "passed" or report.get("candidate_manifest_sha256") != digest(candidate)
            or report.get("critical_failures") != 0 or report.get("omitted") != 0
            or report.get("criteria_frozen") is not True or report.get("real_checkpoint") is not True):
        raise PolicyError("Avaliação real completa e sem falha crítica é obrigatória.")
    if kind == "text":
        if (report.get("kind") != "base-candidate-comparison" or report.get("same_conditions") is not True
                or report.get("regressions") != [] or type(report.get("total")) is not int or report["total"] < 1
                or type(report.get("passed")) is not int or not 0 <= report["passed"] <= report["total"]
                or type(report.get("baseline_passed")) is not int or report["passed"] < report["baseline_passed"]
                or not isinstance(report.get("results"), list) or len(report["results"]) != report["total"]
                or report.get("qualification_suite") is not True):
            raise PolicyError("Promoção requer qualificação completa, comparação com a base e ausência de regressões.")
        ids = [r.get("id") for r in report["results"]]
        if (len(set(ids)) != len(ids) or sum(r.get("passed") is True for r in report["results"]) != report["passed"]
                or any(r.get("passed") is not True and r.get("critical") for r in report["results"])):
            raise PolicyError("Resultados incompletos ou contagem de acertos divergente.")
    if (decision.get("decision") != "approved" or not isinstance(decision.get("human"), str)
            or not decision["human"].strip() or not decision.get("scope")
            or decision.get("candidate_manifest_sha256") != digest(candidate)
            or decision.get("evaluation_sha256") != digest(evaluation)):
        raise PolicyError("Promoção exige autorização humana ligada ao candidato e avaliação exatos.")
    with registry_lock(home) as root:
        active = local_path(root / f"{kind}-model.json")
        previous = read_object(active) if active.exists() else None
        if previous is not None:
            ModelSpec.load(active, kind).verify()
            if kind == "text" and report.get("base_manifest_sha256") != digest(active):
                raise PolicyError("A versão ativa mudou desde a comparação; avalie novamente.")
        journal = root / "promotions" / (uuid.uuid4().hex + ".json")
        record = {"schema": 1, "kind": kind, "previous": previous, "candidate": read_object(candidate),
                  "candidate_manifest_sha256": digest(candidate), "evaluation_sha256": digest(evaluation),
                  "approval_sha256": digest(approval), "human": decision["human"], "scope": decision["scope"], "state": "prepared"}
        write_new(journal, record)
        # A crash before/after replace leaves one complete pointer and a durable
        # previous manifest. Recover checks the actual pointer, not the stage flag.
        replace_json(active, record["candidate"])
        ModelSpec.load(active, kind).verify()
        record["state"] = "activated"
        replace_json(journal, record)
        return {"journal": str(journal), "active_manifest_sha256": digest(active), "rollback_available": previous is not None}


def rollback(home: Path, journal: Path) -> dict:
    record = read_object(local_path(journal))
    if record.get("schema") != 1 or record.get("kind") not in {"text", "image"} or record.get("previous") is None:
        raise PolicyError("Journal não contém versão anterior restaurável.")
    with registry_lock(home) as root:
        journal = local_path(journal)
        if journal.parent != root / "promotions":
            raise PolicyError("Journal pertence a outra instalação.")
        active = local_path(root / f"{record['kind']}-model.json")
        current = read_object(active)
        if current not in (record["candidate"], record["previous"]):
            raise PolicyError("Versão ativa mudou desde este journal; não sobrescrever outra promoção.")
        preserved = root / "promotions" / (uuid.uuid4().hex + ".previous.json")
        write_new(preserved, record["previous"])
        ModelSpec.load(preserved, record["kind"]).verify()
        replace_json(active, record["previous"])
        record["state"] = "rolled_back"
        replace_json(journal, record)
        return {"rolled_back": True, "active_manifest_sha256": digest(active)}
