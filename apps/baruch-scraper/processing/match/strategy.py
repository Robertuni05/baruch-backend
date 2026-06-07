from abc import ABC, abstractmethod


class CanonicalNameStrategy(ABC):
    """
    Produces the canonical display name for a newly-discovered product identity.

    Called only when a product matches no existing canonical — so this product
    *defines* a new canonical. This is the one place a name is cleaned/normalized
    for display, which is exactly where an LLM would help in Phase 2.

    Phase 1 — PassthroughStrategy (keep the raw founding name).
    Phase 2 — swap for LLMNameStrategy / embeddings without touching the match loop.
    """

    @abstractmethod
    def clean(self, raw_name: str) -> str:
        """Receives one raw product name; returns the canonical name to store."""
        ...
