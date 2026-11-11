# Validation record

Checked 2026-11-11. This document separates software evidence from physical tests.

## Passed locally

- Actual firmware compile for the pinned Waveshare ESP32-S3 / CO5300 profile:
  **428,082 bytes flash**, **25,556 bytes static RAM**. PSRAM allocations are
  additional; they total about 1.17 MB before graphics-driver buffers.
- Native C++11 renderer and motion checks under UndefinedBehaviorSanitizer:
  rotation, coast-to-zero, stationary pause, reset, all three cover variants,
  boundary pixels and spindle hole.
- Python-generated RGB565 frame consumed by the C++ receiver: pixel byte order,
  standard CRC32 vector, rejection of corruption/oversized headers, partial-frame
  timeout and a receive-buffer canary.
- **15 Python tests**: wire encoding, live/pause/stale state, artwork failure and
  out-of-order downloads, URL/metadata bounds, HTTP pairing/Host validation,
  complete cover transfer and ACK through a simulated USB peer, foreign-firmware
  refusal, double-read backup and upload gate corruption checks.
- Node checks: DOM-adapter contract fixtures for current and legacy layouts,
  play/pause/ended/buffering/ad states, artwork URL allowlist, selected-tab routing,
  rejected wrong senders, queued Disconnect ordering and tab-close cleanup.
  JavaScript syntax checks also pass. These simulate Chrome APIs; they are not
  a substitute for an installed-extension test.
- Chrome inspection of the actual music website's current `ytmusic-track-info`
  layout; the **finished extraction function** correctly read the current title,
  artist, resized artwork URL and paused state. Play/pause media properties were
  inspected directly. No hidden player/account API was used.
- One captured real player snapshot was posted manually to the running loopback
  bridge using its private token. The bridge accepted it, downloaded the CDN
  artwork and produced a **224 × 224 RGB PNG** with `artReady=true`. This checks
  extraction and conversion, not continuous extension transport. The observation
  stayed in ignored `local/`; no listening data or commercial cover is committed.
- Chrome preview: waiting screen, rehearsal, pause and next-cover interactions.
  The committed screenshot shows only original generated rehearsal artwork.
- The sibling Pocket Eyes GitHub workflow passed after its C++11 portability fix.

GitHub Actions repeats the native/Python/Node checks, extension preparation and
pinned toolchain firmware build on a clean Ubuntu runner. The repository's Actions
page reports the current commit's result; local success alone is not CI success.

## Still requires installation or hardware

- Load the unpacked extension, select a tab, and verify continuous real playback,
  track changes, long background-tab behavior and reconnect on this Chrome version.
  The extension was prepared but **not installed** during code authoring.
- USB enumeration, native CDC handshake, complete artwork transfers and their
  latency on the actual board. A simulated serial peer is not a physical device.
- Display color order, orientation, cropping, frame rate, fading and BOOT behavior.
- Factory flash read/security checks, two real matching reads, upload, power cycle,
  restore and switching back to Pocket Eyes. **No board was flashed.**
- Battery connector/polarity, charging, runtime, temperature and pouch fit.

Use [SETUP.md](SETUP.md) and [FILMING.md](FILMING.md) for the first-run checklist.
The project is ready for those checks; it is not yet a physically validated build.
