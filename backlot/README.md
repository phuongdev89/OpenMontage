# Backlot — the living storyboard

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

No agent involvement. A `watchfiles` watcher on `projects/` publishes change
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
