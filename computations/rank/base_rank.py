from __future__ import annotations
from abc import ABC, abstractmethod
from vbf_object import VBF

class RankComputation(ABC):
    """
    Abstract base class for rank computations on a vectorial Boolean function.
    For example, delta-rank or gamma-rank.
    """

    @abstractmethod
    def compute_rank(self, vbf: VBF) -> int:
        """
        Implement the logic for computing the rank measure on the given vectorial
        Boolean function. Returns an integer rank or None on error.
        """
        raise NotImplementedError