# First question: approval mode

For every NEW video-production task, ask this single question immediately, before
onboarding, grade/solutionMode/concept/runtime questions, research, preflight,
project initialization, artifacts, provider calls or media. Wait for a submitted
answer; a preselected option does not count. Do not do other task work while waiting.

```json
{"questions": [{
  "title": "Bạn muốn duyệt task này theo chế độ nào?",
  "options": [
    "Duyệt thủ công toàn bộ (khuyến nghị)",
    "Duyệt mỗi concept, còn đâu tự động hoàn toàn",
    "Tự động hoàn toàn"
  ]
}]}
```

Use `request_user_input_async` in Codex or the host's selectable UI. If the host
has no buttons, show these exact options and wait for selection. No timeout/default.
Editing code/rules, audits and workflow discussion are not production tasks and
do not activate a mode. On resume, read the current project's stored mode; do not
ask again, renew its timestamp or borrow another project's authorization.

## Persist after the answer

Only after the answer, read the startup guide/manifest, initialize the project and
record the exact submitted label/reply before running any stage:

```python
from lib.checkpoint import set_approval_mode
set_approval_mode(PROJECTS_DIR, project_id,
                  mode="manual_all",  # or concept_only / full_auto
                  authorization_text="<verbatim submitted answer>")
```

| Choice | Mode | Execution |
|---|---|---|
| Duyệt thủ công toàn bộ (khuyến nghị) | manual_all | Present reviewed artifacts at EVERY stage, write awaiting_human, end the turn and await approval, including stages whose manifest default is false. |
| Duyệt mỗi concept, còn đâu tự động hoàn toàn | concept_only | Research/planning run automatically. Show the full concept catalog and obtain approval of the exact concept. All other initial choices and stages run automatically within task constraints. |
| Tự động hoàn toàn | full_auto | Select a suitable concept from the complete catalog, log choices/reasons and run all stages including publish without approval questions. |

For concept_only, after the user's direct choice/approval, record the exact draft:

```python
from lib.checkpoint import record_concept_approval
record_concept_approval(PROJECTS_DIR, project_id,
    artifacts={"proposal_packet": proposal_packet},  # or {"brief": brief}
    approval_text="<verbatim concept approval>")
```

Ensure the selected concept and chosen playbook match the project marker. Then
complete the pending proposal/idea through write_checkpoint with human_approved=False:
the first-question policy authorizes stage gates; the user's concept approval is
separate evidence, not human approval of the script/storyboard/final video.
Concept content, selected option or playbook changes require concept approval again
and a new fingerprint before downstream work. Never fake human_approved=True.

## Precedence

This mode overrides default ask/pause instructions in onboarding, stage skills,
sample review, concept selection and initial grade/solutionMode/runtime selection.
Automatic modes resolve unspecified initial preferences from the source, available
providers and task constraints, and log choices; concept_only keeps concept manual.
Explicit user preferences/required questions still take precedence. Do not silently
switch a locked provider or voice.

Every mode still requires the real manifest, stage order, predecessor checkpoints,
schema/quality/style/audio review, conversation exports and truthful errors. Do not
guess missing/unreadable source material. Ask beyond the approval plan only for an
actual blocker requiring user information or a change to explicit scope.

Changes of mode require a direct user instruction and a new set_approval_mode
record. Do not rewrite old projects just to apply this rule. Legacy auto-approval
remains supported. The first-question order is an agent obligation; Python guards
enforce recorded modes, not chat UI ordering or authenticity of a claimed reply.
