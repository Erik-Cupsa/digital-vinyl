#include <assert.h>
#include <fstream>
#include <iostream>
#include <vector>
#include "../firmware/DigitalVinyl/Record.h"
#include "../firmware/DigitalVinyl/Protocol.h"

int main() {
  using namespace vinyl;
  Motion motion;
  for(int i=0;i<100;++i) motion.step(.033f,true);
  assert(motion.speed>1.8f && motion.angle>=0 && motion.angle<2*kPi);
  const float moving=motion.speed; motion.step(.033f,false);
  assert(motion.speed>0 && motion.speed<moving); // Coasting, not a hard stop.
  for(int i=0;i<200;++i) motion.step(.033f,false);
  assert(motion.speed==0);
  const float held=motion.angle; motion.step(.033f,false); assert(motion.angle==held);
  motion.reset(); assert(motion.angle==0 && motion.speed==0);
  std::vector<uint16_t> base(kScreen*kScreen), art(kArt*kArt), frame(kScreen*kScreen);
  Renderer renderer; renderer.init(base.data()); demoCover(art.data(),0);
  renderer.draw(frame.data(),art.data(),0);
  const auto first=frame;
  renderer.draw(frame.data(),art.data(),1);
  assert(frame!=first && frame[0]==0 && frame.back()==0);
  assert(frame[222*kScreen+233]==rgb(10,11,13));
  for(int variant=0;variant<3;++variant) {
    demoCover(art.data(),variant);
    for(int step=0;step<360;step+=3) renderer.draw(frame.data(),art.data(),step*kPi/180);
  }
  std::ofstream image("build/native-record.ppm",std::ios::binary);
  image<<"P6\n466 466\n255\n";
  for(uint16_t p:frame) {
    const char rgbbytes[]={char(((p>>11)&31)*255/31),char(((p>>5)&63)*255/63),char((p&31)*255/31)};
    image.write(rgbbytes,3);
  }
  uint32_t crc=0xFFFFFFFFu;
  for(char c:std::string("123456789")) crc=crcStep(crc,uint8_t(c));
  assert((crc^0xFFFFFFFFu)==0xCBF43926u); // Standard CRC32 reference vector.
  std::vector<uint8_t> payload(kMaxPayload+1,0xEE);
  Receiver receiver(payload.data());
  std::ifstream fixture("build/protocol.bin",std::ios::binary);
  assert(fixture.good());
  std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(fixture)),{});
  int accepted=0;
  for(uint8_t byte:bytes) if(receiver.feed(byte,10)) ++accepted;
  assert(accepted==1 && receiver.type()==kCover && payload.back()==0xEE);
  assert(payload[0]==0x34 && payload[1]==0x12 && payload[kMaxPayload-1]==0x12);
  bytes.back()^=1; accepted=0;
  for(uint8_t byte:bytes) if(receiver.feed(byte,20)) ++accepted;
  assert(accepted==0); // Corrupt frame does not become visible art.
  for(int i=0;i<20;++i) receiver.feed(bytes[i],30);
  receiver.expire(2031); assert(receiver.idle());
  std::vector<uint8_t> oversized={'D','V','Y','1',2,0,255,255,255,255,0,0,0,0};
  for(uint8_t byte:oversized) receiver.feed(byte,2100);
  assert(receiver.idle());
  std::cout<<"PASS: rotation, coast/hold/reset, renderer, Python-to-C++ frame, CRC, timeout and bounds\n";
}
