# Math video layouts by viewing device

Use this reference for math videos on a real pipeline manifest, such as `animation` or `animated-explainer`. This directory contains shared math rules, not a pipeline named `math`.

## Separate deliverables

- **Landscape 16:9, 1920×1080:** viewing on PC, TV or tablet. Use horizontal space for a readable explanation and diagram when useful.
- **Portrait 9:16, 1080×1920:** Facebook/TikTok viewing on a phone. Author an independent layout; do not shrink or letterbox the horizontal layout.
- Reuse approved narration without new TTS or time stretching. Scene boundaries follow actual audio rather than estimated script duration.

## Portrait composition

- Baseline important-content safe area: left 72 px, right 144 px, top 120 px, bottom 280 px. These are conservative project margins, not platform UI specifications. Preview an overlay representing interaction buttons and caption space at delivery.
- Keep one mathematical idea in focus. Place the diagram/counting objects centrally, the current instruction above, and one relevant equation below.
- At a 360×640 preview, body text must be >=16 px and labels/equations >=18 px. At 1080×1920: body >=48 px and labels/equations >=54 px after SVG/viewBox/CSS scaling.
- Break long problems into consecutive readable pages if needed. Preserve the complete original statement and Vietnamese translation during their readings, without replacing them with lossy summaries.
- Avoid persistent footers that repeat the scene, use unreadable text, consume diagram space or reveal the answer prematurely. Opening and thumbnail must not reveal a completed solution.

## Mathematical state and movement

- Show initial state -> current operation -> resulting state. Counts, lengths and totals must match the narration and current diagram.
- Reveal worked solutions one step at a time. Long narration segments need meaningful sub-beats, not a solved static slide held throughout.
- Distinguish transformed quantities from original quantities. Restore original objects and totals in verification scenes.
- Keep fonts, group colors and treatments within the selected style playbook.

## Required evidence

Before final render, capture every scene and important transformation, wait for verified local fonts, check bounds and overflow, then review the raster at 360 px width. Save font-family/weight status, minimum effective font size, bounding-box failures and frame paths.

After render, inspect actual MP4 frames at the same times and verify dimensions/duration/audio. Compare audio packet hashes when claiming approved audio is unchanged. Source checks alone do not establish MP4 correctness.

For portrait-only revisions, preserve landscape and its hash; report that its previous review was not repeated. Keep old output in project history until the revision passes review. Record output paths, evidence and limitations in render_report and checkpoint metadata through write_checkpoint().
