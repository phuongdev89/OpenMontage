# Backlot — the living storyboard

## Realtime filesystem updates

Native filesystem events update the board and Library through SSE. A metadata
scan every five seconds also detects missed writes, additions, renames and
deletions, including when `watchfiles` is unavailable or its watcher fails.
Dependency/cache directories are excluded; media bytes are not read by this scan.
The watcher retries transient errors and waits for a missing projects root to appear.
On file-handle/inotify resource exhaustion, it logs one warning and uses only
reconciliation for the rest of that server session, avoiding repeated tracebacks.
Restart Backlot after resolving OS limits to retry native notifications.
Browsers refetch on SSE reconnect and when returning to the tab. Media URLs are
revalidated so overwriting an image at the same path shows the new content.
`?static=1` intentionally disables live updates for screenshots/exports.

## Studio workspace

Library supports persistent Grid (table)/Item (cards), search and status filters. Published
projects open Player and Hỗ trợ đăng video; production sections collapse once on
the transition to publish completed and remain available as expandable sections.
Reopened sections, manual prompt drafts and video playback survive SSE updates.
Project has no Grid/Item button. Double-click the heading (or press F2/Enter)
to rename inline after compose/publish; Escape cancels. Only the display override
changes, never the video's publishing title.

The player uses locally hosted Video.js 8.24.1 with seeking, ±10 seconds,
playback speed, fullscreen and picture-in-picture (where supported). It discovers
exported video variants independently of copy. The detail workspace puts player
and posting side by side; copy/thumbnail tabs keep it compact. The full video path
with copy/download actions appears immediately below the player for uploading first.

Tạo hỗ trợ uses configured AI_CHAT to fill missing title/description/caption and
prepare a thumbnail prompt from project-only source artifacts. It saves
`artifacts/posting_support.json`, retains existing copy, checks revisions and
never advances checkpoints or creates media. Provider failures leave data intact.
The prompt is visible even when no image exists; drafts/prepared prompts are
distinguished from recorded image-generation prompts. All images under
`exports/thumbnails/` appear alongside metadata-registered images. Selecting one
saves `artifacts/thumbnail_selection.json` and updates the Library poster.

Quản lý tệp opens a live modal with a folder tree left and a single Detail pane
right, search, upload, UTF-8 create/edit, downloads, reversible delete and Undo.
Async reads are guarded against selection races; current editor drafts survive
SSE changes and reselecting the same file. All project images (Library, storyboard,
thumbnails and file previews) open a gallery dialog with navigation/download.
Uploads are capped at
16 MB and text edits at 2 MB. Revision checks reject stale edits. Operations are
project-scoped, reject traversal/outside symlinks, and keep project markers and
checkpoint files read-only. Deleted files remain in `.backlot-trash` and are
excluded from media scans and project ZIPs.

## Revise posting copy

After publish, the posting section has **Tạo lại caption** and
**Tạo lại description**. Enter a revision request in the dialog and click
**Tạo lại**. The server calls the configured `AI_CHAT_URL`, `AI_CHAT_KEY` and
`AI_CHAT_MODEL` using `/chat/completions`, then saves the successful response in
that project's `artifacts/posting_copy.json`. Submission closes the dialog;
the field's button spins until completion and the saved result fills its textarea.
Failures appear beside that button and preserve the previous text;
refreshing the board preserves it. Previous versions and revision instructions
are retained in the file's history.

The request includes this project's source artifacts and the current field value.
Only the selected field changes. Failed provider calls preserve existing content;
stale revisions are rejected instead of overwriting a newer edit. These user edits
do not advance pipeline stages or modify media/checkpoints. `AI_IMAGE_*` remains
the separate image-generation configuration, never the language-model provider.

A local board that shows a production happening: pipeline stages
lighting up, the script as a screenplay page, the scene plan as a filmstrip
that fills in as assets generate, decisions, spend, and activity — all
derived from what the pipeline already writes to `projects/<id>/`.

```bash
python -m backlot open <project-id>   # start server if needed + open browser
python -m backlot open                # library view (all projects)
python -m backlot serve --port 4750   # run the server in the foreground
```

## How it stays live

No agent involvement. A `watchfiles` watcher on the configured projects root publishes change
notifications over SSE; the browser refetches board state. State sources:

| Board element | Disk source |
|---|---|
| identity / rail order | `project.json` + `pipeline_defs/<type>.yaml` |
| stage states, gates, versions | `checkpoint_<stage>.json` + `history/` |
| script card / modal | `artifacts/script.json` |
| filmstrip cards | `scene_plan × script × asset_manifest` join |
| generating shimmer, activity | `events.jsonl` (written by `BaseTool` instrumentation) |
| cost meter | checkpoint `cost_snapshot` |
| renders | `renders/*.mp4` (+ root-level mp4 heuristic) |

Projects without checkpoints degrade gracefully to a "what the watcher
found" view — media, snapshots, renders.

**Replay**: a completed run can be scrubbed end-to-end (▶ REPLAY RUN on the
board) — reconstructed from checkpoint history and event timestamps.

Try it without a real production:

```bash
python scripts/backlot_simulate_run.py          # live demo run (~1 min)
python -m backlot open backlot-demo-run
```

Design doc: `internal/design/LIVING_STORYBOARD.md`.

After compose/publish completion, “Sửa tiêu đề” saves a presentation title in
project-local display_title.json. Original marker/checkpoints and last_activity
remain unchanged. Only the Backlot library/project heading uses this organizational name.
The video title in the posting package retains its original metadata.
Thumbnail cards show the exact stored generation prompt, with editable copy text
for manual generation; editing that textarea does not save provenance or call AI.
Agents fill the shared thumbnail-prompt.txt template from the hook and record the
fully resolved prompt in posting-package thumbnail metadata.
