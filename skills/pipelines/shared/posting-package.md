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

Generate a dedicated hook image under `exports/thumbnails/`, consistent with the
approved playbook. One focal puzzle, high contrast, large 3–5 word hook, readable
at mobile size. Keep true numbers/units and the challenge; never reveal the answer
or completed solution. Inspect the actual image before passing review. Generation
requires the project's valid publish approval or recorded auto-authorization.
Generation failure is an incomplete package; do not silently use a frame.

Both final videos belong under `exports/video/video-portrait.mp4` and
`exports/video/video-landscape.mp4`. Verify existence, size, dimensions and audio
ownership. Backlot derives the tab previews and copyable absolute paths from these
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
