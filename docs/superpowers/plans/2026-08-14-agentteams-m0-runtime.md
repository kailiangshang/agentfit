# AgentTeams M0 Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare and verify a no-image-build AgentTeams v1.1.2 runtime path for AgentFit without exposing model credentials or claiming that the AgentFit loop has run.

**Architecture:** AgentTeams runs from official pinned prebuilt images. AgentFit keeps runtime helpers and declarative assets as tracked source, while credentials, platform state, generated packages, and raw run evidence stay below ignored `.local-demo/agentteams/`. M0 ends only after installation and version/status readback; absent LiteLLM configuration leaves it `IN_PROGRESS`.

**Tech Stack:** Python 3 standard library, Bash, Docker Engine/Compose, AgentTeams v1.1.2 installer, `unittest`.

## Global Constraints

- Do not run `docker build`, `make install`, or set any `AGENTTEAMS_INSTALL_*_IMAGE` override.
- Pin `AGENTTEAMS_VERSION=v1.1.2` and use the official registry selected by the AgentTeams installer.
- Keep API keys and passwords out of tracked files, process output, Git diffs, and evidence files.
- Use `/home/shangkailiang/workspace/sigen-agent-team/AgentTeams/install/agentteams-install.sh` rather than downloading an unreviewed installer at runtime.
- Keep AgentTeams persistent state under `agentfit/.local-demo/agentteams/platform/`.
- Do not claim M0 complete until the installed controller returns version and status evidence.
- Do not claim M1 or an AgentFit closed loop from platform preflight evidence.

---

### Task 1: Deterministic M0 environment preflight

**Files:**
- Create: `runtime/agentteams/preflight.py`
- Test: `tests/runtime/test_agentteams_preflight.py`

**Interfaces:**
- Consumes: AgentTeams checkout path, pinned version, Docker CLI, host resource information.
- Produces: `run_preflight(repo: Path, version: str, runner: Runner) -> PreflightReport` and a JSON CLI report that never contains environment variable values.

- [ ] **Step 1: Write failing tests**

Cover healthy Docker/repository/image checks, missing Docker daemon, wrong Git tag, insufficient resources, and secret redaction. Use a fake command runner so tests do not require Docker or network.

- [ ] **Step 2: Verify RED**

Run: `python3 -m unittest tests.runtime.test_agentteams_preflight -v`

Expected: import failure because `runtime.agentteams.preflight` does not exist.

- [ ] **Step 3: Implement the minimal preflight**

Define immutable `CheckResult` and `PreflightReport` dataclasses, a subprocess-backed runner, deterministic checks, JSON serialization, and CLI arguments `--agentteams-repo`, `--version`, and `--output`. Report only whether `AGENTTEAMS_LLM_API_KEY`, `AGENTTEAMS_OPENAI_BASE_URL`, and `AGENTTEAMS_DEFAULT_MODEL` are configured.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m unittest tests.runtime.test_agentteams_preflight -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add runtime/agentteams/preflight.py tests/runtime/test_agentteams_preflight.py
git commit -m "feat: add AgentTeams runtime preflight"
```

### Task 2: Prebuilt-image installer wrapper

**Files:**
- Create: `runtime/agentteams/install-prebuilt.sh`
- Create: `runtime/agentteams/private.env.example`
- Test: `tests/runtime/test_install_prebuilt.py`

**Interfaces:**
- Consumes: ignored private env file containing `AGENTTEAMS_LLM_API_KEY`, `AGENTTEAMS_OPENAI_BASE_URL`, and `AGENTTEAMS_DEFAULT_MODEL`.
- Produces: sanitized `--check` output or an invocation of the pinned upstream installer with root-mode persistence and no local image overrides.

- [ ] **Step 1: Write failing tests**

Assert that the wrapper rejects a missing or overly permissive private file, placeholders, absent variables, a version other than `v1.1.2`, and every `AGENTTEAMS_INSTALL_*_IMAGE` variable. Assert that `--check` prints names/status only and never prints the key.

- [ ] **Step 2: Verify RED**

Run: `python3 -m unittest tests.runtime.test_install_prebuilt -v`

Expected: failure because the wrapper does not exist.

- [ ] **Step 3: Implement the wrapper and example**

The wrapper resolves the repository root, validates that the private file is ignored and mode `0600`, sources it without shell tracing, exports `AGENTTEAMS_NON_INTERACTIVE=1`, `AGENTTEAMS_VERSION=v1.1.2`, `AGENTTEAMS_ROOT_DIR=<repo>/.local-demo/agentteams/platform`, and `AGENTTEAMS_LOCAL_ONLY=1`, then executes the reviewed sibling installer. `--check` stops before any mutation.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m unittest tests.runtime.test_install_prebuilt -v`

Expected: all tests pass and no test output contains the fixture key.

- [ ] **Step 5: Commit**

```bash
git add runtime/agentteams/install-prebuilt.sh runtime/agentteams/private.env.example tests/runtime/test_install_prebuilt.py
git commit -m "feat: add pinned prebuilt AgentTeams installer"
```

### Task 3: Canonical runtime guide and status alignment

**Files:**
- Create: `runtime/agentteams/README.md`
- Modify: `docs/guides/home-demo-runbook.md`
- Modify: `docs/agentfit-solution.md`
- Test: `tests/runtime/test_runtime_docs.py`

**Interfaces:**
- Consumes: the preflight and installer commands from Tasks 1-2.
- Produces: one canonical M0 entrypoint and truthful `AUTHORIZED / IN_PROGRESS` status language.

- [ ] **Step 1: Write failing documentation-contract tests**

Require the guide to state the hybrid runtime boundary, pinned version, no-build rule, private configuration path, exact preflight/check/install/status commands, and M0/M1 evidence boundary. Reject `docker build`, keys, and claims that M0/M1 is complete.

- [ ] **Step 2: Verify RED**

Run: `python3 -m unittest tests.runtime.test_runtime_docs -v`

Expected: failure because the canonical runtime guide is absent and status still says `NOT_STARTED`.

- [ ] **Step 3: Write and align the docs**

Make `runtime/agentteams/README.md` the operational entrypoint. Change the solution and home Demo guide only where authorization/runtime mode changed; keep formal Candidate and sealed-holdout gates unchanged.

- [ ] **Step 4: Verify GREEN and full documentation tests**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest competition/2026-08-15/submission/test_submission_contract.py -v
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [ ] **Step 5: Commit**

```bash
git add runtime/agentteams/README.md docs/guides/home-demo-runbook.md docs/agentfit-solution.md tests/runtime/test_runtime_docs.py
git commit -m "docs: authorize AgentTeams M0 runtime"
```

### Task 4: Execute the local M0 gate

**Files:**
- Create ignored: `.local-demo/agentteams/preflight.json`
- Create ignored: `.local-demo/agentteams/private.env`
- Create ignored after install: `.local-demo/agentteams/platform/**`
- Create ignored after install: `.local-demo/agentteams/evidence/{version.txt,status.json,containers.txt}`

**Interfaces:**
- Consumes: user-provided LiteLLM-compatible base URL, model ID, and API key in the private file.
- Produces: verified AgentTeams version/status and container evidence, or an explicit M0 blocker without partial success claims.

- [ ] **Step 1: Run public preflight**

```bash
python3 runtime/agentteams/preflight.py \
  --agentteams-repo ../AgentTeams \
  --version v1.1.2 \
  --output .local-demo/agentteams/preflight.json
```

Expected now: infrastructure/image checks pass and private model configuration is reported missing without revealing values.

- [ ] **Step 2: Stop at the credential gate when configuration is absent**

Copy `private.env.example` to ignored `.local-demo/agentteams/private.env`, set mode `0600`, and leave values for the owner to provide locally. Do not invent, search for, or print credentials.

- [ ] **Step 3: Validate configuration without mutation**

```bash
runtime/agentteams/install-prebuilt.sh --check
```

Expected: pinned version, local-only mode, root directory, and `configured` statuses only.

- [ ] **Step 4: Install and read back evidence after configuration exists**

```bash
runtime/agentteams/install-prebuilt.sh
python3 runtime/agentteams/preflight.py \
  --agentteams-repo ../AgentTeams \
  --version v1.1.2 \
  --output .local-demo/agentteams/preflight-post-install.json
```

Then use the controller-internal CLI supported by the installed version to record version and status. M0 remains `IN_PROGRESS` if either readback fails.

- [ ] **Step 5: Review secret boundary and commit only tracked source**

```bash
git status --short --ignored
git diff --check
```

Expected: private configuration, platform state, and raw evidence are ignored; tracked worktree is clean after the three task commits.
