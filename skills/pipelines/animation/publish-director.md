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
- exports are labeled by purpose and platform,
- the package is usable without extra manual work.

#### Math-Video Publishing Contract

When the project is a math video and its compose artifacts include
`artifacts/formats.json`:

- Ensure the project's `exports/video/` contains both final renders as
  `video-portrait.mp4` (1080x1920) and `video-landscape.mp4` (1920x1080).
  Copy them from the paths recorded in `formats.json`; verify both files exist,
  are non-empty, and pass `ffprobe` dimension checks before completing publish.
- The final thumbnail must not reveal the answer in either `answer` or
  `guided` mode. Do not use the answer value, a completed solving equation,
  a circled result, or a frame from an answer-reveal scene. Inspect the actual
  image, or review the thumbnail concept if no image was generated; revise any
  answer-revealing element before publishing.
- Do not mark publish complete if either video variant is missing or the
  thumbnail reveals the answer.

## Common Pitfalls

- Writing generic metadata that ignores the animation style.
- Creating a thumbnail concept unrelated to the final frames.
- Mixing platform variants without clear labels.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
