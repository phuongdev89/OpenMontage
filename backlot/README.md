# Backlot — the living storyboard

## Revise posting copy

After publish, the posting section has **Tạo lại caption** and
**Tạo lại description**. Enter a revision request in the dialog and click
**Tạo lại**. The server calls the configured `AI_CHAT_URL`, `AI_CHAT_KEY` and
`AI_CHAT_MODEL` using `/chat/completions`, then saves the successful response in
that project's `artifacts/posting_copy.json`. The dialog shows the saved result;
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
