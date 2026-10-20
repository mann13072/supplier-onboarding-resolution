"""Stage only backend source; keep local environments out of the Worker bundle."""
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parent.parent
target = ROOT / ".wrangler" / "backend"
(target / "app").mkdir(parents=True, exist_ok=True)
copy2(ROOT / "worker.py", target / "worker.py")
for source in (ROOT / "app").glob("*.py"):
    copy2(source, target / "app" / source.name)
