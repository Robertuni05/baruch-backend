import re
from typing import List
from rapidfuzz import fuzz
from processing.normalize.strategy import CanonicalizationStrategy

CLUSTER_THRESHOLD = 0.88

# Tokens that are units but contain no digits
UNIT_TOKENS = {'w', 'l', 'gb', 'tb', 'mb', 'kg', 'g', 'ml', 'cm', 'mm',
               'hz', 'mhz', 'ghz', 'k', 'mp', 'fps', 'v', 'mah', 'rpm'}


class FuzzyClusterStrategy(CanonicalizationStrategy):
    """
    Groups raw product names by fuzzy similarity (threshold 0.88).
    Each cluster produces one canonical name — the name with the most spec tokens
    (digits, measurements, model numbers). Phase 1 — swap for LLMStrategy in Phase 2.
    """

    def canonicalize(self, names: List[str]) -> List[str]:
        clusters: List[List[str]] = []

        for name in names:
            matched_cluster = self._find_cluster(name, clusters)
            if matched_cluster is not None:
                matched_cluster.append(name)
            else:
                clusters.append([name])

        return [self._pick_representative(cluster) for cluster in clusters]

    def _find_cluster(self, name: str, clusters: List[List[str]]) -> List[str] | None:
        for cluster in clusters:
            representative = cluster[0]
            score = fuzz.token_sort_ratio(name.lower(), representative.lower()) / 100.0
            if score >= CLUSTER_THRESHOLD:
                return cluster
        return None

    def _count_spec_tokens(self, name: str) -> int:
        count = 0
        for token in name.lower().split():
            if re.search(r'\d', token):   # contains a digit: 700W, 20L, 512GB, 15.6"
                count += 1
            elif token in UNIT_TOKENS:     # standalone unit: W, L, GB
                count += 1
        return count

    def _pick_representative(self, cluster: List[str]) -> str:
        return max(cluster, key=lambda name: self._count_spec_tokens(name))
