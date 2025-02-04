# base_rank.py
# Description: Abstract base for rank computations.

from abc import ABC, abstractmethod

class RankComputation(ABC):
    """
    Abstract base class for rank computations on an APN.
    For example, delta-rank or gamma-rank.
    """
    @abstractmethod
    def compute_rank(self, apn):
        """
        Implement the logic for computing the rank measure on the given APN.
        Returns an integer rank or None on error.
        """
        pass