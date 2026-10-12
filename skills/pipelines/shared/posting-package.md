# Published posting package

Read this before every publish stage. The completed project must have a usable
posting package in `publish_log.metadata.posting_package` for Backlot.

## Required content

- `title`: a specific curiosity hook grounded in the actual video, no false claims.
- `description`: first sentence poses the central challenge; then source/year/grade,
  complete problem context and units, what the video teaches, language, method,
  accurate chapters matching the final timeline, CTA and relevant hashtags.
- `caption`: independently written for Facebook/TikTok. Open with a concrete
  challenge, give enough data to understand it, invite a relevant comment and
  include a small set of hashtags. Never substitute the YouTube description.
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
