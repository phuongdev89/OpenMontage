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
  const isPathOrTitle = label.toLowerCase().includes('path') || label.toLowerCase().includes('đường dẫn') || label === 'Tiêu đề video';
  const rows = isPathOrTitle ? '2' : label.includes('Prompt tạo thumbnail') ? '8' : '5';
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

  let openingCalendar = false;
  const triggerOpenCalendar = async () => {
    if (openingCalendar || document.querySelector('dialog.calendar-sync-dialog[open]')) return;
    openingCalendar = true;
    try {
      const info = await getJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/info`);
      openCalendarSyncDialog(s, projectId, info, onUpdated);
    } catch (e) {
      console.error('Lỗi tải thông tin lịch đăng:', e);
    } finally {
      openingCalendar = false;
    }
  };

  const addToCalHeaderBtn = el('button', {
    type: 'button',
    class: 'studio-button studio-button-primary',
    onclick: triggerOpenCalendar,
  }, '📅 Thêm vào lịch đăng');

  getJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/info`).then(info => {
    const hasCal = Boolean(info.has_calendar || info.is_added);
    const scheduledDate = info.calendar?.scheduled_date || info.scheduled_date || info.sync_state?.scheduled_date || '';
    if (hasCal) {
      addToCalHeaderBtn.disabled = true;
      addToCalHeaderBtn.className = 'studio-button';
      addToCalHeaderBtn.textContent = 'Đã thêm vào lịch đăng';
      addToCalHeaderBtn.title = scheduledDate ? `Đã lên lịch đăng ngày ${scheduledDate}` : 'Đã thêm vào lịch đăng';
      addToCalHeaderBtn.style.opacity = '0.7';
      addToCalHeaderBtn.style.cursor = 'not-allowed';
    } else {
      addToCalHeaderBtn.disabled = false;
      addToCalHeaderBtn.className = 'studio-button studio-button-primary';
      addToCalHeaderBtn.textContent = '📅 Thêm vào lịch đăng';
      addToCalHeaderBtn.onclick = () => {
        if (openingCalendar || document.querySelector('dialog.calendar-sync-dialog[open]')) return;
        openCalendarSyncDialog(s, projectId, info, onUpdated);
      };
    }
  }).catch(() => {});

  const header = el('div', {class: 'posting-header'},
    el('h2', {}, 'Hỗ trợ đăng video'),
    el('div', {class: 'posting-header-actions'}, addToCalHeaderBtn, create, supportStatus)
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

  section.append(renderCalendarSyncSection(s, projectId, onUpdated));

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

function renderCalendarSyncSection(s, projectId, onUpdated) {
  const container = el('div', {class: 'calendar-sync-box', id: `calendar-sync-${projectId}`});
  const textCol = el('div');
  const title = el('strong', {}, '📅 Thêm vào lịch đăng (Script Calendar Management)');
  const desc = el('p', {style: 'margin-top:4px;font-size:13px;color:var(--color-ink-2)'}, 'Đang tải thông tin lịch đăng…');
  textCol.append(title, desc);

  const actions = el('div', {class: 'calendar-sync-actions'});
  container.append(textCol, actions);

  getJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/info`).then(info => {
    const hasCal = Boolean(info.has_calendar || info.is_added);
    const sync = info.sync_state || {};
    const scheduledDate = info.calendar?.scheduled_date || info.scheduled_date || sync.scheduled_date || '';
    const scheduledTime = info.calendar?.scheduled_time || info.scheduled_time || sync.scheduled_time || '';
    const status = hasCal ? 'DONE' : (sync.status || 'IDLE');

    actions.innerHTML = '';
    if (status === 'DONE' || hasCal) {
      title.innerHTML = '✓ Đã thêm vào lịch đăng thành công';
      desc.textContent = `Campaign ID: ${sync.campaign_id || info.calendar?.campaign_id || 'N/A'} · Ngày lên lịch: ${scheduledDate || 'N/A'}${scheduledTime ? ' · Giờ đăng: ' + scheduledTime : ''}`;
      container.classList.add('calendar-sync-done');
      const resyncBtn = el('button', {
        type: 'button',
        class: 'studio-button',
        onclick: () => openCalendarSyncDialog(s, projectId, info, onUpdated),
      }, 'Cập nhật lịch đăng…');
      actions.append(resyncBtn);
    } else if (status === 'UNKNOWN') {
      title.innerHTML = '⚠ Hết thời gian chờ tạo Campaign (POST timeout)';
      desc.textContent = 'Trạng thái UNKNOWN: Chưa xác định server đã tạo campaign hay chưa. Vui lòng bấm Đối soát để kiểm tra tránh tạo trùng.';
      container.classList.add('calendar-sync-warning');
      const reconcileBtn = el('button', {
        type: 'button',
        class: 'studio-button studio-button-primary',
        onclick: async () => {
          reconcileBtn.disabled = true;
          reconcileBtn.textContent = 'Đang đối soát…';
          try {
            const res = await requestJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/reconcile`, {calendar_url: info.calendar_url});
            alert(res.message);
            if (onUpdated) await onUpdated();
          } catch (e) {
            alert('Lỗi đối soát: ' + e.message);
          } finally {
            reconcileBtn.disabled = false;
            reconcileBtn.textContent = 'Đối soát danh sách';
          }
        }
      }, 'Đối soát danh sách');
      actions.append(reconcileBtn);
    } else if (status === 'CONFLICT_409') {
      title.innerHTML = '⚠ Xung đột kịch bản (Revision 409)';
      desc.textContent = 'Kịch bản trên server đã có thay đổi khác với bản của Backlot. Cần chọn ghi đè hoặc giữ bản server.';
      container.classList.add('calendar-sync-error');
      const conflictBtn = el('button', {
        type: 'button',
        class: 'studio-button studio-button-primary',
        onclick: () => openConflictDialog(projectId, sync, info.calendar_url, onUpdated),
      }, 'Xử lý xung đột…');
      actions.append(conflictBtn);
    } else if (status === 'ERROR') {
      title.innerHTML = '✕ Lỗi đồng bộ lịch đăng';
      desc.textContent = sync.error || 'Đồng bộ gặp lỗi. Bấm để thử lại.';
      container.classList.add('calendar-sync-error');
      const retryBtn = el('button', {
        type: 'button',
        class: 'studio-button',
        onclick: () => openCalendarSyncDialog(s, projectId, info, onUpdated),
      }, 'Thử lại…');
      actions.append(retryBtn);
    } else if (status === 'CAMPAIGN_CREATED' || status === 'SCRIPT_SAVED') {
      title.innerHTML = '⏳ Đang đồng bộ dở dang';
      desc.textContent = `Campaign: ${sync.campaign_id} (Mốc hiện tại: ${status}). Bấm để tiếp tục hoàn tất.`;
      const resumeBtn = el('button', {
        type: 'button',
        class: 'studio-button studio-button-primary',
        onclick: () => openCalendarSyncDialog(s, projectId, info, onUpdated),
      }, 'Tiếp tục đồng bộ…');
      actions.append(resumeBtn);
    } else {
      title.innerHTML = '📅 Thêm vào lịch đăng';
      desc.textContent = 'Tạo task, kịch bản và caption lên Script Calendar Management.';
      const syncBtn = el('button', {
        type: 'button',
        class: 'studio-button studio-button-primary',
        onclick: () => openCalendarSyncDialog(s, projectId, info, onUpdated),
      }, 'Thêm vào lịch đăng…');
      actions.append(syncBtn);
    }
  }).catch(() => {
    desc.textContent = 'Chưa kết nối được với thông tin lịch đăng.';
  });

  return container;
}

export function openCalendarSyncDialog(s, projectId, info, onUpdated) {
  // Dọn dẹp bất kỳ dialog nào đang tồn tại trước khi tạo mới để đảm bảo duy nhất 1 modal
  for (const old of document.querySelectorAll('dialog.calendar-sync-dialog, dialog.calendar-full-dialog')) {
    try { old.close(); } catch (_) {}
    old.remove();
  }

  const sync = info.sync_state || {};
  const dialog = el('dialog', {class: 'calendar-full-dialog calendar-sync-dialog', 'aria-labelledby': 'cal-sync-title'});

  // Đảm bảo dialog luôn tự động remove khỏi DOM khi đóng (kể cả qua phím ESC)
  dialog.addEventListener('close', () => {
    dialog.remove();
  });

  const kocSchedule = info.koc_schedule || [];
  const eventsByDate = new Map();
  for (const item of kocSchedule) {
    const d = item.scheduled_date || item.date;
    if (d) {
      if (!eventsByDate.has(d)) eventsByDate.set(d, []);
      eventsByDate.get(d).push(item);
    }
  }

  // Pre-selected date: sync.scheduled_date or info.scheduled_date or tomorrow
  let initialDateStr = sync.scheduled_date || info.scheduled_date;
  if (!initialDateStr) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    initialDateStr = tomorrow.toISOString().split('T')[0];
  }

  let selectedDate = initialDateStr;
  let selectedTime = sync.scheduled_time || info.scheduled_time || '11:30';

  const initialD = new Date(selectedDate);
  let viewYear = isNaN(initialD.getFullYear()) ? new Date().getFullYear() : initialD.getFullYear();
  let viewMonth = isNaN(initialD.getMonth()) ? new Date().getMonth() : initialD.getMonth();

  const title = el('h2', {id: 'cal-sync-title', style: 'margin: 0 0 4px; font-size: 18px;'}, '📅 Thêm vào lịch đăng · Chọn ngày đăng');
  const subtitle = el('p', {style: 'margin: 0 0 14px; color: var(--color-ink-2); font-size: 13px;'},
    'KOC: ', el('strong', {style: 'color: #58a6ff;'}, 'Toán Olympic Cùng Con'),
    ' · Chọn 1 ngày trên lịch để đăng video (tránh đăng trùng ngày đã có bài)'
  );

  const hasCampaign = Boolean(sync.campaign_id);
  const titleInput = el('input', {
    type: 'text', maxLength: 180, required: '',
    value: sync.title || info.title || s.title,
    style: 'width: 100%;',
    disabled: hasCampaign ? '' : null,
  });
  const titleRow = el('div', {class: 'cal-field-row', style: 'margin-bottom: 14px;'},
    el('label', {}, 'Tiêu đề video *:' + (hasCampaign ? ' (cố định theo campaign)' : '')),
    titleInput
  );

  // Month navigation bar
  const navBar = el('div', {class: 'cal-nav-bar'});
  const prevBtn = el('button', {type: 'button', class: 'studio-button', style: 'padding: 4px 10px; font-size: 12px;'}, '◀ Tháng trước');
  const nextBtn = el('button', {type: 'button', class: 'studio-button', style: 'padding: 4px 10px; font-size: 12px;'}, 'Tháng sau ▶');
  const todayBtn = el('button', {type: 'button', class: 'studio-button', style: 'padding: 4px 10px; font-size: 12px; margin-left: 8px;'}, 'Hôm nay');
  const navTitle = el('div', {class: 'cal-nav-title'});
  const leftGroup = el('div', {style: 'display: flex; align-items: center; gap: 8px;'}, prevBtn, nextBtn, todayBtn);
  navBar.append(navTitle, leftGroup);

  // Weekdays header
  const weekdaysHeader = el('div', {class: 'cal-grid', style: 'margin-bottom: 4px;'});
  for (const name of ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']) {
    weekdaysHeader.append(el('div', {class: 'cal-weekday'}, name));
  }

  // Calendar Grid Container
  const gridContainer = el('div', {class: 'cal-grid'});

  // Selection summary bar & actions
  const selectionBar = el('div', {class: 'cal-selection-bar'});
  const errorMsg = el('p', {role: 'alert', style: 'margin-top: 8px; color: #f85149; font-size: 13px; display: none;'});
  const cancelBtn = el('button', {type: 'button', class: 'studio-button', onclick: () => { dialog.close(); dialog.remove(); }}, 'Hủy');
  const submitBtn = el('button', {type: 'button', class: 'studio-button studio-button-primary'}, sync.campaign_id ? 'Cập nhật lịch đăng' : 'Thêm vào lịch đăng');
  const actionRow = el('div', {style: 'display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px;'}, cancelBtn, submitBtn);

  const timeInput = el('input', {
    type: 'text', value: selectedTime, placeholder: '11:30',
    style: 'width: 80px; padding: 4px 8px; font-size: 13px; border: var(--rule); border-radius: 4px; text-align: center; background: var(--color-paper); color: var(--color-ink);'
  });
  timeInput.addEventListener('input', () => { selectedTime = timeInput.value.trim() || '11:30'; });

  function renderSelectionBar() {
    selectionBar.innerHTML = '';
    if (!selectedDate) {
      selectionBar.append(el('p', {style: 'color: var(--color-ink-2); font-size: 13px; margin: 0;'}, 'Vui lòng nhấn chọn một ngày trên lịch ở trên.'));
      submitBtn.disabled = true;
      return;
    }

    const events = eventsByDate.get(selectedDate) || [];
    const dateObj = new Date(selectedDate);
    const dayNames = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
    const dayName = isNaN(dateObj.getDay()) ? '' : dayNames[dateObj.getDay()];
    const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
    const goldenHours = isWeekend ? ['09:00', '15:00', '20:00'] : ['11:45', '19:30', '20:30'];

    const timeRow = el('div', {class: 'cal-time-row'});
    timeRow.append(
      el('label', {style: 'font-size: 12px; font-weight: 500;'}, 'Khung giờ:'),
      timeInput
    );
    for (const gh of goldenHours) {
      const btn = el('button', {
        type: 'button',
        class: 'cal-preset-btn',
        title: `Gợi ý giờ vàng ${isWeekend ? 'cuối tuần' : 'ngày thường'}`,
        onclick: () => { timeInput.value = gh; selectedTime = gh; }
      }, `${gh} ⭐`);
      timeRow.append(btn);
    }

    const topRow = el('div', {style: 'display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;'},
      el('div', {},
        el('span', {style: 'font-size: 13px; color: var(--color-ink-2);'}, 'Ngày đăng đã chọn: '),
        el('strong', {style: 'font-size: 15px; color: #58a6ff;'}, `${selectedDate} (${dayName})`)
      ),
      timeRow
    );

    let statusBox = null;
    if (events.length > 0) {
      const titles = events.map(e => `"${e.title}"`).join(', ');
      statusBox = el('div', {class: 'cal-warn-box'},
        `⚠ Ngày ${selectedDate} đã có ${events.length} video của KOC Toán Olympic Cùng Con (${titles}). Hãy cân nhắc chọn ngày khác để tránh đăng trùng!`
      );
    } else {
      statusBox = el('div', {class: 'cal-free-box'},
        `✓ Ngày ${selectedDate} hiện còn trống lịch! Không có video nào bị trùng.`
      );
    }

    selectionBar.append(topRow, statusBox);
    submitBtn.disabled = false;
  }

  function renderMonth() {
    navTitle.textContent = `Tháng ${viewMonth + 1}, Năm ${viewYear}`;
    gridContainer.innerHTML = '';

    const firstDayIndex = (new Date(viewYear, viewMonth, 1).getDay() + 6) % 7; // Monday = 0
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const todayStr = new Date().toISOString().split('T')[0];

    // Empty slots before 1st of month
    for (let i = 0; i < firstDayIndex; i++) {
      gridContainer.append(el('div', {class: 'cal-day is-empty-slot'}));
    }

    // Days in current month
    for (let d = 1; d <= daysInMonth; d++) {
      const monthStr = String(viewMonth + 1).padStart(2, '0');
      const dayStr = String(d).padStart(2, '0');
      const dateStr = `${viewYear}-${monthStr}-${dayStr}`;
      const events = eventsByDate.get(dateStr) || [];
      const hasEvents = events.length > 0;
      const isToday = dateStr === todayStr;
      const isSelected = dateStr === selectedDate;

      const dayCell = el('div', {
        class: `cal-day${hasEvents ? ' has-events' : ''}${isToday ? ' is-today' : ''}${isSelected ? ' is-selected' : ''}`,
        onclick: () => {
          selectedDate = dateStr;
          renderMonth();
          renderSelectionBar();
        }
      });

      const dayNum = el('div', {class: 'cal-day-num'},
        el('span', {}, String(d)),
        isToday ? el('span', {class: 'cal-today-badge'}, 'Hôm nay') : null
      );
      dayCell.append(dayNum);

      if (hasEvents) {
        const eventsContainer = el('div', {class: 'cal-day-events'});
        for (const ev of events.slice(0, 2)) {
          const rawTitle = (ev.title || '').trim();
          const words = rawTitle.split(/\s+/).filter(Boolean);
          const shortTitle = words.length > 3 ? words.slice(0, 3).join(' ') + '…' : rawTitle;
          const displayTitle = shortTitle.length > 18 ? shortTitle.slice(0, 16).trim() + '…' : shortTitle;
          const timePrefix = ev.scheduled_time ? `${ev.scheduled_time} ` : '';
          const pill = el('div', {
            class: 'cal-event-pill',
            title: `${ev.scheduled_time ? ev.scheduled_time + ' · ' : ''}${rawTitle}`
          }, `${timePrefix}${displayTitle}`);
          eventsContainer.append(pill);
        }
        if (events.length > 2) {
          eventsContainer.append(el('div', {style: 'font-size: 9px; color: #e3b341;'}, `+${events.length - 2} bài khác`));
        }
        dayCell.append(eventsContainer);
      } else {
        dayCell.append(el('div', {class: 'cal-free-pill'}, 'Trống'));
      }

      gridContainer.append(dayCell);
    }
  }

  prevBtn.onclick = () => {
    viewMonth--;
    if (viewMonth < 0) { viewMonth = 11; viewYear--; }
    renderMonth();
  };
  nextBtn.onclick = () => {
    viewMonth++;
    if (viewMonth > 11) { viewMonth = 0; viewYear++; }
    renderMonth();
  };
  todayBtn.onclick = () => {
    const now = new Date();
    viewYear = now.getFullYear();
    viewMonth = now.getMonth();
    renderMonth();
  };

  submitBtn.onclick = async () => {
    const tVal = titleInput.value.trim();
    if (!tVal || !selectedDate) {
      errorMsg.textContent = 'Vui lòng điền tiêu đề và chọn ngày trên lịch.';
      errorMsg.style.display = 'block';
      return;
    }
    submitBtn.disabled = true;
    cancelBtn.disabled = true;
    submitBtn.textContent = 'Đang thêm vào lịch đăng…';
    errorMsg.style.display = 'none';

    try {
      const payload = {
        title: tVal,
        scheduled_date: selectedDate,
        scheduled_time: selectedTime,
        koc: 'Toan_Olympic_Cung_Con',
        idea: info.idea || '',
        product_url: info.product_url || '',
        planned_outfit_count: 1,
        calendar_url: info.calendar_url || '',
        script: info.script || '',
        caption: info.caption || '',
      };
      await requestJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/start`, payload);
      dialog.close();
      dialog.remove();
      if (onUpdated) await onUpdated();
    } catch (err) {
      errorMsg.textContent = err.message || 'Lỗi khi thêm vào lịch đăng.';
      errorMsg.style.display = 'block';
      submitBtn.disabled = false;
      cancelBtn.disabled = false;
      submitBtn.textContent = 'Thử lại';
      if (onUpdated) await onUpdated();
    }
  };

  // Close dialog when clicking on the backdrop
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      const clickedOutside = (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      );
      if (clickedOutside) {
        dialog.close();
        dialog.remove();
      }
    }
  });

  renderMonth();
  renderSelectionBar();

  dialog.append(title, subtitle, titleRow, navBar, weekdaysHeader, gridContainer, selectionBar, errorMsg, actionRow);
  document.body.append(dialog);
  dialog.showModal();
}

function openConflictDialog(projectId, syncState, calendarUrl, onUpdated) {
  for (const old of document.querySelectorAll('dialog.calendar-sync-dialog, dialog.cleanup-dialog')) {
    try { old.close(); } catch (_) {}
    old.remove();
  }
  const dialog = el('dialog', {class: 'cleanup-dialog calendar-sync-dialog', 'aria-labelledby': 'conflict-title'});
  dialog.addEventListener('close', () => dialog.remove());
  const title = el('h2', {id: 'conflict-title'}, 'Xung đột kịch bản (Revision 409)');
  const desc = el('p', {style: 'margin: 6px 0 16px; color: var(--color-ink-2); font-size: 13px;'},
    'Kịch bản trên Script Calendar đã có người chỉnh sửa hoặc khác revision với bản local.');

  const detail = syncState.conflict_detail || {};
  const grid = el('div', {style: 'display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;'});
  const localCol = el('div', {},
    el('strong', {style: 'font-size: 13px;'}, 'Bản local (Backlot):'),
    el('textarea', {readonly: '', rows: '10', style: 'width: 100%; margin-top: 6px; font-family: var(--font-meta); font-size: 12px;'}, detail.local_content || '')
  );
  const remoteCol = el('div', {},
    el('strong', {style: 'font-size: 13px;'}, `Bản server (Revision: ${(detail.remote_revision || '').slice(0, 8)}…):`),
    el('textarea', {readonly: '', rows: '10', style: 'width: 100%; margin-top: 6px; font-family: var(--font-meta); font-size: 12px;'}, detail.remote_content || '')
  );
  grid.append(localCol, remoteCol);

  const cancelBtn = el('button', {type: 'button', class: 'studio-button', onclick: () => { dialog.close(); dialog.remove(); }}, 'Đóng');
  const keepRemoteBtn = el('button', {type: 'button', class: 'studio-button', onclick: async () => {
    keepRemoteBtn.disabled = true;
    try {
      await requestJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/resolve-conflict`, {action: 'keep_remote', calendar_url: calendarUrl});
      dialog.close(); dialog.remove();
      if (onUpdated) await onUpdated();
    } catch (e) { alert(e.message); keepRemoteBtn.disabled = false; }
  }}, 'Giữ bản kịch bản trên server');

  const overwriteBtn = el('button', {type: 'button', class: 'studio-button studio-button-primary', onclick: async () => {
    overwriteBtn.disabled = true;
    try {
      await requestJSON(`/api/project/${encodeURIComponent(projectId)}/calendar-sync/resolve-conflict`, {action: 'overwrite', calendar_url: calendarUrl});
      dialog.close(); dialog.remove();
      if (onUpdated) await onUpdated();
    } catch (e) { alert(e.message); overwriteBtn.disabled = false; }
  }}, 'Ghi đè bằng bản Backlot');

  const actions = el('div', {class: 'cleanup-dialog-actions', style: 'display: flex; justify-content: flex-end; gap: 8px;'}, cancelBtn, keepRemoteBtn, overwriteBtn);

  dialog.append(title, desc, grid, actions);
  document.body.append(dialog);
  dialog.showModal();
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
      ? el('span', {class: 'selected-thumbnail thumb-action-btn', 'data-icon': 'check', title: 'Đang chọn làm thumbnail chính', 'aria-label': 'Đang chọn làm thumbnail chính'})
      : el('button', {
          type: 'button',
          class: 'choose-thumb-btn thumb-action-btn',
          'data-icon': 'check',
          title: 'Chọn làm thumbnail chính',
          'aria-label': 'Chọn làm thumbnail chính',
          onclick: async () => {
            choose.disabled = true;
            try {
              await requestJSON(`/api/project/${encodeURIComponent(projectId)}/thumbnail`, {path: thumb.path});
              if (onUpdated) await onUpdated();
            } catch(error) {
              selectStatus.textContent = error.message;
              choose.disabled = false;
            }
          }
        });

    const copyPathBtn = el('button', {
      type: 'button',
      class: 'copy-thumb-path-btn thumb-action-btn',
      'data-icon': 'copy',
      title: 'Sao chép đường dẫn file',
      'aria-label': 'Sao chép đường dẫn file',
      onclick: async () => {
        const pStr = thumb.absolute_path || thumb.path;
        try {
          await navigator.clipboard.writeText(pStr);
          copyPathBtn.setAttribute('data-icon', 'check');
          copyPathBtn.title = 'Đã sao chép!';
          setTimeout(() => {
            copyPathBtn.setAttribute('data-icon', 'copy');
            copyPathBtn.title = 'Sao chép đường dẫn file';
          }, 1500);
        } catch {
          window.prompt('Đường dẫn file thumbnail:', pStr);
        }
      }
    });

    const remove = el('button', {
      type: 'button',
      class: 'delete-thumbnail thumb-action-btn',
      'data-icon': 'trash',
      title: 'Xóa thumbnail này',
      'aria-label': 'Xóa thumbnail này',
      onclick: async () => {
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
      }
    });

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
      el('div', {class: 'thumbnail-card-actions'}, choose, copyPathBtn, remove),
      selectStatus
    );
    thumbnails.append(card);
  }

  if (items.length) {
    root.append(thumbnails);
    const selectedThumb = items.find(t => t.selected) || items[0];
    const thumbPath = selectedThumb?.absolute_path || selectedThumb?.path || '';
    if (thumbPath) {
      root.append(copyField('Đường dẫn file thumbnail (để tải lên)', thumbPath));
    }
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
