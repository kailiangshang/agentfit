# Contributing to AgentFit

## Repository rules

- Every active artifact has one canonical stable name and is edited in place. Git history records evolution.
- Do not add parallel draft, stage, final, or numbered copies of source, docs, Skills, manifests, examples, or deployment objects.
- Protocol, dependency, release-package, and immutable run-evidence versions are compatibility or evidence identities and are allowed.
- Never modify `competition/2026-08-16/submission/`; it is the already-submitted preliminary-round archive.
- Keep AgentTeams, τ²-bench, LiteLLM, and vendor-specific imports under `bridges/`. The core package must remain platform-independent.

## Development workflow

1. Read `docs/architecture.md` and `docs/development-plan.md`.
2. Add a focused failing test for every behavior change.
3. Implement the smallest change that makes the test pass.
4. Run the focused test, then the complete suite.
5. Regenerate `bridges/agentteams/team.yaml` through `render_team.py`; do not edit copied Skill content manually.
6. Keep real runs in separate ignored output directories and preserve their manifests and hashes.

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
pytest -q
python bridges/agentteams/render_team.py --check
python -m compileall -q src bridges tests
git diff --check
```

## Evidence and claims

- A simulator pass is not real-model evidence.
- A bridge fixture pass is not a completed external run.
- An Active Team is not a completed task.
- A report may only claim results that can be recomputed from persisted Episodes and traces.
- Mark missing, blocked, unverified, and not-run states explicitly.

## Changes to contracts

Changes to Sample, Manifest, EvaluationIdentity, Solution, Human Gate, RunStore, or package schemas require:

- compatibility impact in the commit description;
- tests for serialization and rejection paths;
- updated architecture text when the normative contract changes;
- bridge fixture updates for every affected external system.
