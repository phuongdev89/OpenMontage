import {el, mediaURL} from '/ui/lib.js';

let selectedRatio = 'portrait';

function copyField(label, value, regenerate = null) {
  const button = el('button', {type: 'button', disabled: value ? null : '', onclick: async () => {
    try {
      await navigator.clipboard.writeText(value);
      button.textContent = 'Đã sao chép';
    } catch {
      field.focus(); field.select();
      button.textContent = 'Chọn nội dung để sao chép';
    }
  }}, 'Sao chép');
  const field = el('textarea', {readonly: '', rows: label.includes('path') ? '2' : '4', 'aria-label': label}, value || 'Chưa có nội dung');
  const actions = el('div', {class: 'posting-actions'}, button);
  if (regenerate) actions.append(el('button', {type: 'button', onclick: regenerate.run}, regenerate.label));
  return el('div', {class: 'posting-field'}, el('div', {class: 'posting-label'}, el('strong', {}, label), actions), field);
}

function openCopyDialog(projectId, field, p, onUpdated) {
  const label = field === 'caption' ? 'caption' : 'description';
  const dialog = el('dialog', {class: 'copy-dialog', 'aria-labelledby': 'copy-dialog-title'});
  const input = el('textarea', {id: 'copy-instruction', rows: '6', maxlength: '4000', placeholder: 'Ví dụ: mở đầu bằng câu hỏi gây tò mò, viết ngắn hơn và thêm lời mời bình luận.'});
  const status = el('p', {role: 'status', 'aria-live': 'polite'});
  const result = el('textarea', {readonly: '', rows: '8', 'aria-label': 'Nội dung mới đã lưu', hidden: ''});
  const submit = el('button', {type: 'button'}, 'Tạo lại');
  const close = el('button', {type: 'button', onclick: () => dialog.close()}, 'Đóng');
  let busy = false;
  dialog.addEventListener('cancel', e => { if (busy) e.preventDefault(); });
  dialog.addEventListener('close', () => dialog.remove());
  submit.addEventListener('click', async () => {
    const instruction = input.value.trim();
    if (!instruction) { status.textContent = 'Hãy nhập yêu cầu chỉnh sửa.'; input.focus(); return; }
    busy = true; submit.disabled = true; close.disabled = true; input.disabled = true;
    status.textContent = 'AI đang tạo nội dung…';
    try {
      const response = await fetch(`/api/project/${encodeURIComponent(projectId)}/posting-copy/regenerate`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({field, instruction, expected_revision: p.revisions[field]}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Yêu cầu không hợp lệ. Hãy tải lại trang rồi thử lại.');
      p[field] = data.content; p.revisions[field] = data.revision;
      result.value = data.content; result.hidden = false;
      status.textContent = 'Đã tạo và lưu nội dung mới cho project này.';
      if (onUpdated) await onUpdated();
    } catch (error) {
      status.textContent = error.message || 'Không gửi được yêu cầu. Hãy thử lại.';
    } finally {
      busy = false; submit.disabled = false; close.disabled = false; input.disabled = false;
    }
  });
  dialog.append(el('h2', {id: 'copy-dialog-title'}, `Tạo lại ${label}`),
    el('label', {for: 'copy-instruction'}, 'Yêu cầu chỉnh sửa'), input, status, result,
    el('div', {class: 'posting-actions'}, close, submit));
  document.body.append(dialog); dialog.showModal(); input.focus();
}

export function renderPublishPackage(s, projectId, onUpdated = null) {
  const p = s.publish_package;
  if (!p || !s.stages.some(stage => stage.name === 'publish' && stage.status === 'completed')) return null;
  const section = el('section', {class: 'posting-package', 'aria-label': 'Hỗ trợ đăng video'},
    el('h2', {}, 'Hỗ trợ đăng video'),
    copyField('Tiêu đề video', p.title),
    copyField('Description · YouTube', p.description, {label: 'Tạo lại description', run: () => openCopyDialog(projectId, 'description', p, onUpdated)}),
    copyField('Caption · Facebook / TikTok', p.caption, {label: 'Tạo lại caption', run: () => openCopyDialog(projectId, 'caption', p, onUpdated)}));
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
