# OpenMontage - Agent Guide

Start here. This is the complete operating guide and agent contract for OpenMontage.

## Approval configuration per stage

Không hỏi 3 chế độ duyệt khi bắt đầu task mới. Đọc `skills/meta/approval-mode.md`.
`NEED_APPROVE_<STAGE>=true` chờ duyệt stage; `false` tự tiếp tục sau review.
`.env` ghi đè `.env.example`; stage không có cấu hình mặc định cần duyệt.
`init_project()` lưu snapshot vào project.json. Resume dùng snapshot/quyền cũ;
không tự áp cấu hình mới lên project đang có. Snapshot per-stage ưu tiên hơn
manifest và chỉ dẫn chờ duyệt mặc định; không bỏ schema, chất lượng, predecessor,
provider routing hoặc nghĩa vụ xuất hội thoại. Không tự đặt human_approved=True.

For architecture, key files, and conventions see [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).

## First Interaction — Onboarding

When the user's first message is vague, exploratory, or asks what you can do ("make me a video", "what can you do?", "help me create something", "I want to make content"), read the onboarding skill **before** doing anything else:

**Read:** `skills/meta/onboarding.md`

This skill teaches you to run discovery, classify the user's setup, present capabilities in plain language, and offer starter prompts tailored to their available tools. The goal: get the user from "curious" to "making a video" in under 60 seconds.

**Skip onboarding** when the user arrives with a specific, actionable request (e.g., "Make a 60-second explainer about black holes"). Go directly to Rule Zero.

## Reference Video Entry Point

When the user provides a **video URL or local video file as inspiration** — for example:

- "Can you make a video like this?"
- "I love this YouTube Short. Make me something similar."
- "Use this Reel as a reference."

— do **not** treat this as a generic web-search or prompt-writing request.

This is a first-class workflow in OpenMontage.

### Required behavior

1. **Read:** `skills/meta/video-reference-analyst.md`
2. **Run the reference analysis workflow** using the local analysis tools (`video_analyzer`, transcript extraction, scene detection, frame sampling)
3. **Produce a grounded summary** of what the reference is doing:
   - content
   - pacing
   - structure
   - style
   - what makes it work
4. **Then** run normal capability audit and pipeline selection
5. Present differentiated creative directions and the **complete existing visual-concept catalog**, following `skills/meta/concept-selection.md`.

### Important distinction

- **Reference-driven request:** "make me something like this" -> use `video-reference-analyst.md`
- **Source-footage request:** "edit this footage" / "cut this into clips" -> use `source_media_review` and the appropriate footage-led pipeline

If a model misses this distinction, it will often fall back to plain search + guesswork. That is incorrect for OpenMontage.

## Rule Zero — All Production Goes Through a Pipeline

**Every video production request MUST go through the pipeline system. No exceptions.**

When the user asks to make, create, produce, or generate any video content — a trailer, explainer, clip, animation, or any other video — the agent must:

1. **Identify the pipeline.** Match the request to one of the pipelines in `pipeline_defs/`. If unclear, ask the user.
2. **Read the pipeline manifest.** `pipeline_defs/<pipeline>.yaml` — know the stages, tools, and quality gates.
3. **Run preflight.** Discover available tools via the registry. Present the capability menu.
4. **Execute stage by stage.** For EACH stage, read the stage director skill (`skills/pipelines/<pipeline>/<stage>-director.md`) BEFORE doing any work in that stage.
5. **Read Layer 3 skills before calling tools.** Before using any tool with an `agent_skills` field, read the referenced skill in `.agents/skills/`. These contain provider-specific prompting guidance, parameter optimization, and quality techniques that dramatically improve output.

**Do NOT:**
- Write ad-hoc Python scripts to call tools directly
- Skip the pipeline and go straight to API calls
- Generate assets without reading the stage director skill first
- Use a tool without checking its Layer 3 skill for prompting guidance
- Bypass preflight, checkpoints, or review

The intelligence is in the skills, not in improvised code. An agent that reads the director skills and Layer 3 knowledge will produce significantly better output than one that calls tools directly with generic prompts.

## What OpenMontage Is

OpenMontage is an instruction-driven video production system. The AI agent IS the intelligence — it reads instructions (pipeline manifests + stage director skills + meta skills) and drives the pipeline using tools.

```
Agent reads pipeline manifest (YAML) -> reads stage director skill (MD)
-> uses tools (Python BaseTool subclasses) -> self-reviews (meta skill)
-> checkpoints (Python utility) -> presents gated stages for human approval unless the project has explicit auto-authorization
```

**Python = tools + persistence.** No orchestration logic, creative decisions, review logic, or checkpoint policy in Python code. The agent makes those decisions guided by instructions.

Core loop:

1. Select a pipeline.
2. Run preflight.
3. Discover real tools from the registry.
4. Present the user with concepts, tool plan, production plan, and cost.
5. Execute stage by stage with checkpoints.

## Decision Communication Contract

For any meaningful production decision, the agent must communicate the decision before acting. The user should never have to infer which provider, model, or render path was chosen after the fact.

### Announce Before Execution

Before any paid or consequential generation call, state:

- the exact tool name,
- the provider,
- the model or provider variant,
- the reason it was chosen,
- whether it is a sample or a batch run.

### Ask Before Major Changes

The agent must ask the user before changing any major production choice, including:

- switching provider,
- switching model family or provider variant,
- switching from video-led to still-led treatment,
- switching composition engine when that changes the output character,
- dropping narration, music, or other approved creative elements,
- changing from sample mode to batch mode.

Minor prompt refinements inside an already approved provider/model path do not require separate approval unless they materially change the creative direction.

### Re-log Changed Decisions (Binding)

The `decision_log` is the board's Decisions rail and the run's audit trail. It is **append-only history, not a scratchpad.** When a choice you already logged changes mid-run — the user swaps the voice, you switch provider/model/runtime/music, or a fallback overrides an earlier pick — you MUST **append a new `decision_log` entry** for the new choice, reusing the **same `category` AND the same `subject`** (e.g. `category: "voice_selection"`, `subject: "Narration TTS provider"`), with the superseded option moved into `options_considered` and `rejected_because` noting it was changed.

Editing only a downstream artifact (the `asset_manifest`, a prop) while leaving the old decision in the log is a defect: the board keeps showing the stale choice (e.g. `voice → openai_onyx` after the user moved to Chirp3). The board identifies a decision by its **(category, subject) pair** and renders the latest entry for that pair as current (tagged "revised") — so the fix is to append the new entry with an identical `subject`, never to silently mutate the old one or reword the subject (a reworded subject reads as a different decision and both will show). Keeping distinct decisions in one category (e.g. TTS vs image `provider_selection`) is exactly why the pair, not the category alone, is the key. This applies at every stage, not just `idea`.

### Present Both Composition Runtimes (HARD RULE)

When both Remotion and HyperFrames are available on the machine (check `video_compose.get_info()["render_engines"]`), the agent **MUST present both options to the user** before locking `render_runtime` at the proposal stage. The agent MAY recommend one with rationale — but silently picking a "default" is forbidden even when the pipeline manifest or a director skill suggests one.

The presentation MUST include, for each runtime:

1. A one-sentence plain-language description of what it is best at for **this specific brief**.
2. A one-sentence honest tradeoff (why it might not be the right pick here).
3. The agent's recommendation and the reason, tied to the brief's delivery_promise and visual approach.

Then wait for explicit user approval before advancing. Record the full shortlist — BOTH runtimes plus any "ffmpeg" option that applies — as `options_considered` in the `render_runtime_selection` decision logged in `decision_log`. A decision log entry with only one runtime considered when both were available is a CRITICAL reviewer finding.

Exception: if only one runtime is available on the machine, the agent proceeds with it but MUST say so explicitly ("HyperFrames isn't installed on this machine; I'm proceeding with Remotion. Install HyperFrames if you want the alternative."). The `render_runtime_selection` decision still records the unavailable option as `rejected_because: "runtime not available on this machine"`.

This rule applies to every pipeline that invokes `video_compose` — not just Wave 1. A pipeline's director skill may recommend a runtime, but that recommendation is input to the conversation with the user, not a decision.

### Composition Authoring Mode — Templated vs Atelier

Orthogonal to *runtime* is *authoring mode*: **how** the composition is built. Present it as its own proposal decision and log it in `decision_log` (`category: "composition_mode"`).

- **Templated** — assemble the stock `cut.type` scene-types (`text_card`, `stat_card`, `bar_chart`, …) into the `Explainer`/`CinematicRenderer` compositions. Fast, cheap, reliable — and the reason most videos look alike. Right for batch output, localization variants, quick drafts, and low-stakes internal clips.
- **Atelier** — **hand-author the composition from scratch**: bespoke scenes, a one-off theme, and motion written for this piece, rendered via `composition_mode: "atelier"` (see `video_compose` → `_render_via_atelier`). No reusable creative components; a fresh visual language every time.

**Default to atelier for hero work** — marketing, launches, brand pieces, any single-deliverable explainer that must impress. The deciding rule: *reuse engine knowledge, never creative components.* In atelier mode the stock scene-type catalog, `hyperframes-registry` blocks, fixtures, and finished components are **off-limits** — they are frozen looks that reintroduce sameness. Before building, route through **`skills/meta/taste-direction.md`** to set the design read and taste dials, then **`skills/meta/bespoke-composition.md`**, which sequences: art direction (`visual-style`) → motion principles (Disney 12 via `framer-motion`/`lottie-bodymovin`) → engine mechanics (`remotion-best-practices` + the stock components read *only as a mechanics codex*) → render via the atelier path. Close with a **distinctness review**: *could this be any other product's video? does it reuse a look I've made before?* — the inverse of "does it match the reference." Atelier costs more tokens and iteration than templated; say so at proposal so the user opts in knowingly.

### Escalate Blockers Explicitly

When a blocker occurs, the agent must surface it immediately using this structure:

1. What was attempted
2. What failed
3. Whether the issue is auth, provider access, tool bug, or prompt/design quality
4. What options exist next
5. Which option the agent recommends, with reasoning

Do not continue with a substitute path until the user approves.

### Recommendation Style

When asking the user to choose, do not just list options. The agent should:

- provide the shortlist,
- explain the tradeoffs briefly,
- recommend one option,
- wait for approval before proceeding.

### No Unilateral Substitutions

If the approved path is blocked, the agent may investigate and prepare alternatives, but may not execute those alternatives without user approval.

This applies especially to:

- provider swaps,
- model swaps,
- fallback tools,
- prompt-only substitutes for reference-driven generation,
- still-image animatics in place of true motion.

## Math Problem Videos — English Prompt, Vietnamese Explanation

When making a math problem-solving video where the supplied problem is in English and the user requests a Vietnamese explanation, the script and final video MUST follow this order:

1. **Read the original English problem aloud, verbatim.** Preserve the supplied wording, numbers, units, conditions, and question; do not paraphrase or skip it. Mathematical notation may be spoken naturally in English without changing its meaning.
2. **Read a complete Vietnamese translation aloud.** Translate every part of the problem faithfully, preserving all mathematical information and what is being asked.
3. **Only then begin the solution walkthrough in Vietnamese.** Do not introduce solution steps, hints, or the answer before both readings finish.

Keep these as separate, consecutive script sections and scene/audio segments. Show the original English problem during its reading and the Vietnamese translation during its reading; long problems may span multiple readable screens. Reserve time for both readings before budgeting the solution. Generic hook, brevity, and on-screen word limits must not shorten or reorder the problem and translation.

At script review and final video review, verify the verbatim English reading, complete and accurate Vietnamese translation, and the English → Vietnamese translation → Vietnamese solution order in both narration and visuals. This rule applies across pipelines and render runtimes.

### Narration defaults (all new renders)

- **Readable pace:** Extend scene timing to fit the generated audio. Never speed narration up to force it into old timing.
- **Vietnamese and English narration speed:** Fix effective speed at `0.90x` relative to the provider native `1.0x` for both languages. Do not multiply the previous rate or apply an additional 10% slowdown. Pass Vbee `speed_rate=0.90` (or `speed=0.90` when the adapter uses that name). For VieNeu without speed control, generate native audio and apply pitch-preserving `atempo=0.90` exactly once. Audio already at `0.90x` must retain its rate during compose/mix. Record `baseline_speed=1.0`, `target_speed=0.90`, `effective_speed=0.90`, and actual post-processing filter in `voice_performance.provider_settings`. Verify reused audio metadata rather than assuming native speed; extend scene timing to match audio.
- **No first-person narrator:** In all agent-authored dialogue and narration, never self-identify as a teacher, host, or guide and never use first-person forms such as "I", "we", "tôi", "mình", "ta", or "chúng ta". Address viewers directly or use neutral/imperative phrasing (for example, "Chào các con. Hôm nay hãy cùng đến với một thử thách..."). Apply this to `voiceText`, subtitles, and visible dialogue. Preserve source material that must be quoted or read verbatim.
- **Full grade-level explanations:** Explain every solution step clearly, completely and at the confirmed grade level (from `grade-selection.json`). Never narrate tersely or skip steps — no "dễ dàng thấy", "tự nhiên suy ra", "clearly", "obviously"; define any above-grade term in grade-level language before using it. Extend scene timing to fit the fuller explanation; never compress explanations to fit old timing.
- **Vietnamese narration routing:** First use the `vieneu-tts` skill to generate Vietnamese audio locally with the selected male preset voice. If that skill is unavailable because the package, model, or runtime fails, fall back to the Vbee API using `VBEE_VOICE_CODE_VI`. Do not silently choose another provider; record the actual provider and fallback reason in the asset manifest and render report.
- **English problem reading:** Use the Vbee API with the configured `VBEE_VOICE_CODE_EN` (`am_echo`), render it at `0.90x`, then apply a `1.20` gain to that English segment during the mix. Verify the gain with an audio probe/FFmpeg measurement and confirm that it does not clip. Missing Vbee English configuration is a blocker; provider changes require user approval.

## Math Video — Extended Rules

All math problem-solving videos MUST also follow the full rule set in:

**[`skills/pipelines/math/voice-text-rules.md`](skills/pipelines/math/voice-text-rules.md)** — persona, `voiceText` encoding, hook, EN-TTS blocker, closing wish, `solutionMode` text rules.

**[`skills/pipelines/math/script-director.md`](skills/pipelines/math/script-director.md)** — grade detection, `solutionMode` UI, phase sequences, per-phase rules, guided answer-leak checklist, template table.

**[`skills/pipelines/math/pedagogy-rules.md`](skills/pipelines/math/pedagogy-rules.md)** — 7 sư phạm nguyên tắc, ví dụ đạt/chưa đạt, `teachingAid` design, `requiresIllustration` / `needsIllustration`, rà soát trước TTS.

**[`skills/pipelines/math/compose-director.md`](skills/pipelines/math/compose-director.md)** — các tỷ lệ được bật qua `.env` và lưu tại `project.json.output_video_formats`, layout, audio dùng chung, `formats.json`, kiểm tra sau render.

**Publish rules:** Math project phải có mọi bản được bật trong `exports/video/` theo `skills/pipelines/shared/output-formats.md` và thumbnail không lộ đáp án; áp dụng publisher tương ứng với manifest: [`explainer`](skills/pipelines/explainer/publish-director.md) hoặc [`animation`](skills/pipelines/animation/publish-director.md).

**Concurrent runs:** Read [`project-isolation`](skills/pipelines/shared/project-isolation.md) before assets/compose. Use exact project directories, project-local source/public assets and unique render props. Never overwrite shared narration/source files. Review audio ownership in every enabled ratio and bind conversation exports to the correct chat.

**Posting handoff:** Before publish, read [`posting-package`](skills/pipelines/shared/posting-package.md). Store a strong, accurate title, complete YouTube description, distinct Facebook/TikTok caption and a dedicated generated thumbnail in `publish_log.metadata.posting_package`. Route by `AI_IMAGE_PROVIDER` in `.env`: `museai` uses the `muse-image` skill, `zpro`/unset uses `image-generate`; a museai failure falls back one-way to image-generate. Do not extract video frames for posting thumbnails. Backlot shows the published package and copyable local paths with portrait/landscape tabs.

**[`skills/pipelines/math/creator-review.md`](skills/pipelines/math/creator-review.md)** — phần duyệt nội bộ cho người tạo: lời giải đầy đủ + audit result hiển thị trong chat trước TTS/render; `solution.md` không chia sẻ cho học sinh.

**[`skills/pipelines/math/visual-concepts.md`](skills/pipelines/math/visual-concepts.md)** — 6 visual concept (`news`, `detective`, `neon`, `chalkboard`, `notebook`, `manipulatives`), khi nào hỏi người dùng, cách map sang `styles/math-*.yaml` và Remotion/HyperFrames fields.

Summary of binding rules:

- **Narration (HARD):** Do not self-identify as "thầy", "cô", or any other role; remove first-person singular and plural forms. Address viewers as "các em / các con / các bạn nhỏ" or use neutral/imperative phrasing. Preserve verbatim source quotations.
- **`voiceText` encoding:** Digits and math symbols → spoken Vietnamese. No LaTeX/emoji/Markdown in `voiceText`.
- **Hook:** Open with a concrete puzzle contradiction shaped by the selected visual concept; build curiosity and ask a specific question without self-reference or answer leakage. Keep production sound cues outside `voiceText`. Declare the final challenge question in `math-intro.hookQuestion`.
- **Grade detection:** Analyse the problem, ask the user to confirm grade before solving. Save to `grade-selection.json`.
- **`solutionMode`:** Ask the user (`answer` vs `guided`) before solving. Wait for real input — no defaults, no timeouts.
- **Phase sequence (VI / `answer`):** `introduction → problem → [strategy] → solution → check → answer → closing`
- **Phase sequence (VI / `guided`):** `introduction → problem → strategy → solution → check → practice → closing` (`strategy` mandatory; one `practice`; no `math-answer`)
- **Phase sequence (EN problem):** Insert `read-english → read-translation` after `introduction`, before `strategy`. `read-english` uses `englishText` + empty `voiceText`; TTS = Vbee EN `0.90×`, English segment gain `1.20`. Missing EN config = **blocker**.
- **Guided leak check:** Before TTS — scan every `voiceText`, title, equation, note, diagram annotation for answer leakage.
- **Closing:** CTA before wish; closing wish mandatory as last line.
- **Pedagogy:** Explain *why* each step works (not just the formula). Match method to the confirmed grade. No shortcut tricks without explaining the basis. See `pedagogy-rules.md` for all 7 principles + "đạt/chưa đạt" examples.
- **Full explanations (HARD):** Never terse — every step gets a clear, complete explanation matched to the confirmed grade level; no skipping steps and no "dễ dàng thấy"/"obviously" phrasing; above-grade terms must be defined in grade-level language.
- **Subtitles off (HARD):** Math videos always ship with subtitles disabled in every enabled ratio: no burned-in narration captions, no subtitle track in the export, and no caption upload at publish. On-screen teaching text (title, problem, equations, diagram labels) is not subtitles and still follows the approved storyboard/playbook. Verify no subtitles in the post-render check and record it in `render_report`.
- **`teachingAid`:** Design custom manipulatives per problem. Declare `problem.requiresIllustration: true` and `needsIllustration: true` per scene where needed. Illustration appears from the first scene that uses it — not deferred to conclusions.
- **Render:** Always produce both portrait (1080×1920) and landscape (1920×1080). Do not mark complete with only one video. Shared audio — do not re-call TTS for a ratio change.
- **Device layout:** Landscape 16:9 is for PC/TV/tablet; portrait 9:16 is for Facebook/TikTok on phones. Use independent compositions, phone-safe margins and a 360 px readability review. Read `skills/pipelines/math/device-layout-rules.md` before scene planning and compose.
- **Creator Review:** After audit, display full solution + audit result in chat before TTS/render. `solution.md` is internal only — never served to students.
- **Visual concept:** After Creator Review, show ALL currently supported concepts as selectable options with friendly names and descriptions. Include new supported entries when installed. Recommendations must not hide other options or require custom text to select an existing concept. Read `skills/meta/concept-selection.md` and `visual-concepts.md`, then load the selected playbook. Do not default silently.

Do not re-implement these rules inline. Reference the skill files; keep this section as a summary only.

## Orchestrator

The agent itself orchestrates the production state machine:

`research -> proposal -> script -> scene_plan -> assets -> edit -> compose`

The agent:

1. Reads the pipeline manifest (`pipeline_defs/*.yaml`) to know the process
2. Calls `checkpoint.get_next_stage()` to find where to resume
3. Reads the stage's director skill (`skills/pipelines/<pipeline>/<stage>-director.md`) to know HOW
4. Uses tools (`tools/`) for concrete capabilities
5. Self-reviews using the reviewer meta skill (`skills/meta/reviewer.md`)
6. Checkpoints via the checkpoint protocol (`skills/meta/checkpoint-protocol.md`)
7. Presents to human for approval when `human_approval_default: true` and no project auto-authorization exists

Infrastructure files:

- `lib/checkpoint.py` — read/write checkpoints, stage validation
- `tools/cost_tracker.py` — budget governance
- `lib/pipeline_loader.py` — manifest loading and helpers

## Project Directory Convention

Every production run creates a project workspace under `projects/`. This directory is gitignored — all generated assets are regenerable.

```
projects/YYYY-MM-DD_<project-name>/
├── artifacts/          # JSON artifacts from each stage (research_brief, script, scene_plan, etc.)
├── assets/
│   ├── images/         # Generated images (PNG)
│   ├── video/          # Generated video clips (MP4)
│   ├── audio/          # Narration segments + final mix (MP3/WAV)
│   ├── music/          # Background music track (MP3)
│   └── subtitles.srt   # Generated subtitles
└── renders/
    └── final.mp4       # Final rendered video (the deliverable)
```

**Naming convention**: `YYYY-MM-DD_<kebab-title>` — local-date prefix followed by kebab-case title (e.g., `2026-10-10_hidden-math-of-nature`); no time-of-day component. When the same date+title name is taken by a different project, `init_project` appends `-2`, `-3`… to the slug.

At pipeline initialization, before any stage runs:

1. **Initialize the workspace**: `python -c "from lib.checkpoint import init_project; init_project('<project-id>', title='<Title>', pipeline_type='<pipeline>')"` — `init_project` prepends `YYYY-MM-DD_` automatically; creates the layout above and writes `project.json` (the marker the Backlot board reads).
2. **Open the board immediately**: run `python -m backlot open <project-id>` and verify that the Backlot server is listening before entering the first stage. This starts the Backlot server if needed and opens the user's browser at the project's live board. Do this for every production run; do not wait for the user to ask for a progress link. If the command fails, report the exact URL/startup error immediately and continue the production — the board is an observer, never a blocker. This is the agent's ONLY board duty; the board derives everything else from disk.

All tools and agents must write outputs to these paths — **always pass an explicit `output_path` under `projects/YYYY-MM-DD_<project-id>/`**. Assets written to the repo root, cwd, or temp dirs are invisible to the user's board and violate the workspace contract.

**This applies to atelier and HyperFrames-skill runs too**: hand-authored compositions still write the canonical artifacts they have (script or beats-plan, scene_plan-equivalent, asset manifest) plus checkpoints into `projects/YYYY-MM-DD_<project-id>/`. The board is runtime-agnostic; only runs that skip the artifacts get a degraded board.

## Music Library

Users can place royalty-free music tracks in `music_library/` (gitignored). The asset director will check this folder before falling back to API-based music generation.

```
music_library/
├── ambient_track.mp3
├── cinematic_epic.mp3
└── ...
```

If the folder has tracks, the proposal and asset stages should present them as options alongside generated music. See the proposal-director and asset-director skills for details.

## Available Pipelines

| Pipeline | Best For | Stability |
|----------|----------|-----------|
| `animated-explainer` | Topic to fully generated explainer | production |
| `talking-head` | Footage-led speaker videos | beta |
| `screen-demo` | Screen recordings and walkthroughs | production |
| `clip-factory` | Many clips from one long source | beta |
| `podcast-repurpose` | Podcast highlights and derivatives | beta |
| `cinematic` | Trailer, teaser, and mood-led edits | production |
| `animation` | Motion-graphics and animation-first videos | production |
| `character-animation` | Local rigged cartoon characters and reusable character acting | beta |
| `hybrid` | Source footage plus support visuals | production |
| `avatar-spokesperson` | Presenter-led avatar or lip-sync videos | production |
| `localization-dub` | Subtitle, dub, and translated variants | beta |
| `framework-smoke` | Test: minimal 2-stage smoke test | test |

> **Beta pipelines** have not been fully audited. They work, but expect rough edges. Mention this when the user selects one.

## Mandatory Preflight

Do this before any creative work. **Use `provider_menu_summary()` first — it's the human-ready rollup.** The raw `support_envelope()` dump is a firehose (megabytes of JSON on a well-configured machine); pasting it into chat will bury the user.

```bash
python -c "
from tools.tool_registry import registry
import json
registry.discover()
print(json.dumps(registry.provider_menu_summary(), indent=2))
"
```

The summary returns four fields the agent should translate into plain language:

- `composition_runtimes` — booleans for `ffmpeg`, `remotion`, `hyperframes`. This is the source of truth for the "Present Both Composition Runtimes (HARD RULE)" check.
- `capabilities[]` — one entry per capability family with `configured / total` counts and provider lists. Ready-made for the "N of M configured" menu.
- `setup_offers[]` — unavailable tools whose install is a 1-minute env-var fix. Lead with these when offering upgrades.
- `runtime_warnings[]` — specific signals like "hyperframes: npm package not resolvable". Surface these to the user verbatim — they're the kind of silent-failure bugs that break the governance contract.

Then, for deeper inspection (only when the summary isn't enough):

```bash
# Full menu — grouped available/unavailable per capability.
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu(), indent=2))"

# Raw envelope — every tool's full contract. Slow/firehose; use for debugging only.
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.support_envelope(), indent=2))"
```

Then:

1. Read the selected manifest in `pipeline_defs/`.
2. Check every `required_tools` entry against the registry.
3. Check `fallback_tools` for unavailable tools.
4. Report one of: `passed`, `degraded`, or `blocked`.
5. Do not start production until the user understands the real capability envelope.

### Provider Menu (Mandatory at Preflight)

Already fetched via `provider_menu_summary()` above. Read that output and **present it to the user as a capability menu**, not as a flat tool list. Use `provider_menu()` directly only when you need the per-tool detail the summary collapses.

**How to present:**

```
YOUR CAPABILITIES

  Video Generation:  0/13 configured
  Image Generation:  1/7 configured
  Text-to-Speech:    1/3 configured
  Music Generation:  1/1 configured
  Composition:       3/3 configured (FFmpeg, video_stitch, video_trimmer)

  You can produce videos now with images + TTS + FFmpeg.
  Quick upgrades available — see below.
```

For EACH capability with unavailable providers, read the `install_instructions` field from the menu output and present setup options grouped by effort:

```
QUICK SETUP OPTIONS (1-minute each — set an env var in .env)

  Video Generation (0/13 -> unlock the biggest upgrade):
    Each unavailable provider lists its own install_instructions.
    Read them from the provider_menu output and present grouped by env var.
    Example: if 3 tools need FAL_KEY, group them: "FAL_KEY unlocks 3 providers"

  Image Generation (1/7 -> more style options):
    Same pattern — read install_instructions from each unavailable tool.

  Text-to-Speech (1/3):
    Same pattern.

LOCAL OPTIONS (free, needs hardware):
  Tools with runtime=LOCAL or runtime=LOCAL_GPU — read from the menu.

Already Available:
  List what's working. The user should feel good about what they have.
```

**Rules:**
- Do NOT hardcode provider names, API key names, or setup URLs in your prompts.
  Read them from the registry's `install_instructions` field on each tool.
- Always show the ratio: "X of Y configured" — this makes breadth visible.
- Group by capability, not by individual tool.
- Show what they CAN do now, then what they COULD unlock.
- If the user declines setup, proceed with the best available path — no nagging.
- If a tool shares an env var with others, group them (read from `dependencies` field).

### Setup Offer Protocol

When tools are `UNAVAILABLE` but can be fixed with simple configuration, **offer the user setup help instead of silently working around the limitation.** Many tools are one env var away from working.

| Fix Complexity | Action |
|----------------|--------|
| **1-minute fix** (env var) | Offer to help configure now — read `install_instructions` from the tool |
| **5-minute fix** (install) | Explain what to install and why — read `install_instructions` from the tool |
| **Complex fix** (GPU, model download) | Note the limitation, explain what it would unlock, move on |

**Rules:**
- Always tell the user what they're missing AND what they'd gain
- Show the cost difference (free local vs. paid API)
- If the user declines setup, proceed with the best available path — no nagging
- Group related fixes (tools sharing the same env var dependency)

### Composition Runtimes (Inside video_compose)

`video_compose` has **three** render engines / runtimes. They are parallel, not ranked — the choice is made at proposal and locked in `edit_decisions.render_runtime`. Check which are available:

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
info = registry._tools['video_compose'].get_info()
print('Render engines:', info.get('render_engines'))
print('Remotion note:', info.get('remotion_note'))
print('HyperFrames note:', info.get('hyperframes_note'))
"
```

| Engine | Used For | Requires |
|--------|----------|----------|
| **FFmpeg** | Video-only cuts, concat, trim, subtitle burn | `ffmpeg` binary (always available) |
| **Remotion** | React-based composition: still images → animated video, text cards, stat cards, charts, callouts, comparisons, transitions with spring physics, word-level caption burn, TalkingHead avatar | Node.js (`npx`) + `remotion-composer/` + `node_modules` |
| **HyperFrames** | HTML/CSS/GSAP composition: kinetic typography, product promos, launch reels, website-to-video, registry-block-driven scenes, SVG character rigs | Node.js ≥ 22 + FFmpeg + `npx` (consumed via `npx hyperframes`) |

`render_runtime` is **locked at proposal** (`proposal_packet.production_plan.render_runtime`) and **carried through edit_decisions unchanged**. `video_compose` routes based on this field; silent runtime swaps are forbidden. If the chosen runtime becomes unavailable at compose time, surface a structured blocker per "Escalate Blockers Explicitly" above. See `skills/core/hyperframes.md` for the Remotion-vs-HyperFrames decision matrix.

### Critical Rule: Motion-Required Requests

For any request where the deliverable inherently depends on motion rather than static coverage, treat motion as a hard requirement. Examples:

- sci-fi trailers,
- cinematic teasers built from generated clips,
- hype edits,
- avatar or agent videos,
- any brief whose promise depends on moving shots rather than still frames.

For these requests:

- The `render_runtime` chosen at proposal (Remotion, HyperFrames, or FFmpeg) must be confirmed available up front if the planned visual treatment depends on it.
- Still-image fallback is forbidden. Do not quietly convert the job into a Ken Burns teaser, animatic, or slide-based video.
- FFmpeg-only fallback is forbidden when it changes the approved deliverable from motion-led video to still-led video.
- **Silent runtime swap is forbidden.** If `render_runtime="hyperframes"` was locked and HyperFrames is unavailable, do NOT route to Remotion instead. Surface the blocker, propose options, get user approval, log a `render_runtime_selection` decision — then proceed.
- Bubble critical issues immediately. If the chosen runtime is unavailable, fails to render, or provider clip generation fails in a way that blocks the approved treatment, stop and tell the user before proceeding.
- Do not spend more tokens or time on downgraded output unless the user explicitly approves the downgrade as an animatic or proof-of-concept.

**When Remotion is available**, the agent should design production plans around it:
- Explainer videos with `flat-motion-graphics` playbook -> Remotion animated scenes, not Ken Burns
- Data-driven videos -> Remotion stat cards and charts, not static image screenshots
- Any pipeline using still images -> Remotion spring animations, not FFmpeg pan-and-zoom
- **Screen demos of a CLI/terminal/install flow -> `TerminalScene` (synthetic screen recording), not OS-level capture.** See `.agents/skills/synthetic-screen-recording/SKILL.md`. Faster, deterministic, privacy-safe. Use real capture (`screen_recorder`, `cap_recorder`, `playwright-recording`) only when the demo is a real app UI or requires unpredictable live behavior.

### Remotion scene types available in `remotion-composer/`

See `remotion-composer/SCENE_TYPES.md` for the authoritative list and their cut schemas. Current scene types usable via `cut.type`:
`text_card`, `stat_card`, `callout`, `comparison`, `hero_title`, `terminal_scene`, `anime_scene`, `bar_chart`, `line_chart`, `pie_chart`, `kpi_grid`, `progress_bar`. Overlay types include `section_title`, `stat_reveal`, `hero_title`, `provider_chip`.

These stock scene-types are the **templated** path — fast and reliable, but they are why videos look alike. For **hero work, prefer atelier mode** (hand-authored composition) over this catalog; read those types as a *mechanics codex*, not a menu to assemble. See "Composition Authoring Mode" above and `skills/meta/bespoke-composition.md`.

**When Remotion is NOT available** and `render_runtime="remotion"` was NOT locked, `video_compose` may use FFmpeg Ken Burns motion on still images. This still works but produces less engaging visuals. Mention this tradeoff in the proposal. When `render_runtime="remotion"` IS locked and Remotion is unavailable, that's a blocker — escalate, don't silently swap.

When `render_runtime="hyperframes"` is locked and HyperFrames is unavailable (Node < 22, missing `ffmpeg`/`npx`, or `hyperframes doctor` reports issues), that's also a blocker. Do not substitute Remotion or FFmpeg without user approval + a logged `render_runtime_selection` decision.

Routing is automatic — `video_compose` reads `edit_decisions.render_runtime` and dispatches to the matching engine (`_render_via_hyperframes`, `_remotion_render`, or `_render_via_ffmpeg`). But the **agent must know both Remotion and HyperFrames exist at proposal time** so it can design the visual approach intentionally. Don't default to Remotion for motion-graphics-heavy concepts that HTML/GSAP would express more naturally, and don't default to HyperFrames for briefs that reuse the existing React scene stack.

## Capability Discovery

OpenMontage uses two layers for capability choice:

- selector tools: capability-level routing such as `tts_selector` and `video_selector`
- provider tools: concrete tools discovered via the registry that call a specific backend

Always inspect the registry first:

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_catalog(), indent=2))"
```

For finalist tools inspect:

- `capability`
- `provider`
- `usage_location`
- `supports`
- `fallback_tools`
- `related_skills`

Do not rely on memory or old docs when the registry can answer it.

## Tool Families

**Do not maintain hardcoded tool lists.** Always query the registry at runtime:

```bash
# See all tools grouped by capability (TTS, video_generation, image_generation, etc.)
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"

# See all tools grouped by provider (elevenlabs, openai, ffmpeg, etc.)
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_catalog(), indent=2))"
```

Key capability families to look for in the output:

- **tts** — Text-to-speech providers. Route via `tts_selector`.
- **video_generation** — Video generation providers (cloud, local GPU, stock). Route via `video_selector`.
- **image_generation** — Image generation providers (cloud, local GPU, stock). Route via `image_selector`.
- **music_generation** — Music and sound effect generation.
- **video_post** — Composition, stitching, trimming (FFmpeg-based, always local).
- **audio_processing** — Mixing, enhancement (FFmpeg-based, always local).
- **analysis** — Transcription, scene detection, frame sampling.
- **avatar** — Talking head and lip sync generation.
- **character_animation** — Local character specs, SVG rigs, pose libraries, action timelines, previews, and QA.
- **3d_world_generation** — Local semantic terrain, procedural biome scattering, explicit landmarks, diagnostic passes, and deterministic HyperFrames/Three.js camera fly-throughs. Route through `threejs_world` and read `skills/creative/3d-world-generation.md` plus `.agents/skills/threejs-world-generation/SKILL.md`.
- **3d_asset_acquisition** — Rights-safe GLTF/GLB catalogs for production-tier Three.js worlds. Route through `threejs_asset_catalog`; never substitute blockout primitives for a requested detailed or reference-grade environment.
- **3d_asset_generation** — Unique textured/PBR meshes from text or concept images. Route text-described hero assets through `atlas_3d`, image-conditioned assets and regional object extraction through `fal_3d`, and read `.agents/skills/3d-asset-generation/SKILL.md`. Announce provider/model/unit cost before every first paid call and sample before batching.
- **3d_world_rendering** — Production assembly, terrain, lighting, materials, camera, and image-sequence rendering in Blender. Route through `blender_world`; use Three.js for interactive/blockout review, not as a substitute for Blender when reference-grade scene density is requested.
- **enhancement** — Upscale, background removal, face enhance, color grading.

Each tool in the registry declares `best_for`, `install_instructions`, `runtime` (LOCAL, API, LOCAL_GPU, HYBRID), and `status`. Read these fields — do not assume tool strengths from memory.

### Tool Class Naming Convention

All tool classes use **PascalCase without a "Tool" suffix**. When importing tools in Python:

| Module | Class Name | NOT |
|--------|-----------|-----|
| `tools.audio.music_gen` | `MusicGen` | ~~MusicGenTool~~ |
| `tools.video.video_compose` | `VideoCompose` | ~~VideoComposeTool~~ |
| `tools.audio.audio_mixer` | `AudioMixer` | ~~AudioMixerTool~~ |
| `tools.tts.elevenlabs_tts` | `ElevenLabsTTS` | ~~ElevenLabsTTSTool~~ |
| `tools.analysis.transcriber` | `Transcriber` | ~~TranscriberTool~~ |
| `tools.subtitle.subtitle_gen` | `SubtitleGen` | ~~SubtitleGenTool~~ |

When in doubt, check: `grep "^class " tools/<path>.py`

All tools call via `.execute(params_dict)` (returns `ToolResult` with `.success`, `.data`, `.error`), NOT `.run()`.

### Selector Pattern

Three selector tools abstract multi-provider capabilities. **Selectors auto-discover providers from the registry.** Adding a new provider tool automatically makes it available through the selector — no selector code changes needed.

| Selector | Routes to | How it discovers |
|----------|-----------|-----------------|
| `tts_selector` | All tools with `capability="tts"` (ElevenLabs, Google TTS, OpenAI, Piper, Azure, fish.audio) | `registry.get_by_capability("tts")` |
| `image_selector` | All tools with `capability="image_generation"` (FLUX, Google Imagen, GPT Image, Recraft, etc.) | `registry.get_by_capability("image_generation")` |
| `video_selector` | All tools with `capability="video_generation"` | `registry.get_by_capability("video_generation")` |

Selectors route based on: user preference > availability > discovery order. They adapt input schemas between providers transparently.

## User-Facing Planning Protocol

Before committing to execution, present:

1. Creative directions when the brief is open, plus the complete existing concept/style catalog when asking for a choice. Read `skills/meta/concept-selection.md`; never replace existing options with a shortlist and a custom-text field.
2. Recommended pipeline.
3. Recommended tool path.
4. Alternative tool paths that are actually available.
5. Cost estimate and quality tradeoffs.
6. **Music plan** — mandatory for every pipeline that has audio. See below.
7. Production plan by stage.
8. Approval gate before asset generation.

If a user prefers a specific vendor and that tool is available, surface it directly. Do not hide provider choice.

### Music Plan (Mandatory)

Music is a critical part of any video. **Surface the music situation to the user at proposal/idea time** — do not silently defer it to the asset stage where a failure becomes expensive.

Check music availability in this order and present the options:

1. **User music library:** Check `registry.get_by_capability("music_library")` and inspect `music_library/`. If tracks exist, list durations and let the user pick one.
2. **Royalty-free search:** Check `registry.get_by_capability("music_search")` for configured search/download tools. Report licensing constraints and whether a key is required.
3. **Music generation APIs:** Check `registry.get_by_capability("music_generation")`. Report status, quota, cost, and quality tradeoffs honestly.
4. **Bring your own:** Note that the user can provide a track (for example from YouTube Audio Library or Jamendo) through the `music_library/` drop path.

**Always present the user with explicit choices:**
- Use a track from their library (which one?)
- Provide a different track (drop it in `music_library/`)
- Generate one via API (if available — name the provider and cost)
- Proceed without music

**If no music source is available:** Tell the user explicitly. Do NOT let this surface as a surprise at the asset stage.

Record the music decision in the proposal/brief artifact so the asset director knows what to do.

## Pipeline Asset Expectations

Each pipeline manifest's `tools_available` field declares what tools a stage can use. Use selectors for multi-provider capabilities — the selector handles routing to whatever is available. Read the pipeline manifest for the authoritative list per stage.

## Stage Agents

Each stage produces one canonical artifact that becomes the contract for the next stage. The stage director skill teaches the agent HOW to produce it.

| Stage | Director Skill | Canonical output | Core quality bar |
|------|---------------|------------------|------------------|
| `idea` | `*-director.md` | `brief` | Clear hook, target platform, duration, tone, and user intent |
| `script` | `*-director.md` | `script` | Structured sections, valid timing, coherent narration |
| `scene_plan` | `*-director.md` | `scene_plan` | Ordered scenes, timings, asset requirements |
| `assets` | `*-director.md` | `asset_manifest` | Provenance, paths, model/tool metadata, scene linkage |
| `edit` | `*-director.md` | `edit_decisions` | Concrete cuts, overlays, subtitle/music decisions |
| `compose` | `*-director.md` | `render_report` | Output paths, encoding profile, verification notes |

Stage contract rules:

- A completed or awaiting-human checkpoint must include the stage's canonical artifact.
- Canonical artifacts must validate against the JSON schema in `schemas/artifacts/`.
- Non-canonical outputs such as media files belong in stage-specific directories.
- Tools should record seeds/model versions for reproducibility.

## Reviewer Protocol

The reviewer is a meta skill (`skills/meta/reviewer.md`) — advisory, never directly blocks progression.

- Self-review after every stage execution, before checkpointing.
- Load `review_focus` items from the pipeline manifest for the current stage.
- Maximum two review rounds. After that, pass with warnings and move on.
- Findings categorized: critical (must fix), suggestion (should fix), nitpick (nice-to-have).
- Critical findings -> fix and re-review. Suggestions -> note and proceed.
- Check playbook `quality_rules` as constraints, not suggestions.

## Human Checkpoint Protocol

The checkpoint protocol meta skill (`skills/meta/checkpoint-protocol.md`) teaches the agent when to pause:

- Read `human_approval_default` from the pipeline manifest per stage. **New projects use saved NEED_APPROVE stage settings; legacy projects retain manifest/mode gates.** `lib.checkpoint.py` enforces each gate unless the current project has an explicit auto-approval authorization recorded by `authorize_auto_approval()`.
- Typical gated stages: `idea`/`proposal`, `script`, `scene_plan`, **`assets`** (review the generated assets scene-by-scene — the Backlot board's filmstrip — before compose locks them in), and `publish` where the pipeline has one. Most pipelines auto-proceed on `edit` and `compose`, but not all (documentary-montage gates `edit`) — the manifest you loaded is the only authority.
- When approval is required and no project auto-authorization exists: write the checkpoint as `awaiting_human`, present artifact summary, review findings, and cost snapshot — then **END YOUR TURN**. Doing further pipeline work in the same response is a gate violation.
- **Approval is per-gate.** An early "go ahead" never covers later gates. Full-run pre-authorization must use `authorize_auto_approval()` and is recorded in the project marker; do not infer it from a general request to make the video.
- When the user explicitly says **"cho phép tự động duyệt"** for the current project, call `authorize_auto_approval()` after project initialization and before crossing a gate. This is scoped to that project and may be revoked with `revoke_auto_approval()`. Keep `human_approved=False`; automatic gate resolution is recorded separately in `approval_resolution`.
- This exception takes precedence over stage-director instructions to pause, sample review, and approval checklists, including the publish gate within the authorized task. Review, schema validation, checkpoints, stage order, locked provider/voice/runtime choices, budget, and explicit user constraints remain mandatory. Do not enable this policy merely because the user asks to implement or discuss the feature.
- When paused at a human gate, wait for approval, revision request, or abort.

### Conversation Export After Compose and Publish

- After the `compose` stage is successfully completed, use the `export-conversation` skill to export the current conversation in both Markdown and JSON (`-f all`) to its session directory. Do this after the completed compose checkpoint is written; do not treat an `in_progress` or `awaiting_human` checkpoint as completion.
- Keep the conversation ID and exact output base path for both files. After the user authorizes publishing and the `publish` stage successfully completes, run `export-conversation` again for the same conversation and base path so the existing `.md` and `.json` files are overwritten with the updated conversation. Pass the file base path, not only its directory, because directory output creates new timestamped files.
- Follow the skill's source selection and output rules; do not manually reconstruct or copy the conversation transcript.

## Communication Protocol

Agents coordinate through canonical JSON artifacts, checkpoints, pipeline manifests, and the tool registry.

Primary files:

- Artifact schemas: `schemas/artifacts/`
- Checkpoint schema: `schemas/checkpoints/checkpoint.schema.json`
- Pipeline manifest schema: `schemas/pipelines/pipeline_manifest.schema.json`
- Pipeline manifests: `pipeline_defs/`
- Style playbooks: `styles/*.yaml` (validated by `schemas/styles/playbook.schema.json`)
- Tool contract: `tools/base_tool.py`
- Tool registry: `tools/tool_registry.py`
- Stage director skills: `skills/pipelines/<pipeline>/<stage>-director.md`
- Meta skills: `skills/meta/*.md`

Checkpoint rules:

- Checkpoints live at `projects/YYYY-MM-DD_<project_id>/checkpoint_<stage>.json` (the project workspace — this is what the Backlot board watches).
- `status` may be `completed`, `failed`, `awaiting_human`, or `in_progress`.
- Write an `in_progress` checkpoint on entering each stage; during `assets`/`compose`, refresh `metadata.partial_progress` after each completed scene/asset unit — this powers live progress on the board.
- `completed` and `awaiting_human` checkpoints must include the canonical artifact.
- A gated stage (`human_approval_default: true`) can be written `completed` with either an actual human approval (`human_approved=True`) or valid project auto-authorization (`approval_resolution.type: "auto_authorized"`); the latter keeps `human_approved=False` and records its source instruction.
- Superseded checkpoints are archived automatically to `projects/YYYY-MM-DD_<project_id>/history/` — stage re-runs never destroy run history.
- Invalid checkpoints or invalid canonical artifacts are contract violations and should fail fast.

Pipeline manifest rules:

- Pipelines are declarative YAML manifests in `pipeline_defs/`.
- Stages declare: `skill` (director skill path), `produces`, `tools_available`, `review_focus`, `success_criteria`, `human_approval_default`.
- Adding a new pipeline requires a manifest + stage director skills.

Tool rules:

- Every production tool must inherit from `BaseTool`.
- Tool discovery flows through the registry, not ad hoc imports.
- Support-envelope reporting is the source of truth for capability, status, and resource requirements.

## Style Playbooks

For Toán Olympic Cùng Con channel videos, read
[`channel-branding`](skills/pipelines/shared/channel-branding.md) before assets
and compose. Use the supplied original logo as a watermark fixed at top-left;
the gap to each adjacent edge must never exceed 5% (default 2%). Save the corner
schedule per project and include it in final render QA.

| Playbook | Best For |
|----------|----------|
| `clean-professional` | Corporate, educational, SaaS |
| `premium-minimalist` | Investor updates, expert explainers, product narratives |
| `flat-motion-graphics` | Social media, TikTok, startups |
| `minimalist-diagram` | Technical deep-dives, architecture |
| `ink-sketch` (Ink Theater) | Hand-drawn ink-on-white doodle animation; a character that draws itself, walks, dances; contraption explainers |

For custom, atelier, brand, launch, or hero work, read `skills/meta/taste-direction.md` before choosing a playbook. Carry its `taste_profile` into the proposal so later stages can preserve the design read, visual variance, motion intensity, information density, reference strategy, and anti-patterns.

### Style Fidelity Gate

The selected `styles/<style_playbook>.yaml` is the authority for the composition's overall visual language: background family, palette, typography, shapes, texture, shadows, and motion. The human-approved storyboard translates that contract into scene-level treatments; it does not silently replace the playbook. A scene-specific variation is allowed only when the approved storyboard explicitly calls for it and the variation stays within the playbook's `quality_rules`.

Before rendering, audit the complete composition source against both artifacts. Inspect global and scene-level CSS, inline styles, SVG fills/strokes, component themes, and runtime presets. Verify typography, every foreground/background pairing, color contrast, color-count limits, shadow/gradient/texture use, motion treatment, and consistency between portrait and landscape. A matching background alone is not a pass. Do not infer a dark, neon, branded, or other theme from a project name, template, renderer default, or older artifact.

Fix source-level deviations before render. If compliance would require changing the approved visual direction, stop and obtain storyboard approval before rendering. After an approved render, inspect representative frames across scenes and every enabled aspect ratio for actual style fidelity. A source-only correction does not change an already published MP4; rerender only when the user requests it or the active compose stage has valid approval.

### Hand-drawn "doodle" animation → Ink Theater / Ink Puppet

For any brief that wants a **hand-drawn ink doodle** look — "a sketch that comes to life", "a pencil / stick figure that walks or dances", "a little character that acts out the idea", whiteboard-doodle explainers — use the **Ink Theater** engine + **Ink Puppet** mocap system (`skills/creative/ink-theater.md`, `ink-theater/README.md`). It is a **style + reusable engine, not a new pipeline**: illustration / contraption pieces run on the `animation` pipeline; a mocap character (draws itself → walks / dances / waves via `InkPuppet.choreograph([...])`) runs on `character-animation`. Cross-tool entry points: **`/ink-art`** (create a vector doodle from scratch) and **`/animated-drawing`** (animate a *supplied* drawing with mocap — raster; `skills/creative/animated-drawing.md`). Never hand-tune character motion — the agent only chooses named mocap clips.

## Layer Map

OpenMontage has three instruction layers:

1. `tools/`
   What exists, what is available, cost, runtime, fallback, related skills.
2. `skills/`
   How OpenMontage wants those tools used in pipelines.
3. `.agents/skills/`
   Raw vendor or technology knowledge.

Reading order:

1. registry / tool contract — discover what's available
2. relevant pipeline or creative skill (Layer 2) — know HOW to use it in this context
3. underlying vendor skill (Layer 3) — **mandatory before calling any generation tool**

**Prefer skills over source code for tool usage.** Skills exist precisely so you don't need implementation details in the common case. Layer 2 tells you *what* and *when*. Layer 3 tells you *how*. For authoring prompts, choosing parameters, or understanding usage patterns, you should be reading skills — not `.py` files.

**Exception: debugging, audits, and verifying the governance contract.** When a skill and a tool disagree, or when something behaves differently than the skill claims, reading the tool source is fair game — that's often the only way to catch a silent-availability bug or a stale doc string. An audit that refuses to look at the implementation will miss exactly the bugs that matter most. If you do read source to debug, consider whether the finding belongs in a skill update afterward so the next agent doesn't need to repeat the dive.

**Layer 3 is not optional.** Every generation tool (video, image, TTS, music) has an `agent_skills` field listing its Layer 3 skills. These skills contain provider-specific prompt engineering, parameter tuning, and quality techniques. Read them before writing prompts. The difference between a generic prompt and a skill-informed prompt is the difference between "usable" and "cinematic."

Example: Before calling `kling_video`, read its `agent_skills` → `ai-video-gen` → get Kling-specific prompt structure, camera direction syntax, and quality keywords that the model responds to best.

### Layer 3 skills, by category

The `.agents/skills/` directory is large. When you're not coming in through a tool's `agent_skills` pointer, use this table to find the right file by *what you're trying to do*:

| Category | Skills |
|---|---|
| **Composition runtime** | `remotion`, `remotion-best-practices`, `synthetic-screen-recording` (fake terminal/UI demos via Remotion TerminalScene), `threejs-world-generation` (semantic terrain and free-viewpoint HyperFrames worlds) |
| **Animation knowledge (generic)** | `gsap-core`, `gsap-timeline`, `gsap-plugins` (SplitText / MorphSVG / DrawSVG / MotionPath / Flip / CustomEase), `gsap-utils`, `gsap-react`, `gsap-performance`, `gsap-scrolltrigger`, `gsap-frameworks`, `framer-motion` (Disney 12 principles), `lottie-bodymovin` (Lottie export) |
| **Character animation** | `character-rigging`, `svg-character-animation`, `pose-library-design`, `canvas-procedural-animation`, `character-animation-qa` |
| **Image generation** | `bfl-api`, `flux-best-practices` |
| **Video generation** | `seedance-2-0` (preferred premium default — cinematic, trailer, multi-shot, synced audio, lip-sync), `gemini-omni` (conversational video editing, reference tags, timecoded beats), `ai-video-gen`, `ltx2` |
| **Audio** | `elevenlabs`, `music`, `sound-effects`, `acestep`, `text-to-speech`, `azure-text-to-speech` (optional cloud TTS — tool `azure_tts`, same Speech key as `azure_stt`), `setup-api-key` |
| **Speech-to-text** | `speech-to-text` (whisper `transcriber` — default, offline), `azure-speech-to-text` (optional cloud STT — tool `azure_stt`, preferred when `AZURE_SPEECH_KEY` is set) |
| **Avatar / lip-sync** | `avatar-video`, `heygen`, `create-video`, `faceswap`, `video-translate`, `agents` |
| **Capture** | `playwright-recording` (browser flows), `ffmpeg` (post) |
| **Visualization** | `beautiful-mermaid`, `d3-viz`, `manim-composer`, `manimce-best-practices`, `manimgl-best-practices` |
| **Media editing** | `video-edit`, `video-download`, `video-understand`, `video-toolkit`, `visual-style` |

**When in doubt, read the category's meta routing file first:**
- Picking an animation runtime? → `skills/meta/animation-runtime-selector.md` routes between Remotion primitives, GSAP plugins, framer-motion, Lottie, Manim, D3.
- Picking a screen-recording mode (real capture vs synthetic terminal)? → `pipeline_defs/screen-demo.yaml` + `skills/pipelines/screen-demo/idea-director.md`.

## Quick Lookup

| Question | Where to look |
|----------|---------------|
| What tools exist? | `tools/tool_registry.py` and `registry.support_envelope()` |
| What providers are available for a capability? | `registry.capability_catalog()` |
| What tools exist for a vendor? | `registry.provider_catalog()` |
| How does a tool actually work? | the tool's `usage_location` from the registry |
| How should this pipeline stage behave? | `skills/pipelines/<pipeline>/...` |
| What is the checkpoint/review policy? | `skills/meta/` |

## What Not To Do

- **Do not bypass the pipeline.** Never write ad-hoc scripts to call tools directly. All production goes through pipeline stages with director skills. See Rule Zero.
- **Do not call generation tools without reading their Layer 3 skill.** Check the tool's `agent_skills` field, read the referenced skill, then craft your prompts using that guidance.
- **Do not skip stage director skills.** Before executing any pipeline stage, read its director skill. The skill contains the quality bar, the workflow, and the review criteria.
- Do not use deleted legacy names such as `tts_cloud`, `tts_engine`, or `video_gen`.
- Do not hardcode provider names, API key names, or setup URLs. Read them from the registry's `install_instructions` and `dependencies` fields.
- Do not tell a restricted shared-installation user to add credentials manually, create a `.env`, or export a key. Surface the unavailable provider as an administrator setup request and continue only with centrally provisioned capabilities.
- Before offering a direct vendor credential, check the registry for an available wrapper through an already configured provider (for example, a partner model hosted by fal.ai).
- Do not begin asset generation before user approval on the production plan unless the current project has explicit auto-authorization recorded with `authorize_auto_approval()`.
- Do not hide degraded paths. Record substitutions and blocked options explicitly.
- Do not present a single unavailable tool in isolation. Always show the full capability picture: "X of Y providers configured for this capability."
- Do not skip the Provider Menu at preflight. The user must see what they have AND what they could unlock.
- Do not change provider, model, or render path without telling the user first and getting approval when the change is material.

### Hook-first acceptance gate

- Câu được đọc đầu tiên phải nêu manh mối/mâu thuẫn hoặc thử thách cụ thể theo concept; cấm mở bằng "Chào", "Xin chào", lời giới thiệu lớp/kỳ thi hoặc "Hôm nay...". SFX mở đầu không thay thế hook trong lời đọc.
- Trong 3–5 giây đầu, hình và lời đọc phải cùng tạo tò mò từ dữ kiện đúng của bài toán. Lời chào, nếu có, xuất hiện sau dữ kiện hook; không bắt buộc có lời chào.
- Hook phải có câu hỏi/thách thức cụ thể, không lộ đáp án; tạo kịch tính bằng concept, không bịa dữ kiện hay phóng đại sai toán học.
- Review script phải trích nguyên câu đầu và ghi PASS/FAIL cho hook-first. FAIL thì sửa trước TTS, kể cả chế độ tự động duyệt.

## Vietnamese typography and text containment gate

- Dùng font hỗ trợ đầy đủ dấu tiếng Việt ở đúng weight/style; kiểm tra chuỗi có ă â ê ô ơ ư đ và dấu kép. Nạp font local hoặc font đã xác minh, không dựa vào fallback trên máy preview.
- Trước capture/render phải chờ font tải xong (`document.fonts.ready` với HTML/browser). Xác minh font thực tế và ảnh raster tiếng Việt; chỉ khai báo font-family không đủ bằng chứng.
- Kiểm tra mọi text container ở mọi tỷ lệ được bật (portrait/landscape), gồm tiêu đề, đề bài, labels, phụ đề và CTA. Với HTML kiểm tra scrollWidth/clientWidth và scrollHeight/clientHeight, sau đó kiểm tra ảnh thật để bắt dấu bị cắt hoặc glyph lỗi; runtime khác dùng kiểm tra bounding box tương đương.
- Chữ và dấu phải nằm trong border với padding an toàn. Sửa bằng wrap, chia trang, tăng vùng chữ hoặc giảm cỡ chữ trong giới hạn dễ đọc của playbook. Cấm dùng overflow:hidden/ellipsis để che mất nội dung hay bóp chữ méo.
- Ghi bằng chứng font, frame/ảnh review, tỷ lệ khung hình và kết quả containment vào review/render_report. Font lỗi hoặc chữ tràn = critical: sửa source trước render; auto-approval không bỏ qua kiểm tra này.

### Conversation export completion evidence

- After every successful export (after compose and after publish), copy both Markdown and JSON from the skill session directory into `<project_dir>/exports/conversation/`. Preserve the two filenames and overwrite those same project copies after publishing; do not create another timestamped pair. Confirm both project copies exist, are nonempty, and match their sources by hash or byte comparison before reporting export completion. Record source and project-copy paths in the corresponding checkpoint metadata, and link the project copies in the handoff. Report copy failures explicitly; a scratch-only export does not complete delivery.

- Sau checkpoint compose completed, bắt buộc thực thi skill `export-conversation` trước khi kết thúc lượt hoặc tiến tới publish, kể cả chế độ tự động duyệt. Đây là nghĩa vụ agent, không phải một bước cần hỏi người dùng.
- Không coi lệnh export được dự định hoặc đoạn transcript viết tay là đã xuất. Xác nhận exit code thành công, hai tệp Markdown/JSON tồn tại, đúng conversation ID/source và có nội dung transcript thật.
- Ghi conversation ID, source agent, output base path tuyệt đối, đường dẫn hai tệp và thời điểm export vào metadata checkpoint compose qua `write_checkpoint()`; giữ nguyên artifact và trạng thái approval khi bổ sung metadata. Dẫn link hai tệp khi báo hoàn tất.
- Sau publish completed, chạy lại export cùng ID/base path để ghi đè, xác minh lại và ghi bằng chứng vào metadata checkpoint publish. Auto-approval cũng phải thực hiện bước này.
- Nếu export thất bại hoặc không xác định được nguồn transcript: báo lỗi cụ thể, ghi pending/failed export trong metadata và không tuyên bố đã bàn giao đầy đủ; không tự tạo transcript thay thế.
