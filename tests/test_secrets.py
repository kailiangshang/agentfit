"""密钥守护：任何被 git 跟踪的文件出现 API key 模式即失败。

防止 .env 类敏感信息被意外 add/commit（配合 .gitignore 双保险）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),          # OpenAI / DeepSeek 风格
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]"),
]


def test_no_secrets_in_tracked_files():
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.splitlines()
    assert tracked, "git ls-files 为空，测试环境异常"
    violations = []
    for rel in tracked:
        path = REPO / rel
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".pdf", ".pptx", ".zip"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            m = pattern.search(content)
            if m:
                violations.append(f"{rel}: 命中 {m.group(0)[:12]}…")
    assert not violations, "检测到疑似密钥泄漏：\n" + "\n".join(violations)
