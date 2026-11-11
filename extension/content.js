'use strict';
// Reading stops at the player DOM. Networking and the pairing token stay in the worker.
let timer;
let inFlight = false;
async function report() {
  if (inFlight) return;
  inFlight = true;
  try {
    await chrome.runtime.sendMessage({kind: 'snapshot', data: DigitalVinylExtract.read(document)});
  } catch { /* Extension reloaded or bridge unavailable: the receiver times out safely. */ }
  finally { inFlight = false; }
}
function schedule() {
  clearTimeout(timer);
  timer = setTimeout(report, 150); // Let title, artwork and media update together.
}
for (const event of ['play', 'pause', 'ended', 'loadeddata', 'emptied', 'waiting', 'playing']) {
  document.addEventListener(event, schedule, true);
}
new MutationObserver(schedule).observe(document.documentElement, {
  subtree: true, childList: true, characterData: true,
  attributes: true, attributeFilter: ['src', 'title']
});
setInterval(report, 2000); // Heartbeat also discovers replacement player elements.
chrome.runtime.onMessage.addListener(message => { if (message.kind === 'sample') schedule(); });
report();
