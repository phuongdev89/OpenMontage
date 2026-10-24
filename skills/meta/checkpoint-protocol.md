# Checkpoint Protocol — Meta Skill

## When to Use

After completing a stage's work AND passing review. This skill teaches you when and how to checkpoint, and when to ask the human for approval. It replaces the Python `checkpoint_policy.py` with an instruction-driven protocol.

Checkpoints are the save points of a pipeline. They enable resume-from-failure, human oversight, and audit trails.

## Protocol

First apply `skills/meta/approval-mode.md`. Persist the selected mode with
`set_approval_mode()` after init. manual_all gates every stage regardless of
manifest defaults. concept_only permits automatic research but requires
`record_concept_approval()` for the exact proposal/brief before automatically
resolving other gates. full_auto resolves gates without human_approved=True.
These mode rules override the default pause table below. Validation and review
remain mandatory. Never activate a mode while merely editing rules.

### Step 1: Check Manifest Policy

**Project auto-authorization exception:** The explicit project policy below
overrides this document's instructions to pause at gates (including sample
review and an existing `awaiting_human` checkpoint). Stage reviews, artifact
validation, sequential execution, and checkpoint writes remain mandatory.
An already waiting stage must be reviewed and rewritten through
`write_checkpoint(..., status="completed", human_approved=False)` before
downstream work. Never continue from an unchanged `awaiting_human` checkpoint.

When the user says "cho phép tự động duyệt" for a production project:

```python
from lib.checkpoint import authorize_auto_approval, PROJECTS_DIR
authorize_auto_approval(
    PROJECTS_DIR, project_id,
    authorization_text="<exact user instruction authorizing this project>",
)
```

Call this after `init_project()`; on resume read the existing marker instead
of renewing its timestamp. Do not enable it merely because the user is
discussing this feature or asks to implement the rule. On "tắt tự động duyệt"
or "yêu cầu duyệt lại", call `revoke_auto_approval(PROJECTS_DIR, project_id)`;
future gates pause again. All pipeline gates including `publish` are covered,
within the production task scope the user authorized. Locked voice/provider,
budget, and explicit user constraints still apply.

Read the current stage's configuration from the pipeline manifest:

```yaml
- name: idea
  checkpoint_required: true      # Must we checkpoint?
  human_approval_default: true   # Must we ask the human?
```

| `checkpoint_required` | `human_approval_default` | Action |
|----------------------|------------------------|--------|
| true | true | Checkpoint + present to human for approval |
| true | false | Checkpoint + proceed automatically |
| false | * | Skip checkpoint entirely (rare) |

### Step 2: Prepare Checkpoint Data

Gather everything needed for the checkpoint:

1. **Stage name** — which stage just completed
2. **Status** — `"completed"` (or `"awaiting_human"` if approval needed)
3. **Artifacts** — the canonical artifact(s) produced by this stage
4. **Metadata** — review findings, cost snapshot, timing info

### Step 3: Write Checkpoint

Call the checkpoint utility:

```python
write_checkpoint(
    pipeline_dir,      # Project working directory
    project_name,      # Project identifier
    stage_name,        # e.g., "idea"
    status,            # "completed" or "awaiting_human"
    artifacts,         # {"brief": {...}} — the stage's output
)
```

The checkpoint utility will:
- Validate the artifact against its schema
- Enforce the approval gate (a gated stage cannot be written `completed` without `human_approved=True`)
- Archive any superseded checkpoint to `projects/<id>/history/` (stage versions and gate transitions are never destroyed)
- Write the checkpoint JSON to disk
- Include timestamp and stage metadata

Canonical location: `projects/YYYY-MM-DD_<project_id>/checkpoint_<stage>.json` — always
pass the repo's `projects/` directory as `pipeline_dir` (or use
`lib.checkpoint.PROJECTS_DIR`). Always pass `pipeline_type` — gate enforcement
reads the manifest through it.

At pipeline initialization (before any stage), call `init_project()`:

```python
from lib.checkpoint import init_project
init_project("my-project", title="My Project", pipeline_type="cinematic")  # dir created as YYYY-MM-DD_my-project
```

This creates the canonical directory layout and writes `project.json` — the
marker the Backlot board needs to show the project before its first
checkpoint. Then launch the board: `python -m backlot open my-project`
(non-fatal if unavailable — the board is an observer, never a blocker).

### Step 4: Intra-Stage Checkpointing (Resume Support + Liveness)

**On entering any stage, write an `in_progress` checkpoint first.** This is
what tells the user (via the Backlot board) that the stage is live rather
than stalled — certainty matters more than speed.

Long-running stages (like `assets` or `compose` loops) can fail midway due to API errors, rate limits, or session interruptions. To allow resuming from the exact point of failure (e.g., Scene 4):

1. **Write partial progress**: Every time you successfully generate a significant item (e.g., one scene's assets, one clip), write an `in_progress` checkpoint.

   `in_progress` checkpoints may omit the stage's canonical artifact, but any artifact stored under a known artifact name is still schema-validated. If the partial data is not yet a valid canonical artifact, store it under `metadata.partial_progress` instead of `artifacts`.
   ```python
   write_checkpoint(
       pipeline_dir, project_name,
       stage="assets",
       status="in_progress",
       artifacts={},  # no incomplete canonical artifact yet
       metadata={
           "partial_progress": {
               "asset_manifest_draft": partial_manifest_dict,
               "completed_scene_ids": completed_scene_ids,
           }
       },
   )
   ```
   If the partial artifact already satisfies its schema (for example, an `asset_manifest` with `version: "1.0"` and valid `assets[]` entries), it may be stored in `artifacts` directly.
2. **Resume from partial progress**: When starting a stage, ALWAYS check if an `in_progress` checkpoint exists for it. See Step 7 (Resume Protocol) for how to handle it.

### Step 5: Human Approval (If Required)

**The manifest value is binding.** `human_approval_default` in the pipeline
manifest is the single source of truth for whether a stage gates. This skill
never overrides it, and neither do you — there is no "this case is different."
(`lib/checkpoint.py` enforces this: writing `status="completed"` for a gated
stage without `human_approved=True` raises a `GATE VIOLATION` error.)

When `human_approval_default: true`:

First check whether the current project marker contains a valid
`approval_policy.mode: "auto_approved"` recorded by
`authorize_auto_approval()` from an explicit user instruction for this
project. If so, continue without asking at this gate. Write the stage as
`completed` with `human_approved=False` and an `approval_resolution` object
that preserves the authorization text and timestamp. This is automatic
authorization, not a claim that a human reviewed the artifact. The policy is
project-scoped and remains in force when resuming until the user revokes it.

If no such authorization exists, follow the human approval steps below:

1. **Write the checkpoint with `status="awaiting_human"`** (not `completed`).

2. **Present a summary** to the human:
   ```
   ## Stage Complete: [stage_name] — awaiting your approval

   ### Artifact Summary
   [Key details from the artifact — title, duration, key decisions]
   [If the Backlot board is running, point to it: the artifact renders there]

   ### Review Findings
   [Summary from reviewer: N critical (all fixed), N suggestions]

   ### Cost So Far
   [Budget spent / total, breakdown by tool]

   ### Action Required
   Please review and approve to continue, or provide feedback for revision.
   ```

3. **END YOUR TURN.** Performing any further pipeline work in the same
   response is a gate violation. "Present and continue" is not waiting —
   the turn must end with the question, and the next pipeline action must
   be caused by the user's reply.

4. **On the user's response:**
   - **Approved** → re-write the checkpoint with `status="completed"`,
     `human_approved=True`, then proceed to the next stage
   - **Revision requested** → go back to the stage director skill with the
     human's feedback, produce revised artifacts, re-review, re-checkpoint
     (the superseded checkpoint is preserved automatically in `history/`)
   - **Abort** → stop the pipeline

5. **Approval is per-gate.** A prior approval, however broad ("looks great,
   go ahead and make the whole thing"), never covers a later gate. If the
   user explicitly pre-authorizes the full run, record that as a
   `decision_log` entry (`category: "approval_policy"`) at the moment they
   say it — absent that entry, stop at every gate.

6. **The assets gate reviews the storyboard — before any draft render.**
   `assets` now gates in every pipeline: present the generated assets
   scene-by-scene (the Backlot board's filmstrip is the natural review
   surface), including spend so far and the projected compose cost. A bad
   asset caught here saves a full re-render.

   **Do not render a draft/full composition to earn this review.** The review
   surface is the filmstrip populated with per-scene assets — stock picks,
   generated stills, narration waveforms — *not* a rendered video. For scenes
   whose "asset" is a bespoke/atelier composition (no thumbnailable file), the
   agent writes one **per-scene review still** to
   `projects/<id>/snapshots/<scene_id>.png` (a `remotion still` at a
   representative frame — see `skills/meta/bespoke-composition.md`); the board
   shows those on the filmstrip. Refresh `metadata.partial_progress` as stills
   land, then STOP at the gate. The draft/final render is the **compose**
   stage — it runs only after the assets gate is approved. Rendering a full
   draft inside the assets stage jumps the gate the user is meant to hold.

### Step 6: Determine Next Stage

After checkpoint is written and its gate is resolved by human approval or valid project auto-authorization:

```python
next_stage = get_next_stage(pipeline_dir, project_name)
```

This reads all existing checkpoints and returns the next stage that needs to run, or `None` if the pipeline is complete.

### Step 7: Resume Protocol

At the START of any pipeline run (not just after a stage), always check for existing progress:

```python
next_stage = get_next_stage(pipeline_dir, project_name)
```

If `next_stage` is not the first stage:
1. Inform the human: "Found existing progress. Resuming from stage: [next_stage]"
2. **Check for partial progress**: Read the checkpoint for `next_stage`:
   ```python
   current_cp = read_checkpoint(pipeline_dir, project_name, next_stage)
   ```
   If `current_cp` exists and its status is `"in_progress"`, inform the human you are resuming from the middle of the stage.
3. **Load artifacts**: Load prior artifacts from checkpoints for context. If resuming from `"in_progress"`, first load any schema-valid partial artifact from `current_cp["artifacts"]`. If the partial data is stored in `current_cp["metadata"]["partial_progress"]`, use that draft data and its completion markers (such as `completed_scene_ids`) to skip sub-tasks that are already done.
4. **Continue**: Continue generation from the next successful step, appending to the partial artifact.

If a checkpoint exists with status `"awaiting_human"`:
1. Inform the human: "Stage [name] is awaiting your approval"
2. Present the checkpoint data for review
3. Wait for approval before proceeding

### Sample Checkpoint (Reference-Driven Productions)

When a production is reference-driven (VideoAnalysisBrief exists), there is an
additional checkpoint between proposal approval and full production:

| Stage | checkpoint_required | human_approval_default | Notes |
|-------|--------------------|-----------------------|-------|
| `sample` | true | true | Always requires human approval |

The sample checkpoint:
1. Presents: rendered sample clip (10-15 seconds)
2. Cost: sample cost vs. projected full-video cost
3. Action: approve (→ proceed to script), revise (→ re-generate sample), abort

The sample checkpoint is NOT a pipeline stage — it's a sub-checkpoint within the
proposal stage. It does not produce a canonical artifact. It produces a rendered
preview clip stored at `projects/<name>/assets/sample/sample_v{N}.mp4`.

**Presentation format:**
```
## Sample Preview Ready

**Sample clip:** [path to sample_v1.mp4]
- Duration: [X] seconds (hook + 1 middle scene)
- Voice: [TTS provider + voice name]
- Visuals: [description — AI images, Remotion animations, etc.]
- Music: [source]

**Sample cost:** $[X.XX]
**Projected full video cost:** $[X.XX]

Does this feel right? I can adjust: voice, visual style, pacing, music, colors.
```

## Key Principles

1. **Always checkpoint completed work.** Even if `checkpoint_required: false`, consider checkpointing anyway if the stage took significant time or cost. Losing work is worse than an extra file on disk.

2. **Never skip a configured gate without recorded authorization.** Creative stages such as `idea` and `script` still require a human pause unless the user explicitly authorizes automatic approval for the current project.

3. **Include cost snapshots.** The human should know how much has been spent and how much remains before approving expensive downstream stages (assets, compose).

4. **Checkpoints enable resume.** If the pipeline crashes at `compose`, the human can restart and it picks up from `compose` — not from `idea`. This is the whole point.

5. **Be transparent in approval requests.** Don't just show the artifact — show the review findings, the cost, and any concerns. Help the human make an informed decision.
