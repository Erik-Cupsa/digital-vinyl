# First setup and daily use

## 1. Start with the board as it arrived

You need the Waveshare ESP32-S3-Touch-AMOLED-1.75, your Mac and a **data-capable USB
cable**. The screen is built in; no soldering or jumper wires are needed. Leave the
battery disconnected until connector and polarity are checked. Place the board on
a nonmetal surface and connect USB without holding buttons. Allow the accessory
if macOS asks. Observe and film the factory demo before replacing any firmware.

The Mac builds the program; uploading writes it into the board's flash memory.
Simply plugging in USB does not upload a program. Build success alone does not
prove that the physical display works.

## 2. Prepare the computer

On the prepared development Mac, `.venv`, the toolchain and recovery file are
already present. On a clean checkout, install Python 3.12 and Git, then run:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
python3 tools/project.py setup
python3 tools/project.py build
```

With `uv` already installed, these first two commands are equivalent:

```sh
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python requirements.lock
```

Run all commands from the repository directory. Setup uses `local/` rather than
changing global Arduino libraries. A fresh toolchain takes several GB. The prepared
workspace shares its tool cache with Pocket Eyes; a clean clone is independent.
The CLI is the tested path; Arduino IDE is optional. Node.js and a C++ compiler
are only needed to run `make check`, not to use the bridge.

Equivalent Arduino settings: ESP32S3 Dev Module, Espressif core **3.3.10**, flash
16 MB, **16M Flash (3MB APP/9.9MB FATFS)**, OPI PSRAM, Hardware CDC and JTAG,
USB CDC on boot enabled, UART0 / Hardware CDC upload. Use the pinned bundled
`local/waveshare/examples/arduino/libraries/GFX_Library_for_Arduino` library.
Sketch: `firmware/DigitalVinyl/DigitalVinyl.ino`. Exact FQBN is in `dependencies.json`.

## 3. Identify the port and preserve the original firmware

List ports before and after connecting the board:

```sh
python3 tools/project.py ports
```

Use the newly appearing device, normally `/dev/cu.usbmodem…` on macOS. Do not use
Bluetooth-Incoming-Port or debug-console. If no device appears, try a known data
cable and a direct Mac port. Follow [RECOVERY.md](RECOVERY.md) to check the chip and
make a verified backup **before the first upload**. If Pocket Eyes already has a
verified factory backup of this exact board, reuse it.

## 4. Install Digital Vinyl on the board

Close serial monitors and stop the bridge with Ctrl-C before uploading. Replace
the port placeholder with the detected port. For this project's own backup:

```sh
python3 tools/project.py upload --port /dev/cu.YOUR_ACTUAL_PORT
```

Or reuse the original Pocket Eyes backup in an adjacent checkout:

```sh
python3 tools/project.py upload --port /dev/cu.YOUR_ACTUAL_PORT \
  --backup ../esp32-pocket-eyes/backups/factory-first
```

If the bootloader is needed, hold **BOOT while connecting USB**, release it, list
ports again and use the new port. After flashing, unplug/replug USB with BOOT
released if it remains in download mode. The normal boot screen should show the
record and **WAITING**. Tap BOOT to toggle live waiting ↔ labeled rehearsal. PWR
controls power; it is not a generic reset or animation button.

## 5. Prepare and load the Chrome connector

Start in preview-only mode so music synchronization can be checked separately:

```sh
.venv/bin/python tools/prepare_extension.py
.venv/bin/python bridge/server.py
```

The preparation command prints the full extension directory, without printing its
token. It creates a private paired build; it does not install browser software.

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**, choose **Load unpacked**, and select the printed
   `local/chrome-extension` directory. On macOS's folder chooser, Cmd-Shift-G lets
   you paste the full path. Select the generated directory, not `extension/`.
3. Pin Digital Vinyl from Chrome's extensions menu if convenient.
4. Open or reload `https://music.youtube.com/` after installing.
5. Open Digital Vinyl's popup while that music tab is active. Click **Connect
   this tab**, then play a track.
6. Open `http://127.0.0.1:8766/`. Leave **Live** selected. Check the current cover,
   title, play/pause, and changing tracks. The popup also shows bridge status.

The extension requests access to `music.youtube.com` to read player metadata,
loopback `127.0.0.1` to reach the local bridge, and session storage to remember the
chosen tab. Chrome host patterns cannot restrict loopback to a single port; the
code fixes requests to port 8766. There is no cookies, history, debugger, broad
all-sites or remote-code permission. This is an unpacked local extension, not a
Chrome Web Store release. Only install code you have reviewed and trust.

Chrome's official [local installation guide](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world)
explains Load unpacked. No Apple Events JavaScript setting or remote debugging
port is needed.

## 6. Connect live music to the physical display

Stop the preview-only bridge with Ctrl-C, then restart it with the explicit port:

```sh
.venv/bin/python bridge/server.py --port /dev/cu.YOUR_ACTUAL_PORT
```

The bridge probes for `DVY1 READY` before sending binary frames. The desktop
preview reports whether that handshake succeeded. Music should start the record,
pause should let it coast, and the next track should replace the center artwork.
The board displays the cover and a small state label; title and artist are shown
in the desktop preview, not rendered on the board.

To start the board in rehearsal mode deliberately:

```sh
.venv/bin/python bridge/server.py --port /dev/cu.YOUR_ACTUAL_PORT --demo
```

Or tap BOOT after boot. On-board rehearsal cycles three covers over 18 seconds,
playing for 4.2 seconds and pausing for 1.8 seconds per cover. It needs no music
source. A power cycle returns to live WAITING unless the bridge reconnects with
`--demo`.

## Daily use and troubleshooting

- Keep the bridge terminal running, the Mac awake, and the chosen music tab open.
  After restarting Chrome, use **Connect this tab** again. Only one tab is selected.
- Play and pause in the music website. The extension only observes playback.
  **Disconnect** clears the selected source; it does not stop your music.
- WAITING: check the bridge, selected tab, and USB port. Chrome may throttle a
  long-idle background tab. Bring it forward; the next sample recovers. Do not
  disable browser protections to mask this limitation.
- NO ART / artwork error: wait for a retry, try another track and check internet.
  Artwork must come from the service's allowed HTTPS image hosts. Ads are treated
  as unavailable when the player's ad marker is present. Future site layout
  changes can require an update to `extension/extract.js`.
- Pairing mismatch: rerun `tools/prepare_extension.py`, click **Reload** on the
  extension card, reload the music tab, and reconnect. Keep the generated token
  and extension directory private.
- Address already in use: close the previous bridge terminal; only one bridge can
  bind 8766. Serial busy: stop any serial monitor or another bridge.
- Foreign firmware warning: install Digital Vinyl first. The bridge deliberately
  refuses to stream artwork to Pocket Eyes or the factory program.
- Updating source: rerun preparation and reload the extension; restart the bridge.
  Firmware changes require a fresh upload. Stop the bridge before uploading.
- Removal: remove the extension in Chrome and stop the bridge. It installs no
  launch agent or background service and does not change your music account.

The USB live version is tethered to the Mac. Adding a battery alone does not make
Chrome synchronization work away from the computer. See [hardware](HARDWARE.md).
