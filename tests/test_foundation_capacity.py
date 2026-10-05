"""Capacity arithmetic and fail-closed evidence; no checkpoint capability claims."""
from copy import deepcopy
import unittest

from localauthor.errors import PolicyError
from localauthor.foundation.capacity import assess, preflight
from localauthor.foundation.models import read_object, write_new
from tests.helpers import WorkspaceCase


def fixtures():
    return ({"schema": 1, "model_id": "original/fixture", "revision": "a" * 40,
             "sources": ["https://example.org/fixture"], "weights_bytes": 1000,
             "additional_weight_copies": 2, "additional_disk_overhead_bytes": 200,
             "required_ram_bytes": 500, "gpu_profiles": []},
            {"schema": 1, "total_ram_bytes": 1500, "available_ram_bytes": 500,
             "free_disk_bytes": 2200, "gpus": []})


class CapacityTests(unittest.TestCase):
    def test_capacity_boundary_does_not_authorize_or_qualify_model(self):
        req, hw = fixtures()
        result = assess(req, hw)
        self.assertEqual(result["status"], "capacity-only")
        self.assertEqual(result["additional_disk_bytes_required"], 2200)
        self.assertFalse(result["acquisition_authorized"])
        self.assertFalse(result["qualification_suite"])

    def test_both_ram_and_disk_shortfalls_are_recorded(self):
        req, hw = fixtures()
        hw.update(available_ram_bytes=499, free_disk_bytes=2199)
        self.assertEqual(assess(req, hw)["blockers"], ["insufficient_disk", "insufficient_available_ram"])

    def test_gpu_memory_is_per_matching_device_not_summed_with_ram(self):
        req, hw = fixtures()
        req["gpu_profiles"] = [{"family": "B200", "count": 4, "minimum_memory_bytes_each": 1000}]
        hw["total_ram_bytes"] = hw["available_ram_bytes"] = 100000
        hw["gpus"] = [{"family": "RTX2060", "memory_bytes": 100000}]
        self.assertIn("no_matching_gpu_profile", assess(req, hw)["blockers"])
        hw["gpus"] = [{"family": "B200", "memory_bytes": 1000} for _ in range(3)]
        hw["gpus"].append({"family": "B200", "memory_bytes": 999})
        self.assertIn("no_matching_gpu_profile", assess(req, hw)["blockers"])
        hw["gpus"][-1]["memory_bytes"] = 1000
        self.assertEqual(assess(req, hw)["status"], "capacity-only")

    def test_alternative_homogeneous_gpu_profiles(self):
        req, hw = fixtures()
        req["gpu_profiles"] = [{"family": "B200", "count": 4, "minimum_memory_bytes_each": 1000},
                               {"family": "H100", "count": 8, "minimum_memory_bytes_each": 500}]
        hw["gpus"] = [{"family": "H100", "memory_bytes": 500} for _ in range(8)]
        self.assertEqual(assess(req, hw)["gpu_profile_matches"], [req["gpu_profiles"][1]])

    def test_existing_weights_zero_additional_copies_still_need_runtime_memory(self):
        req, hw = fixtures()
        req.update(additional_weight_copies=0, additional_disk_overhead_bytes=0)
        hw.update(free_disk_bytes=0, available_ram_bytes=499)
        self.assertEqual(assess(req, hw)["blockers"], ["insufficient_available_ram"])

    def test_rejects_invalid_or_missing_budget_instead_of_defaulting_to_zero(self):
        req, hw = fixtures()
        for field in ("weights_bytes", "additional_weight_copies", "additional_disk_overhead_bytes", "required_ram_bytes"):
            for value in (None, True, -1, 1.0, "1000"):
                changed = deepcopy(req); changed[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(PolicyError): assess(changed, hw)
        hw["available_ram_bytes"] = hw["total_ram_bytes"] + 1
        with self.assertRaises(PolicyError): assess(req, hw)

    def test_requires_immutable_revision_sources_and_valid_gpu_inventory(self):
        req, hw = fixtures()
        for field, value in (("revision", "main"), ("sources", []), ("schema", True),
                             ("gpu_profiles", [{"family": "B200", "count": True, "minimum_memory_bytes_each": 1}])):
            changed = deepcopy(req); changed[field] = value
            with self.subTest(field=field), self.assertRaises(PolicyError): assess(changed, hw)
        hw["gpus"] = [{"family": "B200", "memory_bytes": False}]
        with self.assertRaises(PolicyError): assess(req, hw)

    def test_rejects_joined_urls_and_sources_with_credentials(self):
        req, hw = fixtures()
        for source in ("https://one.example/a https://two.example/b", "https://user:private@example.org", "https://"):
            req["sources"] = [source]
            with self.subTest(source=source), self.assertRaises(PolicyError): assess(req, hw)


class CapacityEvidenceTests(WorkspaceCase):
    def test_report_hashes_inputs_and_never_overwrites_existing_evidence(self):
        req, hw = fixtures()
        requirements = self.root / "requirements.json"; hardware = self.root / "hardware.json"
        report = self.root / "capacity.json"
        write_new(requirements, req); write_new(hardware, hw)
        result = preflight(requirements, hardware, report)
        self.assertEqual(read_object(report), result)
        self.assertEqual(len(result["requirements_sha256"]), 64)
        original = report.read_bytes()
        with self.assertRaises(FileExistsError): preflight(requirements, hardware, report)
        self.assertEqual(report.read_bytes(), original)
