"""Freeze per-stage approval settings for new projects."""
import os
from pathlib import Path
from dotenv import dotenv_values
from lib.env_loader import load_env


def configured_stage_approvals(pipeline_type):
    from lib.pipeline_loader import load_pipeline_readonly, get_stage_order
    manifest = load_pipeline_readonly(pipeline_type)
    load_env()
    defaults = dotenv_values(Path(__file__).resolve().parent.parent / '.env.example')
    stages = {}
    for stage in get_stage_order(manifest):
        key = 'NEED_APPROVE_' + stage.upper()
        value = os.environ.get(key, defaults.get(key) or 'true').strip().lower()
        if value not in ('true', 'false'):
            raise ValueError(f'{key} must be true or false')
        stages[stage] = value == 'true'
    return {'mode': 'stage_config', 'execution_mode': 'stage_config',
            'authorization_source': 'environment_config',
            'authorization_text': '\n'.join('NEED_APPROVE_' + s.upper() + '=' + str(v).lower() for s, v in stages.items()),
            'stage_approvals': stages}
