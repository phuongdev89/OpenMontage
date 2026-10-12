import copy
import json
import pytest
from lib.checkpoint import (
    CheckpointValidationError, init_project, set_approval_mode,
    record_concept_approval, write_checkpoint, read_checkpoint,
    CANONICAL_STAGE_ARTIFACTS, get_pipeline_stages,
    authorize_auto_approval,
)
from tests.contracts.test_phase0_contracts import sample_artifact


def project(tmp_path, mode, name='mode-test'):
    path = init_project(name, title='Approval mode test', pipeline_type='animation', pipeline_dir=tmp_path)
    set_approval_mode(tmp_path, name, mode=mode, authorization_text=mode)
    return path, name


def write(tmp_path, name, stage, **kwargs):
    artifact = sample_artifact(CANONICAL_STAGE_ARTIFACTS[stage])
    if stage == 'edit':
        artifact['render_runtime'] = 'remotion'
    return write_checkpoint(tmp_path, name, stage, 'completed',
                            {CANONICAL_STAGE_ARTIFACTS[stage]: artifact}, **kwargs)


def test_manual_all_requires_human_even_for_non_gated_research(tmp_path):
    _, name = project(tmp_path, 'manual_all')
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write(tmp_path, name, 'research')
    write(tmp_path, name, 'research', human_approved=True)
    assert read_checkpoint(tmp_path, name, 'research')['human_approval_required']
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write(tmp_path, name, 'proposal')


def test_full_auto_completes_pipeline_without_faking_human_approval(tmp_path):
    _, name = project(tmp_path, 'full_auto')
    for stage in get_pipeline_stages('animation'):
        write(tmp_path, name, stage)
        cp = read_checkpoint(tmp_path, name, stage)
        assert cp['human_approved'] is False
        if cp['human_approval_required']:
            assert cp['approval_resolution']['type'] == 'auto_authorized'


def test_concept_only_waits_for_exact_concept_then_auto_runs_remaining(tmp_path):
    _, name = project(tmp_path, 'concept_only')
    write(tmp_path, name, 'research')
    artifacts = {'proposal_packet': sample_artifact('proposal_packet')}
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write(tmp_path, name, 'proposal')
    write_checkpoint(tmp_path, name, 'proposal', 'awaiting_human', artifacts)
    record_concept_approval(tmp_path, name, artifacts=artifacts, approval_text='Chọn và duyệt concept này')
    write_checkpoint(tmp_path, name, 'proposal', 'completed', artifacts)
    for stage in get_pipeline_stages('animation')[2:]:
        write(tmp_path, name, stage)
        assert not read_checkpoint(tmp_path, name, stage)['human_approved']
    changed = copy.deepcopy(artifacts)
    changed['proposal_packet']['concept_options'][0]['hook'] = 'A revised unapproved hook'
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write_checkpoint(tmp_path, name, 'proposal', 'completed', changed)


def test_mode_persists_on_resume_without_borrowing_other_project(tmp_path):
    path, name = project(tmp_path, 'full_auto', name='a')
    before = json.loads((path/'project.json').read_text())['approval_policy']['authorized_at']
    set_approval_mode(tmp_path, name, mode='full_auto', authorization_text='full_auto')
    assert json.loads((path/'project.json').read_text())['approval_policy']['authorized_at'] == before
    project(tmp_path, 'manual_all', name='b')
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write(tmp_path, 'b', 'research')


def test_legacy_auto_helper_cannot_erase_concept_only_mode(tmp_path):
    _, name = project(tmp_path, 'concept_only')
    with pytest.raises(CheckpointValidationError, match='set_approval_mode'):
        authorize_auto_approval(tmp_path, name, authorization_text='An inferred automatic instruction')
