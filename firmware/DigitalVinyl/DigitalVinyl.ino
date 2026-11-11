#include "Board.h"
#include "Record.h"
#include "Protocol.h"

uint16_t *background=nullptr,*liveCover=nullptr,*demoArt=nullptr;
uint8_t* incoming=nullptr;
vinyl::Receiver* receiver=nullptr;
vinyl::Renderer renderer;
vinyl::Motion motion;
bool ready=false, demo=false, playing=false, sourceAvailable=false, haveCover=false;
uint32_t lastLive=0, lastFrame=0, demoStart=0, coverChanged=0;
int demoIndex=-1;

void setup() {
  Serial.begin(115200); // Native USB CDC; no busy-wait for a laptop.
  if(!board::begin()) return;
  background=static_cast<uint16_t*>(board::allocate(466*466*2));
  liveCover=static_cast<uint16_t*>(board::allocate(vinyl::kArtBytes));
  demoArt=static_cast<uint16_t*>(board::allocate(vinyl::kArtBytes));
  incoming=static_cast<uint8_t*>(board::allocate(vinyl::kArtBytes));
  if(!background||!liveCover||!demoArt||!incoming) return;
  memset(liveCover,0,vinyl::kArtBytes);
  receiver=new vinyl::Receiver(incoming);
  renderer.init(background); ready=true;
  Serial.println("DVY1 READY");
}

void setMode(bool next, uint32_t now) {
  demo=next; demoStart=now; demoIndex=-1; motion.reset();
}

void loop() {
  if(!ready) { Serial.println("DVY1 ERROR: display/PSRAM initialization"); delay(1000); return; }
  const uint32_t now=millis();
  receiver->expire(now);
  for(int budget=0; budget<16384 && Serial.available(); ++budget) {
    const uint8_t byte=uint8_t(Serial.read());
    if(receiver->idle() && byte=='?') { Serial.println("DVY1 READY"); continue; }
    if(!receiver->feed(byte,now)) continue;
    if(receiver->type()==vinyl::kState) {
      sourceAvailable=incoming[0]==1; playing=incoming[1]==1; lastLive=now;
    } else if(receiver->type()==vinyl::kCover) {
      // Wire format is explicitly little-endian RGB565.
      for(int i=0;i<vinyl::kArt*vinyl::kArt;++i)
        liveCover[i]=uint16_t(incoming[2*i])|(uint16_t(incoming[2*i+1])<<8);
      haveCover=true; coverChanged=now;
    } else if(receiver->type()==vinyl::kMode) setMode(incoming[0]==1,now);
    Serial.printf("ACK %u %08lx\n",receiver->type(),static_cast<unsigned long>(receiver->checksum()));
  }
  if(board::pressed(now)) setMode(!demo,now);
  if(uint32_t(now-lastFrame)<33) { delay(1); return; }
  const float dt=uint32_t(now-lastFrame)/1000.0f; lastFrame=now;
  bool spin=false;
  const char* label="WAITING";
  const uint16_t* art=liveCover;
  uint8_t opacity=255;
  if(demo) {
    const uint32_t t=uint32_t(now-demoStart)%18000;
    const int index=t/6000;
    if(index!=demoIndex) { vinyl::demoCover(demoArt,index); demoIndex=index; }
    spin=t%6000<4200; art=demoArt; label=spin?"DEMO":"DEMO PAUSED";
  } else if(sourceAvailable && uint32_t(now-lastLive)<6000) {
    spin=playing && haveCover; label=haveCover?(playing?"LIVE":"PAUSED"):"NO ART";
    const uint32_t age=uint32_t(now-coverChanged);
    if(age<300) opacity=uint8_t(age*255/300);
  }
  motion.step(dt,spin);
  renderer.draw(board::canvas.getFramebuffer(),art,motion.angle,opacity);
  board::canvas.setTextSize(1);
  board::canvas.setTextColor(vinyl::rgb(180,180,180));
  board::canvas.setCursor(233-static_cast<int>(strlen(label))*3,442);
  board::canvas.print(label);
  board::canvas.flush();
}
