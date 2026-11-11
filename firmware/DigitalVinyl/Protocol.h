#pragma once
#include <stdint.h>
#include <stddef.h>

namespace vinyl {
constexpr uint8_t kState = 1, kCover = 2, kMode = 3;
constexpr size_t kMaxPayload = 224 * 224 * 2;
inline uint32_t crcStep(uint32_t crc, uint8_t byte) {
  crc ^= byte;
  for (int i=0;i<8;++i) crc=(crc>>1) ^ (0xEDB88320u & (0u-(crc&1u)));
  return crc;
}
inline uint32_t little32(const uint8_t* p) {
  return uint32_t(p[0]) | (uint32_t(p[1])<<8) | (uint32_t(p[2])<<16) | (uint32_t(p[3])<<24);
}
class Receiver {
 public:
  explicit Receiver(uint8_t* payload) : payload_(payload) {}
  void reset() { headerUsed_=used_=length_=0; crc_=0xFFFFFFFFu; }
  void expire(uint32_t now) {
    if (headerUsed_ && uint32_t(now-lastByte_)>2000) reset();
  }
  // True only after a complete, bounded, CRC-checked message. Caller consumes now.
  bool feed(uint8_t byte, uint32_t now) {
    expire(now); lastByte_=now;
    if (headerUsed_<14) {
      static const char magic[]="DVY1";
      if (headerUsed_<4 && byte!=uint8_t(magic[headerUsed_])) {
        reset();
        if(byte=='D') { header_[0]=byte; headerUsed_=1; }
        return false;
      }
      header_[headerUsed_++]=byte;
      if(headerUsed_==14) {
        type_=header_[4]; length_=little32(header_+6); expected_=little32(header_+10);
        if(header_[5]!=0 || !((type_==kState && length_==2) ||
            (type_==kCover && length_==kMaxPayload) || (type_==kMode && length_==1))) reset();
      }
      return false;
    }
    payload_[used_++]=byte; crc_=crcStep(crc_,byte);
    if(used_!=length_) return false;
    const bool valid=(crc_^0xFFFFFFFFu)==expected_;
    completedType_=type_; completedCrc_=expected_;
    reset(); return valid;
  }
  uint8_t type() const { return completedType_; }
  bool idle() const { return headerUsed_==0; }
  uint32_t checksum() const { return completedCrc_; }
 private:
  uint8_t* payload_;
  uint8_t header_[14]={}, type_=0, completedType_=0;
  size_t headerUsed_=0, used_=0, length_=0;
  uint32_t crc_=0xFFFFFFFFu, expected_=0, completedCrc_=0, lastByte_=0;
};
} // namespace vinyl
