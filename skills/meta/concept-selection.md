# Complete concept selection

Read before asking the user to choose a visual concept or style.

Read the project mode from `skills/meta/approval-mode.md` first. full_auto inspects
the complete catalog, selects a suitable concept and logs why without asking.
concept_only shows the full list and records explicit concept approval through
`record_concept_approval()`. manual_all uses the full selection UI and retains
per-stage approval. A new task must first receive the user's approval-mode answer.

- Discover the current catalog from the relevant concept reference, pipeline
  `compatible_playbooks`, and installed style playbooks (including custom entries).
  Do not rely on a remembered count or hide less-recommended options.
- For math, inspect `skills/pipelines/math/visual-concepts.md` and the current
  `styles/math-*.yaml` files. The current supported set is news, detective, neon,
  chalkboard, notebook and manipulatives. Include new supported concepts too.
- Show EVERY existing concept with a friendly name and short description.
  Keep technical identifiers internal; choosing must not require reading code.
- Recommendations may mark entries within the complete list. Never replace it
  with 2–3 recommended choices and a free-text field for everything else.
- A custom concept is an optional addition after all existing choices, never
  the only way to choose an existing option.

## Selection UI

Use the host's selectable-option UI with the complete options list. Codex's
`request_user_input_async` accepts all entries in one question; do not imitate
another host's 2–3 option limit.

If the host imposes a hard limit, display the complete catalog in numbered groups
and provide a full-list selector or let the user pick a displayed number. Do not
require them to invent/type a concept name or inspect code. Preserve every option
and description, including options that are not recommended.

Wait for an explicit selection. A preselected option is not a submitted answer;
a concept preference is not stage approval.

## Creative proposals

Research-backed story pitches can still be developed for the brief. When also
asking for an existing visual concept/style, show its complete catalog alongside
those pitches; pitch count is not a limit on style choices. If selecting among
already created proposal concepts, list all of those too.
