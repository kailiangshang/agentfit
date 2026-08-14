import re
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "runtime" / "agentteams" / "m1" / "agentfit-retail-m1.yaml"


class AgentFitM1ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        cls.documents = list(yaml.safe_load_all(cls.text)) if cls.text else []

    def setUp(self):
        self.assertTrue(self.documents, f"missing M1 manifest: {MANIFEST}")
        teams = [document for document in self.documents if document["kind"] == "Team"]
        self.assertEqual(1, len(teams), "M1 must declare exactly one Team")
        self.assertIn("leader", teams[0]["spec"], "v1.1.2 Team requires spec.leader")
        self.assertIn("workers", teams[0]["spec"], "v1.1.2 Team requires spec.workers")

    def test_declares_one_v112_team_and_one_human(self):
        kinds = [document["kind"] for document in self.documents]

        self.assertEqual(0, kinds.count("Worker"))
        self.assertEqual(1, kinds.count("Team"))
        self.assertEqual(1, kinds.count("Human"))
        self.assertEqual(2, len(kinds))
        for document in self.documents:
            self.assertEqual("hiclaw.io/v1beta1", document["apiVersion"])

    def test_team_members_freeze_runtime_model_and_identity_contracts(self):
        team = next(document for document in self.documents if document["kind"] == "Team")
        leader = team["spec"]["leader"]
        workers = {worker["name"]: worker for worker in team["spec"]["workers"]}
        expected_workers = {
            "agentfit-business-engineer",
            "agentfit-agent-architect",
            "agentfit-validation-engineer",
            "agentfit-governance-auditor",
        }

        self.assertEqual("agentfit-engagement-lead", leader["name"])
        self.assertEqual("aliyun-qwen3.7-max", leader["model"])
        self.assertEqual("Running", leader["state"])
        self.assertIn("You are an AI Agent, not a human", leader["soul"])
        self.assertIn("Never reveal API keys", leader["soul"])
        self.assertTrue(leader["identity"].strip())
        self.assertEqual(expected_workers, set(workers))
        for name, worker in workers.items():
            with self.subTest(name=name):
                self.assertEqual("copaw", worker["runtime"])
                self.assertEqual("aliyun-qwen3.7-max", worker["model"])
                self.assertEqual("Running", worker["state"])
                self.assertIn("You are an AI Agent, not a human", worker["soul"])
                self.assertIn("Never reveal API keys", worker["soul"])
                self.assertTrue(worker["identity"].strip())

    def test_team_has_one_leader_and_four_workers(self):
        team = next(document for document in self.documents if document["kind"] == "Team")

        self.assertEqual("agentfit-retail-m1", team["metadata"]["name"])
        self.assertEqual("agentfit-engagement-lead", team["spec"]["leader"]["name"])
        self.assertEqual(4, len(team["spec"]["workers"]))
        self.assertFalse(team["spec"]["peerMentions"])

    def test_human_is_scoped_to_the_m1_team(self):
        human = next(document for document in self.documents if document["kind"] == "Human")

        self.assertEqual("agentfit-owner", human["metadata"]["name"])
        self.assertEqual(2, human["spec"]["permissionLevel"])
        self.assertEqual(["agentfit-retail-m1"], human["spec"]["accessibleTeams"])
        self.assertNotIn("email", human["spec"])

    def test_role_boundaries_are_explicit(self):
        team = next(document for document in self.documents if document["kind"] == "Team")
        souls = {team["spec"]["leader"]["name"]: team["spec"]["leader"]["soul"]}
        souls.update({worker["name"]: worker["soul"] for worker in team["spec"]["workers"]})

        self.assertIn("do not replace the responsibility artifacts", souls["agentfit-engagement-lead"])
        self.assertIn("must not generate a Candidate", souls["agentfit-business-engineer"])
        self.assertIn("four immutable SampleSetManifest", souls["agentfit-agent-architect"])
        self.assertIn("must remain BLOCKED", souls["agentfit-agent-architect"])
        self.assertIn("preflight is not a Candidate", souls["agentfit-validation-engineer"])
        self.assertIn("only after Candidate freeze", souls["agentfit-governance-auditor"])
        self.assertNotRegex(
            self.text,
            re.compile(r"(?i)(?:api[_-]?key|password|bearer)\s*[:=]\s*[^<\s][^\s]{7,}"),
        )


if __name__ == "__main__":
    unittest.main()
