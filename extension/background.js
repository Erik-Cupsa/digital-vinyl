'use strict';
importScripts('config.js');
const ENDPOINT = 'http://127.0.0.1:8766';
const EMPTY = {title:'', artist:'', trackId:'', artUrl:'', available:false, playing:false};
// Serialize source changes and snapshots: an older request must not undo Disconnect.
let queue = Promise.resolve();
function serialize(task) {
  const next = queue.then(task);
  queue = next.catch(() => {});
  return next;
}
function musicURL(value) {
  try { return new URL(value).origin === 'https://music.youtube.com'; } catch { return false; }
}
async function publish(data) {
  if (!/^[a-f0-9]{64}$/.test(DIGITAL_VINYL_TOKEN)) throw new Error('Run tools/prepare_extension.py first.');
  const response = await fetch(ENDPOINT + '/api/now-playing', {
    method:'POST', headers:{'Content-Type':'application/json', Authorization:'Bearer ' + DIGITAL_VINYL_TOKEN},
    body:JSON.stringify(data), signal:AbortSignal.timeout(10000), credentials:'omit', redirect:'error'
  });
  if (!response.ok) throw new Error(response.status === 401 ? 'Pairing mismatch: prepare and reload the extension.' : 'Bridge rejected the player data.');
}
async function dispatch(message, sender) {
  const selected = (await chrome.storage.session.get('selectedTab')).selectedTab;
  if (message?.kind === 'snapshot') {
    if (sender.frameId !== 0 || !musicURL(sender.url) || sender.tab?.id !== selected) return {ok:false, ignored:true};
    await publish(message.data);
    return {ok:true};
  }
  // Control messages are only accepted from this extension's popup.
  if (sender.url !== chrome.runtime.getURL('popup.html') || sender.tab) return {ok:false};
  if (message.kind === 'connect') {
    const [tab] = await chrome.tabs.query({active:true, currentWindow:true});
    if (!tab || !musicURL(tab.url)) throw new Error('Open your music tab, then click Connect here.');
    await chrome.storage.session.set({selectedTab:tab.id});
    await publish(EMPTY); // Clear the old source before the new tab sends a sample.
    try { await chrome.tabs.sendMessage(tab.id, {kind:'sample'}); }
    catch { throw new Error('Reload the music tab after installing the extension, then connect again.'); }
    return {ok:true, connected:true};
  }
  if (message.kind === 'disconnect') {
    await chrome.storage.session.remove('selectedTab');
    await publish(EMPTY);
    return {ok:true, connected:false};
  }
  if (message.kind === 'status') {
    const response = await fetch(ENDPOINT + '/api/state', {signal:AbortSignal.timeout(2000), credentials:'omit', redirect:'error'});
    if (!response.ok) throw new Error('Bridge unavailable.');
    return {ok:true, connected:Number.isInteger(selected), state:await response.json()};
  }
  return {ok:false};
}
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  serialize(() => dispatch(message, sender)).then(respond).catch(error => respond({ok:false, error:error.message}));
  return true;
});
chrome.tabs.onRemoved.addListener(id => serialize(async () => {
  if ((await chrome.storage.session.get('selectedTab')).selectedTab === id) {
    await chrome.storage.session.remove('selectedTab');
    await publish(EMPTY);
  }
}).catch(() => {}));
