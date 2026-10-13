# Publish Director - Animation Pipeline

## When To Use

Package the animation so the metadata, thumbnail concept, and platform framing reflect the actual visual system of the project.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/publish_log.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["compose"]["render_report"]`, `state.artifacts["proposal"]["proposal_packet"]`, `state.artifacts["research"]["research_brief"]`, `state.artifacts["script"]["script"]` | Final outputs and topic framing |
| Playbook | Active style playbook | Visual naming consistency |

## Process

### 1. Match Packaging To The Animation Mode

Examples:

- diagram-heavy videos should look structured and legible,
- kinetic-type pieces should package around strong copy,
- illustrative animation should package around hero imagery.

### 2. Preserve Visual-System Truth

Store in `publish_log.metadata`:

- `animation_mode`
- `hero_frame_notes`
- `thumbnail_concept`
- `platform_notes`

### 3. Quality Gate

- metadata fits the actual animation mode,
- thumbnail concept matches the final visual system,
- thumbnail passes the binding hook gate in
  `skills/pipelines/shared/posting-package.md`: three candidates before generation,
  actual image reviewed at approximately 320×180, specific viewer question and
  visible evidence; generic labels or decorative mystery alone fail,
- exports are labeled by purpose and platform,
- the package is usable without extra manual work.

#### Math-Video Publishing Contract

When the project is a math video and its compose artifacts include
`artifacts/formats.json`:

- Read `skills/pipelines/shared/output-formats.md`. Ensure `exports/video/`
  contains every enabled `video-<ratio>.mp4` from `formats.json`; verify they exist,
  are non-empty, and pass `ffprobe` dimension checks before completing publish.
- The final thumbnail must not reveal the answer in either `answer` or
  `guided` mode. Do not use the answer value, a completed solving equation,
  a circled result, or a frame from an answer-reveal scene. Inspect the actual
  image, or review the thumbnail concept if no image was generated; revise any
  answer-revealing element before publishing.
- Do not mark publish complete if any enabled video variant is missing or the
  thumbnail reveals the answer.

## Common Pitfalls

- Writing generic metadata that ignores the animation style.
- Creating a thumbnail unrelated to the concept, or copying the problem into a worksheet-like thumbnail.
- Mixing platform variants without clear labels.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.


## Posting package (binding)

Before completing publish, read `skills/pipelines/shared/posting-package.md`. Produce the title, full YouTube description, distinct Facebook/TikTok caption, concept-led dedicated image-generate thumbnail and every enabled final video variant for Backlot. No video-frame thumbnails.
