#!/usr/bin/env python3
"""Project-local setup, compile, upload and monitor. Setup/build never flash a board."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.json").read_text())
LOCAL = ROOT / "local"
CLI = LOCAL / "bin/arduino-cli"
CONFIG = LOCAL / "arduino-cli.yaml"
VENDOR = LOCAL / "waveshare"
GFX = VENDOR / "examples/arduino/libraries/GFX_Library_for_Arduino"
PYTHON = ROOT / ".venv/bin/python"


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download(url, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256(destination) == expected:
        return
    temp = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {destination.name}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as source, temp.open("wb") as target:
        shutil.copyfileobj(source, target)
    if sha256(temp) != expected:
        raise RuntimeError(f"Checksum mismatch: {temp}; not using this download.")
    temp.replace(destination)


def arduino(*args):
    return run([CLI, "--config-file", CONFIG, *args])


def setup():
    key = platform.system() + "-" + platform.machine()
    if key not in LOCK["cli_assets"]:
        raise RuntimeError("Setup supports macOS and Linux; see docs/SETUP.md for manual IDE settings.")
    suffix, checksum = LOCK["cli_assets"][key]
    version = LOCK["arduino_cli"]
    archive = LOCAL / "arduino-cli.tar.gz"
    download(f"https://github.com/arduino/arduino-cli/releases/download/v{version}/"
             f"arduino-cli_{version}_{suffix}.tar.gz", archive, checksum)
    CLI.parent.mkdir(parents=True, exist_ok=True)
    # Extract only the known executable, never arbitrary archive paths.
    with tarfile.open(archive) as bundle, CLI.open("wb") as output:
        source = bundle.extractfile("arduino-cli")
        if source is None:
            raise RuntimeError("Arduino CLI archive contains no executable")
        shutil.copyfileobj(source, output)
    CLI.chmod(0o755)
    config = {
        "board_manager": {"additional_urls": ["https://espressif.github.io/arduino-esp32/package_esp32_index.json"]},
        "directories": {name: str(LOCAL / "arduino" / name)
                        for name in ("data", "downloads", "user")}}
    CONFIG.write_text(json.dumps(config, indent=2) + "\n")

    revision = LOCK["waveshare_commit"]
    if not VENDOR.exists():
        run(["git", "init", VENDOR])
        run(["git", "-C", VENDOR, "remote", "add", "origin", LOCK["waveshare_repository"]])
        run(["git", "-C", VENDOR, "sparse-checkout", "init", "--cone"])
        run(["git", "-C", VENDOR, "sparse-checkout", "set",
             "examples/arduino/libraries/GFX_Library_for_Arduino",
             "examples/arduino/libraries/Mylibrary", "examples/arduino/01_HelloWorld"])
        run(["git", "-C", VENDOR, "fetch", "--depth", "1", "--filter=blob:none", "origin", revision])
        run(["git", "-C", VENDOR, "checkout", "--detach", revision])
    actual = run(["git", "-C", VENDOR, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if actual != revision:
        raise RuntimeError("Existing vendor checkout differs from dependencies.json; keep it and resolve before building.")
    run(["git", "-C", VENDOR, "diff", "--exit-code", "HEAD", "--",
         "examples/arduino/libraries/GFX_Library_for_Arduino"])
    factory = LOCK["factory_file"]
    download(f"https://raw.githubusercontent.com/waveshareteam/ESP32-S3-Touch-AMOLED-1.75/"
             f"{revision}/firmware/{factory}", LOCAL / "recovery" / factory,
             LOCK["factory_sha256"])
    arduino("core", "update-index")
    arduino("core", "install", LOCK["arduino_core"])
    print("Setup ready. Factory recovery image checksum verified. No device was accessed.")


def build(vendor_example=False):
    if not CLI.exists() or not GFX.exists():
        raise RuntimeError("Run python3 tools/project.py setup first.")
    sketch = VENDOR / "examples/arduino/01_HelloWorld" if vendor_example else ROOT / "firmware/DigitalVinyl"
    output = ROOT / "build" / ("vendor-hello" if vendor_example else "firmware")
    args = ["compile", "--fqbn", LOCK["fqbn"], "--library", str(GFX),
            "--build-path", str(output)]
    if vendor_example:
        args.extend(["--library", str(VENDOR / "examples/arduino/libraries/Mylibrary")])
    arduino(*args, str(sketch))
    if not vendor_example:
        manifest = {"dependencies": LOCK, "source_sha256": {
            str(p.relative_to(ROOT)): sha256(p) for p in sorted(sketch.iterdir()) if p.is_file()},
            "binaries_sha256": {p.name: sha256(p) for p in sorted(output.glob("*.bin"))}}
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verified_backup(directory):
    directory = Path(directory)
    record = json.loads((directory / "VERIFIED.json").read_text())
    binary = directory / "factory.bin"
    if (record.get("matching_reads") != 2 or record.get("bytes") != 16777216
            or binary.stat().st_size != 16777216 or sha256(binary) != record.get("sha256")):
        raise RuntimeError("Backup is missing, damaged or not a full 16 MiB verified copy.")
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "build", "vendor-check", "ports"):
        commands.add_parser(name)
    for name in ("upload", "monitor", "restore"):
        sub = commands.add_parser(name)
        sub.add_argument("--port", required=True)
        if name in ("upload", "restore"):
            sub.add_argument("--backup", type=Path, default=ROOT / "backups/factory-first")
    args = parser.parse_args()
    if args.command == "setup": setup()
    elif args.command == "build": build()
    elif args.command == "vendor-check": build(vendor_example=True)
    elif args.command == "ports": arduino("board", "list")
    elif args.command == "monitor":
        arduino("monitor", "--port", args.port, "--config", "baudrate=115200")
    elif args.command == "upload":
        verified_backup(args.backup)
        build()  # Always upload a fresh build of the current source.
        arduino("upload", "--fqbn", LOCK["fqbn"], "--port", args.port,
                "--input-dir", str(ROOT / "build/firmware"), str(ROOT / "firmware/DigitalVinyl"))
    elif args.command == "restore":
        binary = verified_backup(args.backup)
        if not PYTHON.exists():
            raise RuntimeError("Install the pinned Python tools first; see README.")
        run([PYTHON, "-m", "esptool", "--chip", "esp32s3", "--port", args.port,
             "--baud", "460800", "write-flash", "0x0", binary])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f"Stopped: {error}")
