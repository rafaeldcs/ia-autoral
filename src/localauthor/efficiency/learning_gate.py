"""Fail-closed candidate assessment. It does not train or promote any weights.

A report is an attestation by a trusted local evaluator, not self-authentication.
Hash strings record identity; they do not prove execution or grant data rights.
"""
from __future__ import annotations

import math
import re

from ..errors import PolicyError

HASH = re.compile(r"[a-f0-9]{64}")
IDENTITY = ("checkpoint_sha256", "suite_sha256", "runner_sha256", "environment_sha256", "dataset_sha256")


def finite_number(value, name: str, *, positive=False) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise PolicyError(f"Métrica inválida: {name}.")
    return float(value)


def validate_report(report: dict) -> None:
    if not isinstance(report, dict) or type(report.get("schema")) is not int or report["schema"] != 1:
        raise PolicyError("Relatório de avaliação inválido.")
    for name in IDENTITY:
        if not isinstance(report.get(name), str) or not HASH.fullmatch(report[name]):
            raise PolicyError(f"Identidade/hash ausente: {name}.")
    for field in ("real_model_execution", "rights_reviewed", "human_reviewed"):
        if type(report.get(field)) is not bool:
            raise PolicyError(f"Decisão explícita ausente: {field}.")
    if not isinstance(report.get("reviewed_by"), str) or not report["reviewed_by"].strip():
        raise PolicyError("Revisor não informado.")
    if type(report.get("safety_failures")) is not int or report["safety_failures"] < 0:
        raise PolicyError("Contagem de segurança inválida.")
    finite_number(report.get("elapsed_seconds"), "elapsed_seconds", positive=True)
    finite_number(report.get("peak_ram_bytes"), "peak_ram_bytes", positive=True)
    outcomes = report.get("outcomes")
    if not isinstance(outcomes, dict) or not outcomes or len(outcomes) > 100000:
        raise PolicyError("Avaliação sem casos individuais ou excessiva.")
    if any(not isinstance(k, str) or not HASH.fullmatch(k) or type(v) is not bool for k, v in outcomes.items()):
        raise PolicyError("Cada resultado deve ligar hash do problema a um booleano.")
    training = report.get("training_problem_hashes")
    if not isinstance(training, list) or len(training) > 1000000:
        raise PolicyError("Inventário de problemas de treino ausente/excessivo.")
    if any(not isinstance(v, str) or not HASH.fullmatch(v) for v in training):
        raise PolicyError("Hash de problema de treino inválido.")


def assess_candidate(baseline: dict, candidate: dict, *, minimum_cases: int = 50,
                     minimum_gain: float = 0.01, max_slowdown: float = 1.2,
                     max_ram_growth: float = 1.0) -> dict:
    validate_report(baseline)
    validate_report(candidate)
    if type(minimum_cases) is not int or minimum_cases < 1:
        raise PolicyError("Mínimo de casos inválido.")
    minimum_gain = finite_number(minimum_gain, "minimum_gain")
    if minimum_gain > 1:
        raise PolicyError("Ganho deve estar entre zero e um.")
    max_slowdown = finite_number(max_slowdown, "max_slowdown", positive=True)
    max_ram_growth = finite_number(max_ram_growth, "max_ram_growth", positive=True)
    reasons = []
    for label, report in (("baseline", baseline), ("candidate", candidate)):
        for field in ("real_model_execution", "rights_reviewed", "human_reviewed"):
            if not report[field]:
                reasons.append(f"{label}:{field}=false")
        if set(report["training_problem_hashes"]) & set(report["outcomes"]):
            reasons.append(f"{label}:holdout_contaminated")
    for field in ("suite_sha256", "runner_sha256", "environment_sha256"):
        if baseline[field] != candidate[field]:
            reasons.append(f"comparison:{field}_mismatch")
    if baseline["checkpoint_sha256"] == candidate["checkpoint_sha256"]:
        reasons.append("candidate:checkpoint_unchanged")
    if set(baseline["outcomes"]) != set(candidate["outcomes"]):
        reasons.append("comparison:case_set_mismatch")
    cases = len(candidate["outcomes"])
    if cases < minimum_cases:
        reasons.append("candidate:insufficient_cases")
    # Reject leakage across either run, not just within the candidate manifest.
    evaluation = set(baseline["outcomes"]) | set(candidate["outcomes"])
    training = set(baseline["training_problem_hashes"]) | set(candidate["training_problem_hashes"])
    if evaluation & training:
        reasons.append("comparison:cross_run_holdout_contamination")
    before = sum(baseline["outcomes"].values()) / len(baseline["outcomes"])
    after = sum(candidate["outcomes"].values()) / cases
    gain = after - before
    if gain + 1e-12 < minimum_gain:
        reasons.append("candidate:quality_gain_below_threshold")
    if candidate["safety_failures"]:
        reasons.append("candidate:safety_failures")
    if candidate["elapsed_seconds"] > baseline["elapsed_seconds"] * max_slowdown:
        reasons.append("candidate:latency_regression")
    if candidate["peak_ram_bytes"] > baseline["peak_ram_bytes"] * max_ram_growth:
        reasons.append("candidate:ram_regression")
    return {"schema": 1, "eligible_for_human_promotion": not reasons,
            "reasons": reasons, "cases": cases, "baseline_accuracy": before,
            "candidate_accuracy": after, "absolute_gain": gain,
            "weights_modified": False, "automatically_promoted": False,
            "statistical_significance_established": False,
            "near_duplicate_leakage_checked": False}
