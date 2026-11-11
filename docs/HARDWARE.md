# Hardware and power

Target: **Waveshare ESP32-S3-Touch-AMOLED-1.75**, the standard board with integrated
466 × 466 round AMOLED. The B case variant shares the display wiring; the separately
named 1.75C is not this target.

```text
Mac running Chrome + bridge ── USB data cable ── Waveshare board + built-in screen
```

No display wiring or jumper cables are needed. The ESP32-S3R8 has 16 MiB flash and
8 MiB octal PSRAM. The board adapter uses the vendor CO5300 QSPI initialization:
CS 12, clock 38, data 4/5/6/7, reset 39, six-column panel offset, I2C SDA 15/SCL 14.
BOOT is GPIO 0. These are existing PCB connections, not instructions to wire pins.

The display bus is configured at 40 MHz. Full frame, background, two covers and
receive buffer occupy about 1.17 MB of PSRAM, plus driver buffers. The loop targets
33 ms between frames, but actual frame rate, transfer time, power and screen
brightness must be measured on hardware. Panel brightness is 128/255. The record
uses a stylized 18 RPM for legibility, not a claim of turntable-speed accuracy.
Touch, microphone, speaker, SD card, IMU, Wi-Fi and Bluetooth are unused.

## Battery and case are later checks

Begin on USB power. The board has a **3.7 V MX1.25 2-pin battery connector** and a
separate speaker connector. Confirm the labeled battery socket, mating connector,
and positive/negative wire order against the schematic before connecting any cell.
Do not assume a fitting two-pin plug has the correct polarity.

A purchased 3.7 V / 1300 mAh / 103040 battery has not been physically checked for
connector, polarity, thickness, clearance or charging behavior. Clear keychain
pouch fit is also unverified. Do not squeeze the cell to make it fit, leave exposed
conductors against it, or describe the assembly as pocket-ready before inspection.
This firmware does not reconfigure the power-management chip or implement a
battery gauge. Runtime and thermal behavior have not been measured.

A battery could power a standalone rehearsal after validation, but **live music
in this release requires USB data to the awake Mac**, Chrome, the extension and
the bridge. It has no phone, standalone streaming or wireless synchronization.
USB cable data capability also needs a real connection check.

Sources: [official product documentation](https://docs.waveshare.com/ESP32-S3-Touch-AMOLED-1.75),
[pinned board reference](https://github.com/waveshareteam/ESP32-S3-Touch-AMOLED-1.75/blob/e4344e70c2fa78a13e8a06566507f1ba8af6672a/HARDWARE_REFERENCE.md),
[schematic](https://files.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.75/ESP32-S3-Touch-AMOLED-1.75.pdf).
