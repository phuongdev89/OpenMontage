# OpenMontage — Claude Code Governance

This file is auto-loaded by the Claude Code runtime. It contains **binding
rules** that the agent must obey before, during, and after every production
task. Rules marked **(HARD)** are non-negotiable. Rules marked **(CODE-ENFORCED)**
are also checked by `lib/checkpoint.py` at write time.

For the full operating guide — pipeline selection, tool families, preflight,
style playbooks, capability discovery, and stage details — read
[`AGENT_GUIDE.md`](AGENT_GUIDE.md). For architecture and key files, read
[`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).

---

## Startup Self-Check (MANDATORY)

Before executing ANY production task (video creation, rendering, TTS, image
generation, or any pipeline stage work), run this checklist. If any item
cannot be verified, do NOT call a generation tool.

```
1. Read AGENT_GUIDE.md                                          □
2. Read the pipeline manifest for the selected pipeline         □
3. Determine current stage via checkpoint.get_next_stage()      □
4. Verify all predecessor stages are completed + approved       □
5. Check whether current stage is gated (human_approval_default)□
6. Identify approval evidence from user's actual message        □
7. Verify TTS routing (VieNeu first for Vietnamese)             □
8. Confirm no generation tool will be called before approval    □
```

If item 1 or 2 is incomplete, stop and read the file.
If item 4 fails, stop and report the gap to the user.
If item 6 has no evidence, write `awaiting_human` and end the turn.
If item 7 is unverified, check VieNeu availability before calling any TTS.
If item 8 would be violated, stop and ask the user first.

**`TaskCreate`/`TaskUpdate` are UI tracking tools, NOT checkpoints.**
Never treat a task-list update as evidence of stage completion or approval.

---

## Pipeline Rules (HARD)

1. **Every production request goes through a pipeline.** No ad-hoc scripts.
   No direct API calls outside a pipeline stage. Read `AGENT_GUIDE.md §Rule Zero`.

2. **Identify the pipeline before creating any artifact or calling any
   generation tool.** Match the request to `pipeline_defs/*.yaml`. If unclear,
   ask the user.

3. **Execute stages in manifest order.** The stage sequence is defined by the
   pipeline manifest, not by the agent's judgment.
   **(CODE-ENFORCED):** `write_checkpoint()` calls `_enforce_stage_prerequisites()`
   which raises `PREREQUISITE VIOLATION` if predecessors are missing.

4. **Read the stage director skill before executing any stage.**
   Path: `skills/pipelines/<pipeline>/<stage>-director.md`.

5. **Read the Layer 3 skill before calling any generation tool.**
   Check the tool's `agent_skills` field in the registry.

---

## Human Approval Rules (HARD)

### What is NOT stage approval

User preferences (grade level, `solutionMode`, visual concept, render runtime,
voice choice) are **input-gathering**, not stage approval. Receiving a preference
answer does not authorize advancing a gated stage.

### Gated stage protocol

For any stage where the pipeline manifest declares `human_approval_default: true`:

1. **Write `awaiting_human` first.**
   **(CODE-ENFORCED):** `write_checkpoint()` raises `GATE VIOLATION` if you write
   `status="completed"` without `human_approved=True` on a gated stage.

2. **Present the artifact summary, review findings, and cost snapshot.**

3. **End your turn.** Do not perform any further pipeline work in the same
   response after writing `awaiting_human`. This includes: no TTS calls, no
   image generation, no rendering, no advancing to the next stage. Continuing
   downstream in the same turn after `awaiting_human` is a gate violation.

4. **Wait for the user's explicit reply.** Only a direct message from the user
   constitutes approval. The following do NOT count as approval:
   - The user chose a preference option (grade, mode, concept).
   - An artifact was successfully created.
   - A task was marked completed in the task list.
   - The user originally requested "make me a video" (initial request ≠ per-gate approval).
   - A timeout elapsed.
   - The agent inferred approval from context.

5. **Only after explicit user approval:** re-write the checkpoint with
   `status="completed"` and `human_approved=True`, then proceed.

6. **Never self-set `human_approved=True`.** The agent must not pass
   `human_approved=True` to `write_checkpoint()` unless the user has explicitly
   approved that specific stage's output in a message directed at that gate.

7. **Approval is per-gate.** An early "go ahead" does not cover later gates
   unless recorded as a `decision_log` entry (`category: "approval_policy"`).

### Remaining vulnerability (HONEST DISCLOSURE)

`write_checkpoint(human_approved=True)` accepts the flag without verifying its
origin. The Python function trusts the caller. There is no runtime mechanism
that proves the `True` value came from an actual user message rather than the
agent's own decision. This is an **instruction-only** guard: the agent must
not pass `True` unless the user explicitly approved. No code prevents it.

---

## Checkpoint Rules (HARD)

1. **Always use `lib.checkpoint.write_checkpoint()`.** Never write checkpoint
   JSON files directly via `json.dump()`, `Path.write_text()`, or any other
   mechanism. The checkpoint writer provides:
   - Artifact schema validation
   - Gate enforcement (GATE VIOLATION)
   - Stage prerequisite enforcement (PREREQUISITE VIOLATION)
   - History archival
   - Atomic writes
   **(CODE-ENFORCED):** Bypassing `write_checkpoint()` skips ALL of these guards.

2. **Do not write `completed` for a stage when its predecessor is missing or
   unapproved.**
   **(CODE-ENFORCED):** `_enforce_stage_prerequisites()` raises
   `PREREQUISITE VIOLATION`.

3. **If `write_checkpoint()` raises `GATE VIOLATION` or `PREREQUISITE VIOLATION`:**
   - Stop immediately.
   - Report the full error message to the user.
   - Do NOT fix the error by adding `human_approved=True`.
   - Do NOT fix the error by writing a fake predecessor checkpoint.
   - Ask the user how to proceed, or correct the actual state (get real
     approval, complete the missing stage).

4. **Write `in_progress` on entering each stage.** This powers the Backlot
   board's liveness indicator.

---

## TTS Routing Rules (HARD)

### Vietnamese narration

1. **First: try `vieneu-tts` skill** to generate audio locally with VieNeu-TTS
   and the selected male preset voice.
2. **Only if VieNeu fails** (package missing, model unavailable, runtime error):
   fall back to Vbee API with `VBEE_VOICE_CODE_VI`.
3. **Never call `VbeeTTS()` directly for Vietnamese** without first attempting
   VieNeu. "I already know Vbee works" is not a valid reason to skip VieNeu.

### English problem reading (math videos)

- Always use Vbee API with `VBEE_VOICE_CODE_EN` (`am_echo`).
- Render at `0.85×`, apply `1.20` gain to the English segment during mix.
- Missing Vbee English configuration (`VBEE_VOICE_CODE_EN`, `VBEE_APP_ID`,
  `VBEE_ACCESS_TOKEN`) is a **blocker**. Stop and report before calling any
  Vietnamese TTS.

### Fallback recording

When a fallback occurs, record in BOTH `asset_manifest` and `render_report`:
- `tts_provider_actual`: the provider that was actually used
- `tts_fallback_reason`: why the primary provider was skipped
- `tts_primary_attempted`: the provider that was tried first

**Enforcement level: instruction-only.** No code validates TTS routing order.
The agent must self-enforce.

---

## Generation Gate Rules (HARD)

1. **No TTS, image, video, music, or render calls before the corresponding
   stage's approval gate is passed.** Specifically:
   - No TTS before `script` stage is approved (for gated pipelines).
   - No image/video generation before `scene_plan` stage is approved.
   - No rendering before `edit` stage checkpoint exists.

2. **Do not use a successfully created artifact as evidence that the stage
   was user-approved.** Creation ≠ approval.

3. **If an error or uncertainty arises, stop and report.** Do not:
   - Silently swap providers.
   - Silently swap runtime (Remotion ↔ HyperFrames ↔ FFmpeg).
   - Silently downgrade from motion to still images.
   - Continue with a substitute path without user approval.

**Enforcement level: partially code-enforced.** `_enforce_stage_prerequisites()`
prevents advancing a stage checkpoint when predecessors are missing, but it
does NOT prevent calling a generation API before writing any checkpoint at all.
The agent must self-enforce the "no generation before approval" rule.

---

## Math Video Rules (HARD)

All math problem-solving videos must also follow:

- **[`skills/pipelines/math/voice-text-rules.md`](skills/pipelines/math/voice-text-rules.md)**
  — persona (male teacher, "thầy"), `voiceText` encoding, hook, EN-TTS blocker,
  closing wish, `solutionMode` text rules.
- **[`skills/pipelines/math/script-director.md`](skills/pipelines/math/script-director.md)**
  — grade detection, `solutionMode` UI, phase sequences, per-phase rules,
  guided answer-leak checklist.
- **[`skills/pipelines/math/pedagogy-rules.md`](skills/pipelines/math/pedagogy-rules.md)**
  — 7 pedagogy principles, pass/fail examples, `teachingAid` design.
- **[`skills/pipelines/math/compose-director.md`](skills/pipelines/math/compose-director.md)**
  — two mandatory videos (portrait + landscape), shared audio, post-render checks.
- **[`skills/pipelines/math/creator-review.md`](skills/pipelines/math/creator-review.md)**
  — internal review: full solution + audit in chat before TTS/render.
- **[`skills/pipelines/math/visual-concepts.md`](skills/pipelines/math/visual-concepts.md)**
  — 6 visual concepts, user choice required, mapping to `styles/math-*.yaml`.

Read each file at its corresponding stage. Do not re-implement these rules
inline — the files are the source of truth.

---

## Decision Communication (HARD)

Before any paid or consequential generation call, state:
- the exact tool name and provider
- the model or variant
- the reason it was chosen
- whether it is a sample or batch run

See `AGENT_GUIDE.md §Decision Communication Contract` for the full protocol
including the `decision_log` append-only rule and the "Present Both Composition
Runtimes" hard rule.

---

## Enforcement Summary

| Rule | Enforcement level | Guard mechanism |
|---|---|---|
| Stage order | **CODE-ENFORCED** | `_enforce_stage_prerequisites()` raises `PREREQUISITE VIOLATION` |
| Gate approval required | **CODE-ENFORCED** | `write_checkpoint()` raises `GATE VIOLATION` |
| Artifact schema valid | **CODE-ENFORCED** | `validate_checkpoint()` + `validate_artifact()` |
| Style playbook exists | **CODE-ENFORCED** | `_validate_style_playbook()` raises error |
| Use `write_checkpoint()` not raw JSON | **Instruction-only** | No runtime guard; agent must self-enforce |
| `human_approved=True` origin verification | **Instruction-only** | Python trusts the caller; agent must self-enforce |
| TTS routing order (VieNeu before Vbee) | **Instruction-only** | No runtime guard; agent must self-enforce |
| No generation before approval | **Partially code-enforced** | Prerequisites check at checkpoint write, but not at API call time |
| End turn after `awaiting_human` | **Instruction-only** | No runtime guard; agent must self-enforce |
| Fallback reason in manifest | **Instruction-only** | No schema field validation; agent must self-enforce |
| Decision log append-only | **Instruction-only** | No runtime guard; agent must self-enforce |
