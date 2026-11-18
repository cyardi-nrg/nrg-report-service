# Design Lab worker v1.2.0 (2026-10-31) — sun on the worst day and the shade check.
# Same basis as the Pluga layout (approved by the owner): 21 December,
# 9:00–15:00 solar time every 30 min; a panel is dropped if ANY corner is
# shaded at any of those times. Vectorised over all points at once.
import math
import numpy as np

LAT_DEFAULT = 22.4   # Vadodara


def winter_sun(lat_deg: float = LAT_DEFAULT) -> list:
    """[(east, south, rise per metre)] — direction towards the sun in the site frame (x east, y south)."""
    lat, dec = math.radians(lat_deg), math.radians(-23.44)
    out = []
    for k in range(13):
        h = math.radians(15 * (9 + 0.5 * k - 12))
        el = math.asin(math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(h))
        ca = (math.sin(dec) - math.sin(el) * math.sin(lat)) / (math.cos(el) * math.cos(lat))
        az = math.acos(max(-1, min(1, ca)))
        az = az if h < 0 else 2 * math.pi - az
        out.append((math.sin(az), -math.cos(az), math.tan(el)))
    return out


def shaded(site, xs, ys, zs, sun, reach: float = 70.0, step: float = 0.25) -> np.ndarray:
    """True where a point (x, y, height z) is in shade at any of the sun positions."""
    xs, ys, zs = (np.asarray(v, dtype=float) for v in (xs, ys, zs))
    hit = np.zeros(xs.shape, dtype=bool)
    steps = np.arange(0.3, reach, step)
    for dx, dy, t in sun:
        for s in steps:
            live = ~hit
            if not live.any():
                return hit
            hh = site.h(xs[live] + dx * s, ys[live] + dy * s)
            hit[np.where(live)[0][hh > zs[live] + s * t + 0.02]] = True
    return hit
