"""Validation for the manual, post-production upload milestone."""
from urllib.parse import urlsplit

PLATFORMS = ('youtube', 'facebook')


def validate_post_url(platform: str, raw: str) -> str:
    url = raw.strip()
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower()
        allowed = ('youtube.com', 'youtu.be') if platform == 'youtube' else ('facebook.com', 'fb.watch')
        if (parsed.scheme != 'https' or parsed.username or parsed.password
                or parsed.port not in (None, 443)
                or not any(host == domain or host.endswith('.' + domain) for domain in allowed)
                or parsed.path in ('', '/') or any(c.isspace() for c in url)):
            raise ValueError()
    except ValueError:
        raise ValueError(f'Link {platform} phải là HTTPS trên đúng nền tảng và trỏ đến bài/video đã đăng.') from None
    return url


def validate_posted_checkpoint(checkpoint: dict) -> None:
    from lib.checkpoint import CheckpointValidationError
    log = checkpoint.get('artifacts', {}).get('posted_log')
    if not isinstance(log, dict) or set(log) != set(PLATFORMS):
        raise CheckpointValidationError('posted requires youtube and facebook records.')
    for platform in PLATFORMS:
        record = log[platform]
        if not isinstance(record, dict) or type(record.get('confirmed')) is not bool:
            raise CheckpointValidationError('Invalid manual posting confirmation.')
        if record['confirmed']:
            try:
                validate_post_url(platform, record.get('url', ''))
            except (ValueError, AttributeError):
                raise CheckpointValidationError(f'posted requires a valid {platform} URL.') from None
            if record.get('source') != 'backlot_manual' or not record.get('confirmed_at'):
                raise CheckpointValidationError('posted requires manual confirmation evidence.')
    complete = all(log[p]['confirmed'] for p in PLATFORMS)
    if checkpoint.get('status') != ('completed' if complete else 'awaiting_human'):
        raise CheckpointValidationError('posted status must match both manual confirmations.')
    if checkpoint.get('approval_resolution') or checkpoint.get('human_approved'):
        raise CheckpointValidationError('posted uses manual upload evidence, not production approval.')
