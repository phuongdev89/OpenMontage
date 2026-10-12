# Per-stage approval configuration

Do not ask the three-mode startup question for new production tasks.
Read the real pipeline manifest and `.env.example` NEED_APPROVE_<STAGE> values.
`.env` / process environment overrides the example. Strict true/false only.
Unknown/new stages default to true. init_project snapshots these values into
project.json approval_policy.stage_approvals with source, time and resolved values.
Use that snapshot on resume; never read another project's policy or silently
change an existing project's policy when global configuration changes.

true: review artifact, write awaiting_human, present evidence, end the turn;
only complete after a direct approval. false: review and automatically complete,
keeping human_approved=false. This explicit per-stage configuration overrides
manifest/default ask-pause rules and caller default human_approval_required flags.
For concept selection, show the full catalog when proposal/idea requires approval;
otherwise choose from the full catalog using the task requirements and record why.
Source information blockers and explicit user constraints still require clarification.

Manual design checkpoints should include proposal design direction, scene_plan
per-scene layout/background/motion, and assets actual storyboard frames in every
enabled aspect ratio. No draft/full video render at assets in place of storyboard.
Review/schema/predecessors, quality, fonts, containment, providers and conversation
exports are always required. false never means skipping verification.

Existing manual_all/concept_only/full_auto and legacy authorizations remain valid
for their original projects. Do not change them merely to adopt this configuration.
set_approval_mode and record_concept_approval remain legacy-compatible APIs, not
mandatory startup steps for new projects.
