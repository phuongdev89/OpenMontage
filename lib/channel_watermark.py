"""Fixed-corner watermark with deterministic occasional logo rotations."""
from __future__ import annotations

import hashlib
import math
import random

CORNERS = ('top-left', 'top-right', 'bottom-left', 'bottom-right')


def plan_corner_watermark(*, width: int, height: int, duration: float,
                          asset_path: str, seed: str, interval: float = 8,
                          inset: float = .02, size: float = .10,
                          opacity: float = .55, corner: str = 'top-left') -> dict:
    """Anchor the square channel logo within 5% of both adjacent edges.

    The 5% constraint refers to gap from the logo box to the two nearest frame
    edges, not logo size. Randomness is fixed by the project's saved seed;
    the selected corner stays unchanged for the entire video.
    """
    if width <= 0 or height <= 0 or not all(math.isfinite(x) for x in (duration, interval, inset, size, opacity)):
        raise ValueError('Invalid watermark dimensions or settings')
    if duration <= 0 or interval <= 0 or not 0 <= inset <= .05 or not 0 < size <= .25 or not 0 < opacity <= 1:
        raise ValueError('Watermark inset must be between 0 and 5%; duration/interval/size/opacity must be valid')
    logo = max(1, round(min(width, height) * size))
    # floor ensures rounding never takes the edge gap above the requested %.
    x, y = math.floor(width * inset), math.floor(height * inset)
    if 2*x + logo >= width or 2*y + logo >= height:
        raise ValueError('Watermark does not fit the frame')
    positions = {
        'top-left': (x, y), 'top-right': (width-x-logo, y),
        'bottom-left': (x, height-y-logo),
        'bottom-right': (width-x-logo, height-y-logo),
    }
    if corner not in CORNERS:
        raise ValueError('Invalid fixed watermark corner')
    left, top = positions[corner]
    segments = [{'corner': corner, 'asset_path': asset_path,
                         'x': left, 'y': top, 'width': logo, 'height': logo,
                         'start_seconds': 0, 'end_seconds': duration,
                         'opacity': opacity}]
    spin_rng = random.Random(hashlib.sha256((seed + ':spin').encode('utf-8')).hexdigest())
    spins = []
    for index in range(math.ceil(duration/interval)):
        start_slot = index*interval
        if index % 2 == 0 and min(duration-start_slot,interval) >= 4:
            start = start_slot + spin_rng.uniform(1.5, 2.5)
            spins.append({'start_seconds': round(start, 3), 'duration_seconds': 1.2,
                          'axis': 'y', 'degrees': 360})
    return {'version': '1.2', 'seed': seed, 'corner': corner, 'width': width, 'height': height,
            'duration': duration, 'edge_inset_fraction': inset,
            'maximum_edge_inset_fraction': .05, 'segments': segments,
            'rotations': spins}
