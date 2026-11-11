const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {read, artwork} = require('../extension/extract.js');
// Contract fixtures for player DOM values. Real selectors were also inspected in Chrome.
function player({paused=false, ended=false, readyState=4, ad=false, title='Example track', old=false, image='https://yt3.googleusercontent.com/example=w60-h60-l90-rj'}={}) {
  const bar = {querySelector(selector) {
    if (selector.includes('.title')) return {textContent:title};
    if (selector.includes('.byline')) return {textContent:'Example artist • Album • 2026'};
    if (selector.includes('img')) return {currentSrc:image};
  }};
  return {querySelector(selector) {
    if (selector==='ytmusic-track-info') return old ? null : bar;
    if (selector==='ytmusic-player-bar') return old ? bar : null;
    if (selector==='video.html5-main-video') return {paused,ended,readyState};
    if (selector==='.ad-showing') return ad ? {} : null;
    return null;
  }};
}
assert.equal(read(player()).playing,true);
assert.equal(read(player()).artist,'Example artist');
assert.equal(read(player()).artUrl,'https://yt3.googleusercontent.com/example=w448-h448-l90-rj');
for (const options of [{paused:true},{ended:true},{readyState:1},{ad:true},{title:''}]) assert.equal(read(player(options)).playing,false);
assert.equal(read(player({old:true})).title,'Example track');
assert.equal(read(player({ad:true})).available,false);
assert.equal(artwork('https://lh3.googleusercontent.com.evil.test/cover'),'');
assert.equal(artwork('http://lh3.googleusercontent.com/cover'),'');
assert.equal(artwork('https://user:secret@lh3.googleusercontent.com/cover'),'');
assert.equal(read({querySelector:()=>null}).available,false);

async function main() {
  let listener, removed, selectedTab, active=7;
  const sent=[];
  const popup={url:'chrome-extension://test/popup.html'};
  const music=id=>({tab:{id},frameId:0,url:'https://music.youtube.com/'});
  const chrome={
    runtime:{getURL:path=>'chrome-extension://test/'+path,onMessage:{addListener:fn=>listener=fn}},
    storage:{session:{get:async()=>({selectedTab}),set:async data=>selectedTab=data.selectedTab,remove:async()=>{selectedTab=undefined;}}},
    tabs:{query:async()=>[{id:active,url:'https://music.youtube.com/'}],sendMessage:async()=>{},onRemoved:{addListener:fn=>removed=fn}}
  };
  const context=vm.createContext({chrome,URL,AbortSignal,importScripts:()=>{},DIGITAL_VINYL_TOKEN:'a'.repeat(64),
    fetch:async(url,options={})=>{
      assert.ok(url.startsWith('http://127.0.0.1:8766/'));
      if (options.method) {assert.equal(options.headers.Authorization,'Bearer '+'a'.repeat(64));sent.push(JSON.parse(options.body));}
      return {ok:true,json:async()=>({mode:'waiting'})};
    }});
  vm.runInContext(fs.readFileSync('extension/background.js','utf8'),context);
  const send=(message,sender)=>new Promise(resolve=>listener(message,sender,resolve));
  const data=read(player());
  assert.equal((await send({kind:'snapshot',data},music(7))).ignored,true);
  assert.equal((await send({kind:'connect'},popup)).ok,true);
  assert.equal(sent.at(-1).available,false);
  assert.equal((await send({kind:'snapshot',data},music(8))).ignored,true);
  assert.equal((await send({kind:'snapshot',data},{...music(7),url:'https://evil.test/'})).ignored,true);
  assert.equal((await send({kind:'snapshot',data},{...music(7),frameId:1})).ignored,true);
  assert.equal((await send({kind:'disconnect'},music(7))).ok,false);
  await send({kind:'snapshot',data},music(7));
  assert.equal(sent.at(-1).playing,true);
  // A queued old snapshot cannot re-enable a disconnected source.
  await Promise.all([send({kind:'snapshot',data},music(7)),send({kind:'disconnect'},popup),send({kind:'snapshot',data},music(7))]);
  assert.equal(sent.at(-1).available,false);
  active=8; await send({kind:'connect'},popup);
  await removed(8);
  assert.equal(selectedTab,undefined); assert.equal(sent.at(-1).available,false);
  console.log('PASS: player states, artwork allowlist, tab selection, sender checks, disconnect ordering and tab-close cleanup');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
