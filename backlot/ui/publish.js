import {el, getJSON, mediaURL} from '/ui/lib.js';
import {requestJSON} from '/ui/workspace.js';
import {openProjectGallery} from '/ui/gallery.js';

// Keep pending requests across the board's SSE-driven DOM replacements.
const copyRequests = new Map();
const copyViews = new Map();
const supportRequests = new Map();
const postingTabs = new Map();
const videoTitles = new Map();
const manualCopies = new Map();
const postingEdits = new Map();

function videoTitleField(p, projectId) {
  let state = videoTitles.get(projectId);
  if (!state || (!state.busy && state.value === state.saved && !state.error)) {
    state = {value: p.title || '', saved: p.title || '', revision: p.revisions.title};
    videoTitles.set(projectId, state);
  }
  const root = copyField('Tiêu đề video', state.value);
  const field = root.querySelector('textarea');
  field.removeAttribute('readonly'); field.maxLength = 300;
  field.value = state.value;
  const status = el('span', {role: 'status'});
  root.querySelector('.posting-actions').append(status);
  state.show = () => {
    status.textContent = state.busy ? 'Đang lưu…' : state.error || (state.value === state.saved ? 'Đã lưu' : 'Rời ô để lưu');
    field.setAttribute('aria-busy', String(!!state.busy));
  };
  field.addEventListener('input', () => { state.value = field.value; state.error = ''; state.show(); });
  field.addEventListener('blur', async () => {
    state.queued = true;
    if (state.busy) return;
    while (state.queued) {
      state.queued = false;
      const title = state.value.trim();
      if (title === state.saved) continue;
      if (!title || /[\r\n]/.test(title)) { state.error = 'Tiêu đề cần có nội dung trên một dòng.'; state.show(); break; }
      state.busy = true; state.error = ''; state.show();
      try {
        const result = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/posting-copy/title`, {
          title, expected_revision: state.revision,
        });
        state.saved = result.content; state.revision = result.revision;
        p.title = result.content; p.revisions.title = result.revision;
      } catch(error) { state.error = error.message; state.queued = false; }
      finally { state.busy = false; state.show(); }
    }
  });
  state.show();
  return root;
}

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
  const rows = label.includes('path') || label === 'Tiêu đề video' ? '2' : label.includes('Prompt tạo thumbnail') ? '8' : '5';
  const field = el('textarea', {readonly: '', rows, 'aria-label': label}, value || 'Chưa có nội dung');
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
    let edit = manualCopies.get(key);
    if (!edit || (!edit.busy && edit.value === edit.saved && !edit.error)) {
      edit = {value: value || '', saved: value || '', revision: regenerate.package.revisions[regenerate.field]};
      manualCopies.set(key, edit);
    }
    field.removeAttribute('readonly'); field.maxLength = 50000;
    field.value = edit.value; field.placeholder = 'Nhập nội dung…';
    const savedStatus = el('span', {role: 'status', 'aria-live': 'polite'});
    const paint = () => {
      savedStatus.textContent = edit.busy ? 'Đang lưu…' : edit.error || (edit.value === edit.saved ? 'Đã lưu' : 'Rời ô để lưu');
      field.setAttribute('aria-busy', String(!!edit.busy));
      button.disabled = !field.value;
      retry.disabled = !!edit.busy || edit.value !== edit.saved || !!copyRequests.get(key)?.busy;
    };
    edit.show = paint;
    field.addEventListener('input', () => { edit.value = field.value; edit.error = ''; edit.show(); });
    field.addEventListener('blur', async () => {
      edit.queued = true;
      if (edit.busy) return;
      while (edit.queued) {
        edit.queued = false;
        const content = edit.value;
        if (content === edit.saved) continue;
        edit.busy = true; edit.error = ''; edit.show();
        try {
          const result = await requestJSON(`/api/project/${encodeURIComponent(regenerate.projectId)}/posting-copy/save`, {
            field: regenerate.field, content, expected_revision: edit.revision,
          });
          edit.saved = result.content; edit.revision = result.revision;
          regenerate.package[regenerate.field] = result.content;
          regenerate.package.revisions[regenerate.field] = result.revision;
        } catch(error) { edit.error = error.message; edit.queued = false; }
        finally { edit.busy = false; edit.show(); }
      }
    });
    const retry = el('button', {type: 'button', onclick: () => {
      if (!copyRequests.get(key)?.busy) openCopyDialog(regenerate.projectId, regenerate.field, regenerate.package, regenerate.onUpdated);
    }}, regenerate.label);
    const status = el('p', {role: 'alert', hidden: ''});
    const update = (request) => {
      retry.disabled = !!request?.busy || !!edit.busy || edit.value !== edit.saved;
      retry.setAttribute('aria-busy', String(!!request?.busy));
      retry.classList.toggle('copy-busy', !!request?.busy);
      status.textContent = request?.error || '';
      status.hidden = !request?.error;
      if (request?.content != null && !edit.busy && edit.value === edit.saved && !edit.error) {
        field.value = request.content; button.disabled = false;
        edit.value = request.content; edit.saved = request.content; edit.revision = request.revision;
        regenerate.package[regenerate.field] = request.content;
        regenerate.package.revisions[regenerate.field] = request.revision;
      }
      edit.show();
    };
    copyViews.set(key, update);
    update(copyRequests.get(key));
    actions.append(retry, savedStatus, status);
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

  const section = el('section', {class: 'posting-package', 'aria-label': 'Hỗ trợ đăng video'});

  const pending = supportRequests.get(projectId);
  const supportStatus = el('span', {role: 'status', class: 'posting-support-status'}, pending?.error || '');
  const create = el('button', {type: 'button', class: 'studio-button', disabled: pending?.busy ? '' : null, 'aria-busy': String(!!pending?.busy), onclick: async () => {
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

  const header = el('div', {class: 'posting-header'},
    el('h2', {}, 'Hỗ trợ đăng video'),
    el('div', {class: 'posting-header-actions'}, create, supportStatus)
  );
  section.append(header);

  // Tabpanels
  const youtubePanel = el('div', {class: 'posting-subpanel', role: 'tabpanel', id: `posting-yt-${projectId}`});
  const facebookPanel = el('div', {class: 'posting-subpanel', role: 'tabpanel', id: `posting-fb-${projectId}`});

  // Tab YouTube fields
  youtubePanel.append(
    videoTitleField(p, projectId),
    copyField('Description · YouTube', p.description, {label: 'Tạo lại description', projectId, field: 'description', package: p, onUpdated}),
    renderPlatformConfirm('youtube', 'YouTube', s.posting_status, projectId, onUpdated)
  );

  // Tab Facebook fields
  facebookPanel.append(
    copyField('Caption · Facebook / TikTok', p.caption, {label: 'Tạo lại caption', projectId, field: 'caption', package: p, onUpdated}),
    renderPlatformConfirm('facebook', 'Facebook', s.posting_status, projectId, onUpdated)
  );

  const thumbnailSection = renderThumbnailsSection(p, projectId, onUpdated);

  const tablist = el('div', {class: 'posting-work-tabs', role: 'tablist', 'aria-label': 'Nền tảng đăng'});
  const panels = {youtube: youtubePanel, facebook: facebookPanel};

  const selectTab = key => {
    postingTabs.set(projectId, key);
    for (const [name, panel] of Object.entries(panels)) {
      panel.hidden = name !== key;
    }
    panels[key].append(thumbnailSection);
    for (const tab of tablist.children) {
      const selected = tab.dataset.tab === key;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
  };

  for (const [key, name, icon] of [['youtube', 'YouTube', 'youtube'], ['facebook', 'Facebook', 'facebook']]) {
    const tab = el('button', {
      type: 'button', role: 'tab',
      'data-tab': key, 'data-icon': icon,
      id: `posting-tab-${key}-${projectId}`,
      'aria-controls': panels[key].id,
      onclick: () => selectTab(key),
    }, name);
    panels[key].setAttribute('aria-labelledby', tab.id);
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = key === 'youtube' ? 'facebook' : 'youtube';
      selectTab(next);
      tablist.querySelector(`[data-tab=${next}]`).focus();
    });
    tablist.append(tab);
  }

  section.append(tablist, youtubePanel, facebookPanel);

  const currentTab = postingTabs.get(projectId) || 'youtube';
  selectTab(panels[currentTab] ? currentTab : 'youtube');

  if (p.copy_warning) section.append(el('p', {role: 'alert'}, p.copy_warning));

  if (s.is_cleaned) {
    const manifest = s.completed_record?.cleanup_manifest || {};
    const freedMb = (manifest.bytes_freed ? manifest.bytes_freed / 1048576 : 0).toFixed(1);
    const freedCount = manifest.files_freed || 0;
    section.append(el('div', {class: 'cleanup-box cleaned-box'},
      el('div', {},
        el('strong', {}, '✓ Đã dọn project — lưu hồ sơ kinh nghiệm'),
        el('p', {style: 'margin-top:4px;font-size:13px;color:var(--color-ink-2)'},
          `Đã giải phóng ${freedMb} MB (${freedCount} tệp). Bản video local đã được thu hồi; kịch bản, prompt, lịch sử và embed được bảo toàn vĩnh viễn.`)
      )
    ));
  } else if (s.posting_status?.status === 'completed') {
    const cleanupBtn = el('button', {
      type: 'button',
      class: 'studio-button',
      onclick: () => openCleanupDialog(s, projectId, onUpdated),
    }, 'Dọn dẹp project (Dry-run)…');

    section.append(el('div', {class: 'cleanup-box'},
      el('div', {},
        el('strong', {}, '✓ Đã xác nhận đăng đủ YouTube & Facebook'),
        el('p', {style: 'margin-top:4px;font-size:13px;color:var(--color-ink-2)'},
          'Có thể dọn MP4 local, audio, source composition và cache. Quá trình sản xuất, kịch bản, prompt và video embed được bảo toàn.')
      ),
      cleanupBtn
    ));
  }

  return section;
}

function openCleanupDialog(s, projectId, onUpdated) {
  const dialog = el('dialog', {class: 'cleanup-dialog', 'aria-labelledby': 'cleanup-dialog-title'});
  const title = el('h2', {id: 'cleanup-dialog-title'}, `Dọn dẹp project · ${s.title}`);
  const statusMsg = el('p', {style: 'margin: 10px 0; color: var(--color-ink-2);'}, 'Đang phân tích dung lượng và tệp (dry-run)…');
  const contentWrap = el('div');
  const closeBtn = el('button', {type: 'button', class: 'studio-button', onclick: () => { dialog.close(); dialog.remove(); }}, 'Hủy');
  const actions = el('div', {class: 'cleanup-dialog-actions'}, closeBtn);

  dialog.append(title, statusMsg, contentWrap, actions);
  document.body.append(dialog);
  dialog.showModal();

  getJSON(`/api/project/${encodeURIComponent(projectId)}/cleanup/preview`).then(preview => {
    if (preview.already_cleaned) {
      statusMsg.textContent = 'Project này đã được dọn hoàn tất từ trước.';
      return;
    }
    statusMsg.textContent = 'Kết quả phân tích trước khi dọn:';

    const beforeMb = (preview.bytes_before / 1048576).toFixed(1);
    const afterMb = (preview.bytes_after / 1048576).toFixed(1);
    const freedMb = (preview.bytes_freed / 1048576).toFixed(1);

    const statGrid = el('div', {class: 'cleanup-stat-grid'},
      el('div', {class: 'cleanup-stat-card'}, el('span', {class: 'num'}, `${beforeMb} MB`), el('span', {class: 'lbl'}, `Trước dọn (${preview.files_count_before} tệp)`)),
      el('div', {class: 'cleanup-stat-card'}, el('span', {class: 'num', style: 'color:#3fb950;'}, `${afterMb} MB`), el('span', {class: 'lbl'}, `Sau dọn (${preview.files_count_after} tệp)`)),
      el('div', {class: 'cleanup-stat-card'}, el('span', {class: 'num', style: 'color:#3fb950;'}, `-${freedMb} MB`), el('span', {class: 'lbl'}, `Giải phóng (${preview.pct_freed}%)`))
    );

    const catList = el('ul');
    const categoryLabels = {
      rendered_video: 'Bản video MP4 và local exports',
      narration_audio: 'Tệp âm thanh lời đọc (WAV, MP3 stems)',
      composition_source: 'Mã nguồn dựng video (TSX, fonts)',
      inspection_frame: 'Ảnh kiểm tra dư (frames, verify)',
      backup_draft: 'Bản nháp và thư mục backup cũ',
      trash_cache: 'Thùng rác và cache nội bộ',
    };
    for (const [cat, data] of Object.entries(preview.categories || {})) {
      const mb = (data.size / 1048576).toFixed(1);
      catList.append(el('li', {},
        el('span', {}, categoryLabels[cat] || cat),
        el('strong', {}, `${data.count} tệp · ${mb} MB`)
      ));
    }

    const categoriesBox = el('div', {class: 'cleanup-categories'},
      el('strong', {}, 'Phân loại các tệp sẽ xóa:'),
      catList
    );

    const keptBox = el('div', {class: 'cleanup-kept-list'},
      el('strong', {}, '✓ Nội dung bảo toàn tuyệt đối không xóa:'),
      el('ul', {},
        el('li', {}, 'Toàn bộ Checkpoint hiện tại & 100% lịch sử (history/)'),
        el('li', {}, 'Kịch bản cuối (script.json), Storyboard (scene_plan.json) & Lời giải (solution.md)'),
        el('li', {}, 'Tất cả Prompt thực tế đã dùng & cấu hình model/voice'),
        el('li', {}, 'Thumbnail đã chọn (exports/thumbnails) & Branding kênh'),
        el('li', {}, 'Toàn bộ bản xuất hội thoại Markdown & JSON (exports/conversation/)'),
        el('li', {}, 'Quyết định (decision_log.json), Event logs (events.jsonl) & Link bài đăng hai nền tảng')
      )
    );

    const warning = el('p', {class: 'cleanup-warn'},
      '⚠ Lưu ý: Các tệp video/audio cục bộ sẽ được giải phóng khỏi ổ đĩa. Backlot sẽ chuyển sang phát video qua embed YouTube & Facebook.');

    contentWrap.replaceChildren(statGrid, categoriesBox, keptBox, warning);

    const confirmBtn = el('button', {
      type: 'button',
      class: 'btn-danger',
      onclick: async () => {
        confirmBtn.disabled = true;
        closeBtn.disabled = true;
        confirmBtn.textContent = 'Đang dọn dẹp…';
        try {
          await requestJSON(`/api/project/${encodeURIComponent(projectId)}/cleanup/execute`, {
            expected_revision: preview.plan_revision,
          });
          dialog.close();
          dialog.remove();
          if (onUpdated) await onUpdated();
        } catch(error) {
          warning.textContent = `Lỗi: ${error.message}`;
          warning.style.color = '#cf222e';
          confirmBtn.disabled = false;
          closeBtn.disabled = false;
          confirmBtn.textContent = 'Thử lại';
        }
      },
    }, `Xác nhận xóa ${preview.files_freed} tệp (giải phóng ${freedMb} MB)`);

    actions.prepend(confirmBtn);
  }).catch(error => {
    statusMsg.textContent = `Không tải được thông tin dọn dẹp: ${error.message}`;
    statusMsg.style.color = '#cf222e';
  });
}

function renderThumbnailsSection(p, projectId, onUpdated) {
  const root = el('div', {class: 'posting-thumbnails-section'});
  const header = el('div', {class: 'thumbnails-header'},
    el('h3', {}, 'Ảnh Thumbnail')
  );
  root.append(header);

  const items = p.thumbnails || [];
  const thumbnails = el('div', {class: 'posting-thumbnails-compact'});

  for (const thumb of items) {
    const selectStatus = el('p', {role: 'status', class: 'thumb-status'});
    const choose = thumb.selected
      ? el('span', {class: 'selected-thumbnail'}, '✓ Đang chọn')
      : el('button', {type: 'button', class: 'choose-thumb-btn', onclick: async () => {
          choose.disabled = true;
          try {
            await requestJSON(`/api/project/${encodeURIComponent(projectId)}/thumbnail`, {path: thumb.path});
            if (onUpdated) await onUpdated();
          } catch(error) {
            selectStatus.textContent = error.message;
            choose.disabled = false;
          }
        }}, 'Chọn thumbnail');

    const remove = el('button', {type: 'button', class: 'delete-thumbnail', onclick: async () => {
      if (items.length <= 1) return;
      if (!window.confirm(`Xóa thumbnail này?\n${thumb.path}`)) return;
      remove.disabled = true;
      try {
        const base = `/api/project/${encodeURIComponent(projectId)}`;
        const revision = await getJSON(`${base}/files/revision?path=${encodeURIComponent(thumb.path)}`);
        await requestJSON(`${base}/files/delete`, {path: thumb.path, expected_revision: revision.revision});
        if (onUpdated) await onUpdated();
      } catch(error) {
        selectStatus.textContent = error.message;
        remove.disabled = false;
      }
    }}, 'Xóa');

    if (items.length <= 1) {
      remove.disabled = true;
      remove.title = 'Không thể xóa thumbnail cuối cùng';
    }

    const card = el('figure', {class: `thumbnail-card${thumb.selected ? ' is-selected' : ''}`},
      el('button', {
        type: 'button',
        class: 'gallery-thumb-btn',
        'aria-label': `Xem ${thumb.label || thumb.path}`,
        onclick: () => openProjectGallery(projectId, thumb.path),
      }, el('img', {src: mediaURL(projectId, thumb.path), alt: thumb.label || 'Thumbnail', loading: 'lazy'})),
      el('div', {class: 'thumbnail-card-actions'}, choose, remove),
      selectStatus
    );
    thumbnails.append(card);
  }

  if (items.length) {
    root.append(thumbnails);
  } else {
    root.append(el('p', {class: 'empty-note'}, 'Chưa có thumbnail.'));
  }

  const promptValue = p.thumbnail_prompt || p.thumbnails?.find(t => t.prompt)?.prompt || '';
  if (promptValue || p.thumbnail_prompt_source) {
    const promptField = copyField('Prompt tạo thumbnail (chỉnh sửa để gen thủ công)', promptValue, {editable: true, projectId});
    root.append(promptField);
    if (p.thumbnail_prompt_source === 'draft') {
      root.append(el('p', {class: 'posting-note'}, 'Prompt nháp · Tạo hỗ trợ để bổ sung cảnh hook theo video.'));
    } else if (p.thumbnail_prompt_source === 'prepared') {
      root.append(el('p', {class: 'posting-note'}, 'Prompt đã chuẩn bị để tạo ảnh thủ công.'));
    }
  }

  return root;
}

function renderPlatformConfirm(platform, label, saved, projectId, onUpdated) {
  const record = saved?.platforms?.[platform] || {};
  const isConfirmed = Boolean(record.confirmed && record.url);
  const key = `${projectId}:${platform}`;
  let edit = postingEdits.get(key);
  if (!edit || (!edit.busy && edit.value === edit.saved && !edit.error)) {
    edit = {value: record.url || '', saved: record.url || '', confirmed: isConfirmed, savedConfirmed: isConfirmed, revision: record.revision};
    postingEdits.set(key, edit);
  }

  const check = el('input', {type: 'checkbox', role: 'switch', checked: edit.confirmed ? '' : null});
  const slider = el('span', {class: 'switch-slider'});
  const switchLabel = el('span', {class: 'switch-text'}, 'Đã đăng');
  const switchWrapper = el('label', {class: 'posting-switch'}, check, slider, switchLabel);

  const url = el('input', {
    type: 'url',
    value: edit.value,
    placeholder: `Nhập link ${label} đã đăng (https://…)`,
    'aria-label': `Link ${label} đã đăng`,
    required: isConfirmed ? '' : null,
  });
  const button = el('button', {type: 'submit', class: 'studio-button'}, 'Lưu link');
  const feedback = el('span', {role: 'status', class: 'posting-status-msg'});
  const confirmedAt = (isConfirmed && record.confirmed_at)
    ? el('small', {class: 'confirmed-time'}, `Đã xác nhận: ${new Date(record.confirmed_at).toLocaleString('vi-VN')}`)
    : el('small', {class: 'confirmed-time'});

  const linkRow = el('div', {class: 'posting-link-row'}, url, button);
  linkRow.hidden = !edit.confirmed;

  const form = el('form', {class: 'posting-platform-confirm'},
    el('div', {class: 'posting-confirm-top'}, switchWrapper, confirmedAt, feedback),
    linkRow
  );

  async function submitStatus(submitted) {
    if (edit.busy) return;
    edit.busy = true; edit.error = '';
    button.disabled = true; check.disabled = true; url.disabled = true;
    feedback.textContent = 'Đang lưu…';
    try {
      const result = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/posted`, {
        platform, ...submitted, expected_revision: edit.revision,
      });
      const updated = result.platforms[platform];
      edit.saved = updated.url; edit.value = updated.url;
      edit.confirmed = updated.confirmed; edit.savedConfirmed = updated.confirmed; edit.revision = updated.revision;
      edit.busy = false;
      feedback.textContent = submitted.confirmed ? 'Đã lưu' : 'Đã hủy đánh dấu';
      if (onUpdated) await onUpdated();
    } catch(error) {
      edit.error = error.message; feedback.textContent = error.message;
    } finally {
      edit.busy = false;
      button.disabled = false; check.disabled = false; url.disabled = false;
    }
  }

  check.addEventListener('change', () => {
    edit.confirmed = check.checked;
    if (check.checked) {
      linkRow.hidden = false;
      url.required = true;
      url.focus();
    } else {
      linkRow.hidden = true;
      url.required = false;
      if (edit.savedConfirmed) {
        submitStatus({confirmed: false, url: ''});
      }
    }
  });

  const saveLink = async () => {
    if (!check.checked || edit.busy) return;
    const link = url.value.trim();
    if (link === edit.saved && edit.savedConfirmed) return;
    if (!link) {
      feedback.textContent = 'Hãy nhập link bài đăng trước khi lưu.';
      url.focus();
      return;
    }
    if (!form.reportValidity() || button.disabled) return;
    await submitStatus({confirmed: true, url: link});
  };
  url.addEventListener('input', () => { edit.value = url.value; edit.error = ''; feedback.textContent = 'Rời ô để lưu'; });
  url.addEventListener('blur', event => {
    if (url.isConnected && event.relatedTarget !== check) saveLink();
  });
  feedback.textContent = edit.error || (edit.busy ? 'Đang lưu…' : '');
  button.disabled = check.disabled = url.disabled = !!edit.busy;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    await saveLink();
  });

  return form;
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
      if (edit.value === edit.expected) { cancel(); return; }
      if (!edit.value.trim()) { edit.error = 'Tên project không được để trống.'; titleMounts.get(projectId)?.(); return; }
      edit.busy = true; edit.error = ''; titleMounts.get(projectId)?.();
      try {
        const data = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/title`, {title: edit.value, expected_title: edit.expected});
        s.title = data.title; titleEdits.delete(projectId); titleMounts.get(projectId)?.();
        if (onUpdated) await onUpdated();
      } catch(error) { edit.error = error.message; }
      finally { edit.busy = false; titleMounts.get(projectId)?.(); }
    };
    input.onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); save(); } if (event.key === 'Escape') { event.preventDefault(); cancel(); } };
    input.onblur = event => {
      if (input.isConnected && !root.contains(event.relatedTarget)) save();
    };
    root.append(el('div', {class: 'title-edit-row'}, input,
      el('button', {type: 'button', disabled: edit.busy ? '' : null, 'aria-busy': String(edit.busy), onclick: save}, edit.busy ? 'Đang lưu…' : 'Lưu tiêu đề'),
      el('button', {type: 'button', disabled: edit.busy ? '' : null, onclick: cancel}, 'Hủy')));
    if (edit.error) root.append(el('p', {role: 'alert'}, edit.error));
  };
  titleMounts.set(projectId, draw); draw(); return root;
}
