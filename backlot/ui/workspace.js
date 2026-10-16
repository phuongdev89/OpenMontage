import {el, mediaURL} from '/ui/lib.js';

export async function requestJSON(url, body) {
  const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Yêu cầu không hợp lệ.');
  return data;
}

const players = new Map();
window.addEventListener('pagehide', event => {
  if (event.persisted) return; // BFCache retains the page and its live player tree.
  for (const session of players.values()) {
    if (session.player && !session.player.isDisposed()) session.player.dispose();
  }
  players.clear();
});
export function capturePlayer(projectId) {
  const session = players.get(projectId);
  const p = session?.player;
  if (p && !p.isDisposed()) session.capture = {time: p.currentTime(), playing: !p.paused(), rate: p.playbackRate(), volume: p.volume()};
}
export function renderPlayer(s) {
  const id = s.project_id;
  const videos = Object.entries(s.publish_package?.videos || {}).map(([label, v]) => ({...v, label}));
  if (!videos.length) videos.push(...s.media.renders.map(v => ({...v, label: v.path.split('/').pop()})));
  const section = el('section', {class: 'studio-player', 'aria-label': 'Player'});
  if (!videos.length) return section.append(el('p', {class: 'empty-state'}, 'Chưa có video để xem.')), section;
  let session = players.get(id);
  if (!session) {
    const video = el('video', {class: 'video-js vjs-big-play-centered', controls: '', preload: 'metadata', playsinline: '', 'aria-label': 'Xem video project'});
    session = {path: videos[0].path, mount: el('div', {class: 'videojs-mount'}, video), video};
    players.set(id, session);
  }
  if (!videos.some(v => v.path === session.path)) session.path = videos[0].path;
  const choice = el('div', {class: 'player-variants', role: 'group', 'aria-label': 'Bản video'});
  const name = v => v.label === 'landscape' ? 'Ngang · 16:9' : v.label === 'portrait' ? 'Dọc · 9:16' : v.label;
  for (const v of videos) choice.append(el('button', {
    type: 'button', 'aria-pressed': String(v.path === session.path),
    'data-icon': v.label === 'portrait' ? 'portrait' : 'video',
    onclick: () => {
      session.path = v.path;
      for (const [index, button] of [...choice.children].entries()) button.setAttribute('aria-pressed', String(videos[index].path === session.path));
      source();
    },
  }, name(v)));
  const download = el('a', {class: 'studio-button icon-only', download: '', 'aria-label': 'Tải video', 'data-icon': 'download'});
  const uploadPath = el('input', {readonly: '', 'aria-label': 'Đường dẫn video', onclick: event => event.target.select()});
  const copyPath = el('button', {type: 'button', 'aria-label': 'Sao chép đường dẫn', 'data-icon': 'copy', onclick: async () => {
    try { await navigator.clipboard.writeText(uploadPath.value); copyPath.setAttribute('aria-label', 'Đã sao chép'); setTimeout(() => copyPath.setAttribute('aria-label', 'Sao chép đường dẫn'), 2000); }
    catch { uploadPath.focus(); uploadPath.select(); }
  }});
  const status = el('p', {role: 'status', class: 'player-status'});
  function source() {
    const file = videos.find(v => v.path === session.path);
    const src = mediaURL(id, session.path) + `?v=${encodeURIComponent(file.mtime_ns || file.mtime || file.size || '')}`;
    download.href = src;
    uploadPath.value = file.absolute_path || file.path;
    const portrait = session.path.includes('portrait');
    section.classList.toggle('portrait-player', portrait);
    session.mount.classList.toggle('portrait-mount', portrait);
    const player = session.player;
    if (!player) return;
    player.aspectRatio(portrait ? '9:16' : '16:9');
    if (session.src === src) {
      if (session.capture?.playing && player.paused()) player.play()?.catch(() => {});
      session.capture = null; return;
    }
    const restore = session.loadedPath === session.path ? (session.capture || {time: player.currentTime(), playing: !player.paused(), rate: player.playbackRate(), volume: player.volume()}) : null;
    session.capture = null;
    session.loadedPath = session.path; session.src = src;
    player.one('loadedmetadata', () => {
      if (!restore || player.isDisposed()) return;
      player.currentTime(Math.min(restore.time, player.duration() || 0));
      player.playbackRate(restore.rate); player.volume(restore.volume);
      if (restore.playing) player.play()?.catch(() => {});
    });
    player.src({src, type: session.path.endsWith('.webm') ? 'video/webm' : 'video/mp4'});
  }
  if (videos.length > 1) section.append(el('div', {class: 'player-top'}, choice));
  section.append(session.mount,
    el('div', {class: 'video-upload-path'}, el('div', {class: 'video-upload-actions'}, uploadPath, copyPath, download)), status);
  // Keep the complete Video.js tree and instance through realtime DOM updates.
  queueMicrotask(() => {
    if (!session.mount.isConnected) return;
    if (!session.player) {
      if (!window.videojs) { status.textContent = 'Không tải được Video.js. Hãy tải lại trang.'; return; }
      session.player = window.videojs(session.video, {
        controls: true, fluid: true, responsive: true, language: 'vi',
        playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
        controlBar: {skipButtons: {backward: 10, forward: 10}, currentTimeDisplay: true,
          timeDivider: true, durationDisplay: true, remainingTimeDisplay: false},
        userActions: {hotkeys: true},
      });
      session.player.on('error', () => { status.textContent = 'Không đọc được video. Thử tải về hoặc chọn bản khác.'; });
    }
    source();
  });
  return section;
}
