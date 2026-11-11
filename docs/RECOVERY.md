# Keep the factory demo recoverable

**First, film the real factory demo.** No board has been flashed by this project.
The vendor factory recovery file is available locally after setup, and its SHA-256
has been checked. It may differ from the exact firmware shipped on your unit, so
make your own backup too. Neither recovery route has been physically tested here.

## Install the backup tools

The local `.venv` is already prepared. For a new checkout, use Python 3.12:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
```

If you use `uv`, `uv venv --python 3.12 .venv` followed by
`uv pip sync --python .venv/bin/python requirements.lock` is equivalent.

## Check and copy the board

Close serial monitors. Set the port to the one actually reported on your computer:

```sh
BOARD_PORT='/dev/cu.YOUR_ACTUAL_PORT'
.venv/bin/python -m esptool --chip esp32s3 --port "$BOARD_PORT" flash-id
.venv/bin/python -m esptool --chip esp32s3 --port "$BOARD_PORT" get-security-info
```

Confirm ESP32-S3 and **16 MB**. If the detected hardware differs, or security info
reports secure boot, encryption or disabled download/read access, stop and check
vendor recovery instructions. Do not use `--force` or change eFuses. Connecting
can reset the board; these commands do not write firmware.

For the identified, readable 16 MiB board:

```sh
.venv/bin/python tools/backup_factory.py \
  --port "$BOARD_PORT" --bytes 16777216 \
  --board 'Waveshare ESP32-S3-Touch-AMOLED-1.75' \
  --output backups/factory-first
```

The helper reads all flash twice, without running the factory app between reads.
It creates `VERIFIED.json` only when both full-size files have matching SHA-256
hashes. It never writes board flash and refuses to overwrite an existing backup
directory. Keep a second private copy of that directory. On failure, keep partial
files, power-cycle with BOOT released and diagnose before retrying into a new folder.

A flash dump may include device settings or credentials. `backups/`, `local/` and
`.bin` files are ignored by Git. Do not share the backup. It excludes eFuses,
external SD media and other chips.

## Restore your exact original demo

Use the **same board** and a verified backup. Close monitors, then explicitly run:

```sh
python3 tools/project.py restore --port "$BOARD_PORT"
```

The helper checks the saved size/hash, then writes the full image at address zero.
Esptool verifies the write. This replaces the installed Digital Vinyl project and its flash
data. Power-cycle afterward and visually confirm the original demo. Flash copying
is not a general recovery guarantee for encrypted/protected devices.

## Vendor fallback

Setup downloads Waveshare's complete 16 MiB image to:

```text
local/recovery/ESP32-S3-Touch-AMOLED-1.75-FactoryOnly-260805.bin
```

Its expected SHA-256 is:

```text
2b7e01ff1f37027385a3820e006f945464cfcee2a05954b3239cf75f250080b6
```

If your backup is unavailable and this is the confirmed board, check that hash
before writing the vendor image:

```sh
shasum -a 256 local/recovery/ESP32-S3-Touch-AMOLED-1.75-FactoryOnly-260805.bin
.venv/bin/python -m esptool --chip esp32s3 --port "$BOARD_PORT" --baud 460800 \
  write-flash --flash-mode dio --flash-size 16MB --flash-freq 80m 0x0 \
  local/recovery/ESP32-S3-Touch-AMOLED-1.75-FactoryOnly-260805.bin
```

Use one complete image; do not mix bootloader/partition files from different builds.
If connection fails, hold BOOT while connecting USB, release, then re-list ports.
The vendor image is a fallback demo, not proof of an exact match to your original.
No full-flash erase is required for these normal writes.

Sources: [Waveshare firmware delivery guide](https://github.com/waveshareteam/ESP32-S3-Touch-AMOLED-1.75/blob/e4344e70c2fa78a13e8a06566507f1ba8af6672a/firmware/README.md),
[official flashing instructions](https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-1.75/Firmware-Flashing),
and [Espressif flash commands](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html).

## Switch between episode one and episode two

Stop the bridge and close serial monitors first. Keep one verified **original**
backup for this same board; do not overwrite it when changing projects. If that
backup is in the adjacent Pocket Eyes checkout, from Digital Vinyl run:

```sh
python3 tools/project.py upload --port "$BOARD_PORT" \
  --backup ../esp32-pocket-eyes/backups/factory-first
```

To return to Pocket Eyes, run from the Pocket Eyes checkout:

```sh
python3 tools/project.py upload --port "$BOARD_PORT"
```

To return to the exact saved factory image, run from Digital Vinyl:

```sh
python3 tools/project.py restore --port "$BOARD_PORT" \
  --backup ../esp32-pocket-eyes/backups/factory-first
```

These are alternative firmware uploads, not a dual-boot menu. Each upload replaces
the active application. A successful checksum proves the saved bytes agree; it
does not prove a physical restore has been tried. The backup gate verifies the
file, not the identity of the currently connected device. Use only its original
board. If its factory firmware was already overwritten without a backup, the
vendor image is a fallback, not recovery of that exact shipped state.
