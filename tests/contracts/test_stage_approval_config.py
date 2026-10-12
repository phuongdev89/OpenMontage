import json
import pytest
from lib.approval_config import configured_stage_approvals
from lib.checkpoint import init_project, write_checkpoint, read_checkpoint, CheckpointValidationError
from tests.contracts.test_execution_approval_modes import write


def test_example_defaults_and_strict_values(monkeypatch):
    monkeypatch.setenv('NEED_APPROVE_RESEARCH', 'false')
    monkeypatch.setenv('NEED_APPROVE_PROPOSAL', 'true')
    policy = configured_stage_approvals('animation')
    assert policy['stage_approvals']['research'] is False
    assert policy['stage_approvals']['proposal'] is True
    monkeypatch.setenv('NEED_APPROVE_PROPOSAL', 'yes')
    with pytest.raises(ValueError, match='NEED_APPROVE_PROPOSAL'):
        configured_stage_approvals('animation')


def test_config_overrides_manifest_and_is_frozen(tmp_path, monkeypatch):
    monkeypatch.setenv('NEED_APPROVE_RESEARCH', 'false')
    monkeypatch.setenv('NEED_APPROVE_PROPOSAL', 'true')
    path = init_project('settings', title='Settings', pipeline_type='animation', pipeline_dir=tmp_path)
    monkeypatch.setenv('NEED_APPROVE_RESEARCH', 'true')
    write(tmp_path, 'settings', 'research', human_approval_required=True)
    cp = read_checkpoint(tmp_path, 'settings', 'research')
    assert not cp['human_approved'] and not cp['human_approval_required']
    assert cp['approval_resolution']['authorization_source'] == 'environment_config'
    with pytest.raises(CheckpointValidationError, match='GATE VIOLATION'):
        write(tmp_path, 'settings', 'proposal')
    write(tmp_path, 'settings', 'proposal', human_approved=True)
    assert json.loads((path / 'project.json').read_text())['approval_policy']['stage_approvals']['research'] is False


def test_false_can_disable_manifest_gate(tmp_path, monkeypatch):
    monkeypatch.setenv('NEED_APPROVE_RESEARCH', 'false')
    monkeypatch.setenv('NEED_APPROVE_PROPOSAL', 'false')
    init_project('automatic', title='Automatic', pipeline_type='animation', pipeline_dir=tmp_path)
    write(tmp_path, 'automatic', 'research')
    write(tmp_path, 'automatic', 'proposal')
    assert not read_checkpoint(tmp_path, 'automatic', 'proposal')['human_approved']
    monkeypatch.setenv('NEED_APPROVE_SCRIPT', 'true')
    write(tmp_path, 'automatic', 'script', human_approved=True)
