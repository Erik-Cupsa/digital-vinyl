'use strict';
const status = document.getElementById('status');
async function action(kind) {
  try {
    const result = await chrome.runtime.sendMessage({kind});
    if (!result?.ok) throw new Error(result?.error || 'Connection unavailable.');
    if (kind !== 'status') return action('status');
    status.textContent = !result.connected ? 'Choose a music tab and connect it.' :
      result.state.mode === 'live' ? `${result.state.playing ? 'Playing' : 'Paused'} · ${result.state.title}${result.state.error ? ' — ' + result.state.error : ''}` :
      'Tab connected. Start a track; reload the tab if it stays waiting.';
  } catch (error) {
    status.textContent = `${error.message} Start the local bridge if it is not running.`;
  }
}
document.getElementById('connect').addEventListener('click', () => action('connect'));
document.getElementById('disconnect').addEventListener('click', () => action('disconnect'));
action('status');
