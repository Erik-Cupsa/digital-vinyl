#!/usr/bin/env python3
"""Prepare a private, paired unpacked extension; never installs it into Chrome."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bridge'))
from server import token


def main():
    destination = ROOT / 'local/chrome-extension'
    destination.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / 'extension').iterdir():
        if source.is_file():
            shutil.copy2(source, destination / source.name)
    config = destination / 'config.js'
    config.touch(mode=0o600, exist_ok=True)
    config.chmod(0o600)
    config.write_text('const DIGITAL_VINYL_TOKEN = ' + repr(token()) + ';\n')
    print('Paired extension prepared. In chrome://extensions, load unpacked from:')
    print(destination)
    print('Keep this generated directory private. Reload it in Chrome after code updates.')


if __name__ == '__main__':
    main()
