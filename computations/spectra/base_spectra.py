from __future__ import annotations
from abc import ABC, abstractmethod
from vbf_object import VBF

class SpectraComputation(ABC):
    """
    Abstract base class for spectra computations on a vectorial Boolean function,
    e.g. Ortho-Derivative Differential Spectrum, or Ortho-Derivative extended Walsh Spectrum.
    """

    @abstractmethod
    def compute_spectrum(self, vbf: VBF) -> dict | str:
        """
        Implement the logic for computing the specific spectrum on the given vectorial 
        Boolean function. Should return either a dict of {int: int} or 'non-quadratic' string.
        """
        pass