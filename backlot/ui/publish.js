import {el, mediaURL} from '/ui/lib.js';

let selectedRatio = 'portrait';
// Keep pending requests across the board's SSE-driven DOM replacements.
const copyRequests = new Map();
const copyViews = new Map();

function copyField(label, value, regenerate = null) {
  const button = el('button', {type: 'button', disabled: value ? null : '', onclick: async () => {
    try {
      await navigator.clipboard.writeText(field.value);
      button.textContent = 'Đã sao chép';
    } catch {
      field.focus(); field.select();
      button.textContent = 'Chọn nội dung để sao chép';
    }
  }}, 'Sao chép');
  const field = el('textarea', {readonly: '', rows: label.includes('path') ? '2' : '4', 'aria-label': label}, value || 'Chưa có nội dung');
  const actions = el('div', {class: 'posting-actions'}, button);
  if (regenerate) {
    const key = `${regenerate.projectId}:${regenerate.field}`;
    const retry = el('button', {type: 'button', onclick: () => {
      if (!copyRequests.get(key)?.busy) openCopyDialog(regenerate.projectId, regenerate.field, regenerate.package, regenerate.onUpdated);
    }}, regenerate.label);
    const status = el('p', {role: 'alert', hidden: ''});
    const update = (request) => {
      retry.disabled = !!request?.busy;
      retry.setAttribute('aria-busy', String(!!request?.busy));
      retry.classList.toggle('copy-busy', !!request?.busy);
      status.textContent = request?.error || '';
      status.hidden = !request?.error;
      if (request?.content != null) {
        field.value = request.content; button.disabled = false;
        regenerate.package[regenerate.field] = request.content;
        regenerate.package.revisions[regenerate.field] = request.revision;
      }
    };
    copyViews.set(key, update);
    update(copyRequests.get(key));
    actions.append(retry, status);
  }
  return el('div', {class: 'posting-field'}, el('div', {class: 'posting-label'}, el('strong', {}, label), actions), field);
}

function openCopyDialog(projectId, field, p, onUpdated) {
  const label = field === 'caption' ? 'caption' : 'description';
  const dialog = el('dialog', {class: 'copy-dialog', 'aria-labelledby': 'copy-dialog-title'});
  const input = el('textarea', {id: 'copy-instruction', rows: '6', maxlength: '4000', placeholder: 'Ví dụ: mở đầu bằng câu hỏi gây tò mò, viết ngắn hơn và thêm lời mời bình luận.'});
  const status = el('p', {role: 'status', 'aria-live': 'polite'});
  const submit = el('button', {type: 'button'}, 'Tạo lại');
  const close = el('button', {type: 'button', onclick: () => dialog.close()}, 'Đóng');
  dialog.addEventListener('close', () => dialog.remove());
  submit.addEventListener('click', async () => {
    const instruction = input.value.trim();
    if (!instruction) { status.textContent = 'Hãy nhập yêu cầu chỉnh sửa.'; input.focus(); return; }
    const key = `${projectId}:${field}`;
    if (copyRequests.get(key)?.busy) return;
    const expectedRevision = p.revisions[field];
    const request = {busy: true};
    copyRequests.set(key, request);
    copyViews.get(key)?.(request);
    dialog.close();
    try {
      const response = await fetch(`/api/project/${encodeURIComponent(projectId)}/posting-copy/regenerate`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({field, instruction, expected_revision: expectedRevision}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Yêu cầu không hợp lệ. Hãy tải lại trang rồi thử lại.');
      p[field] = data.content; p.revisions[field] = data.revision;
      request.content = data.content; request.revision = data.revision;
      copyViews.get(key)?.(request);
      if (onUpdated) await onUpdated();
    } catch (error) {
      request.error = error.message || 'Không gửi được yêu cầu. Hãy thử lại.';
    } finally {
      request.busy = false;
      copyViews.get(key)?.(request);
      // Successful content is persisted on the server, not a client override.
      if (!request.error) copyRequests.delete(key);
    }
  });
  dialog.append(el('h2', {id: 'copy-dialog-title'}, `Tạo lại ${label}`),
    el('label', {for: 'copy-instruction'}, 'Yêu cầu chỉnh sửa'), input, status,
    el('div', {class: 'posting-actions'}, close, submit));
  document.body.append(dialog); dialog.showModal(); input.focus();
}

export function renderPublishPackage(s, projectId, onUpdated = null) {
  const p = s.publish_package;
  if (!p || !s.stages.some(stage => stage.name === 'publish' && stage.status === 'completed')) return null;
  const section = el('section', {class: 'posting-package', 'aria-label': 'Hỗ trợ đăng video'},
    el('h2', {}, 'Hỗ trợ đăng video'),
    copyField('Tiêu đề video', p.title),
    copyField('Description · YouTube', p.description, {label: 'Tạo lại description', projectId, field: 'description', package: p, onUpdated}),
    copyField('Caption · Facebook / TikTok', p.caption, {label: 'Tạo lại caption', projectId, field: 'caption', package: p, onUpdated}));
  if (p.copy_warning) section.append(el('p', {role: 'alert'}, p.copy_warning));
  const thumbnails = el('div', {class: 'posting-thumbnails'});
  for (const thumb of p.thumbnails || []) {
    thumbnails.append(el('div', {},
      el('a', {href: mediaURL(projectId, thumb.path), target: '_blank', rel: 'noopener'},
        el('img', {src: mediaURL(projectId, thumb.path), alt: thumb.label || 'Thumbnail', loading: 'lazy'})),
      thumb.generated ? null : el('p', {class: 'posting-note'}, 'Thumbnail cũ · chưa xác minh tạo bằng image-generate'),
      copyField('Thumbnail path', thumb.absolute_path)));
  }
  section.append(el('h3', {}, 'Thumbnail'), thumbnails);
  if (!p.thumbnails?.length) section.append(el('p', {}, 'Chưa có thumbnail.'));
  const tabs = el('div', {role: 'tablist', 'aria-label': 'Tỷ lệ video', class: 'posting-tabs'});
  const preview = el('div', {class: 'posting-preview'});
  const available = Object.keys(p.videos || {});
  if (!available.includes(selectedRatio)) selectedRatio = available[0];
  function select(ratio) {
    selectedRatio = ratio;
    for (const button of tabs.children) button.setAttribute('aria-selected', String(button.dataset.ratio === ratio));
    preview.replaceChildren();
    const video = p.videos[ratio];
    if (!video) return;
    preview.append(el('video', {controls: '', preload: 'metadata', src: mediaURL(projectId, video.path), class: ratio}),
      el('a', {href: mediaURL(projectId, video.path), download: ''}, 'Tải video'),
      copyField('Video path', video.absolute_path));
  }
  for (const ratio of available) tabs.append(el('button', {type: 'button', role: 'tab', 'data-ratio': ratio, onclick: () => select(ratio)}, ratio === 'portrait' ? 'Dọc · 9:16' : 'Ngang · 16:9'));
  section.append(el('h3', {}, 'Video đã xuất'), tabs, preview);
  if (selectedRatio) select(selectedRatio);
  return section;
}
