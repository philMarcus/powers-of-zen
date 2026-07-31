"""STYLE resolution (Layer 2). A journey names a `style` from styles/deck.json;
this looks up the curated word-only style_suffix + recommended model.

Resolution order (highest first):
  1. cli_style   (--style <name> render override, for A/B look-tests)
  2. spec["style"]        (the journey's chosen deck name)
  3. spec["style_suffix"] (LEGACY free-text — back-compat for engine-1 journeys)
  4. deck default

The composer's job is CONTENT; it picks a style NAME by mood, never free text.
The polished words live centrally in the deck so we can retune the whole catalog
in one place (the style flywheel).
"""
import json
from pathlib import Path

_DECK = Path(__file__).resolve().parent.parent / "styles" / "deck.json"


def load_deck():
    return json.loads(_DECK.read_text())


def _tail(deck, sfx):
    """Append the deck's shared brand tail (eye-candy sparkle + colour contrast) to any
    resolved style. Central so the whole catalog retunes in one edit — Layer-2 doctrine."""
    t = deck.get("brand_tail", "")
    return f"{sfx}, {t}" if (sfx and t) else (sfx or t)


def resolve(spec, cli_style=None):
    """-> (style_suffix, recommended_model | None, style_name | None)."""
    deck = load_deck()
    styles = deck.get("styles", {})
    name = cli_style or spec.get("style")
    if name:
        if name not in styles:
            raise SystemExit(f"style '{name}' not in deck; have: {', '.join(sorted(styles))}")
        e = styles[name]
        return _tail(deck, e["style_suffix"]), e.get("model"), name
    # legacy free-text suffix on the journey itself
    if spec.get("style_suffix"):
        return _tail(deck, spec["style_suffix"]), None, None
    # deck default
    dn = deck.get("default")
    if dn and dn in styles:
        return _tail(deck, styles[dn]["style_suffix"]), styles[dn].get("model"), dn
    return "", None, None
