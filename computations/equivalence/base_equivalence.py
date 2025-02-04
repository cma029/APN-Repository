# base_equivalence.py
# Description: Abstract base for equivalence tests (CCZ, 3-to-1, etc.)

from abc import ABC, abstractmethod

class EquivalenceTest(ABC):
    """
    Abstract base class for equivalence tests on two APNs.
    For example, CCZ equivalence or 3-to-1 linear equivalence.
    """

    @abstractmethod
    def are_equivalent(self, apnF, apnG):
        """
        Returns True if apnF and apnG are equivalent, False otherwise.
        """
        pass