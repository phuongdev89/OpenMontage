"""Embed URL normalization and domain allowlist for YouTube and Facebook."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus, urlsplit

ALLOWED_EMBED_DOMAINS = frozenset({
    "youtube.com",
    "www.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "facebook.com",
    "www.facebook.com",
})

FB_USER_AGENT = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extract 11-char YouTube video ID from various standard URL formats."""
    if not url:
        return None
    url = url.strip()
    match = re.search(r"(?:v=|\/shorts\/|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return None


def normalize_youtube_embed(url: str) -> Optional[str]:
    """Return strict privacy-enhanced YouTube embed iframe URL."""
    vid = extract_youtube_video_id(url)
    if not vid:
        return None
    embed_url = f"https://www.youtube-nocookie.com/embed/{vid}"
    parsed = urlsplit(embed_url)
    if parsed.netloc not in ALLOWED_EMBED_DOMAINS or parsed.scheme != "https":
        return None
    return embed_url


def extract_facebook_video_id(url: str) -> Optional[str]:
    """Extract numeric Facebook video ID from URL if already present."""
    if not url:
        return None
    match = re.search(r"(?:videos/|v=|v%3D|reel/|posts/|story_fbid=)(\d+)", url)
    if match:
        return match.group(1)
    return None


@lru_cache(maxsize=128)
def resolve_facebook_canonical_url(url: str, timeout: float = 5.0) -> tuple[str, Optional[str]]:
    """Detect and resolve Facebook URLs (including share/short links) to canonical URL with video ID."""
    if not url:
        return "", None
    url = url.strip()

    # If numeric ID is already directly in the URL
    vid = extract_facebook_video_id(url)
    if vid:
        return f"https://www.facebook.com/watch/?v={vid}", vid

    # If it's a share link or short link, query Facebook to obtain redirect target
    lower = url.lower()
    if "/share/" in lower or "fb.watch" in lower:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": FB_USER_AGENT,
                "Accept": "*/*",
            },
        )
        redirect_target = ""
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                redirect_target = resp.geturl()
                if not extract_facebook_video_id(redirect_target):
                    html = resp.read(15000).decode("utf-8", errors="ignore")
                    m_og = re.search(r'<meta property="og:url" content="([^"]+)"', html)
                    if m_og:
                        redirect_target = m_og.group(1)
        except urllib.error.HTTPError as exc:
            redirect_target = exc.headers.get("Location") or ""
        except Exception:
            redirect_target = ""

        if redirect_target:
            resolved_vid = extract_facebook_video_id(redirect_target)
            if resolved_vid:
                return f"https://www.facebook.com/watch/?v={resolved_vid}", resolved_vid

    return url, None


def normalize_facebook_embed(url: str) -> Optional[str]:
    """Return standard Facebook video plugin embed iframe URL using canonical video link with ID."""
    if not url:
        return None
    url = url.strip()
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https":
            return None
        allowed_origins = ("facebook.com", "fb.watch")
        if not any(host == d or host.endswith("." + d) for d in allowed_origins):
            return None
    except Exception:
        return None

    canonical_url, vid = resolve_facebook_canonical_url(url)
    target_url = canonical_url if vid else url

    encoded = quote_plus(target_url)
    embed_url = f"https://www.facebook.com/plugins/video.php?href={encoded}&show_text=0"
    return embed_url


def build_platform_embeds(posted_links: dict[str, dict]) -> dict[str, dict]:
    """Construct embed descriptors with strict allowlist and direct links."""
    result: dict[str, dict] = {}

    yt = posted_links.get("youtube") or {}
    yt_url = yt.get("url") or ""
    yt_embed = normalize_youtube_embed(yt_url)
    result["youtube"] = {
        "url": yt_url,
        "embed_url": yt_embed,
        "confirmed": bool(yt.get("confirmed")),
        "playable": bool(yt_embed),
        "platform": "YouTube",
    }

    fb = posted_links.get("facebook") or {}
    fb_url = fb.get("url") or ""
    canonical_fb, fb_vid = resolve_facebook_canonical_url(fb_url)
    fb_embed = normalize_facebook_embed(fb_url)
    result["facebook"] = {
        "url": fb_url,
        "canonical_url": canonical_fb if fb_vid else fb_url,
        "video_id": fb_vid,
        "embed_url": fb_embed,
        "confirmed": bool(fb.get("confirmed")),
        "playable": bool(fb_embed and fb_vid),
        "platform": "Facebook",
    }

    return result
