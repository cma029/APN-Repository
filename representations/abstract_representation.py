from abc import ABC, abstractmethod

class Representation(ABC):
    # Abstract base class for representing APN functions.

    @abstractmethod
    def to_univariate_polynomial(self, field_n, irr_poly):
        # Convert the current truth table representation into a univariate polynomial representation.
        # Returns a new Representation instance that represents the function as a univariate polynomial.
        pass

    @abstractmethod
    def to_truth_table(self, field_n, irr_poly):
        # Convert the current univariate polynomial representation into a truth table representation.
        # Returns a new Representation instance that represents the function as a truth table.
        pass