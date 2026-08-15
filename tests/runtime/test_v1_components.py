import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
M1 = REPO_ROOT / "runtime" / "agentteams" / "m1"

SCHEMA = {
    "$id": "agentfit.samplesetmanifest/v1",
    "type": "object",
    "required": ["schema_version", "manifest_name", "contract_status", "membership", "set_hash"],
    "properties": {
        "schema_version": {"const": "agentfit.samplesetmanifest/v1"},
        "manifest_name": {"enum": ["adaptation", "validation", "sealed_holdout", "stress_and_failure"]},
        "contract_status": {"enum": ["instantiated", "not_instantiated"]},
        "not_instantiated_reason": {"type": "string", "minLength": 1},
        "membership": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["sample_id", "source_ref", "content_sha256", "membership_state"],
                "properties": {
                    "sample_id": {"type": "string", "minLength": 1},
                    "content_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            },
        },
        "set_hash": {
            "type": "object",
            "required": ["method", "member_order", "set_model_sha256"],
            "properties": {
                "set_model_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
        },
        "freeze_state": {"type": "object", "required": ["state"]},
    },
    "allOf": [
        {"if": {"properties": {"contract_status": {"const": "not_instantiated"}}},
         "then": {"required": ["not_instantiated_reason"]}},
    ],
}


def manifest(name="adaptation", **overrides):
    doc = {
        "schema_version": "agentfit.samplesetmanifest/v1",
        "manifest_name": name,
        "purpose": name,
        "contract_status": "instantiated",
        "freeze_state": {"state": "not_instantiated"},
        "membership": [{
            "sample_id": "0",
            "source_ref": "tau2-bench/v1.0.1:retail/tasks.json#task-0",
            "content_sha256": "a" * 64,
            "entity_group": None,
            "membership_state": "proposed",
        }],
        "set_hash": {
            "method": "sha256(concat(source_record_sha256) over lexicographic ascending sample_id)",
            "member_order": ["0"],
            "set_model_sha256": "b" * 64,
        },
        "access_policy": "team",
        "isolation_rules": "entity-group",
    }
    doc.update(overrides)
    return doc


class LifecycleTest(unittest.TestCase):
    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lifecycle", M1 / "lifecycle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_valid_manifest_passes(self):
        lc = self.load()
        self.assertEqual([], lc.validate(manifest(), SCHEMA))

    def test_missing_required_fails(self):
        lc = self.load()
        doc = manifest()
        del doc["set_hash"]
        errors = lc.validate(doc, SCHEMA)
        self.assertTrue(any("set_hash" in e for e in errors))

    def test_conditional_reason_enforced(self):
        lc = self.load()
        doc = manifest(contract_status="not_instantiated")
        errors = lc.validate(doc, SCHEMA)
        self.assertTrue(any("not_instantiated_reason" in e for e in errors))

    def test_bad_hash_pattern_fails(self):
        lc = self.load()
        doc = manifest()
        doc["set_hash"]["set_model_sha256"] = "xyz"
        errors = lc.validate(doc, SCHEMA)
        self.assertTrue(any("pattern" in e for e in errors))

    def test_transition_table(self):
        lc = self.load()
        self.assertTrue(lc.transition_allowed("Freeze", "Architect"))
        self.assertFalse(lc.transition_allowed("Intake", "Architect"))
        self.assertTrue(lc.transition_allowed("Learn", "Discover"))

    def test_freeze_gate_requires_audit_pass(self):
        lc = self.load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifests = root / "manifests.json"
            bundle = {
                "manifests": {
                    "adaptation": manifest("adaptation"),
                    "validation": manifest("validation"),
                    "stress_and_failure": manifest("stress_and_failure"),
                    "sealed_holdout": manifest("sealed_holdout", contract_status="not_instantiated",
                                               not_instantiated_reason="no sealed evidence"),
                }
            }
            manifests.write_text(json.dumps(bundle), encoding="utf-8")
            audit = root / "audit.json"
            audit.write_text(json.dumps({
                "verdict": "PASS",
                "minimum_next_action": "proceed_to_freeze_review",
            }), encoding="utf-8")
            result = lc.freeze_gate(manifests, audit, schema_path=write_schema(root))
            self.assertTrue(result["freeze_ready"], result)
            audit.write_text(json.dumps({"verdict": "FAIL",
                                         "minimum_next_action": "fix"}), encoding="utf-8")
            result2 = lc.freeze_gate(manifests, audit, schema_path=write_schema(root))
            self.assertFalse(result2["freeze_ready"])


def write_schema(root: Path) -> Path:
    path = root / "schema.json"
    path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    return path


class LedgerTest(unittest.TestCase):
    def load(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("ledger", M1 / "ledger.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_append_and_verify_chain(self):
        ld = self.load()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.json"
            r1 = ld.append(path, ld.build_record("r1", "Discover", {"events": 10}, [], [], {}))
            r2 = ld.append(path, ld.build_record("r2", "Freeze", {"events": 8}, [], [], {}))
            self.assertIsNone(r1["prev_record_sha256"])
            self.assertEqual(r1["record_sha256"], r2["prev_record_sha256"])
            self.assertEqual([], ld.verify_chain(ld.load_ledger(path)))

    def test_tampered_record_breaks_chain(self):
        ld = self.load()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.json"
            ld.append(path, ld.build_record("r1", "Discover", {}, [], [], {}))
            ledger = ld.load_ledger(path)
            ledger["records"][0]["metrics"]["events"] = 999  # 篡改
            path.write_text(json.dumps(ledger), encoding="utf-8")
            errors = ld.verify_chain(ld.load_ledger(path))
            self.assertTrue(any("self hash mismatch" in e for e in errors))

    def test_append_refuses_on_broken_chain(self):
        ld = self.load()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.json"
            ld.append(path, ld.build_record("r1", "Discover", {}, [], [], {}))
            ledger = ld.load_ledger(path)
            ledger["records"][0]["round_id"] = "tampered"
            path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaises(SystemExit):
                ld.append(path, ld.build_record("r2", "Freeze", {}, [], [], {}))


class ReportTest(unittest.TestCase):
    def test_report_renders_self_contained_html(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "conversation.json").write_text(json.dumps([
                {"sender": "@agentfit-engagement-lead:x", "room": "team",
                 "origin_server_ts": 1786720000000, "body": "delegation"},
                {"sender": "@agentfit-business-engineer:x", "room": "team",
                 "origin_server_ts": 1786720060000, "body": "AGENTFIT-r5-x\nfinal"},
            ]), encoding="utf-8")
            (run_dir / "usage-before.json").write_text(json.dumps(
                {"totals": {"call_count": 10, "total_tokens": 1000}}), encoding="utf-8")
            (run_dir / "usage-after.json").write_text(json.dumps(
                {"totals": {"call_count": 30, "total_tokens": 5000}}), encoding="utf-8")
            ledger = root / "ledger.json"
            result = subprocess.run(
                ["python3", str(M1 / "report.py"),
                 "--run-dir", str(run_dir), "--run-id", "r5",
                 "--ledger", str(ledger), "--output", str(root / "report.html")],
                capture_output=True, text=True, cwd=REPO_ROOT)
            self.assertEqual(0, result.returncode, result.stderr)
            html_text = (root / "report.html").read_text(encoding="utf-8")
            for probe in ("AgentFit Round Report", "Role swimlane",
                          "engagement-lead", "business-engineer", "4000"):
                self.assertIn(probe, html_text)
            self.assertNotIn("http://", html_text)  # 自包含:无外部资源


if __name__ == "__main__":
    unittest.main()
