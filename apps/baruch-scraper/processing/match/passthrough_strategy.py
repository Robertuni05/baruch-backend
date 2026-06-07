from processing.match.strategy import CanonicalNameStrategy


class PassthroughStrategy(CanonicalNameStrategy):
    """
    Phase 1 — use the founding product's raw name as the canonical name.

    The founding product is the spec-richest unmatched name in its cluster (the
    match loop processes richest-spec first), so it is already the most descriptive
    candidate available — the same intent as the old `_pick_representative`.
    """

    def clean(self, raw_name: str) -> str:
        return raw_name.strip()
