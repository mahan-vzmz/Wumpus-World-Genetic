from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_WEIGHTS = ROOT / "best_weights.json"
PACKAGED_WEIGHTS = ROOT / "src" / "wumpus_world" / "data" / "best_weights.json"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not ROOT_WEIGHTS.exists():
        print(f"Error: Root weights file missing: {ROOT_WEIGHTS}", file=sys.stderr)
        sys.exit(1)

    PACKAGED_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_WEIGHTS, PACKAGED_WEIGHTS)

    root_hash = sha256_file(ROOT_WEIGHTS)
    packaged_hash = sha256_file(PACKAGED_WEIGHTS)

    if root_hash != packaged_hash:
        print(f"Error: Weight synchronization failed ({root_hash} != {packaged_hash})", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully synchronized packaged weights: {root_hash[:12]}")


if __name__ == "__main__":
    main()
