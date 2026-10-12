# Toán Olympic Cùng Con — credit and watermark

User-approved channel identity: `branding/toan-olympic-cung-con/channel.json`,
logo `branding/toan-olympic-cung-con/logo.png`. Preserve the original image bytes,
including alpha; do not redraw, recolor or substitute a text watermark. The logo
is an explicitly requested brand overlay; its original colors are permitted
without changing the concept's scene design. Apply this identity to this channel's
videos, not unrelated client channels.

Before assets/compose, copy the channel configuration and logo into the exact
project (`assets/branding/`). Record the source logo SHA-256 and copied SHA-256;
snapshot the settings so shared edits cannot change another ongoing production.
The HTML design preview lives in `output/2026-10-12_credit-preview/index.html`.
Credit is a 3-second design draft; a preview is not a rendered final credit clip.
The credit logo keeps its orientation and does not rotate. Y-axis rotation
applies only to the corner watermark logo.

## Watermark contract

- Use the actual channel logo, default width/height 10% of the video's short edge,
  opacity 0.55. Preserve image aspect ratio (current logo is square).
- Keep the watermark at the top-left corner for the entire video. The gap from the
  logo bounding box to BOTH adjacent frame edges must be <=5% of the corresponding
  frame dimension. Default inset is 2%; this constraint is edge gap, not logo size.
- Never change corners or translate the logo across the image. Keep the logo
  fully inside the frame. Corner placements reserve logo space during layout.
- Use `lib.channel_watermark.plan_corner_watermark` with a project-specific seed
  saved in project-local metadata. The corner remains fixed; the seed controls
  only occasional rotation times. Do not use live randomness while
  rendering frames.
- Occasionally rotate the logo 360 degrees around its vertical (Y) axis over
  1.2 seconds, with smooth acceleration/deceleration, fixed corner anchor and no
  translation. Use the plan's saved `rotations` events. The HTML preview supports
  this effect. For final production, animate the logo layer in the chosen
  HTML/Remotion composition or render that animated layer before FFmpeg overlay;
  the static-image FFmpeg overlay below does not perform Y-axis rotations.
- During an authorized compose stage, invoke `video_compose` operation `overlay`
  with `corner_watermark` after the main composition, before final QA/checkpoint.
  Supply actual ffprobe width, height, duration, the saved seed and project-local
  logo path. Write a new output; preserve the original main render. Example:

```json
{"operation":"overlay", "input_path":"<project>/renders/main-landscape.mp4",
 "output_path":"<project>/renders/video-landscape.mp4",
 "corner_watermark":{"asset_path":"<project>/assets/branding/logo.png",
   "width":1920,"height":1080,"duration":120,"seed":"<project-id>-watermark-v1",
   "corner":"top-left","interval":8,"inset":0.02,"size":0.10,"opacity":0.55}}
```

The tool applies alpha with FFmpeg, uses half-open intervals to prevent two
logos appearing together at switch boundaries, copies audio and saves the exact
schedule alongside the output as `video-<ratio>.watermark.json`. Reference that
sidecar and logo hash in `render_report`. Preview-check logo placement, opacity,
unchanged duration/audio, every switch and both edges of each enabled ratio.
Ensure no mathematical content is hidden by reserving corner space; if collision
cannot be resolved within the <=5% constraint, revise the scene layout.

No automatic logo insertion into already published MP4 files. Standalone renderer
CLI calls do not automatically call this overlay step; follow the compose stage.
