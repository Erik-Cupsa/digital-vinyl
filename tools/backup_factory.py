#!/usr/bin/env python3
"""Read flash twice without booting the app between reads. Never writes flash."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys


def backup(port, size, board, output):
    if not port or not board.strip() or size < 1024 * 1024 or size % (1024 * 1024):
        raise ValueError("Supply a port, board model and verified whole-MiB flash size.")
    output = Path(output)
    # Exclusive directory creation prevents replacing the only factory copy.
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    first, second = output / "factory.bin", output / "factory-second.bin"
    prefix = [sys.executable, "-m", "esptool", "--port", port, "--baud", "460800"]
    subprocess.run(prefix + ["--after", "no-reset", "read-flash", "0", str(size),
                            str(first)], check=True)
    # The first command leaves the chip in download mode: factory NVS cannot
    # change between the two reads. The second returns it to normal boot.
    subprocess.run(prefix + ["--before", "no-reset", "--after", "hard-reset",
                            "read-flash", "0", str(size), str(second)], check=True)
    if first.stat().st_size != size or second.stat().st_size != size:
        raise ValueError("Backup size mismatch. No verification record was created.")
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    if hashlib.sha256(second.read_bytes()).hexdigest() != digest:
        raise ValueError("The two reads differ. Keep both; do not upload yet.")
    record = {"board_label": board, "port": port, "bytes": size,
              "sha256": digest, "esptool": "5.1.0", "matching_reads": 2,
              "restoration_tested": False,
              "note": "Flash only; excludes eFuses, external SD and other chips."}
    (output / "VERIFIED.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Two reads match: {first} ({size} bytes). Recovery not yet tested.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--bytes", type=lambda s: int(s, 0), required=True,
                        help="Full capacity from flash-id, in bytes; no guessed default")
    parser.add_argument("--board", required=True, help="Identified board model/revision")
    parser.add_argument("--output", type=Path, required=True,
                        help="New private directory, normally backups/factory-first")
    args = parser.parse_args()
    if importlib.metadata.version("esptool") != "5.1.0":
        parser.error("Install the pinned requirements.lock into .venv first.")
    try:
        backup(args.port, args.bytes, args.board, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Backup incomplete: {error}\nKeep any files; do not upload yet.\n")


if __name__ == "__main__":
    main()
