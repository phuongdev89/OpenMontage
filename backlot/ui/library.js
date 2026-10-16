import { el, fmtAgo, getJSON, subscribe, thumbURL, postedProgress } from "/ui/lib.js";

const grid = document.getElementById("grid");
const THEME_KEY = "backlot.theme";
let currentTheme = localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
let view = localStorage.getItem('backlot.libraryView') === 'item' ? 'item' : 'grid';
let projects = [];
const search = el('input', {type: 'search', placeholder: 'Tìm project…', 'aria-label': 'Tìm project'});
const filter = el('select', {'aria-label': 'Lọc trạng thái'},
  el('option', {value: ''}, 'Tất cả'),
  el('option', {value: 'cleaned'}, 'Đã dọn'),
  el('option', {value: 'posted'}, 'Đã đăng'),
  el('option', {value: 'published'}, 'Sẵn sàng đăng'),
  el('option', {value: 'awaiting'}, 'Chờ duyệt'),
  el('option', {value: 'live'}, 'Đang chạy'));
const views = el('div', {class: 'view-switch', role: 'group', 'aria-label': 'Kiểu hiển thị'});
for (const [value, label] of [['grid', 'Grid view'], ['item', 'Item view']]) views.append(el('button', {type: 'button', 'data-view': value, onclick: () => {
  view = value; localStorage.setItem('backlot.libraryView', view); draw();
}}, label));
const toolbar = el('div', {class: 'library-toolbar'}, search, filter, views);
grid.before(toolbar);
search.oninput = draw; filter.onchange = draw;

function applyTheme(theme) {
  currentTheme = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = currentTheme;
  localStorage.setItem(THEME_KEY, currentTheme);
}

function renderThemeToggle() {
  const next = currentTheme === "light" ? "dark" : "light";
  return el("button", {
    class: "theme-toggle",
    type: "button",
    title: `Switch to ${next} theme`,
    "aria-label": `Switch to ${next} theme`,
    "aria-pressed": currentTheme === "light" ? "true" : "false",
    onclick: () => {
      applyTheme(next);
      const replacement = renderThemeToggle();
      document.querySelector(".theme-toggle").replaceWith(replacement);
    },
  }, el("span", { class: "theme-toggle-icon", "aria-hidden": "true" }, currentTheme === "light" ? "☾" : "☀"));
}

applyTheme(currentTheme);
document.getElementById("liveBadge").before(renderThemeToggle());

function miniRail(states, projectId) {
  const rail = el("div", { class: "mini-rail" });
  for (const s of states) {
    const cls = s.status === "completed" ? "d"
      : s.status === "in_progress" ? "a"
      : s.status === "awaiting_human" ? "w" : "";
    const marker = el("i", { class: cls, title: `${s.name}: ${s.status}` });
    rail.append(marker);
    if (s.name === 'posted' && s.status === 'awaiting_human') {
      // Only partial manual milestones need platform details; the library's
      // lightweight summary already represents empty and completed milestones.
      getJSON(`/api/project/${encodeURIComponent(projectId)}/state`).then(state => {
        const progress = postedProgress(state.posting_status);
        marker.className = `posted-${progress.platform}`;
        marker.title = progress.label;
      }).catch(error => console.error('Không đọc được trạng thái đăng', error));
    }
  }
  return rail;
}

function card(p, index = 0) {
  const poster = el("div", { class: "lib-poster" });
  if (p.poster) {
    const isLcp = index === 0;
    poster.append(el("img", {
      src: thumbURL(p.project_id, p.poster, 640),
      loading: isLcp ? "eager" : "lazy",
      fetchpriority: isLcp ? "high" : null,
      alt: "",
    }));
  } else {
    poster.append(el("span", { class: "lp-txt" }, "NO MEDIA YET"));
  }
  if (p.last_activity) poster.append(el('span', {
    class: 'lp-when', title: new Date(p.last_activity * 1000).toLocaleString(),
  }, fmtAgo(p.last_activity)));
  if (p.is_cleaned) {
    poster.append(el("span", { class: "lp-cleaned" }, "✓ ĐÃ DỌN"));
  } else if (p.live && p.active_stage) {
    poster.append(el("span", { class: "lp-live" },
      el("span", { class: "dot" }),
      p.awaiting_human ? "◈ AWAITING YOU" : `LIVE · ${p.active_stage.toUpperCase()}`));
  } else if (p.awaiting_human) {
    poster.append(el("span", { class: "lp-live" }, "◈ AWAITING YOU"));
  }

  const meta = el("div", { class: "lb-meta" },
    el("span", { class: "chip" }, p.pipeline_type || "unknown"),
    p.scene_count ? el("span", { class: "chip" }, `${p.scene_count} scenes`) : null,
  );

  const staticSuffix = new URLSearchParams(location.search).has("static") ? "?static=1" : "";
  return el("a", { class: `lib-card${p.live ? " live-card" : ""}`, href: `/p/${p.project_id}${staticSuffix}`, style: "text-decoration:none;color:inherit" },
    poster,
    el("div", { class: "lib-body" },
      el("h3", {}, p.title || p.project_id),
      meta,
      p.stage_states.length ? miniRail(p.stage_states, p.project_id) : null,
    ),
  );
}

function projectTable(items) {
  const body = el('tbody');
  const table = el('table', {class: 'projects-table', 'aria-label': 'Danh sách project'},
    el('thead', {}, el('tr', {}, ...['Project', 'Pipeline', 'Trạng thái', 'Cập nhật'].map((name, i) =>
      el('th', {scope: 'col', class: `column-${i}`}, name)))), body);
  for (const [i, p] of items.entries()) {
    const isCleaned = Boolean(p.is_cleaned);
    const done = p.stage_states.some(s => s.name === 'publish' && s.status === 'completed');
    const posted = p.stage_states.some(s => s.name === 'posted' && s.status === 'completed');
    const status = isCleaned ? 'Đã dọn' : posted ? 'Đã đăng' : done ? 'Sẵn sàng đăng' : p.awaiting_human ? 'Chờ duyệt' : p.active_stage ? p.active_stage : 'Chưa publish';
    const staticSuffix = new URLSearchParams(location.search).has('static') ? '?static=1' : '';
    const isLcp = i === 0;
    const poster = p.poster ? el('img', {
      class: 'table-poster',
      src: thumbURL(p.project_id, p.poster, 320),
      loading: isLcp ? 'eager' : 'lazy',
      fetchpriority: isLcp ? 'high' : null,
      alt: '',
    }) : null;
    body.append(el('tr', {'data-project': p.project_id},
      el('td', {class: 'column-0'}, el('a', {class: 'table-project', href: `/p/${encodeURIComponent(p.project_id)}${staticSuffix}`},
        poster, el('div', {}, el('strong', {}, p.title || p.project_id),
          el('small', {}, `${p.scene_count || 0} cảnh · ${p.render_count || 0} video`)))),
      el('td', {class: 'column-1'}, p.pipeline_type || 'unknown'),
      el('td', {class: 'column-2'}, el('span', {class: isCleaned ? 'table-cleaned' : done ? 'table-published' : ''}, status)),
      el('td', {class: 'column-3'}, fmtAgo(p.last_activity) || '—')));
  }
  return table;
}

async function render() {
  projects = await getJSON("/api/projects");
  draw();
}

function draw() {
  document.getElementById("count").textContent = `${projects.length} projects`;
  const liveCount = projects.filter((p) => p.live).length;
  const badge = document.getElementById("liveBadge");
  badge.classList.toggle("idle", liveCount === 0);
  document.getElementById("liveText").textContent = liveCount ? `${liveCount} LIVE` : "IDLE";
  grid.innerHTML = "";
  grid.classList.toggle('lib-table', view === 'grid');
  grid.classList.remove('lib-items');
  for (const button of views.children) button.setAttribute('aria-pressed', String(button.dataset.view === view));
  document.getElementById("empty").style.display = projects.length ? "none" : "block";
  const shown = projects.filter(p => (p.title + ' ' + p.project_id).toLowerCase().includes(search.value.toLowerCase()) &&
    (!filter.value || (
      filter.value === 'cleaned' ? p.is_cleaned :
      filter.value === 'posted' ? p.stage_states.some(s => s.name === 'posted' && s.status === 'completed') :
      filter.value === 'published' ? p.stage_states.some(s => s.name === 'publish' && s.status === 'completed') :
      filter.value === 'awaiting' ? p.awaiting_human :
      p.live
    )));
  if (view === 'grid' && shown.length) grid.append(projectTable(shown));
  else for (const [i, p] of shown.entries()) grid.append(card(p, i));
  if (!shown.length && projects.length) grid.append(el('p', {class: 'empty-state'}, 'Không có project khớp bộ lọc.'));
}

render().catch(console.error);
if (!new URLSearchParams(location.search).has("static")) {
  subscribe("/api/library/events", () => render().catch(console.error));
}
