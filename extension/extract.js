/* Original DOM adapter. No player internals, cookies or account API access. */
(function(root) {
  'use strict';
  const clean = value => (value || '').replace(/\s+/g, ' ').trim().slice(0, 200);
  function artwork(value) {
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.username || url.password ||
          (url.port && url.port !== '443') ||
          !(/\.(googleusercontent\.com|ytimg\.com)$/.test(url.hostname))) return '';
      // The mini player's Google CDN image is only 60px; request a 448px label.
      if (url.hostname.endsWith('.googleusercontent.com')) {
        url.pathname = url.pathname.replace(/=w\d+[^/]*$/, '=w448-h448-l90-rj');
      }
      return url.href.length <= 2048 ? url.href : '';
    } catch { return ''; }
  }
  function read(doc) {
    // New 2026 mini player, with fallback for the earlier Polymer player bar.
    const bar = doc.querySelector('ytmusic-track-info') || doc.querySelector('ytmusic-player-bar');
    const title = clean(bar?.querySelector('.ytmusicTrackInfoTitle, .title')?.textContent);
    const byline = bar?.querySelector('.ytmusicTrackInfoByline, .byline');
    const artist = clean(byline?.textContent?.split('•')[0]);
    const img = bar?.querySelector('img.ytmusicTrackInfoThumbnail, img');
    const artUrl = artwork(img?.currentSrc || img?.getAttribute('src') || '');
    const media = doc.querySelector('video.html5-main-video') || doc.querySelector('video, audio');
    const available = !!(title && media && !doc.querySelector('.ad-showing'));
    return {
      title, artist, artUrl, trackId: clean(title + ' / ' + artist), available,
      playing: available && !media.paused && !media.ended && media.readyState >= 2
    };
  }
  root.DigitalVinylExtract = {read, artwork};
  if (typeof module !== 'undefined') module.exports = root.DigitalVinylExtract;
})(typeof globalThis !== 'undefined' ? globalThis : this);
