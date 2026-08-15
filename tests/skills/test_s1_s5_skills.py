import hashlib
import json
import subprocess
import tempfile
import unittest
from typing import Optional
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
S1 = REPO_ROOT / "skills" / "s1-task-compile" / "compute_set_hashes.py"
S5 = REPO_ROOT / "skills" / "s5-independent-audit" / "verify_manifests.py"

# Known-answer vectors recorded from the real R4 run (retail-home-r4).
R4_EXPECTED = {
    "adaptation": "b3ac22a957dfbeefa8e8b433d5fda469583fb541ce3c80b7d7807fee4bae470c",
    "validation": "e6762160c86d8b5f1e80afec15e4c123ef60bf4c53c70e270a64b31ac86abb30",
    "stress_and_failure": "dbe4a824f3e0746bc954d2861385d882e0ca8a18c9a7f234a3ccde10b97424d8",
}


def sample(sample_id: str, salt: str) -> dict:
    return {
        "sample_id": sample_id,
        "sample_class": "public_official",
        "source_ref": f"tau2-bench/v1.0.1:retail/tasks.json#task-{sample_id}",
        "source_record_sha256": hashlib.sha256(salt.encode()).hexdigest(),
        "source_material": {"summary": salt},
        "exposure_policy": "meta_team_only",
    }


def batch_doc(ids_and_salts: dict[str, str]) -> dict:
    return {
        "schema_version": "agentfit.projectcase-source-batch/v1",
        "source_version": "tau2-bench/v1.0.1",
        "task_ids": sorted(ids_and_salts, key=lambda s: (len(s), s)),
        "answer_material": "stripped",
        "samples": [sample(i, s) for i, s in ids_and_salts.items()],
    }


def build_batch(ids_and_salts: dict[str, str], root: Path) -> Path:
    path = root / "samples.json"
    path.write_text(json.dumps(batch_doc(ids_and_salts)), encoding="utf-8")
    return path


class SkillContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(script), *args],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

    def test_r4_known_answer_vectors_reproduced(self) -> None:
        ids = {
            "0": "alpha", "5": "beta", "15": "gamma", "20": "delta",
            "25": "eps", "30": "zeta", "45": "eta", "60": "theta",
        }
        batch = self.root / "r4.json"
        batch.write_text(
            json.dumps(json.loads(
                Path(
                    ".local-demo/retail-m1/agentteams/round-home-r4/samples.json"
                ).read_text(encoding="utf-8")
            )),
            encoding="utf-8",
        ) if Path(
            ".local-demo/retail-m1/agentteams/round-home-r4/samples.json"
        ).is_file() else None
        if batch.exists() is False or batch.stat().st_size == 0:
            batch = build_batch(ids, self.root)
            self.skipTest("R4 private evidence absent; KAT requires the real batch")
        result = self.run_script(
            S1,
            "--batch", str(batch),
            "--members", "adaptation=0,20,45",
            "--members", "validation=5,15,30",
            "--members", "stress_and_failure=25,60",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        for name, expected in R4_EXPECTED.items():
            self.assertEqual(
                expected, output["manifests"][name]["set_model_sha256"], name
            )
        self.assertEqual(
            "not_instantiated", output["manifests"]["sealed_holdout"]["status"]
        )
        self.assertEqual([], output["unassigned_sample_ids"])

    def test_cross_manifest_duplicate_is_rejected(self) -> None:
        batch = build_batch({"1": "a", "2": "b"}, self.root)
        result = self.run_script(
            S1, "--batch", str(batch),
            "--members", "adaptation=1", "--members", "validation=1,2",
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("more than one manifest", result.stderr)

    def test_batch_schema_drift_is_rejected(self) -> None:
        path = self.root / "drift.json"
        path.write_text(json.dumps({"schema_version": "other/v9"}), encoding="utf-8")
        result = self.run_script(S1, "--batch", str(path), "--members", "adaptation=1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("schema drift", result.stderr)

    def make_manifest_bundle(self, root: Path, ids: dict[str, str],
                             memberships: dict[str, list[str]],
                             entity: Optional[dict] = None,
                             tamper: Optional[str] = None) -> Path:
        records = {i: sample(i, salt) for i, salt in ids.items()}
        manifests = {}
        for name, members in memberships.items():
            concat = "".join(
                records[i]["source_record_sha256"] for i in sorted(members)
            )
            set_hash = hashlib.sha256(concat.encode("ascii")).hexdigest()
            if tamper == name:
                set_hash = "0" * 64
            manifests[name] = {
                "schema_version": "agentfit.samplesetmanifest/v1",
                "manifest_name": name,
                "purpose": name,
                "contract_status": "instantiated",
                "freeze_state": {"state": "not_instantiated"},
                "membership": [
                    {
                        "sample_id": i,
                        "source_ref": records[i]["source_ref"],
                        "content_sha256": records[i]["source_record_sha256"],
                        "entity_group": (entity or {}).get(i),
                        "membership_state": "proposed",
                    }
                    for i in members
                ],
                "set_hash": {
                    "method": "sha256(concat(source_record_sha256) over lexicographic ascending sample_id)",
                    "member_order": sorted(members),
                    "set_model_sha256": set_hash,
                },
                "access_policy": "team",
                "isolation_rules": "entity-group",
            }
        manifests["sealed_holdout"] = {
            "contract_status": "not_instantiated",
            "not_instantiated_reason": "no sealed evidence supplied",
        }
        path = root / "manifests.json"
        path.write_text(json.dumps({"manifests": manifests}), encoding="utf-8")
        return path

    def test_s5_passes_a_consistent_bundle(self) -> None:
        ids = {"1": "a", "2": "b", "3": "c"}
        batch = build_batch(ids, self.root)
        manifests = self.make_manifest_bundle(
            self.root, ids, {"adaptation": ["1"], "validation": ["2"], "stress_and_failure": ["3"]}
        )
        result = self.run_script(S5, "--batch", str(batch), "--manifests", str(manifests))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("PASS", output["verdict"])
        self.assertEqual("proceed_to_freeze_review", output["minimum_next_action"])

    def test_s5_detects_tampered_set_hash(self) -> None:
        ids = {"1": "a", "2": "b"}
        batch = build_batch(ids, self.root)
        manifests = self.make_manifest_bundle(
            self.root, ids, {"adaptation": ["1"], "validation": ["2"]}, tamper="adaptation"
        )
        result = self.run_script(S5, "--batch", str(batch), "--manifests", str(manifests))
        self.assertEqual(1, result.returncode)
        output = json.loads(result.stdout)
        self.assertEqual("FAIL", output["verdict"])
        self.assertTrue(
            any(c["check"] == "adaptation.set_hash_match" for c in output["checks"])
        )

    def test_s5_detects_entity_spanning_splits(self) -> None:
        ids = {"1": "a", "2": "b"}
        batch = build_batch(ids, self.root)
        manifests = self.make_manifest_bundle(
            self.root, ids,
            {"adaptation": ["1"], "validation": ["2"]},
            entity={"1": "G-X", "2": "G-X"},
        )
        result = self.run_script(S5, "--batch", str(batch), "--manifests", str(manifests))
        self.assertEqual(1, result.returncode)
        output = json.loads(result.stdout)
        self.assertTrue(
            any(c["check"].endswith("no_entity_span") and c["result"] == "FAIL"
                for c in output["checks"])
        )


if __name__ == "__main__":
    unittest.main()
