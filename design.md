# Design — Backlot

Scope: Backlot Library and project workspace only.

Genre: atmospheric studio, compact operational UI. Theme: Midnight with a
warm neutral daylight variant; both use one amber action accent. Status colors
communicate live/approval/error only. Preserve existing routes and data contracts.

Library is a Catalogue: Grid is a data table with columns/rows; Item is cards.
Project has no Grid/Item toggle. File manager has one Detail layout: folder tree
left, folder listing or file content/editor right; preserve drafts during updates.
Project is a Workbench: Video.js player left, posting handoff right (tabs for
copy and thumbnails), followed by expandable
production history. Use edge-aligned functional navigation and no marketing footer.
Video upload path and copy/download actions are directly below the player.
Header is compact with inline title editing by double click or keyboard F2/Enter.
Tabs use underline selection; action buttons use contained surfaces. All project
images open the same keyboard-accessible gallery modal, with no new browser tab.

Display: Be Vietnam Pro 600, body: Noto Sans 400–700, metadata: IBM Plex Mono.
Fonts are local, support Vietnamese, headings are upright. Body minimum 14 px,
forms 16 px; avoid uppercasing long project titles. Colors and spacing live in
tokens.css. Single containment layer, quiet surfaces, no decorative gradients,
glass, animated entrances or invented metrics. Focus is immediate and visible.

Published defaults: only Player and Hỗ trợ đăng video expanded. Keep per-project
fold choices and playback across SSE updates. Collapse history once on transition
to publish completed, never repeatedly override a user's reopened section.

Mobile: toolbar reflows, cards use minmax(0,1fr), dialogs fit the viewport,
clickable labels stay on one line; verify 320, 375, 414 and 768 px. No horizontal
page scrolling. Use local Video.js 8.24.1 with keyboard seeking, ±10s, speed,
fullscreen and picture-in-picture. Keep the same instance through SSE redraws.

All mutation controls have busy/error/success states. File deletion is reversible,
edits use revisions, checkpoints/approval configuration are read-only in the file
manager. A prompt draft is labelled as a draft; it is never represented as the
actual image-generation prompt. No image generation occurs from Tạo hỗ trợ.
