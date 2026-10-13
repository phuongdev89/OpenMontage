import {el, getJSON, mediaURL, thumbURL, fmtDuration, subscribe} from '/ui/lib.js';
import {openProjectGallery} from '/ui/gallery.js';

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
  const choice = el('select', {'aria-label': 'Chọn video'});
  const name = v => v.label === 'landscape' ? 'Ngang · 16:9' : v.label === 'portrait' ? 'Dọc · 9:16' : v.label;
  for (const v of videos) choice.append(el('option', {value: v.path, selected: v.path === session.path ? '' : null}, name(v)));
  const download = el('a', {class: 'studio-button', download: ''}, 'Tải video');
  const uploadPath = el('input', {readonly: '', 'aria-label': 'Đường dẫn video', onclick: event => event.target.select()});
  const copyPath = el('button', {type: 'button', onclick: async () => {
    try { await navigator.clipboard.writeText(uploadPath.value); copyPath.textContent = 'Đã sao chép'; }
    catch { uploadPath.focus(); uploadPath.select(); copyPath.textContent = 'Đã chọn đường dẫn'; }
  }}, 'Sao chép đường dẫn');
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
  choice.onchange = () => { session.path = choice.value; source(); };
  section.append(el('div', {class: 'player-top'}, choice), session.mount,
    el('div', {class: 'video-upload-path'}, el('label', {for: `video-path-${id}`}, 'Đường dẫn video'),
      el('div', {class: 'video-upload-actions'}, copyPath, download), uploadPath), status);
  uploadPath.id = `video-path-${id}`;
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

export function openFileManager(projectId, onUpdated) {
  const base = `/api/project/${encodeURIComponent(projectId)}`;
  const dialog = el('dialog', {class: 'file-dialog detail-file-manager', 'aria-label': 'Quản lý tệp project'});
  const status = el('p', {role: 'status', 'aria-live': 'polite'});
  const tree = el('nav', {class: 'file-tree', role: 'tree', 'aria-label': 'Cây thư mục'});
  const content = el('div', {class: 'file-content'});
  const search = el('input', {type: 'search', placeholder: 'Tìm tệp…', 'aria-label': 'Tìm tệp'});
  const upload = el('input', {type: 'file', hidden: ''});
  const locationLabel = el('span', {class: 'file-location'}, '/');
  let files = [], folder = '', selectedPath = null, mode = 'folder', loadRevision = 0;
  const expanded = new Set();
  const collapsed = new Set();
  const safe = async action => { try { await action(); } catch(error) { status.textContent = error.message; } };
  const changed = async () => { await sync(); if (onUpdated) await onUpdated(); };
  const basename = path => path.split('/').pop();
  const isImage = path => /\.(png|jpe?g|webp|gif|svg|avif|bmp)$/i.test(path);
  const filtered = () => files.filter(f => f.path.toLowerCase().includes(search.value.toLowerCase()));
  const selectFolder = path => {
    loadRevision++;
    folder = path; selectedPath = null; mode = 'folder'; locationLabel.textContent = path || '/';
    drawTree(); drawFolder();
  };
  const remove = async file => {
    const rev = await getJSON(base + '/files/revision?path=' + encodeURIComponent(file.path));
    const deleted = await requestJSON(base + '/files/delete', {path: file.path, expected_revision: rev.revision});
    if (selectedPath === file.path) { selectedPath = null; mode = 'folder'; }
    status.replaceChildren(document.createTextNode(`Đã xóa ${basename(file.path)}. `), el('button', {type: 'button', onclick: () => safe(async () => {
      await requestJSON(base + '/files/restore', {token: deleted.undo_token}); await changed(); status.textContent = 'Đã khôi phục tệp';
    })}, 'Hoàn tác'));
    await changed();
  };
  const actions = file => el('div', {class: 'file-actions'},
    el('a', {class: 'studio-button', href: mediaURL(projectId, file.path), download: ''}, 'Tải'),
    el('button', {type: 'button', disabled: file.protected ? '' : null, onclick: () => safe(() => remove(file))}, 'Xóa'));
  const openFile = async path => {
    const file = files.find(f => f.path === path); if (!file) return;
    if (mode === 'editor' && selectedPath === path) { content.querySelector('textarea')?.focus(); return; }
    const epoch = ++loadRevision;
    selectedPath = path; folder = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
    mode = 'file'; locationLabel.textContent = path; drawTree();
    content.replaceChildren(el('h3', {}, basename(path)), el('p', {role: 'status'}, 'Đang đọc tệp…'));
    if (isImage(path)) {
      content.replaceChildren(el('header', {class: 'file-detail-head'}, el('h3', {}, basename(path)), actions(file)),
        el('button', {type: 'button', class: 'file-image-preview', 'aria-label': `Xem ảnh ${basename(path)}`, onclick: () => openProjectGallery(projectId, path)},
          el('img', {src: mediaURL(projectId, path), alt: basename(path)})),
        el('p', {class: 'posting-note'}, 'Bấm vào ảnh để mở gallery.'));
      return;
    }
    if (/\.(mp4|webm|mov)$/i.test(path)) {
      content.replaceChildren(el('header', {class: 'file-detail-head'}, el('h3', {}, basename(path)), actions(file)),
        el('video', {src: mediaURL(projectId, path), controls: '', preload: 'metadata', class: 'file-video-preview'})); return;
    }
    try { await edit(path, epoch); }
    catch(error) {
      if (epoch !== loadRevision) return;
      content.replaceChildren(el('header', {class: 'file-detail-head'}, el('h3', {}, basename(path)), actions(file)),
        el('p', {class: 'empty-state'}, error.message));
    }
  };
  const edit = async (path, epoch = ++loadRevision) => {
    const data = path ? await getJSON(base + '/files/read?path=' + encodeURIComponent(path)) : {content: '', revision: null};
    if (epoch !== loadRevision) return;
    mode = 'editor'; selectedPath = path; drawTree();
    const filename = el('input', {value: path || (folder ? folder + '/' : ''), readonly: path ? '' : null, placeholder: 'notes/ghi-chu.md', 'aria-label': 'Đường dẫn tệp'});
    const text = el('textarea', {rows: '18', spellcheck: 'false', 'aria-label': 'Nội dung tệp', readonly: data.protected ? '' : null}, data.content);
    const message = el('p', {role: 'status'});
    const fileActions = el('div', {class: 'file-actions'});
    const updateActions = () => { const file = files.find(f => f.path === selectedPath); fileActions.replaceChildren(); if (file) fileActions.append(actions(file)); };
    updateActions();
    const save = el('button', {type: 'button', disabled: data.protected ? '' : null, onclick: async () => {
      save.disabled = true; save.setAttribute('aria-busy', 'true');
      try {
        const saved = await requestJSON(base + '/files/write', {path: filename.value.trim(), content: text.value, expected_revision: data.revision});
        data.revision = saved.revision; filename.readOnly = true;
        if (content.contains(text)) selectedPath = saved.path;
        message.textContent = 'Đã lưu'; await changed(); updateActions();
      } catch(error) { message.textContent = error.message; }
      finally { save.disabled = !!data.protected; save.setAttribute('aria-busy', 'false'); }
    }}, 'Lưu tệp');
    content.replaceChildren(el('header', {class: 'file-detail-head'}, el('h3', {}, path ? basename(path) : 'Tạo tệp'),
      el('div', {class: 'posting-actions'}, save, el('button', {type: 'button', onclick: () => selectFolder(folder)}, 'Về thư mục'), fileActions)),
      filename, text, message);
    if (data.protected) content.append(el('p', {class: 'posting-note'}, 'Tệp trạng thái pipeline · chỉ đọc'));
    text.focus();
  };
  function drawFolder() {
    const body = el('tbody');
    const table = el('table', {class: 'file-detail-table', 'aria-label': 'Danh sách tệp'},
      el('thead', {}, el('tr', {}, ...['Tên', 'Loại', 'Kích thước', 'Thao tác'].map(title => el('th', {scope: 'col'}, title)))), body);
    const shown = search.value ? filtered() : files.filter(f => f.path.slice(0, Math.max(0, f.path.lastIndexOf('/'))) === folder && (folder || !f.path.includes('/')));
    const prefix = folder ? folder + '/' : '';
    const directories = [...new Set(files.filter(f => f.path.startsWith(prefix)).map(f => f.path.slice(prefix.length).split('/')).filter(parts => parts.length > 1).map(parts => parts[0]))];
    if (!search.value) for (const name of directories.sort()) body.append(el('tr', {class: 'folder-row'},
      el('td', {}, el('button', {type: 'button', class: 'file-name-button', onclick: () => selectFolder(prefix + name)}, '▸ ' + name)),
      el('td', {}, 'Thư mục'), el('td', {}, '—'), el('td')));
    for (const file of shown) body.append(el('tr', {class: 'file-row'},
      el('td', {}, el('button', {type: 'button', class: 'file-name-button', onclick: () => safe(() => openFile(file.path))}, basename(file.path)),
        el('small', {class: 'file-relative-path'}, file.path)),
      el('td', {}, file.path.split('.').pop().toUpperCase()),
      el('td', {}, `${(file.size/1024).toFixed(1)} KB`), el('td', {}, actions(file))));
    content.replaceChildren(el('h3', {}, folder || 'Project'), table);
    if (!shown.length && !directories.length) content.append(el('p', {class: 'empty-state'}, 'Thư mục chưa có tệp.'));
  }
  function drawTree() {
    const focusLabel = tree.contains(document.activeElement) ? document.activeElement.getAttribute('aria-label') : null;
    const hierarchy = {folders: new Map(), files: []};
    for (const file of filtered()) {
      const parts = file.path.split('/'); parts.pop(); let node = hierarchy;
      for (const part of parts) {
        if (!node.folders.has(part)) node.folders.set(part, {folders: new Map(), files: []});
        node = node.folders.get(part);
      }
      node.files.push(file);
    }
    const branch = (node, prefix = '', depth = 0) => {
      const group = el('div', {role: 'group', class: 'tree-branch'});
      for (const [name, child] of [...node.folders].sort((a,b) => a[0].localeCompare(b[0]))) {
        const path = prefix ? prefix + '/' + name : name;
        const open = expanded.has(path) || search.value || (depth === 0 && !collapsed.has(path));
        const summary = el('summary', {role: 'treeitem', tabindex: '0', 'aria-label': path, 'aria-selected': String(!selectedPath && folder === path), onclick: () => {
          loadRevision++;
          folder = path; selectedPath = null; mode = 'folder'; locationLabel.textContent = path; drawFolder();
          for (const item of tree.querySelectorAll('[aria-selected]')) item.setAttribute('aria-selected', String(item === summary));
        }}, name);
        const details = el('details', {class: 'tree-folder', open: open ? '' : null}, summary, branch(child, path, depth+1));
        details.ontoggle = () => { if (details.isConnected) {
          if (details.open) { expanded.add(path); collapsed.delete(path); } else { expanded.delete(path); collapsed.add(path); }
          summary.setAttribute('aria-expanded', String(details.open));
        } };
        summary.setAttribute('aria-expanded', String(!!open)); group.append(details);
      }
      for (const file of node.files) group.append(el('button', {type: 'button', role: 'treeitem', 'aria-label': file.path, 'aria-selected': String(selectedPath === file.path), onclick: () => safe(() => openFile(file.path))}, basename(file.path)));
      return group;
    };
    tree.replaceChildren(el('button', {type: 'button', role: 'treeitem', 'aria-label': 'Project', 'aria-selected': String(!selectedPath && !folder), onclick: () => selectFolder('')}, 'Project'), branch(hierarchy));
    if (focusLabel) tree.querySelector(`[aria-label="${CSS.escape(focusLabel)}"]`)?.focus({preventScroll: true});
  }
  tree.onkeydown = event => {
    const items = [...tree.querySelectorAll('[role=treeitem]')].filter(e => e.offsetHeight);
    const index = items.indexOf(document.activeElement);
    if (['ArrowUp','ArrowDown','Home','End'].includes(event.key)) {
      event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length-1 : Math.max(0,Math.min(items.length-1,index+(event.key==='ArrowDown'?1:-1)));
      items[next]?.focus();
    } else if (['ArrowLeft','ArrowRight'].includes(event.key)) {
      const details = document.activeElement.closest('details'); if (details) { event.preventDefault(); details.open = event.key === 'ArrowRight'; }
    }
  };
  async function sync() {
    files = await getJSON(base + '/files'); drawTree();
    if (mode === 'folder') drawFolder(); // retain editor drafts and focus during SSE
  }
  search.oninput = () => { drawTree(); if (mode === 'folder') drawFolder(); };
  upload.onchange = () => safe(async () => {
    const file = upload.files[0]; if (!file) return;
    if (file.size > 16*1024*1024) throw new Error('Upload tối đa 16 MB mỗi tệp.');
    const encoded = await new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload=()=>resolve(reader.result.split(',')[1]); reader.onerror=reject; reader.readAsDataURL(file); });
    const path = [folder,file.name].filter(Boolean).join('/');
    await requestJSON(base + '/files/write', {path,content:encoded,encoding:'base64'});
    upload.value=''; status.textContent='Đã upload'; await changed(); await openFile(path);
  });
  dialog.append(el('header', {class: 'dialog-header'}, el('h2', {}, 'Quản lý tệp'), el('button', {type: 'button', onclick: () => dialog.close()}, 'Đóng')),
    el('div', {class: 'file-toolbar'}, search, el('button', {type: 'button', onclick: () => safe(() => edit(null))}, 'Tạo tệp'),
      el('button', {type: 'button', onclick: () => upload.click()}, 'Upload')), upload, locationLabel, status,
    el('div', {class: 'file-detail-workspace'}, tree, content));
  document.body.append(dialog); dialog.showModal(); safe(sync);
  const feed = subscribe(base + '/events', () => safe(sync));
  dialog.addEventListener('close', () => { feed.close(); dialog.remove(); });
}
