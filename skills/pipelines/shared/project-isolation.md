# Concurrent project isolation

Read before assets and compose. Production may run in several chats at once.

1. Preserve the exact absolute `project_dir` returned by `init_project()`.
   Validate `project.json.project_id`, pipeline and style before every stage.
   No newest-directory lookup, first glob result, global current-project variable
   or process-wide cwd change may select inputs.
2. Store source, props, concat lists, public assets and outputs in that project.
   Source must remain available for future repair. Do not author production into
   shared `remotion-composer/src/Root.tsx` or shared generic components. The
   existing composer is an engine/dependency tree, not a mutable project workspace.
3. Remotion atelier uses `bespoke.public_dir=<project_dir>/public` and a project
   entry; every CLI render must pass `--public-dir`. Populate it from this project's
   approved assets only. Never write `public/master_narration.mp3` in the shared
   composer tree. Render-specific props and media snapshots are immutable until
   that render completes; concurrent renders must not share temporary filenames.
4. Audio reuse is allowed between this project's portrait and landscape variants.
   It is never implicitly allowed across projects. Resolve symlinks and assert
   narration is inside the bound project. Record project ID, absolute source,
   SHA-256, script section IDs, durations and effective speed. Verify approved
   provider/voice metadata and never time-stretch already slowed audio again.
5. Review audio from BOTH final videos against the approved master and scene
   timeline. Account for AAC encoder delay when comparing waveforms. For a music
   mix, compare/inspect spoken segments independently and confirm the complete
   original English question and Vietnamese translation refer to this problem.
   File existence, matching length, no clipping or one ratio's PASS are insufficient.
6. Publish copies from explicit paths in this project's verified formats/report;
   compare hashes after copying and preserve per-variant identity. Never use a
   shared `video.mp4` or newest render as the source. Stop on foreign audio/path
   or mismatched content and report the error before further media operations.
7. Export conversation from this exact current chat ID/source. During concurrent
   runs, automatic newest-global-session detection is unsafe. Confirm transcript
   includes this project's identity and source problem, then copy the MD/JSON pair
   and compare bytes. A matching copy hash only proves copying, not chat identity.

Render guards in `video_compose` reject foreign narration paths and atelier
public directories. Direct CLI calls do not inherit those Python guards; agents
must obey the same checks. These instructions do not claim runtime enforcement
of semantic correctness or of calls made outside the tool.
