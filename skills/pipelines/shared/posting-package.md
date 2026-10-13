# Published posting package

Read this before every publish stage. The completed project must have a usable
posting package in `publish_log.metadata.posting_package` for Backlot.

## Required content

- `title`: a specific curiosity hook grounded in the actual video, no false claims.
- Both `description` and `caption` must open with a concrete hook grounded in
  the problem, followed by the complete English problem verbatim when an English
  source exists, the complete Vietnamese problem (faithful translation), source
  attribution (competition/book, year, grade, question number), and relevant hashtags. Keep units and all conditions intact.
  Never invent an English original or source details. Do not insert source URLs,
  Scribd links or any other external links automatically. The user adds links manually. If provenance is
  unavailable, explicitly say the source has not been verified. Do not reveal
  the answer or completed solution in the hook/problem sections.
- `description`: YouTube copy also explains what the video teaches, includes
  accurate verified chapters when available, and a CTA.
- `caption`: independently phrase the hook and comment invitation for Facebook/
  TikTok. Keep the mandatory problem/source blocks even when they make it longer;
  do not shorten away conditions or replace it with the YouTube description.
- Use a small set of topic-specific hashtags, e.g. #ToanOlympicCungCon,
  #ToanOlympic, a verified grade/competition tag and the mathematical topic.
  No unrelated trending tags or unverified competition names.
- `thumbnails`: objects with project-relative `path`, `label`, `method`, `provider`,
  `prompt` and `review` (hook, readability, factual accuracy, no answer leak).

## Thumbnail generation

`AI_IMAGE_URL`, `AI_IMAGE_KEY`, `AI_IMAGE_MODEL` and the image protocol options
configure the image-generate API fallback. `AI_CHAT_URL`, `AI_CHAT_KEY` and
`AI_CHAT_MODEL` are separate and used only for text. Backlot's user-triggered
caption/description revisions are saved in `artifacts/posting_copy.json`; use
these field overrides when reading the latest posting copy. Such edits do not
advance the production pipeline or change published media/checkpoints.

Use the installed **image-generate** skill. Classify this as new image creation.
Try the agent's built-in image generation first; record the actual exposed tool
and provider, without inventing a model name. If unavailable or service-blocked,
follow the skill's configured API fallback and record the exact reason. Do not
use image_selector as a replacement for this routing. Never extract a video frame
or use a screenshot as the posting thumbnail.

Use the two 2026-10-12 refreshed thumbnails as quality references:
- Q21: Louis holding a rope coil in a sunlit wooden garden shed, expressive face,
  a thought bubble with exactly three unequal rope pieces and a question mark;
  short readable Vietnamese headline “BA ĐOẠN DÂY”.
- Q16: child detective with magnifying glass, real wooden-framed green felt board,
  pinned 1/2/4 clues with red string, mystery envelope, warm desk lamp;
  short readable Vietnamese headline “MANH MỐI BÍ ẨN”.
These are composition references, not a template to reuse for every problem.
Their headlines demonstrate short readable text, not sufficient hook strength:
“BA ĐOẠN DÂY” names a prop and “MANH MỐI BÍ ẨN” is generic. Neither alone
passes the hook gate below; the actual scene must carry a specific unresolved
question grounded in the source problem.
Build each thumbnail from that problem's concept, character, prop and coherent
setting. Favor expressive faces, tactile scenery, layered light/shadow and a
clear curiosity cue readable at mobile size. Do not replace the scene with a
worksheet, full problem statement, formulas or a generic flat card.
Review the actual generated image; these examples are not a guarantee that a
future generation is acceptable. If generation fails or the result fails review,
report the specific issue and leave thumbnail pending. The user may generate it
manually; preserve that supplied image and register it honestly as user-supplied.
Never claim a poor image passes just to finish the package.

Generate a dedicated concept-led narrative image under `exports/thumbnails/`,
consistent with the approved playbook's visual language. Start from the concept,
character, relevant prop, setting and an unresolved action/emotion. The thumbnail
is a curiosity scene, not a miniature lesson slide: do not reproduce the full
problem, equations, diagrams, answer options or a dense data table. Numbers and
units are optional; if used they must be accurate. A short 3–5 word hook is
optional, never mandatory when the scene tells the story clearly.

Example for `2026-10-12_16-49-11_amo-2022-grade2-q21-rope`: Louis holds a coil
of rope in a coherent garden shed, barn or orchard scene, looking curious. A
simple thought bubble shows three rope pieces and a length question mark.
Use the approved character appearance/reference when available. Do not put the
solution or all problem text into the bubble. Choose one believable setting,
not a collage of all settings. Preserve the mathematical premise without turning
decorative details into fabricated conditions of the source problem.

Record the exact prompt, concept, character/reference, setting and review.
Review the actual image at mobile size: concept fidelity, clear character/prop,
coherent scene, curiosity, readable optional text, factual accuracy and no answer
leak. Avoid generic worksheet/card layouts. Generation
requires the project's valid publish approval or recorded auto-authorization.
Generation failure is an incomplete package; do not silently use a frame.

Read `skills/pipelines/shared/output-formats.md`. Only enabled final videos belong
under `exports/video/video-<ratio>.mp4`. Verify existence, size, dimensions and audio
ownership for each enabled format. Backlot derives tab previews and paths from these
files. Metadata stays project-specific; do not reuse another project's log.

Example:

```json
{"posting_package": {
  "title": "A concrete puzzle hook",
  "description": "A complete YouTube description with accurate chapters",
  "caption": "A distinct social challenge and comment invitation",
  "thumbnails": [{"path": "exports/thumbnails/thumbnail.png",
    "label": "Thumbnail", "method": "image-generate", "provider": "built-in",
    "prompt": "The exact generation prompt", "review": {"hook": "PASS",
    "readability": "PASS", "factual_accuracy": "PASS", "no_answer_leak": "PASS"}}]
}}
```

## Thumbnail hook gate (binding)

Before generation, develop three distinct hook candidates grounded in the
actual source problem and approved concept. For each record the source fact,
the specific question the viewer should want answered, the visual action or
contrast that communicates it, and optional short Vietnamese headline.
Choose the strongest candidate and record why; this is an internal review,
not a new human approval gate or permission to generate before publish approval.

The hook must communicate a concrete question, surprising relationship or
challenge. A topic/prop label, generic “mystery”, decorative question mark,
thought bubble or expressive face alone is insufficient. Do not invent stakes,
mathematical conditions, difficulty claims or claims about other viewers.
Do not reveal the answer or completed solution. Optional text supports the
visual question; omitting text does not waive hook strength.

Review the actual generated image at approximately 320×180, not just its prompt
or full-resolution preview. Record in each thumbnail's `review`:
- `hook`: PASS or FAIL;
- `viewer_question`: one concrete sentence explaining what the viewer wants to
  find out, specific to this source problem;
- `source_fact`: the actual problem fact supporting that question;
- `visual_evidence`: visible action/contrast/prop relationship communicating it;
- `mobile_preview_size`: the size actually inspected;
- `readability`, `factual_accuracy`, `no_answer_leak`: PASS or FAIL with reasons
  for failures.

Store the three candidates, chosen candidate and selection reason in the
thumbnail generation record. If a reviewer cannot identify a specific viewer
question from the actual small image, hook is FAIL even if the image is beautiful.
Any FAIL blocks thumbnail acceptance and publish completion; revise within the
project's authorized scope or leave thumbnail pending with the reason.
Do not use an average score or a generic PASS to override this gate.

## Agent-owned reusable thumbnail prompt

Agent MUST read `skills/pipelines/shared/thumbnail-prompt.txt`, fill only
{{HOOK_SCENE}} from the selected candidate, including the source fact, specific
viewer question, character/action/prop/setting and visible unresolved relationship,
and send the fully resolved prompt to image generation. The user is not asked
to fill it. Save that exact submitted prompt (not a summary) in each thumbnail's
`prompt` metadata so Backlot can display/copy it. Save final refinements as the
actual prompt used, retaining earlier attempts in the generation record.
The template lives outside projects and survives project deletion. The two
examples above are written composition references and require no project files.
Backlot's prompt textarea is editable for manual copying; edits there do not
regenerate images or silently claim that edited text was the generation prompt.
