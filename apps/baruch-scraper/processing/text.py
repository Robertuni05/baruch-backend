"""
Shared text utilities for the canonicalization + matching pipeline.

Single source of truth so `normalize` (canonical creation) and `score` (matching)
always compare names the same way. Diverging normalization between the two steps
silently lowers match scores — see the normalization-asymmetry risk.

Spec model (grounded in real store data):
  - UNIT-BEARING specs ("4gb", "128gb", "700w") are the hard discriminators —
    RAM/storage/power/capacity. They must match exactly, or it's a different product
    (8GB vs 16GB). Note the same unit can measure two dimensions: "4GB 128GB" =
    RAM + storage, so we keep the full set, not a per-unit value.
  - BARE numbers ("50", "55", "6.7") are softer — screen sizes, often present in one
    listing and omitted in another. They conflict only when BOTH names have them and
    they are disjoint (50" TV vs 55" TV), which protects sizes without over-splitting.

No SQL, no I/O — pure functions, safe to import anywhere.
"""
import re
import unicodedata
from functools import lru_cache
from typing import FrozenSet

# Tokens that are measurement units.
UNIT_TOKENS = {'w', 'l', 'gb', 'tb', 'mb', 'kg', 'g', 'ml', 'cm', 'mm',
               'hz', 'mhz', 'ghz', 'k', 'mp', 'fps', 'v', 'mah', 'rpm'}

_UNIT_GLUE_RE = re.compile(r"(\d)\s+(" + "|".join(sorted(UNIT_TOKENS, key=len, reverse=True)) + r")\b")
_UNIT_SPEC_RE = re.compile(r"^(\d+(?:\.\d+)?)([a-z]+)$")
_BARE_NUM_RE = re.compile(r"^\d+(?:\.\d+)?$")


@lru_cache(maxsize=100_000)
def normalize_name(name: str) -> str:
    """
    Canonical comparison form: strip accents → ASCII, lowercase, collapse whitespace,
    and glue a number to a following unit so spec formatting is consistent across stores.

        "Audífono  Sony.WH-1000" -> "audifono sony.wh-1000"
        "Laptop HP 14  8 GB"     -> "laptop hp 14 8gb"
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"\s+", " ", name.lower()).strip()
    return _UNIT_GLUE_RE.sub(r"\1\2", name)


@lru_cache(maxsize=100_000)
def unit_specs(name: str) -> FrozenSet[str]:
    """
    Unit-bearing spec tokens — the hard product discriminators.

        "Laptop HP 14 8GB 256GB SSD" -> {"8gb", "256gb"}
        "Smart TV LG 50"             -> frozenset()   (no unit-bearing specs)
    """
    out = set()
    for token in normalize_name(name).split():
        m = _UNIT_SPEC_RE.match(token)
        if m and m.group(2) in UNIT_TOKENS:
            out.add(token)
    return frozenset(out)


@lru_cache(maxsize=100_000)
def bare_numbers(name: str) -> FrozenSet[str]:
    """
    Standalone numbers — softer discriminators (screen size, etc).

        "Smart TV LG 50" -> {"50"}
        "Laptop HP 14 8GB" -> {"14"}
    """
    return frozenset(t for t in normalize_name(name).split() if _BARE_NUM_RE.match(t))


def spec_conflict(a: str, b: str) -> bool:
    """
    True when two names cannot be the same product.

      - unit-bearing specs NOT subset-related → conflict. Subset semantics let one
        store omit a spec the other lists ({256gb} vs {8gb, 256gb} → same product),
        while genuine disagreements still conflict ({8gb} vs {16gb}; {8gb, 256gb} vs
        {16gb, 256gb} — each carries a value the other lacks).
      - both have bare numbers, disjoint → conflict (TV 50 vs TV 55)

    Exact-equality was too strict for cross-store matching: stores describe specs
    inconsistently (one lists RAM+storage, another only storage), which split true
    twins into separate canonicals. Subset tolerance fixes the dominant miss.
    """
    sa, sb = unit_specs(a), unit_specs(b)
    if not (sa <= sb or sb <= sa):
        return True
    ba, bb = bare_numbers(a), bare_numbers(b)
    if ba and bb and ba.isdisjoint(bb):
        return True
    return False
