from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_WEIGHTS = ROOT / "best_weights.json"
PACKAGED_WEIGHTS = ROOT / "src" / "wumpus_world" / "data" / "best_weights.json"


def canonical_json_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
    except Exception:
        return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize or check packaged genetic weights.")
    parser.add_argument("--check", action="store_true", help="Only verify weight sync without modifying files.")
    args = parser.parse_args()

    if not ROOT_WEIGHTS.exists():
        print(f"Error: Root weights file missing: {ROOT_WEIGHTS}", file=sys.stderr)
        sys.exit(1)

    root_hash = canonical_json_sha256(ROOT_WEIGHTS)
    packaged_hash = canonical_json_sha256(PACKAGED_WEIGHTS)

    if args.check:
        if root_hash != packaged_hash:
            print(
                f"Error: Packaged weights out of sync with root ({root_hash[:12]} != {packaged_hash[:12]}).",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Packaged weights are cleanly synchronized ({root_hash[:12]}).")
        return

    PACKAGED_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT_WEIGHTS, PACKAGED_WEIGHTS)

    root_hash = canonical_json_sha256(ROOT_WEIGHTS)
    packaged_hash = canonical_json_sha256(PACKAGED_WEIGHTS)

    if root_hash != packaged_hash:
        print(f"Error: Weight synchronization failed ({root_hash} != {packaged_hash})", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully synchronized packaged weights: {root_hash[:12]}")


if __name__ == "__main__":
    main()
