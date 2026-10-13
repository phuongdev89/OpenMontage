import {el, mediaURL} from '/ui/lib.js';
import {requestJSON} from '/ui/workspace.js';
import {openProjectGallery} from '/ui/gallery.js';

// Keep pending requests across the board's SSE-driven DOM replacements.
const copyRequests = new Map();
const copyViews = new Map();
const supportRequests = new Map();
const postingTabs = new Map();

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
  const field = el('textarea', {readonly: '', rows: label.includes('path') || label === 'Tiêu đề video' ? '2' : '5', 'aria-label': label}, value || 'Chưa có nội dung');
  const actions = el('div', {class: 'posting-actions'}, button);
  if (regenerate?.editable) field.removeAttribute('readonly');
  if (regenerate?.editable && regenerate.projectId) {
    const key = `backlot.promptDraft.${regenerate.projectId}`;
    try {
      const saved = JSON.parse(localStorage.getItem(key) || 'null');
      if (saved?.source === value) field.value = saved.content;
    } catch {}
    field.oninput = () => localStorage.setItem(key, JSON.stringify({source: value, content: field.value}));
  }
  if (regenerate && !regenerate.editable) {
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
    el('a', {href: `/api/project/${encodeURIComponent(projectId)}/download`, download: ''}, 'Tải project (.zip)'),
    copyField('Tiêu đề video', p.title),
    copyField('Description · YouTube', p.description, {label: 'Tạo lại description', projectId, field: 'description', package: p, onUpdated}),
    copyField('Caption · Facebook / TikTok', p.caption, {label: 'Tạo lại caption', projectId, field: 'caption', package: p, onUpdated}));
  const pending = supportRequests.get(projectId);
  const supportStatus = el('p', {role: 'status'}, pending?.error || '');
  const create = el('button', {type: 'button', disabled: pending?.busy ? '' : null, 'aria-busy': String(!!pending?.busy), onclick: async () => {
    if (supportRequests.get(projectId)?.busy) return;
    const request = {busy: true}; supportRequests.set(projectId, request);
    create.disabled = true; create.setAttribute('aria-busy', 'true'); create.textContent = 'Đang tạo…';
    try {
      const result = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/posting-support`, {expected_revision: p.support_revision});
      supportStatus.textContent = result.message || 'Đã tạo nội dung còn thiếu';
      if (onUpdated) await onUpdated();
    } catch(error) { request.error = error.message; supportStatus.textContent = request.error; }
    finally { request.busy = false; create.disabled = false; create.setAttribute('aria-busy', 'false'); create.textContent = 'Tạo hỗ trợ'; if (onUpdated) await onUpdated(); }
  }}, pending?.busy ? 'Đang tạo…' : 'Tạo hỗ trợ');
  const download = section.querySelector('a[download]');
  section.querySelector('h2').after(el('div', {class: 'posting-create'}, create, download), supportStatus);
  const contentPanel = el('div', {class: 'posting-subpanel', role: 'tabpanel', id: `posting-copy-${projectId}`});
  for (const field of section.querySelectorAll(':scope > .posting-field')) contentPanel.append(field);
  const thumbnailPanel = el('div', {class: 'posting-subpanel', role: 'tabpanel', id: `posting-thumb-${projectId}`});
  const tablist = el('div', {class: 'posting-work-tabs', role: 'tablist', 'aria-label': 'Hỗ trợ đăng'});
  const panels = {copy: contentPanel, thumb: thumbnailPanel};
  const selectTab = key => {
    postingTabs.set(projectId, key);
    for (const [name, panel] of Object.entries(panels)) panel.hidden = name !== key;
    for (const tab of tablist.children) {
      const selected = tab.dataset.tab === key;
      tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1;
    }
  };
  for (const [key, name] of [['copy', 'Nội dung'], ['thumb', 'Thumbnail']]) {
    const tab = el('button', {type: 'button', role: 'tab', 'data-tab': key, id: `posting-tab-${key}-${projectId}`, 'aria-controls': panels[key].id, onclick: () => selectTab(key)}, name);
    panels[key].setAttribute('aria-labelledby', tab.id);
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); const next = key === 'copy' ? 'thumb' : 'copy'; selectTab(next); tablist.querySelector(`[data-tab=${next}]`).focus();
    });
    tablist.append(tab);
  }
  section.append(tablist, contentPanel, thumbnailPanel);
  selectTab(postingTabs.get(projectId) || 'copy');
  if (p.copy_warning) section.append(el('p', {role: 'alert'}, p.copy_warning));
  const thumbnails = el('div', {class: 'posting-thumbnails'});
  for (const thumb of p.thumbnails || []) {
    const selectStatus = el('p', {role: 'status'});
    const choose = thumb.selected ? el('span', {class: 'selected-thumbnail'}, '✓ Thumbnail đang chọn') : el('button', {type: 'button', onclick: async () => {
      choose.disabled = true;
      try { await requestJSON(`/api/project/${encodeURIComponent(projectId)}/thumbnail`, {path: thumb.path}); if (onUpdated) await onUpdated(); }
      catch(error) { selectStatus.textContent = error.message; choose.disabled = false; }
    }}, 'Chọn làm thumbnail');
    thumbnails.append(el('figure', {class: `thumbnail-candidate${thumb.selected ? ' is-selected' : ''}`},
      el('button', {type: 'button', class: 'gallery-thumb', 'aria-label': `Xem ${thumb.label || thumb.path}`, onclick: () => openProjectGallery(projectId, thumb.path)},
        el('img', {src: mediaURL(projectId, thumb.path), alt: thumb.label || 'Thumbnail', loading: 'lazy'})),
      thumb.generated ? null : el('p', {class: 'posting-note'}, 'Chưa có metadata tạo ảnh'),
      choose, selectStatus,
      el('details', {class: 'technical-path'}, el('summary', {}, 'Đường dẫn ảnh'), copyField('Thumbnail path', thumb.absolute_path))));
  }
  thumbnailPanel.append(
    copyField('Prompt tạo thumbnail · có thể sửa để gen thủ công', p.thumbnail_prompt || p.thumbnails?.find(t => t.prompt)?.prompt || '', {editable: true, projectId}));
  if (p.thumbnail_prompt_source === 'draft') thumbnailPanel.append(el('p', {class: 'posting-note'}, 'Prompt nháp · Tạo hỗ trợ để bổ sung cảnh hook theo video.'));
  if (p.thumbnail_prompt_source === 'prepared') thumbnailPanel.append(el('p', {class: 'posting-note'}, 'Prompt đã chuẩn bị để tạo ảnh thủ công.'));
  thumbnailPanel.append(thumbnails);
  if (!p.thumbnails?.length) thumbnailPanel.append(el('p', {}, 'Chưa có thumbnail.'));
  return section;
}

const titleEdits = new Map();
const titleMounts = new Map();
export function renderTitleEditor(s, projectId, onUpdated) {
  const root = el('div', {class: 'project-title'});
  const editable = s.stages.some(x => ['compose', 'publish'].includes(x.name) && x.status === 'completed');
  const draw = () => {
    const edit = titleEdits.get(projectId);
    root.replaceChildren();
    if (!edit) {
      const heading = el('h1', {tabindex: editable ? '0' : null, title: editable ? 'Nhấn đúp hoặc F2 để sửa tên' : null}, s.title);
      const start = () => {
        if (!editable) return;
        titleEdits.set(projectId, {value: s.title, expected: s.title, busy: false});
        draw(); root.querySelector('input').focus(); root.querySelector('input').select();
      };
      heading.ondblclick = start;
      heading.onkeydown = event => { if (['Enter', 'F2'].includes(event.key)) { event.preventDefault(); start(); } };
      root.append(heading); return;
    }
    const input = el('input', {value: edit.value, maxlength: '300', 'aria-label': 'Tên project trên Backlot', disabled: edit.busy ? '' : null});
    input.oninput = () => { edit.value = input.value; };
    const cancel = () => { if (edit.busy) return; titleEdits.delete(projectId); titleMounts.get(projectId)?.(); };
    const save = async () => {
      if (edit.busy) return;
      edit.busy = true; edit.error = ''; titleMounts.get(projectId)?.();
      try {
        const data = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/title`, {title: edit.value, expected_title: edit.expected});
        s.title = data.title; titleEdits.delete(projectId); titleMounts.get(projectId)?.();
        if (onUpdated) await onUpdated();
      } catch(error) { edit.error = error.message; }
      finally { edit.busy = false; titleMounts.get(projectId)?.(); }
    };
    input.onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); save(); } if (event.key === 'Escape') { event.preventDefault(); cancel(); } };
    root.append(el('div', {class: 'title-edit-row'}, input,
      el('button', {type: 'button', disabled: edit.busy ? '' : null, 'aria-busy': String(edit.busy), onclick: save}, edit.busy ? 'Đang lưu…' : 'Lưu tiêu đề'),
      el('button', {type: 'button', disabled: edit.busy ? '' : null, onclick: cancel}, 'Hủy')));
    if (edit.error) root.append(el('p', {role: 'alert'}, edit.error));
  };
  titleMounts.set(projectId, draw); draw(); return root;
}
