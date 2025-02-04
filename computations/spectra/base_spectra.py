# base_spectra.py
# Description: Abstract base for spectra computations (Differential, Walsh, etc.)

from abc import ABC, abstractmethod

class SpectraComputation(ABC):
    """
    Abstract base class for spectra computations on an APN.
    For example, Ortho-Derivative Differential Spectrum, Ortho-Derivative Walsh Spectrum, etc.
    """

    @abstractmethod
    def compute_spectrum(self, apn):
        """
        Implement the logic for computing the specific spectrum on the given APN,
        and return a dict or some structure of results.
        """
        pass