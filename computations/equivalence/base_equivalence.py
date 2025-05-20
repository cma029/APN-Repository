from abc import ABC, abstractmethod

class EquivalenceTest(ABC):
    """
    Abstract base class for equivalence tests on two vectorial Boolean functions.
    For example, CCZ equivalence or 3-to-1 linear equivalence.
    """

    @abstractmethod
    def are_equivalent(self, vbf_F, vbf_G):
        """
        Returns True if vbf_F and vbf_G are equivalent, False otherwise.
        """
        pass