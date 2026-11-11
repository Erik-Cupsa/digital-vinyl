'use strict';
const $=id=>document.getElementById(id);
const canvas=document.querySelector('canvas'), ctx=canvas.getContext('2d');
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let mode='live', angle=0, speed=0, last=performance.now(), demoIndex=0, demoPlaying=!reduced;
let state={mode:'waiting',playing:false,artReady:false}, art=null, artVersion=-1, loadingVersion=-1;
const names=['Blue hour','Sideways','Afterglow'];
const covers=names.map((_,variant)=>{
  const cover=document.createElement('canvas'); cover.width=cover.height=224;
  const c=cover.getContext('2d'), pixels=c.createImageData(224,224);
  for(let y=0;y<224;y++) for(let x=0;x<224;x++) {
    let color;
    if(variant===0) color=(x-138)**2+(y-76)**2<48**2 ? [255,205,128] :
      (y>139+15*Math.sin(x*.04)?[38,91,125]:[205,88+Math.floor(y/4),80]);
    else if(variant===1) color=(x-80)**2+(y-137)**2<48**2 ? [246,175,74] :
      (Math.floor((x+Math.floor(y/2))/28)%2===0?[80,59,152]:[188,159,226]);
    else color=x>102&&x<117?[255,238,177]:
      (y>110+35*Math.sin(x*.025)?[30,95+Math.floor(y/3),113]:[209,230,193]);
    pixels.data.set([...color,255],(y*224+x)*4);
  }
  c.putImageData(pixels,0,0); return cover;
});
function sync() {
  const demo=mode==='demo';
  $('live').setAttribute('aria-pressed',!demo); $('demo').setAttribute('aria-pressed',demo);
  $('demo-controls').hidden=!demo;
  $('title').textContent=demo?names[demoIndex]:(state.title||'Your next record');
  $('artist').textContent=demo?'Original rehearsal artwork':(state.artist||'Start the local bridge to connect your player.');
  $('source').textContent=demo?'Rehearsal · no live music connection':
    (state.mode==='live'?(state.playing?'Live signal · playing':'Live signal · paused'):'Waiting for a music connection');
  $('detail').textContent=demo?'These three covers are generated for rehearsing the reveal. Demo controls affect this preview only.':
    (state.error||'Artwork and playback come from the local bridge. If the source disappears, the record coasts to a stop.');
  $('play').textContent=demoPlaying?'Pause':'Play';
  $('device').textContent=state.device||'Preview only · physical display not yet tested';
}
function select(next) {mode=next;angle=speed=0;last=performance.now();sync();}
$('demo').onclick=()=>select('demo'); $('live').onclick=()=>select('live');
$('play').onclick=()=>{demoPlaying=!demoPlaying;sync();};
$('next').onclick=()=>{demoIndex=(demoIndex+1)%3;sync();};
$('reset').onclick=()=>{demoIndex=0;demoPlaying=true;angle=speed=0;last=performance.now();sync();};
$('clean').onclick=()=>document.body.classList.toggle('clean');
document.addEventListener('keydown',event=>{
  if(event.ctrlKey||event.metaKey||event.altKey) return;
  if(event.key==='Escape') document.body.classList.remove('clean');
  if(event.key.toLowerCase()==='f'&&!event.target.matches('input,button,textarea')) document.body.classList.toggle('clean');
});
async function poll() {
  try {
    const response=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(5000)});
    if(!response.ok) throw new Error('Bridge unavailable');
    state=await response.json();
    if(state.artReady&&state.artVersion!==artVersion&&state.artVersion!==loadingVersion) {
      const version=state.artVersion; loadingVersion=version;
      const image=new Image(); image.src=`/api/art.png?v=${version}`;
      await image.decode();
      if(state.artVersion===version) {art=image;artVersion=version;}
      loadingVersion=-1;
    }
  } catch {state={mode:'waiting',playing:false,artReady:false,device:'Local bridge is not connected'};loadingVersion=-1;}
  sync(); setTimeout(poll,750);
}
function draw(now) {
  const dt=Math.min(.1,Math.max(0,(now-last)/1000)); last=now;
  const playing=mode==='demo'?demoPlaying:(state.mode==='live'&&state.playing&&state.artReady);
  const target=playing?18*Math.PI*2/60:0;
  speed+=(target-speed)*(1-Math.exp(-dt/.45));
  if(!playing&&speed<.002) speed=0;
  angle=(angle+speed*dt)%(Math.PI*2);
  ctx.fillStyle='#000';ctx.fillRect(0,0,466,466);
  ctx.save();ctx.translate(233,222);
  ctx.fillStyle='#33343a';ctx.beginPath();ctx.arc(0,0,207,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#141518';ctx.beginPath();ctx.arc(0,0,204,0,Math.PI*2);ctx.fill();
  for(let r=115;r<203;r+=2.15) {
    ctx.strokeStyle=r%4<2?'#27282b':'#202124';ctx.lineWidth=.7;
    ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.stroke();
  }
  const shine=ctx.createConicGradient(-.6,0,0);
  shine.addColorStop(0,'#ffffff00');shine.addColorStop(.1,'#ffffff14');shine.addColorStop(.2,'#ffffff00');
  shine.addColorStop(.5,'#ffffff00');shine.addColorStop(.6,'#ffffff12');shine.addColorStop(.7,'#ffffff00');shine.addColorStop(1,'#ffffff00');
  ctx.fillStyle=shine;ctx.beginPath();ctx.arc(0,0,203,0,Math.PI*2);ctx.fill();
  ctx.save();ctx.rotate(angle);ctx.beginPath();ctx.arc(0,0,111,0,Math.PI*2);ctx.clip();
  const cover=mode==='demo'?covers[demoIndex]:(state.artReady?art:null);
  if(cover)ctx.drawImage(cover,-112,-112,224,224);
  else {ctx.fillStyle='#33343a';ctx.fillRect(-112,-112,224,224);}
  ctx.restore();ctx.fillStyle='#0a0b0d';ctx.beginPath();ctx.arc(0,0,6,0,Math.PI*2);ctx.fill();ctx.restore();
  ctx.fillStyle='#b4b4b4';ctx.font='10px monospace';ctx.textAlign='center';
  const label=mode==='demo'?(demoPlaying?'DEMO':'DEMO PAUSED'):
    (state.mode==='live'?(state.artReady?(state.playing?'LIVE':'PAUSED'):'NO ART'):'WAITING');
  ctx.fillText(label,233,450);
  requestAnimationFrame(draw);
}
sync();poll();requestAnimationFrame(draw);
