# Configured final video formats

Read before proposal, compose and publish. This replaces the older mandatory
portrait + landscape rule. `.env` defines defaults for NEW projects:

```ini
OUTPUT_VIDEO_LANDSCAPE=true
OUTPUT_VIDEO_PORTRAIT=false
```

`init_project()` snapshots `lib.output_formats.configured_output_formats()` in
`project.json.output_video_formats`. Bind selection to the exact project with
`lib.output_formats.project_output_formats(project_dir)`; never borrow another
run's selection. Legacy projects without the field retain both formats.
Resume uses the saved list; changing `.env` does not rewrite existing projects.
Only `true` and `false` are valid; both false is an error before initialization.
Restart persistent processes after editing `.env`.

- Plan, author and render ONLY enabled formats. Landscape: 1920×1080;
  portrait: 1080×1920. Each enabled format has its own composition layout.
- `artifacts/formats.json` records only enabled, successfully rendered outputs.
  `video.mp4`, if used as a compatibility alias, uses portrait when enabled,
  otherwise landscape. Do not create a disabled format for compatibility.
- Copy every enabled final output to `exports/video/video-<ratio>.mp4`;
  use an enabled render as `export_bundle.video_path`. The bundle's generic
  `output.mp4` does not replace those named files.
- Verify size, dimensions, typography, scene states, style and approved audio
  ownership for EVERY enabled format. Missing disabled formats are not failures.
  A missing enabled format blocks completion. Never delete earlier media when
  a selection changes; an existing project change needs an explicit request.
- Carry the saved selection and verification evidence in render/publish metadata.
  Backlot's tabs reflect delivered files; do not hide an older project's output
  because current global defaults differ.

The Python helper persists and validates configuration; `video_compose` rejects
disabled canonical `video-portrait.mp4` / `video-landscape.mp4` destinations
before invoking a renderer. Stage instructions govern other renderer invocations;
arbitrary filenames and direct external renderer commands are not guarded.
