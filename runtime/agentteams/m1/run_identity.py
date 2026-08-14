"""Generate and validate run-bound terminal identities."""

from __future__ import annotations

import re
import secrets


RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
NONCE = re.compile(r"[0-9a-f]{32}")


def require_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("run id must contain only safe path-independent characters")
    return run_id


def new_terminal_prefix(run_id: str) -> str:
    run_id = require_run_id(run_id)
    return f"AGENTFIT-{run_id}-{secrets.token_hex(16)}"


def require_run_terminal_prefix(run_id: str, prefix: str) -> str:
    run_id = require_run_id(run_id)
    expected = f"AGENTFIT-{run_id}-"
    nonce = prefix[len(expected) :] if isinstance(prefix, str) and prefix.startswith(expected) else ""
    if not NONCE.fullmatch(nonce):
        raise ValueError("terminal prefix is not a run-bound run_id plus 128-bit nonce")
    return prefix
