from __future__ import annotations

import random
import re

from okf.colors import KS_PALETTE, pick_ks_color

_HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_picks_curated_color_when_room():
    color = pick_ks_color(set())
    assert color in KS_PALETTE


def test_never_repeats_an_existing_color():
    used: set[str] = set()
    # Assign as many colors as the palette holds; none should repeat.
    for _ in range(len(KS_PALETTE)):
        color = pick_ks_color(used)
        assert color not in used
        used.add(color)
    assert used == set(KS_PALETTE)


def test_fallback_generates_distinct_color_when_palette_exhausted():
    used = set(KS_PALETTE)
    color = pick_ks_color(used)
    assert color not in used
    assert _HEX.match(color)


def test_fallback_keeps_producing_new_colors():
    used = set(KS_PALETTE)
    for _ in range(10):
        color = pick_ks_color(used)
        assert color not in used
        assert _HEX.match(color)
        used.add(color)


def test_seeded_rng_is_deterministic():
    a = pick_ks_color(set(), rng=random.Random(0))
    b = pick_ks_color(set(), rng=random.Random(0))
    assert a == b
