import {el, getJSON, mediaURL, thumbURL} from '/ui/lib.js';

const imagePath = path => /\.(png|jpe?g|webp|gif|svg|avif|bmp)$/i.test(path);
export async function openProjectGallery(projectId, selectedPath) {
  let images;
  try { images = (await getJSON(`/api/project/${encodeURIComponent(projectId)}/files`)).filter(f => imagePath(f.path)); }
  catch { images = []; }
  if (!images.some(f => f.path === selectedPath)) images.unshift({path: selectedPath});
  if (!images.length) return;
  let index = Math.max(0, images.findIndex(f => f.path === selectedPath));
  const dialog = el('dialog', {class: 'gallery-dialog', 'aria-label': 'Thư viện ảnh'});
  const title = el('h2', {}, 'Thư viện ảnh');
  const count = el('span', {class: 'gallery-count'});
  const image = el('img', {class: 'gallery-image', alt: ''});
  const status = el('p', {role: 'status'});
  const download = el('a', {class: 'studio-button', download: ''}, 'Tải ảnh');
  const strip = el('div', {class: 'gallery-strip'});
  const show = selected => {
    index = (selected + images.length) % images.length;
    const file = images[index];
    title.textContent = file.path; count.textContent = `${index + 1} / ${images.length}`;
    image.src = mediaURL(projectId, file.path); image.alt = file.path;
    status.textContent = ''; download.href = image.src;
    for (const [i, button] of [...strip.children].entries()) button.setAttribute('aria-pressed', String(i === index));
    strip.children[index]?.scrollIntoView({block: 'nearest', inline: 'nearest'});
  };
  image.onerror = () => { status.textContent = 'Không đọc được ảnh này. Chọn ảnh khác hoặc kiểm tra tệp.'; };
  for (const [i, file] of images.entries()) strip.append(el('button', {type: 'button', 'aria-label': file.path, onclick: () => show(i)},
    el('img', {src: thumbURL(projectId, file.path, 320), alt: '', loading: 'lazy'})));
  dialog.append(el('header', {class: 'dialog-header'}, title, count, el('button', {type: 'button', onclick: () => dialog.close()}, 'Đóng')),
    el('div', {class: 'gallery-stage'}, el('button', {type: 'button', 'aria-label': 'Ảnh trước', onclick: () => show(index - 1)}, '←'),
      image, el('button', {type: 'button', 'aria-label': 'Ảnh sau', onclick: () => show(index + 1)}, '→')),
    el('div', {class: 'gallery-footer'}, status, download), strip);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); show(index + (event.key === 'ArrowLeft' ? -1 : 1)); }
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => dialog.remove());
  document.body.append(dialog); dialog.showModal(); show(index);
}

// Every project image shares one gallery, including Library, storyboard and files.
document.addEventListener('click', event => {
  const image = event.target.closest?.('img');
  if (!image || image.closest('.gallery-dialog')) return;
  const url = new URL(image.currentSrc || image.src, location.href);
  const match = url.pathname.match(/^\/(?:thumb|media)\/([^/]+)\/(.+)$/);
  if (!match) return;
  const projectId = decodeURIComponent(match[1]);
  const path = match[2].split('/').map(decodeURIComponent).join('/');
  if (!imagePath(path)) return;
  event.preventDefault(); event.stopPropagation();
  openProjectGallery(projectId, path).catch(console.error);
}, true);
