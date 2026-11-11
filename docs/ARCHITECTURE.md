# Data flow and behavior

```text
Selected music tab
  DOM adapter: title / artist / artwork URL / video play state
       ↓ Chrome internal message
Extension service worker
  checks tab + sender, posts to fixed loopback endpoint with private pairing token
       ↓ POST 127.0.0.1:8766/api/now-playing
Python bridge
  validates metadata, downloads allowlisted HTTPS image, crops to 224² RGB565
       ├── local browser preview (PNG + JSON state)
       └── acknowledged DVY1 frames over USB → ESP32 → CO5300 AMOLED
```

The extension reads the player, not account tokens, cookies or playlists. Original
adapter supports the observed `ytmusic-track-info` layout and the earlier
`ytmusic-player-bar`. It uses the media element's paused/ended/readiness values,
not translated button labels. The old layout is covered by contract fixtures;
the current new layout was inspected directly. DOM integration is not an official
stable music-service API and can break when the site changes.

Chrome isolated content scripts send internal messages; only the worker performs
cross-origin requests. The worker accepts samples from the explicitly selected
main-frame music tab. Popup selection is held in session storage and cleared on
browser restart. Source changes, snapshots and Disconnect are serialized so old
requests cannot re-enable a disconnected source. No messages from the web page
via `window.postMessage`, arbitrary URL proxy, remote executable code or audio
capture are used. [Chrome networking reference](https://developer.chrome.com/docs/extensions/develop/concepts/network-requests).

The bridge binds **127.0.0.1 only**, checks the Host header, bounds JSON to 8192
bytes, and requires the generated bearer token for updates. No permissive CORS
headers are sent. It keeps only current metadata and artwork in memory, does not
log listening history, and does not persist album images. Only the Python bridge
fetches artwork, restricted to HTTPS subdomains of `googleusercontent.com` and
`ytimg.com`, including after redirects. Image size is capped at 5 MiB and decoded
pixel count is bounded; Pillow converts and crops to 224 × 224. Failed artwork
retries back off 15 seconds. Slow old downloads cannot overwrite a newer track.
GET preview endpoints expose the current state to local processes; this is a
single-user local helper, not a multi-user security boundary.

Heartbeats are sent every two seconds plus debounced player events. Host metadata
expires after ten seconds; the board stops on source-unavailable state or after
six seconds without valid state packets. Chrome background throttling, sleep and
network delay can cause WAITING. On timeout the physical board retains the last
cover but labels WAITING and stops motion; the browser preview hides stale art.
No demo is silently substituted for an unavailable source. Missing artwork never
causes the previous track's cover to be sent as the new track.

## USB protocol (version 1)

The host opens an explicitly provided port with DTR/RTS disabled, sends ASCII `?`,
and requires `DVY1 READY` before binary data. This avoids sending artwork to a
board running a different project. Native USB enumerations can still change the
port; selecting a device is a user setup step.

Header, 14 bytes: `DVY1`, type uint8, reserved byte zero, payload length uint32
little-endian, CRC32 uint32 little-endian. CRC is standard reflected IEEE CRC32,
covering payload only. Payloads:

| Type | Bytes | Meaning |
| --- | ---: | --- |
| 1 STATE | 2 | available, playing (0 or 1); bridge marks available only when the cover is ready |
| 2 COVER | 100352 | 224 × 224 RGB565 pixels, row-major, low byte first |
| 3 MODE | 1 | 0 live, 1 explicit demo |

The bounded firmware parser rejects wrong sizes/types/reserved bytes and bad CRCs.
An incomplete frame resets after two seconds of inactivity. Artwork is copied
into the live cover only after complete validation. The board returns
`ACK <type> <eight lowercase CRC hex digits>`. The host chunks transfers at 2048
bytes and waits for the matching acknowledgement before the next packet. Cover
is sent only on a new artwork version, STATE every half-second. Reconnection
re-sends mode and current cover. MODE is sent once per connection, so BOOT can
toggle rehearsal without the next heartbeat immediately undoing it.

## Rendering

The native renderer caches the stationary record background and rotates only its
circular center label with fixed-point sampling. Motion eases toward 18 RPM with
a 0.45-second time constant and stops exactly once slow enough. Live artwork fades
in over 300 ms. The stationary spindle hole and specular highlights keep the vinyl
readable. BOOT switches to an 18-second deterministic rehearsal with original
procedural covers. Default boot is WAITING.

Browser rehearsal approximates composition, colors and motion. Browser
antialiasing and procedural texture differ from the RGB565 firmware; it is not a
pixel-perfect emulator or proof of physical performance. A reduced-motion browser
preference starts rehearsal paused; live playback still follows the source.
