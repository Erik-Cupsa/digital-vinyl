#pragma once
#include <math.h>
#include <stdint.h>
#include <string.h>

namespace vinyl {
constexpr int kScreen = 466;
constexpr int kArt = 224;
constexpr int kArtBytes = kArt * kArt * 2;
constexpr float kPi = 3.14159265358979323846f;
constexpr float kRpm = 18.0f; // Slow enough to read the artwork on camera.
inline uint16_t rgb(int r, int g, int b) {
  return uint16_t(((r & 248) << 8) | ((g & 252) << 3) | (b >> 3));
}
inline uint16_t blend(uint16_t a, uint16_t b, int alpha) {
  const int inv = 255 - alpha;
  return uint16_t((((((a >> 11) & 31) * inv + ((b >> 11) & 31) * alpha) / 255) << 11) |
    (((((a >> 5) & 63) * inv + ((b >> 5) & 63) * alpha) / 255) << 5) |
    (((a & 31) * inv + (b & 31) * alpha) / 255));
}
struct Motion {
  float angle = 0, speed = 0;
  void reset() { angle = speed = 0; }
  void step(float seconds, bool playing) {
    if (seconds < 0) seconds = 0;
    if (seconds > 0.1f) seconds = 0.1f; // No jump after a stalled USB transfer.
    const float target = playing ? kRpm * 2 * kPi / 60 : 0;
    const float approach = 1 - expf(-seconds / 0.45f);
    speed += (target - speed) * approach;
    if (!playing && speed < 0.002f) speed = 0;
    angle = fmodf(angle + speed * seconds, 2 * kPi);
  }
};

// Original procedural rehearsal covers; no commercial album imagery is bundled.
inline void demoCover(uint16_t* out, int variant) {
  for (int y = 0; y < kArt; ++y) for (int x = 0; x < kArt; ++x) {
    uint16_t color;
    if (variant % 3 == 0) {
      const bool sun = (x-138)*(x-138) + (y-76)*(y-76) < 48*48;
      const bool wave = y > 139 + 15 * sinf(x * 0.04f);
      color = sun ? rgb(255,205,128) : (wave ? rgb(38,91,125) : rgb(205,88+y/4,80));
    } else if (variant % 3 == 1) {
      const bool band = ((x + y / 2) / 28) % 2 == 0;
      color = band ? rgb(80,59,152) : rgb(188,159,226);
      if ((x-80)*(x-80)+(y-137)*(y-137)<48*48) color=rgb(246,175,74);
    } else {
      const bool wave = y > 110 + 35 * sinf(x * 0.025f);
      color = wave ? rgb(30,95+y/3,113) : rgb(209,230,193);
      if (x>102 && x<117) color=rgb(255,238,177);
    }
    out[y*kArt+x] = color;
  }
}

class Renderer {
 public:
  void init(uint16_t* background) {
    background_ = background;
    for (int y=0; y<kScreen; ++y) for (int x=0; x<kScreen; ++x) {
      const float dx=x-233.0f, dy=y-222.0f;
      const float radius=sqrtf(dx*dx+dy*dy);
      int v=0;
      if (radius<207) {
        const float shine=powf(fabsf(dx+0.5f*dy)/(radius*1.12f+1), 12);
        const int groove=static_cast<int>(radius*1.4f)%3;
        v=17 + groove*3 + static_cast<int>(20*shine);
        if (radius>204) v=52;
        if (radius<113) v=27;
      }
      background[y*kScreen+x]=rgb(v,v,v+ (v ? 2:0));
    }
    for (int y=0; y<kArt; ++y) {
      const int dy=y-kArt/2;
      const int extent=static_cast<int>(sqrtf(float((kArt/2-1)*(kArt/2-1)-dy*dy > 0 ?
        (kArt/2-1)*(kArt/2-1)-dy*dy : 0)));
      left_[y]=kArt/2-extent; right_[y]=kArt/2+extent;
    }
  }
  void draw(uint16_t* output, const uint16_t* art, float angle, uint8_t opacity=255) const {
    memcpy(output, background_, kScreen*kScreen*sizeof(uint16_t));
    const int32_t cs=static_cast<int32_t>(cosf(angle)*65536);
    const int32_t sn=static_cast<int32_t>(sinf(angle)*65536);
    for (int y=1; y<kArt-1; ++y) {
      const int dy=y-kArt/2;
      for (int x=left_[y]; x<=right_[y]; ++x) {
        const int dx=x-kArt/2;
        const int sx=(cs*dx+sn*dy)/65536+kArt/2;
        const int sy=(-sn*dx+cs*dy)/65536+kArt/2;
        if (sx<0 || sy<0 || sx>=kArt || sy>=kArt) continue;
        const int target=(222+dy)*kScreen+233+dx;
        output[target]=blend(background_[target],art[sy*kArt+sx],opacity);
      }
    }
    // Spindle hole stays stationary above the turning label.
    for(int dy=-6;dy<=6;++dy) for(int dx=-6;dx<=6;++dx)
      if(dx*dx+dy*dy<=36) output[(222+dy)*kScreen+233+dx]=rgb(10,11,13);
  }
 private:
  uint16_t* background_ = nullptr;
  int16_t left_[kArt] = {}, right_[kArt] = {};
};
} // namespace vinyl
