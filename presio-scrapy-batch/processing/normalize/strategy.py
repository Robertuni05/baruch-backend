from abc import ABC, abstractmethod
from typing import List


class CanonicalizationStrategy(ABC):

    @abstractmethod
    def canonicalize(self, names: List[str]) -> List[str]:
        """
        Receives a list of raw product names from one category.
        Returns a deduplicated list of canonical names to insert.
        """
        ...
