# abstract_representation.py
# Description: Abstract base class for representing APN functions.

from abc import ABC, abstractmethod

class Representation(ABC):
    # Abstract base class for representing APN functions.

    @abstractmethod
    def to_univariate_polynomial(self):
        pass

    @abstractmethod
    def to_truth_table(self, field_n, irr_poly):
        pass