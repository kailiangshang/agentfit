import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (str(ROOT / "src"), str(ROOT), str(ROOT / "tests" / "test_scenarios")):
    if p not in sys.path:
        sys.path.insert(0, p)
plugins_path = str(ROOT)
if plugins_path not in sys.path:
    sys.path.insert(0, plugins_path)
