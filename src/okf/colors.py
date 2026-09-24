import colorsys
import random

# Curated: medium-dark, distinct on a white (#fff) graph background,
# and legible with WHITE chip text. ~16 entries.
KS_PALETTE: list[str] = [
    "#2563eb",  # blue
    "#dc2626",  # red
    "#059669",  # emerald
    "#d97706",  # amber
    "#7c3aed",  # violet
    "#db2777",  # pink
    "#0891b2",  # cyan
    "#4f46e5",  # indigo
    "#ca8a04",  # gold
    "#16a34a",  # green
    "#e11d48",  # rose
    "#9333ea",  # purple
    "#0d9488",  # teal
    "#ea580c",  # orange
    "#65a30d",  # lime
    "#be123c",  # crimson
]

DEFAULT_KS_COLOR = "#94a3b8"  # gray — KS with no assigned color

# Fallback band: keeps generated colors legible with white text and on white bg.
_FALLBACK_SATURATION = 0.65
_FALLBACK_LIGHTNESS = 0.45
_GOLDEN_ANGLE = 137.508


def pick_ks_color(used: set[str], *, rng: random.Random | None = None) -> str:
    """Return a #RRGGBB not already in ``used``.

    Prefers an unused curated color (random among the remaining). When the
    curated palette is exhausted, generates a distinct golden-angle HSL color
    that is also not in ``used``.
    """
    rng = rng or random
    used_lower = {c.lower() for c in used}
    available = [c for c in KS_PALETTE if c.lower() not in used_lower]
    if available:
        return rng.choice(available)
    return _generate_distinct_color(used_lower)


def _generate_distinct_color(used_lower: set[str]) -> str:
    # Step hue by the golden angle until we land on an unused color.
    # Bounded loop; 360 attempts covers every 1-degree hue.
    for i in range(360):
        hue = ((len(used_lower) + i) * _GOLDEN_ANGLE) % 360.0
        candidate = _hsl_to_hex(hue / 360.0, _FALLBACK_SATURATION, _FALLBACK_LIGHTNESS)
        if candidate.lower() not in used_lower:
            return candidate
    return DEFAULT_KS_COLOR  # pathological; effectively unreachable


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)  # note: colorsys is H,L,S order
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))
