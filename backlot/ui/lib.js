// Shared helpers for the Backlot UI.

export async function getJSON(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.json();
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child == null) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  // Decorative CSS masks survive textContent updates (copy/saving/busy states).
  // Leave image buttons, existing glyph controls and player chrome alone.
  if ((tag === 'button' || (tag === 'a' && (attrs.class?.includes('studio-button') || attrs.download != null))) && !attrs['data-icon']) {
    const label = children.flat().filter(child => typeof child === 'string').join(' ').trim();
    const icons = [
      [/^(Sao chép|Copy)/i, 'copy'], [/^(Tải|Download)/i, 'download'],
      [/^(Tạo lại|Regenerate|Refresh)/i, 'refresh'], [/^(Lưu|Save)/i, 'save'],
      [/^(Xóa|Delete)/i, 'trash'], [/^(Đóng|Hủy|Close|Cancel)/i, 'close'],
      [/^(Quản lý|Về thư mục|Mở thư mục)/i, 'folder'],
      [/^(Tạo|Thêm|Upload)/i, 'plus'], [/^(Sửa|Đổi|Edit)/i, 'edit'],
      [/^(Hoàn tác|Undo)/i, 'undo'], [/^(Đánh dấu|Đã đăng|Xác nhận|Chọn làm)/i, 'check'],
      [/^(Thumbnail|Ảnh)/i, 'image'], [/^(Caption|Description|Nội dung)/i, 'text'],
      [/^Grid view$/i, 'list'], [/^Item view$/i, 'grid'],
    ];
    const match = icons.find(([pattern]) => pattern.test(label));
    if (match) node.setAttribute('data-icon', match[1]);
  }
  return node;
}

export function fmtDuration(seconds) {
  const n = Number(seconds);
  if (seconds == null || !Number.isFinite(n)) return "";
  const s = Math.max(0, Math.round(n));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

export function postedProgress(postingStatus) {
  const youtube = postingStatus?.platforms?.youtube?.confirmed === true;
  const facebook = postingStatus?.platforms?.facebook?.confirmed === true;
  return {
    count: Number(youtube) + Number(facebook),
    platform: youtube && facebook ? 'both' : youtube ? 'youtube' : facebook ? 'facebook' : 'none',
    label: `${Number(youtube) + Number(facebook)}/2 · YouTube ${youtube ? 'đã đăng' : 'chưa đăng'} · Facebook ${facebook ? 'đã đăng' : 'chưa đăng'}`,
  };
}

export function fmtMoney(v) {
  const n = Number(v);
  if (v == null || !Number.isFinite(n)) return "—";
  return `$${n.toFixed(2)}`;
}

export function fmtAgo(epochSeconds) {
  if (!epochSeconds) return "";
  const diff = Date.now() / 1000 - epochSeconds;
  if (diff < 90) return "just now";
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

export function fmtClock(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

export function mediaURL(projectId, relPath) {
  return `/media/${encodeURIComponent(projectId)}/${relPath.split("/").map(encodeURIComponent).join("/")}`;
}

// Downscaled cached JPEG for images (full media only in players/lightbox).
export function thumbURL(projectId, relPath, w = 640) {
  return `/thumb/${encodeURIComponent(projectId)}/${relPath.split("/").map(encodeURIComponent).join("/")}?w=${w}`;
}

// HTTP/1.1 has a small per-origin connection pool. Never reserve one SSE
// connection per tab: enough open boards would block state/media requests.
function sharedFeed() {
  const source = { onmessage: null, onerror: null };
  let worker = null;
  let poll = null;
  let closed = false;
  const fallback = () => {
    if (poll || closed) return;
    worker?.port.close();
    poll = setInterval(() => source.onmessage?.({ data: '{"type":"hello"}' }), 5000);
  };
  let lease = null;
  try {
    worker = new SharedWorker('/ui/realtime-worker.js', { name: 'backlot-realtime-v1' });
    worker.port.onmessage = event => source.onmessage?.(event);
    worker.onerror = () => { clearInterval(lease); fallback(); };
    worker.port.start();
    worker.port.postMessage('join');
    lease = setInterval(() => worker.port.postMessage('alive'), 15000);
  } catch {
    fallback();
  }
  source.close = () => {
    closed = true;
    clearInterval(poll);
    clearInterval(lease);
    if (worker) {
      worker.port.postMessage('leave');
      worker.port.close();
    }
  };
  return source;
}

// All tabs share the library feed; each refresh reads its own project state.
// Reconcile every board on a change because the library feed coalesces bursts.
export function subscribe(url, onChange) {
  let timer = null;
  let running = false;
  let pending = false;
  const source = sharedFeed();
  const update = async () => {
    if (running) { pending = true; return; }
    running = true;
    try {
      do {
        pending = false;
        await onChange();
      } while (pending);
    } catch (err) {
      console.error("Backlot refresh failed", err);
    } finally {
      running = false;
    }
  };
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(update, 250);
  };
  source.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      // A reconnect cannot replay events lost while the tab was disconnected.
      if (data.type !== "change" && data.type !== "hello") return;
    } catch {
      return;
    }
    schedule();
  };
  source.onerror = () => { /* EventSource auto-reconnects */ };
  const visible = () => { if (!document.hidden) schedule(); };
  document.addEventListener("visibilitychange", visible);
  const close = source.close.bind(source);
  const leaving = event => { if (!event.persisted) source.close(); };
  window.addEventListener('pagehide', leaving);
  source.close = () => {
    clearTimeout(timer);
    document.removeEventListener("visibilitychange", visible);
    window.removeEventListener('pagehide', leaving);
    close();
  };
  return source;
}

// Deterministic pseudo-waveform bars (seeded by a string).
export function waveBars(container, seedStr, count = 26, maxH = 14) {
  let seed = 0;
  for (const c of seedStr || "wave") seed = (seed * 31 + c.charCodeAt(0)) % 2147483647;
  seed = seed || 7;
  container.innerHTML = "";
  for (let i = 0; i < count; i++) {
    seed = (seed * 16807) % 2147483647;
    const h = 3 + ((seed % 100) / 100) * maxH * (0.55 + 0.45 * Math.sin(i / 5));
    const bar = document.createElement("i");
    bar.style.height = `${Math.max(3, h)}px`;
    container.append(bar);
  }
}

export const STAGE_ICONS = {
  completed: "✓",
  in_progress: "◉",
  awaiting_human: "◈",
  failed: "✕",
};
