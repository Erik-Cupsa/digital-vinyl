#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Arduino_GFX_Library.h>
#include <esp_heap_caps.h>

// Adapted from Waveshare's Apache-2.0 HelloWorld initialization, pinned in
// dependencies.json. See THIRD_PARTY_NOTICES.md. Full-frame PSRAM canvas added.
namespace board {
static Arduino_ESP32QSPI bus(12,38,4,5,6,7);
static Arduino_CO5300 panel(&bus,39,0,466,466,6,0,0,0);
class Canvas : public Arduino_Canvas {
 public:
  Canvas() : Arduino_Canvas(466,466,&panel) {}
  bool begin(int32_t = GFX_NOT_DEFINED) override {
    if(!_framebuffer) _framebuffer=static_cast<uint16_t*>(heap_caps_malloc(
      466*466*2,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    return _framebuffer!=nullptr;
  }
};
static Canvas canvas;
inline void* allocate(size_t bytes) { return heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT); }
inline bool begin() {
  Wire.begin(15,14); pinMode(0,INPUT_PULLUP);
  if(!psramFound() || !canvas.begin() || !panel.begin(40000000)) return false;
  panel.setBrightness(128); panel.fillScreen(RGB565_BLACK); return true;
}
inline bool pressed(uint32_t now) {
  static bool raw=true,stable=true;
  static uint32_t changed=0;
  const bool next=digitalRead(0)!=LOW;
  if(next!=raw) { raw=next; changed=now; }
  if(uint32_t(now-changed)<30 || raw==stable) return false;
  stable=raw; return !stable;
}
} // namespace board
