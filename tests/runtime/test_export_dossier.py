import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "runtime" / "agentteams" / "m1" / "export_dossier.py"


class ExportDossierTest(unittest.TestCase):
    def test_exports_required_shared_artifacts_with_hash_manifest(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            shared = root / "shared"
            project = shared / "projects" / "project-1"
            business = shared / "tasks" / "business-1"
            governance = shared / "tasks" / "governance-1" / "workspace"
            project.mkdir(parents=True)
            business.mkdir(parents=True)
            governance.mkdir(parents=True)
            for name in ("meta.json", "plan.md", "result.md"):
                (project / name).write_text("{}" if name.endswith(".json") else name)
            for name, schema in (
                ("sample-semantic-spec.json", "SampleSemanticSpec"),
                ("task-semantic-spec.json", "TaskSemanticSpec"),
                ("capability-semantic-spec.json", "CapabilitySemanticSpec"),
                ("sample-set-manifests.json", "SampleSetManifestContracts"),
            ):
                (business / name).write_text(json.dumps({"schema_name": schema}))
            (governance / "governance_review.md").write_text("BLOCK")

            fake = root / "docker"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import os, shutil, sys\n"
                "from pathlib import Path\n"
                "args=sys.argv[1:]\n"
                "if args[0]=='inspect': raise SystemExit(0)\n"
                "if args[0]!='cp': raise SystemExit(64)\n"
                "source=args[1].split(':',1)[1]\n"
                "rel=source.split('/shared/',1)[1].removesuffix('/.')\n"
                "src=Path(os.environ['FAKE_SHARED_ROOT'])/rel\n"
                "dst=Path(args[2]); dst.mkdir(parents=True, exist_ok=True)\n"
                "for item in src.iterdir():\n"
                "    target=dst/item.name\n"
                "    shutil.copytree(item,target) if item.is_dir() else shutil.copy2(item,target)\n",
                encoding="utf-8",
            )
            fake.chmod(0o700)
            team = root / "team.json"
            team.write_text(
                json.dumps({"leaderName": "agentfit-engagement-lead"}),
                encoding="utf-8",
            )
            output = root / "dossier"
            environment = os.environ.copy()
            environment["FAKE_SHARED_ROOT"] = str(shared)

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--container-command",
                    str(fake),
                    "--team-file",
                    str(team),
                    "--project-id",
                    "project-1",
                    "--business-task-id",
                    "business-1",
                    "--governance-task-id",
                    "governance-1",
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((output / "business" / "sample-semantic-spec.json").is_file())
            self.assertTrue(
                (output / "governance" / "workspace" / "governance_review.md").is_file()
            )
            manifest = json.loads(
                (output / "export-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual("project-1", manifest["project_id"])
            self.assertIn(
                "business/sample-semantic-spec.json", manifest["artifact_sha256"]
            )
            for path in output.rglob("*"):
                expected = 0o700 if path.is_dir() else 0o600
                self.assertEqual(expected, path.stat().st_mode & 0o777, path)

            unsafe_output = REPO_ROOT / "docs" / ".agentfit-unsafe-export-test"
            self.addCleanup(shutil.rmtree, unsafe_output, True)
            unsafe = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--container-command",
                    str(fake),
                    "--team-file",
                    str(team),
                    "--project-id",
                    "project-1",
                    "--business-task-id",
                    "business-1",
                    "--governance-task-id",
                    "governance-1",
                    "--output-dir",
                    str(unsafe_output),
                ],
                cwd=REPO_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, unsafe.returncode)
            self.assertIn(".local-demo", unsafe.stderr)


if __name__ == "__main__":
    unittest.main()
